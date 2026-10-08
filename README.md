# AIE · DevOps para IA — repositório dos laboratórios

Código-base dos laboratórios da disciplina **Deploy and CI/CD** do MBA AI Engineering (FIAP).
Use **Use this template → Create a new repository** (público) e trabalhe no seu.

## Qual stack em cada lab

A regra da disciplina: **AWS Academy primeiro; GitHub Actions + Azure Web Apps quando o Academy não
der; stack 100% gratuita quando nenhuma das duas se encaixar.**

| Aula | Laboratório | Onde roda | Roteiro |
| --- | --- | --- | --- |
| 1 · Cultura DevOps | CODEOWNERS: branch → teste → PR → revisão → merge protegido | GitHub + terminal/Codespace | [aula-01-codeowners](roteiros/aula-01-codeowners.md) |
| 2 · CI/CD para IA | Pipeline do classificador: lint → testes → dados → treino → **model gate** → build → deploy | GitHub Actions + **AWS Academy** (Lambda + ECR) | [aula-02](roteiros/aula-02.md) |
| 3 · GitOps | Repositório de configuração, Argo CD, *drift*, PR com policy-as-code | **Gratuito**: kind + Argo CD no Codespaces | [aula-03](roteiros/aula-03.md) |
| 4 · Rollout | Canary com aliases ponderados do Lambda, rollback automático | **AWS Academy** (Lambda) | [aula-04](roteiros/aula-04.md) |
| 5 · MLOps e LLMOps | MLflow: Model Registry com aliases e Prompt Registry | **AWS Academy** (EC2 + S3) ou **gratuito** (MLflow local) | [aula-05](roteiros/aula-05.md) |
| 6 · Capstone | **Agent gate** sobre o golden dataset + deploy do agente | GitHub Actions + Ollama (gratuito) no gate; deploy no **AWS Academy** (Lambda), com o Azure Web Apps como alternativa | [aula-06](roteiros/aula-06.md) |

O capstone também fica no AWS Academy: as credenciais expiram a cada sessão de 4h, mas os recursos
serverless (Lambda, ECR, S3) **continuam no ar** entre as sessões (só as EC2 são paradas no "End Lab").
Veja `roteiros/setup-aws-academy.md`, passo 4.

## Antes da primeira aula

1. [`roteiros/setup-aws-academy.md`](roteiros/setup-aws-academy.md) — confira quais serviços o seu Learner Lab libera
2. [`roteiros/setup-gratuito.md`](roteiros/setup-gratuito.md) — Codespaces (use este ambiente em todas as aulas)
3. [`roteiros/setup-azure.md`](roteiros/setup-azure.md) — só para a Aula 6. **Leia as regras da parceria:** a sua
   assinatura do Azure for Students só cria recursos em **algumas regiões (a sua lista é só sua)**; descubra-as
   antes. O script `azure/criar-webapp.sh` faz isso por você

## Estrutura

```text
azure/           Aula 6     — criar-webapp.sh: cria o Web App descobrindo uma região permitida
classificador/   Aulas 2 e 4 — classificador de avaliações (treino, model gate, serviço Lambda, canary)
gitops/          Aula 3     — Kustomize (base + overlays), Argo CD, policy-as-code do PR
mlops/           Aula 5     — MLflow: registro de modelo, promoção por alias, Prompt Registry
agente/          Aulas 5–6  — agente de atendimento (Quantum Commerce), golden dataset, agent gate
.github/         workflows de cada aula
roteiros/        passo a passo e setup
```

## Comandos úteis

```bash
pytest                                # todos os testes unitários (sem rede)
ruff check . && ruff format --check . # lint
python classificador/treino.py        # treina e mede
python classificador/model_gate.py artefatos/metricas.json
```

## Status dos testes

**Testado** (pytest: 36 testes; ruff; `actionlint`) e **executado no GitHub Actions**: o CI do classificador
(todas as etapas até o *build* da imagem) e o *agent gate* completo, com Ollama no runner — ambos passaram:

- classificador: treino, model gate (aprova a base saudável e reprova o `lote-novo.csv`), imagem do Lambda
  rodando em Docker e canary contra o alias local (promove o saudável, reverte o que erra 20%)
- GitOps: Kustomize, Argo CD v3.5.3 em kind sincronizando os dois ambientes a partir de um Git, promoção
  por commit (~40 s), *drift* (produção fica `OutOfSync`, staging se cura)
- MLflow 3.16: registro, promoção por alias, bloqueio do lote ruim, rollback e Prompt Registry
- agent gate: promptfoo 0.123 + Ollama (`qwen2.5:3b`): 28/36 casos, passa nos pisos de `limites.yaml`;
  o provedor `simulado` reprova. ~11 min numa máquina de 4 núcleos e **13 min no runner do GitHub (2 vCPU)**
- Codespace de 2 núcleos, criado de verdade: construção do devcontainer, `postCreate`, `pytest` (37 testes),
  `subir-cluster.sh` (183 s) com o Argo CD sincronizando os dois ambientes do GitHub, *drift* (produção
  `OutOfSync`, staging se cura) e Ollama (modelo baixado em 52 s). Isso revelou e corrigiu 3 bugs: `moby` na
  imagem Debian trixie, `zstd` ausente para o Ollama e scripts sem bit de execução.
- juiz de fidelidade (extra opcional, `qwen2.5:3b`): testado em 6 casos locais — pegou a contradição real e
  deu 2 alarmes falsos, por isso só informa por padrão (ainda não rodou no GitHub)

**Nunca executado** — precisa de conta real ou do GitHub:

- os scripts da AWS (`publicar.sh`, `trafego.sh`, `servidor-mlflow-ec2.sh`) e o uso do Bedrock
- os workflows `deploy-classificador` e `canary-classificador` (precisam dos secrets da AWS); passaram só no
  `actionlint`. Já rodaram no GitHub: o CI, o *agent gate*, o `gitops-pr` (dois PRs) e o `deploy-agente-azure`
  (deploy real num Web App F1 de uma assinatura Visual Studio, agente respondendo; sem LLM real em produção)

Ver o aviso no topo de cada roteiro de setup.
