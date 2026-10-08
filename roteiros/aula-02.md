# Aula 2 — Pipeline de CI/CD do classificador

**Onde roda:** GitHub Actions + AWS Academy (Lambda + ECR). **Tempo:** ~40 min.

O classificador rotula avaliações de produto (positiva, negativa, neutra). Você vai fazer o pipeline
de sete etapas da aula rodar de verdade.

## 1. Ver o pipeline passar

```bash
git push                                # o CI dispara sozinho
gh run watch                            # ou aba Actions → "Aula 2 · CI do classificador"
```

Cada etapa é um job; `needs` desenha a ordem. O **model gate** (`classificador/model_gate.py`)
compara o F1 do candidato com `classificador/producao.json` e com pisos por classe.

## 2. Ver o gate barrar um lote ruim

O arquivo `classificador/dados/lote-novo.csv` "parece normal" (passa no schema), mas 30% dos textos
são só emojis e a classe *neutra* caiu para ~9%. Teste na ordem do pipeline:

```bash
DADOS=classificador/dados/lote-novo.csv pytest classificador/tests/test_dados.py   # etapa 3: já barra
python classificador/treino.py --dados classificador/dados/lote-novo.csv           # etapa 4
python classificador/model_gate.py artefatos/metricas.json                          # etapa 5: reprova
```

**Perguntas:** o que barrou o lote primeiro, o teste de dados ou o gate? Qual regra é de bloqueio e
qual é só alerta (`warnings.warn` em `test_dados.py`)? Mude os limites e justifique.

## 3. Deploy no AWS Academy

Pré-requisito: `roteiros/setup-aws-academy.md` (passos 1 a 3).

```bash
gh workflow run "Aula 2 · Deploy do classificador (AWS Lambda)"
```

O workflow refaz treino e gate, publica a imagem no ECR, cria uma **versão** do Lambda, aponta o
alias `producao` e testa a URL pública. A URL aparece no resumo da execução.

## Desafio

Adicione ao `test_dados.py` uma checagem de **tamanho do texto** (média de palavras por avaliação
dentro de ±30% da base de treino) e faça o lote-novo falhar também por ela.
