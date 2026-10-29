# Estratégia de rollout — modelos e prompts

## Resumo executivo

| Cenário | Estratégia | Chegada esperada a 100% |
|---|---|---|
| Classificador de risco de fraude | *Shadow* inicial + versões imutáveis (*blue/green*) + canary progressivo controlado por alias/feature toggle | 3 a 7 dias em tráfego alto; 7 a 14 dias se os rótulos de fraude demorarem |
| Prompt do agente de atendimento | Agent gate offline + feature toggle + canary progressivo e **aderente por conversa/cliente** | 2 a 4 dias, após amostra humana suficiente em cada etapa |

Nos dois casos, “tempo” não é o único critério: cada etapa só avança depois de atingir a amostra mínima e passar por todos os guardrails.

---

## Cenário 1 — modelo clássico de risco de fraude

### 1. Estratégia escolhida

Usar a sequência **shadow → blue/green com canary progressivo (1% → 5% → 10% → 25% → 50% → 100%)**, protegida por feature toggle.

1. O candidato roda em *shadow* por 24–48 horas: recebe cópia das entradas, mas a decisão continua sendo da versão atual. Isso revela problemas de schema, latência, distribuição de scores e segmentos desconhecidos sem barrar compras reais.
2. Aprovado no *shadow*, o modelo vira uma versão imutável da Lambda. A versão estável continua sendo o ambiente “blue” e a candidata é o “green”.
3. O alias `producao` envia uma fração pequena para a candidata. Cada etapa compara candidata e estável no mesmo período.
4. Qualquer guardrail violado aponta o alias imediatamente de volta para a versão estável. A imagem e a versão anterior permanecem intactas.

Essa escolha é compatível com o código: `classificador/deploy/publicar.sh` publica versões imutáveis, `trafego.sh` usa `AdditionalVersionWeights` no alias da Lambda, e o workflow `canary-classificador.yml` promove ou reverte automaticamente.

### 2. Métricas de decisão

#### Antes de receber tráfego decisório — model gate

Aplicar os limites já definidos em `classificador/model_gate.py`:

- F1 macro do candidato ≥ 0,80;
- F1 de cada classe ≥ 0,70;
- queda de F1 macro contra a produção ≤ 0,02.

Para o caso real de fraude, também medir **recall de fraude**, **precision de fraude**, PR-AUC e métricas por segmento (valor da compra, canal, região, cliente novo/recorrente). A média global não pode esconder piora justamente no grupo mais arriscado.

#### Durante o canary — guardrails automáticos

Os três primeiros limites já são implementados por `classificador/deploy/canary_check.py`:

| Métrica | Avança | Rollback automático |
|---|---|---|
| Erros HTTP 5xx da candidata | ≤ 2% e diferença para a estável ≤ 1 ponto percentual | > 2% **ou** > 1 p.p. acima da estável |
| Latência p95 | ≤ 1,5× a p95 da estável | > 1,5× a estável |
| Distribuição das previsões por classe | diferença absoluta ≤ 15 p.p. por classe | qualquer classe difere > 15 p.p. |
| Taxa de aprovação/bloqueio | dentro de ±3 p.p. da estável, geral e por segmento crítico | desvio > 3 p.p. sem explicação prevista |
| Score médio e percentis | dentro da faixa calibrada no shadow | deslocamento fora do intervalo validado |

As duas últimas métricas devem ser adicionadas à telemetria do caso real; o classificador didático atual retorna apenas rótulo, confiança e versão.

#### Métricas de negócio com rótulo atrasado

- falso positivo: compra legítima barrada;
- falso negativo: fraude aprovada;
- taxa e valor de chargeback;
- conversão no checkout e receita legítima aprovada;
- custo de revisão manual.

Como o rótulo definitivo de fraude pode levar dias, esses indicadores não devem ser substituídos apenas por métricas técnicas. Uma piora estatisticamente relevante contra a estável **pausa a expansão**; fraude aprovada ou perda financeira acima do limite de risco definido pelo negócio dispara rollback. Antes de começar, o time deve registrar esse limite em reais e por segmento.

### 3. Plano até 100%

| Etapa | Duração mínima sugerida | Condição para avançar |
|---|---:|---|
| Shadow | 24–48 h | schema, latência, score e segmentos dentro dos limites |
| 1% | 2 h e amostra mínima | zero incidente grave e guardrails verdes |
| 5% | 4 h e amostra mínima | guardrails verdes e revisão de segmentos |
| 10% | 8–24 h | métricas operacionais e proxies de negócio verdes |
| 25% | 24 h | sem regressão por segmento |
| 50% | 24–48 h | primeiros rótulos de negócio aceitáveis |
| 100% | monitoramento reforçado por 7 dias | manter a versão anterior pronta para rollback |

Estimativa: **3–7 dias** com tráfego e feedback abundantes. Se chargeback for o único rótulo confiável, manter 50% por mais tempo e chegar a 100% em **7–14 dias**.

### 4. Justificativa em uma frase

Escolhemos shadow + canary sobre versões blue/green porque o modelo nunca viu produção e decide compras em tempo real; um corte total, rolling update simples ou teste A/B exporia clientes demais antes de comprovar segurança, enquanto o alias permite comparação simultânea e rollback imediato.

---

## Cenário 2 — prompt do agente conversacional

### 1. Estratégia escolhida

Usar **agent gate offline + feature toggle + canary progressivo aderente por conversa/cliente (5% → 20% → 50% → 100%)**, mantendo o prompt anterior versionado para rollback.

Antes do canary, rodar o golden dataset contra as duas versões. O repositório já fornece `agente/agent_gate.py`, que avalia roteamento, recuperação e resposta por categoria, impede que a média esconda uma categoria ruim e compara com `agente/baseline.json`.

O sorteio do canary deve ocorrer uma única vez no início da conversa e persistir para todo o atendimento. Misturar prompt antigo e novo no mesmo histórico torna a experiência incoerente e contamina a comparação.

### 2. Métricas de decisão

#### Gate offline

Conforme `agente/limites.yaml` e `agent_gate.py`:

- acerto de roteamento, recuperação e resposta ≥ 50% em **cada categoria** do dataset didático;
- nenhuma camada de uma categoria pode regredir mais de 34 p.p. contra a baseline;
- no projeto final, ampliar o golden dataset e recalibrar esses limites, pois hoje há apenas seis casos por categoria;
- adicionar casos específicos de reembolso elegível, reembolso inelegível, exceções, ambiguidades, tentativas de *prompt injection* e conversas com múltiplos turnos.

#### Canary online

| Métrica | Avança | Rollback automático |
|---|---|---|
| Violação da política de reembolso | nenhuma violação grave confirmada | 1 violação grave confirmada ou ≥ 2 alertas automáticos em 100 conversas |
| Recusa indevida de pedido elegível | diferença para a estável ≤ 2 p.p. | > 2 p.p. acima da estável |
| Escalonamento para humano | diferença ≤ 5 p.p. | aumento > 5 p.p. |
| Resolução/contensão sem reabertura | não piora > 3 p.p. | queda > 3 p.p. |
| CSAT | queda ≤ 0,3 ponto em escala de 1–5 | queda > 0,3 com amostra suficiente |
| Tom (“seco”), empatia e clareza | avaliação humana/juiz ≥ baseline | queda > 5 p.p. ou padrão grave confirmado |
| Erros, timeout e latência p95 | erro ≤ 2%; p95 ≤ 1,5× estável | qualquer limite excedido |
| Tokens e custo por conversa | aumento previsto e ≤ 20% | aumento > 20% sem ganho de qualidade |

Métricas ruidosas de LLM-as-judge servem como alerta, não como único bloqueio, até o juiz ser calibrado contra avaliações humanas. Violações objetivas de política podem bloquear automaticamente.

### 3. Plano até 100%

1. Golden dataset e revisão adversarial antes do deploy.
2. 5% por no mínimo 4 horas e 50 conversas completas revisáveis.
3. 20% por no mínimo 8 horas e cobertura dos principais tipos de reembolso.
4. 50% por 24 horas, incluindo um ciclo de pico de atendimento.
5. 100% em **2–4 dias**, com monitoramento reforçado por uma semana.

### 4. O que muda por ser prompt, e não modelo treinado

- A qualidade é semântica e multidimensional: uma resposta pode estar correta na política e ainda ser seca, confusa ou pouco útil.
- A saída é estocástica; por isso o gate precisa de repetições, tolerância a ruído e revisão humana calibrada.
- É necessário avaliar a conversa inteira, memória, ferramentas e RAG, não só uma entrada isolada.
- O canary precisa ser aderente à sessão/cliente; alternar prompt no meio da conversa invalida o teste.
- Prompt, modelo-base, parâmetros, documentos recuperados e ferramentas formam uma única versão observável.
- Mudanças de prompt são rápidas e não exigem retreino, mas podem causar regressões amplas, *prompt injection*, aumento de tokens e mudanças de tom que métricas clássicas não capturam.

### 5. Justificativa em uma frase

Escolhemos feature toggle + canary aderente, precedido por agent gate, porque um prompt pode regredir política, tom e comportamento de forma estocástica; troca total, rolling não aderente ou A/B puramente orientado a conversão não oferecem contenção nem coerência por conversa.

---

## Parte prática — canary real na AWS Lambda

### Caminho automatizado recomendado

Pré-requisitos: função da Aula 2 já publicada, environment `producao` no GitHub e credenciais temporárias do AWS Academy configuradas conforme `roteiros/setup-aws-academy.md`.

Canary saudável com 10% de tráfego e 300 chamadas de análise:

```bash
gh workflow run "Aula 4 · Canary do classificador (AWS Lambda)" \
  -f peso=0.1 -f erro_simulado=0 -f requisicoes=300
gh run watch
```

Teste de rollback, injetando 20% de erro somente na candidata:

```bash
gh workflow run "Aula 4 · Canary do classificador (AWS Lambda)" \
  -f peso=0.1 -f erro_simulado=0.2 -f requisicoes=300
gh run watch
```

Resultado esperado:

- execução saudável: o `canary_check.py` termina com código 0 e o workflow aponta `producao` 100% para a candidata;
- execução ruim: o verificador termina com código 1, o workflow restaura 100% na versão estável e finaliza vermelho de propósito.

### Execução manual para demonstrar cada etapa

Executar na raiz de `aula1`, depois de treinar o modelo:

```bash
python classificador/treino.py
ESTAVEL=$(aws lambda get-alias --function-name classificador-avaliacoes \
  --name producao --query FunctionVersion --output text)
CANDIDATA=$(classificador/deploy/publicar.sh | tail -1)
URL=$(classificador/deploy/trafego.sh "$ESTAVEL" "$CANDIDATA" 0.1)
python classificador/deploy/canary_check.py "$URL" --requisicoes 300
```

Se a análise passar:

```bash
classificador/deploy/trafego.sh "$CANDIDATA"
```

Se falhar:

```bash
classificador/deploy/trafego.sh "$ESTAVEL"
```

Manter o peso abaixo de 50%, pois o verificador didático identifica como estável a versão que recebeu mais requisições.

### Observação estatística importante

Com 300 requisições e peso de 10%, espera-se apenas cerca de 30 respostas da candidata. Isso é suficiente para demonstrar uma falha artificial de 20%, mas **não** comprova com confiança uma meta de erro de 2%.

Para ter 95% de chance de observar pelo menos um erro quando a taxa real é 2%, são necessárias aproximadamente 149 requisições da candidata. Com 10% do tráfego, isso significa cerca de 1.490 requisições totais; a 15 requisições por minuto, aproximadamente **99 minutos**. Em produção, o avanço deve usar tamanho de amostra/intervalo de confiança, não apenas uma janela fixa de tempo.

---

## Decisão para compartilhar em 1 minuto

> A decisão mais importante é separar “deploy” de “liberação de tráfego”. Publicamos a candidata como versão imutável, mas só a expomos gradualmente por um alias. No modelo de fraude, começamos em shadow e o rollback é acionado por erro, latência, mudança de distribuição e impacto em aprovação/fraude. No prompt, acrescentamos golden dataset, avaliação por categoria e afinidade por conversa, porque qualidade e tom são semânticos e estocásticos. Assim, uma versão melhor offline nunca recebe 100% do tráfego antes de provar segurança em produção.
