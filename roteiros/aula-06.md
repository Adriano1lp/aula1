# Aula 6 — Capstone: o agent gate

**Onde roda:** GitHub Actions + Ollama (gratuito) + Azure Web Apps (deploy). **Tempo:** laboratório de 90 min.

Missão do enunciado: *"configurar o pipeline que testa o comportamento dos agentes automaticamente
antes de cada atualização no site da Quantum"*. Aqui o agente é uma versão mínima (roteador + RAG +
especialista); no capstone, **troque pelo multiagente do seu grupo** mantendo `atender()`.

## 1. Entender as três camadas

`agente/golden/chamados.csv` tem 36 chamados anotados (6 por categoria). Para cada um o promptfoo mede:

| Camada | Pergunta | Como mede (`promptfooconfig.yaml`) |
|---|---|---|
| Roteamento | o chamado foi para a categoria certa? | categoria == anotada |
| Recuperação | o documento de política certo foi achado? | documento == anotado |
| Resposta | a resposta cita o fato da política (prazo, valor)? | contém o trecho anotado |

Tudo determinístico — sem LLM-as-judge — para rodar em todo PR sem custo.

## 2. Rodar o gate

```bash
ollama serve > /dev/null 2>&1 & ollama pull qwen2.5:3b
npx -y promptfoo@0.123.1 eval -c agente/promptfooconfig.yaml -o resultado-eval.json --no-progress-bar
python agente/agent_gate.py resultado-eval.json
```

~13 min em 2 núcleos (medido no runner do GitHub). O resultado é uma tabela **por categoria** e por camada. Os critérios estão em
`agente/limites.yaml`: pisos por camada e tolerância de ruído.

## 3. A regra que o enunciado pede

*"O que acontece quando uma categoria piora mesmo que a média geral melhore?"*

```bash
python agente/agent_gate.py resultado-eval.json --salvar-baseline   # fixa a baseline atual
```

Agora piore **só** `fraude_vendedor` (por exemplo, apague a linha dessa categoria no `roteador.txt`, o que
derruba os 6 casos dela) e melhore outra categoria. Uma piora pequena (1 ou 2 casos) fica dentro da
tolerância de ruído de propósito. Rode o eval de novo: o gate reprova pela **regressão da categoria**, mesmo com a média igual
ou melhor. É a regra 2 do cabeçalho de `agent_gate.py`.

## 4. No CI e o override

Abra um PR mexendo em `agente/prompts/especialista.txt`. O workflow **Aula 6 · Agent gate** roda o
eval no runner (com Ollama) e escreve a tabela no resumo. Para liberar uma exceção, ponha o rótulo
`override-agent-gate` no PR — a exceção fica registrada no resumo, com o PR e o autor.

## 5. Extra opcional: o juiz de fidelidade

O gate acima confere se o fato da política foi *citado*; não vê a resposta que o *contradiz*. O extra
`agente/promptfooconfig-juiz.yaml` põe um LLM-as-judge para isso:

```bash
npx -y promptfoo@0.123.1 eval -c agente/promptfooconfig-juiz.yaml -o resultado-juiz.json --no-progress-bar
python agente/juiz_resumo.py resultado-juiz.json
```

No workflow: *Actions → Aula 6 · Agent gate → Run workflow → com_juiz*. Testado com o juiz padrão
(`qwen2.5:3b`) em 6 casos: pegou a contradição real (promessa de reembolso onde a política diz que
não há) e deu 2 alarmes falsos. Por isso ele **só informa** por padrão; para bloquear, use um modelo
maior (`LLM_JUIZ_BASE_URL`, `LLM_JUIZ_MODELO`, secret `LLM_JUIZ_API_KEY`) e `JUIZ_BLOQUEIA=true`.

## 6. Deploy (AWS Academy por padrão)

Com as credenciais do Learner Lab nos secrets (`roteiros/setup-aws-academy.md`, passo 3), faça merge na
`main` (ou *Actions → Aula 6 · Deploy do agente (AWS Lambda) → Run workflow*): o workflow chama o gate e só
então publica o agente numa função **Lambda** com URL pública, que **continua no ar entre as sessões** do lab.

```bash
curl https://<sua-function-url>/
curl -X POST https://<sua-function-url>/chamado -H 'content-type: application/json' \
  -d '{"texto": "Meu pedido está atrasado há 6 dias úteis"}'
```

LLM em produção: variável `AGENTE_LLM_PROVEDOR` (`bedrock`, `openai` ou `simulado`, o padrão); veja
`roteiros/setup-aws-academy.md`, passo 4. **Alternativa:** o Azure Web Apps (`roteiros/setup-azure.md`),
pelo workflow *Aula 6 · Deploy do agente (Azure Web Apps)*, que roda só manualmente.

## O que entregar (vira o trabalho final)

Este repositório (esteira + golden dataset + gate funcionando) é o **entregável 1 e 2**. Os
entregáveis 3 a 6 estão no documento: `gitops/` (repositório de configuração), estratégia de rollout,
book de métricas e pitch.
