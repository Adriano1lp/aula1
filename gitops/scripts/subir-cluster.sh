#!/usr/bin/env bash
# Sobe um Kubernetes local (kind) com o Argo CD e registra os dois ambientes.
# Pensado para o GitHub Codespaces deste repositório (já vem com kind/kubectl),
# mas roda em qualquer máquina com Docker.
#
#   gitops/scripts/subir-cluster.sh
#
# O repositório precisa ser PÚBLICO para o Argo CD ler sem credenciais.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

ARGOCD_VERSAO="${ARGOCD_VERSAO:-v3.5.3}"
REPO_URL="${REPO_URL:-$(git remote get-url origin | sed -E 's#git@github.com:#https://github.com/#')}"

kind get clusters 2>/dev/null | grep -qx aie || kind create cluster --name aie --wait 120s

kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n argocd --server-side --force-conflicts \
  -f "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSAO}/manifests/install.yaml" >/dev/null
echo "Esperando o Argo CD subir (1–3 min)..."
kubectl -n argocd rollout status deploy/argocd-server --timeout=300s
kubectl -n argocd rollout status deploy/argocd-repo-server --timeout=300s
# Polling a cada 30s, sem jitter (o padrão é 2 min + até 1 min de jitter) para o laboratório não esperar
kubectl -n argocd patch configmap argocd-cm --type merge \
  -p '{"data":{"timeout.reconciliation":"30s","timeout.reconciliation.jitter":"0s"}}'
kubectl -n argocd rollout restart statefulset/argocd-application-controller deploy/argocd-repo-server >/dev/null
kubectl -n argocd rollout status statefulset/argocd-application-controller --timeout=180s >/dev/null
kubectl -n argocd rollout status deploy/argocd-repo-server --timeout=180s >/dev/null

for app in gitops/apps/*.yaml; do
  sed "s#REPO_URL#${REPO_URL}#" "$app" | kubectl apply -f -
done

SENHA=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)
cat <<FIM

✅ Pronto. Repositório observado: ${REPO_URL}

Painel do Argo CD:
  kubectl -n argocd port-forward svc/argocd-server 8443:443
  → abra https://localhost:8443  (usuário: admin · senha: ${SENHA})

Ver a configuração ativa em cada ambiente:
  gitops/scripts/consultar.sh
FIM
