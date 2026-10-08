# Aula 4 — Canary com aliases ponderados do Lambda

**Onde roda:** AWS Academy (Lambda). **Tempo:** ~30 min.

Pré-requisito: o deploy da Aula 2 já feito (a função `classificador-avaliacoes` e o alias `producao`).

## 1. Canary saudável

```bash
gh workflow run "Aula 4 · Canary do classificador (AWS Lambda)" -f peso=0.1
gh run watch
```

O workflow publica uma versão candidata, manda 10% do tráfego, mede (`canary_check.py`) e **promove**
(100%) ou faz **rollback** (0%) sozinho. Os critérios estão no cabeçalho do `canary_check.py`.

## 2. Canary com falha: ver o rollback acontecer

```bash
gh workflow run "Aula 4 · Canary do classificador (AWS Lambda)" -f erro_simulado=0.2
```

A versão candidata falha em 20% das requisições (`ERRO_SIMULADO`). O canary vê a taxa de erro
acima de 2% e o workflow termina em **rollback** (vermelho de propósito).

## 3. Manualmente, para entender cada passo

```bash
V=$(classificador/deploy/publicar.sh | tail -1)        # nova versão, ainda sem tráfego
URL=$(classificador/deploy/trafego.sh 1 "$V" 0.2)      # alias: 80% na versão 1, 20% na nova
python classificador/deploy/canary_check.py "$URL" --requisicoes 300
classificador/deploy/trafego.sh "$V"                   # promover   (ou "1" para voltar)
```

A resposta traz `"versao"`: é assim que se vê qual versão atendeu.

## Perguntas

Com ~15 requisições por minuto, quanto tempo para ter evidência de 2% de erro com 10% de tráfego?
O canary comparou distribuição das previsões, não só erro — por quê isso importa para modelo, e não só
para serviço? O que mudaria se o que estivesse em canary fosse um **prompt**?
