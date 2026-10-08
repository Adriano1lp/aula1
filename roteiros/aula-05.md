# Aula 5 — MLflow: Model Registry e Prompt Registry

**Onde roda:** AWS Academy (EC2 + S3) ou gratuito (MLflow local). **Tempo:** ~40 min.

## 1. Onde fica o MLflow

```bash
# Opção A — AWS Academy (~3 min; confira o aviso no topo do script)
mlops/servidor-mlflow-ec2.sh
export MLFLOW_TRACKING_URI=http://<ip-impresso>:5000

# Opção B — gratuito: sem variável nenhuma, grava em mlflow.db
mlflow server --backend-store-uri sqlite:///mlflow.db --port 5000   # opcional, para ver a interface
```

## 2. Registrar e promover um modelo

```bash
python mlops/registrar_modelo.py        # versão 1 → alias @candidato
python mlops/promover.py                # passa no model gate? vira @producao
```

Os **aliases** (`@candidato`, `@producao`, `@anterior`) substituem os antigos *stages* do MLflow.

## 3. O lote ruim não vira produção

```bash
python mlops/registrar_modelo.py --dados classificador/dados/lote-novo.csv
python mlops/promover.py                # ❌ reprova: o gate é o mesmo da Aula 2
```

Abra a interface e compare os runs: parâmetros, métricas e as *tags* de **linhagem**
(`git_commit`, `dados_sha256`). Dado o `dados_sha256` de um modelo em produção, quais dados o geraram?

## 4. Rollback pelo registry

```bash
python mlops/registrar_modelo.py --C 8 && python mlops/promover.py     # versão nova em produção
python mlops/promover.py --rollback                                    # volta para @anterior
```

## 5. Prompts: o Prompt Registry (LLMOps)

```bash
python mlops/registrar_prompts.py -m "versão inicial"           # prompts do agente, com o commit
python mlops/registrar_prompts.py --alias producao --versao 1
PROMPT_FONTE=mlflow PROMPT_ALIAS=producao LLM_PROVEDOR=simulado \
  python agente/atendimento.py "Comprei um perfume que parece falsificado"
```

O agente carrega o prompt **pelo alias**, sem deploy de código. Edite `agente/prompts/especialista.txt`,
registre a versão 2 e mude só o alias do `staging` — é o mesmo desenho de modelo, agora para prompt.

## Perguntas

O Git ou o registry é a fonte da verdade do texto do prompt? (No repositório: o Git, e o registry
guarda versão + linhagem + métricas.) Quem pode mover o alias `producao`? O rollback do registry basta,
ou precisa agir também no GitOps e no rollout (Aulas 3 e 4)?
