# Entrega — Aulas 1, 2 e 3

## Aula 1 — cultura DevOps, CODEOWNERS e branch protegida

### Implementação

- `.github/CODEOWNERS` solicita `@biapretz-dotcom` para qualquer mudança e mantém regras explícitas para produção e prompts.
- `classificador/tests/test_texto.py` cobre o caso `limpar("") == ""`.
- O teste local é executado com `pytest classificador/tests/test_texto.py -v`.

O usuário em `CODEOWNERS` deve ser trocado caso `@biapretz-dotcom` não seja a pessoa revisora da dupla.

### Resposta obrigatória

**Revisor solicitado** é uma indicação automática de quem deve analisar a mudança. Sozinho, isso não impede merge. **Merge bloqueado** é uma regra de proteção da branch/ruleset que exige PR, aprovação e aprovação do code owner antes de liberar o botão de merge. Portanto, CODEOWNERS define responsabilidade; a proteção da `main` transforma essa responsabilidade em gate obrigatório.

### Evidências a anexar ao PR

1. Link do repositório e do PR.
2. Saída do pytest.
3. Tela mostrando `@biapretz-dotcom` como revisão solicitada.
4. Tela do ruleset da `main` com PR obrigatório, uma aprovação, code owner obrigatório, bloqueio de push direto/exclusão e sem bypass.
5. Comentário concreto da pessoa revisora, resposta da pessoa autora e aprovação final.

Essas evidências dependem do GitHub e de uma segunda pessoa; não podem ser produzidas honestamente apenas no workspace local.

---

## Aula 2 — CI/CD do classificador

### Fluxo das sete etapas

O workflow `.github/workflows/ci-classificador.yml` executa:

1. lint;
2. testes unitários;
3. testes de dados;
4. treino;
5. model gate;
6. build da imagem;
7. deploy, realizado separadamente pelo workflow `deploy-classificador.yml` após os gates.

### Respostas das perguntas

**O que barra primeiro o lote novo?** O teste de dados, etapa 3, antes do treino e do model gate. O lote excede o máximo de 10% de textos compostos apenas por emojis e também viola regras de distribuição. Com o desafio implementado, ele ainda viola o tamanho médio da classe neutra.

**Qual regra bloqueia e qual apenas alerta?** Todo `assert` bloqueia o pipeline. Em `test_distribuicao_das_classes`, desvio maior que 5 pontos percentuais emite `warnings.warn`, mas o job continua; desvio maior que 10 p.p. falha no `assert` e bloqueia.

**Limites escolhidos e justificativa:**

- 5 p.p. para alerta de distribuição: antecipa investigação sem interromper qualquer oscilação pequena;
- 10 p.p. para bloqueio de distribuição: mudança grande o bastante para alterar o aprendizado por classe;
- 10% de textos somente com emoji: acima disso o lote tem pouco sinal textual para o TF-IDF;
- ±30% na média de palavras **por classe**: detecta mudança de densidade textual sem deixar a mistura das classes esconder uma regressão.

O teste de tamanho foi feito por classe porque a média global do lote novo é 8,05 palavras contra 11,15 da referência, queda de 27,8% — ainda dentro do limite pedido. Na classe neutra, a média cai de 12,20 para 8,19, queda de aproximadamente 32,8%, e o gate falha corretamente.

### Model gate

O candidato só avança se:

- F1 macro ≥ 0,80;
- F1 de cada classe ≥ 0,70;
- queda de F1 macro contra a produção ≤ 0,02.

Isso impede que uma média aparentemente boa esconda uma classe inutilizável.

### Comandos de validação

No PowerShell, a partir da pasta `aula1`:

```powershell
pytest classificador/tests/test_dados.py -v
$env:DADOS = "classificador/dados/lote-novo.csv"
pytest classificador/tests/test_dados.py -v
Remove-Item Env:DADOS
python classificador/treino.py
python classificador/model_gate.py artefatos/metricas.json
```

Resultado esperado: a base padrão passa; o lote novo reprova primeiro nos testes de dados. Se for usado no treino mesmo assim, o model gate também deve reprovar.

O deploy real exige credenciais temporárias do AWS Academy e é disparado por:

```bash
gh workflow run "Aula 2 · Deploy do classificador (AWS Lambda)"
```

---

## Aula 3 — GitOps com Argo CD

### Estado declarado após a promoção

- Staging e produção usam `PROMPT_VERSAO=v12`.
- O modelo comum aos ambientes é `openai/gpt-4.1-mini`.
- O índice RAG é `politicas-2026-09`.
- Produção mantém três réplicas.
- Staging e produção usam `selfHeal: true`.

Modelo, prompt e RAG estão declarados em `gitops/base/agente-suporte/inference-config.env`; diferenças por ambiente ficam nos respectivos `gitops/overlays/*/inference-config.env`. Réplicas de produção ficam em `gitops/overlays/producao/escala.patch.yaml`.

### Política escolhida para drift

Escolhemos **self-heal habilitado em produção**, porque o Git deve ser a única fonte da verdade: uma alteração manual não revisada pode mudar capacidade ou comportamento silenciosamente. O Argo CD deve restaurar o estado aprovado. Em uma emergência, usa-se um PR/commit de correção ou um procedimento de break-glass auditável, em vez de manter drift indefinidamente.

### Segredos

A chave do LLM não deve existir em ConfigMap nem no Git. Em ambiente real, ela fica em AWS Secrets Manager, External Secrets/Vault ou Kubernetes Secret criado por uma integração segura. O Deployment referencia o segredo; o valor nunca aparece no overlay. A policy-as-code rejeita nomes terminados em `KEY`, `TOKEN`, `SECRET`, `SENHA` ou `PASSWORD` dentro da ConfigMap.

### Quem pode mudar produção

Tecnicamente, qualquer pessoa com escrita poderia propor uma alteração, mas ninguém deve promovê-la sem revisão. `CODEOWNERS` exige o responsável de produção, e o ruleset da `main` deve bloquear merge e push direto até aprovação e checks verdes. Depois do merge, somente o Argo CD reconcilia o cluster.

### Teste da policy-as-code

O teste destrutivo do enunciado não deve ficar commitado. Em uma branch temporária, trocar `PROMPT_VERSAO` por `latest` e incluir `OPENAI_API_KEY=sk-123` produz dois motivos de reprovação:

```text
PROMPT_VERSAO precisa de versão explícita (está 'latest')
'OPENAI_API_KEY' parece segredo em texto claro — use um Secret externo
```

Depois da demonstração, descartar a alteração insegura.

### Rollback e tempo de recuperação

O rollback é `git revert <commit-da-promocao>` seguido de push/merge por PR. Com o polling de 30 segundos configurado em `subir-cluster.sh`, espera-se retorno da produção em aproximadamente **30–60 segundos após o merge**, mais o tempo de atualização/saúde dos pods. O tempo total percebido também inclui revisão e merge do PR.

### Comandos de validação

```bash
kubectl kustomize gitops/overlays/staging
kubectl kustomize gitops/overlays/producao
python gitops/politicas/verificar.py
gitops/scripts/subir-cluster.sh
gitops/scripts/consultar.sh
```

Os três primeiros podem ser executados sem Argo CD se `kubectl` estiver instalado. Os dois últimos exigem Docker, kind, acesso à internet e repositório público na branch `main`.

---

## Checklist final de entrega

- [x] CODEOWNERS configurado no repositório.
- [x] Teste de texto vazio implementado.
- [x] Teste de tamanho médio por classe implementado.
- [x] Promoção declarativa do prompt `v12` para produção.
- [x] Política de self-heal de produção escolhida e configurada.
- [x] Respostas das Aulas 1, 2 e 3 documentadas.
- [ ] PR, revisão humana e ruleset comprovados no GitHub.
- [ ] Workflow de deploy comprovado com credenciais do AWS Academy.
- [ ] Reconciliação e drift comprovados em cluster kind/Argo CD.
