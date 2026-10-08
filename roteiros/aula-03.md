# Aula 3 — Repositório GitOps com Argo CD

**Onde roda:** Codespaces (gratuito). **Tempo:** ~40 min.

Pré-requisito: o repositório precisa ser **público** e o código na branch `main`.

## 1. Subir o cluster

```bash
gitops/scripts/subir-cluster.sh
gitops/scripts/consultar.sh
```

Staging roda o prompt `v12` e produção o `v11`: `diff` dos dois overlays responde "o que ainda não foi promovido":

```bash
diff gitops/overlays/staging/inference-config.env gitops/overlays/producao/inference-config.env
```

## 2. Promover pelo Git

Mude `PROMPT_VERSAO=v12` em `gitops/overlays/producao/inference-config.env`, abra um **Pull Request**
e veja o workflow *Aula 3 · Checks do PR* (`gitops/politicas/verificar.py`). Depois do merge, em menos de 1 min:

```bash
gitops/scripts/consultar.sh      # produção agora responde prompt=v12
```

## 3. Provocar *drift*

```bash
kubectl -n agente-producao scale deploy/agente-suporte --replicas=5
gitops/scripts/consultar.sh      # produção fica OutOfSync; o Git ainda diz 3 réplicas
```

Produção tem `selfHeal: false` (só alerta). Troque para `true` em `gitops/apps/agente-producao.yaml`,
faça o merge e repita o drift. **Qual política vocês escolhem para produção, e por quê?**

## 4. Quebrar a política de propósito

Em um PR, troque `PROMPT_VERSAO=v12` por `latest` e adicione `OPENAI_API_KEY=sk-123`. O check do PR
deve reprovar com os dois motivos. Rollback do prompt: `git revert` do merge — em quanto tempo
produção volta?

## Perguntas dos critérios da aula

Onde está declarado qual modelo e prompt rodam em cada ambiente? Onde fica a chave do LLM sem estar
em texto claro? Quem muda produção sem revisão? (Ative `CODEOWNERS` e a proteção da `main`.)
