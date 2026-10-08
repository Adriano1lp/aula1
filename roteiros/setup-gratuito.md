# Setup — stack 100% gratuita (Codespaces + kind + Ollama)

Usada onde nem o AWS Academy nem o Azure se encaixam: **Aula 3 (GitOps)**, o **agent gate**
(Aulas 5 e 6) e o **MLflow local** quando o Learner Lab estiver indisponível.

## Codespaces

1. No GitHub, **Use this template → Create a new repository** (deixe **público**: o Argo CD lê o Git sem credencial).
2. **Code → Codespaces → Create codespace on main**. A primeira criação leva ~8 min (medido num Codespace
   de 2 núcleos). **Atenção:** o Codespace aparece como disponível *antes* do `.devcontainer/instalar.sh`
   terminar (dependências Python, kind e Ollama, ~2 min a mais). Espere o terminal mostrar
   `Pronto. Próximos passos: roteiros/README.md` antes de rodar qualquer comando.
3. A conta gratuita dá **120 horas-core por mês**: o `.devcontainer` pede **2 núcleos**, ou seja, ~60 h.
   Se trocar para a máquina de **4 núcleos** (menu do Codespace → *Change machine type*), o eval do
   agent gate e o cluster rodam mais rápido, mas as horas acabam na metade do tempo. **Pare o
   Codespace** ao terminar (menu do canto inferior esquerdo) — ele não pára sozinho de imediato.

## Aula 3 — kind + Argo CD

```bash
gitops/scripts/subir-cluster.sh          # ~3 min: cluster kind, Argo CD, os dois ambientes
gitops/scripts/consultar.sh              # o que roda em staging e produção, e o estado do Argo CD
kubectl -n argocd port-forward svc/argocd-server 8443:443    # painel em https://localhost:8443
```

Para ver o *drift*: `kubectl -n agente-producao scale deploy/agente-suporte --replicas=5` e
acompanhe o Argo CD marcar `OutOfSync` (produção tem `selfHeal: false`; staging desfaz sozinho).

## Agent gate local (Ollama)

```bash
ollama serve > /dev/null 2>&1 &
ollama pull qwen2.5:3b                    # ~2 GB, uma vez
npx -y promptfoo@0.123.1 eval -c agente/promptfooconfig.yaml -o resultado-eval.json --no-progress-bar
python agente/agent_gate.py resultado-eval.json
```

Leva **~13 minutos** em 2 núcleos (36 casos × 2 chamadas; medido no GitHub Actions) e ~11 em 4. Para iterar rápido, use o
provedor simulado — ele **não** mede o seu prompt, só valida a esteira:
`LLM_PROVEDOR=simulado npx promptfoo eval ...`.

## MLflow local (sem AWS)

```bash
python mlops/registrar_modelo.py          # grava em mlflow.db
mlflow server --backend-store-uri sqlite:///mlflow.db --port 5000   # interface em :5000
```

## O que **não** usar: GitHub Models

O GitHub Models (`models.github.ai`) foi **aposentado em 30/07/2026**. O endpoint ainda responde
`200 OK` com o texto "OK", então o SDK da OpenAI falha com `'str' object has no attribute 'choices'`.
Documentação antiga (inclusive a do promptfoo) ainda o cita como ativo.
