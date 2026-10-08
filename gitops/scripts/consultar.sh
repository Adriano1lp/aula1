#!/usr/bin/env bash
# Mostra o que está rodando em cada ambiente e o estado de sincronia no Argo CD.
set -euo pipefail
for ns in agente-staging agente-producao; do
  printf '%-16s ' "$ns"
  kubectl get --raw "/api/v1/namespaces/$ns/services/agente-suporte:80/proxy/" 2>/dev/null \
    || echo "(ainda não sincronizado)"
done
echo
kubectl -n argocd get applications \
  -o custom-columns='APP:.metadata.name,SYNC:.status.sync.status,SAÚDE:.status.health.status,REVISÃO:.status.sync.revision'
