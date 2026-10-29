# Passo a passo completo — Aulas 1, 2 e 3

Este roteiro parte de uma cópia pública do repositório no GitHub. Use o **Codespace** do projeto: ele já instala Python 3.12, dependências, GitHub CLI, AWS CLI, Docker, kind e kubectl. Os comandos abaixo, salvo indicação contrária, são executados no terminal do Codespace, na raiz do repositório.

> Nunca coloque credenciais AWS, tokens ou chaves de LLM em commits, prints ou mensagens do grupo.

## 0. Preparação única

### 0.1 Criar o repositório da dupla

1. No repositório fornecido pelo professor, clique em **Use this template → Create a new repository**.
2. Escolha um nome, deixe como **Public** e crie o repositório.
3. Abra **Settings → Collaborators → Add people** e adicione a outra pessoa da dupla.
4. Vá a **Code → Codespaces → Create codespace on main**.
5. Espere o terminal mostrar a mensagem de instalação concluída. A primeira preparação pode levar cerca de 10 minutos.

Confira:

```bash
pwd
git remote -v
python --version
pytest --version
gh auth status
docker version
kubectl version --client
```

Se `gh auth status` indicar que não há login:

```bash
gh auth login
```

Escolha GitHub.com, HTTPS e autenticação pelo navegador.

### 0.2 Identificar a pessoa revisora

Troque `@biapretz-dotcom` em `.github/CODEOWNERS` pelo usuário real da pessoa que revisará os PRs. O usuário precisa ter acesso ao repositório.

---

# Aula 1 — branch, teste, Pull Request, CODEOWNERS e proteção

## 1. Publicar o CODEOWNERS primeiro

O GitHub lê o `CODEOWNERS` da branch base. Por isso, o caminho mais confiável é incorporá-lo antes do PR usado para provar o gate.

```bash
git switch main
git pull --ff-only
git switch -c config/codeowners
git add .github/CODEOWNERS
git commit -m "chore: define code owners da dupla"
git push -u origin config/codeowners
gh pr create --base main --head config/codeowners \
  --title "chore: configurar CODEOWNERS" \
  --body "Define revisão responsável para todas as mudanças e explicita as áreas de prompts e produção."
```

Abra o link mostrado, peça revisão e faça o merge. Se este for o primeiro CODEOWNERS, a solicitação automática pode não ocorrer ainda; isso será comprovado no próximo PR.

Depois:

```bash
git switch main
git pull --ff-only
```

## 2. Proteger a `main`

No GitHub:

1. Abra **Settings → Rules → Rulesets → New ruleset → New branch ruleset**.
2. Nome: `protecao-main`.
3. Enforcement status: **Active**.
4. Target branches: inclua `main` ou **Default branch**.
5. Ative:
   - Restrict deletions;
   - Block force pushes;
   - Require a pull request before merging;
   - Required approvals: `1`;
   - Require review from Code Owners;
   - Dismiss stale approvals when new commits are pushed, se disponível;
   - Require conversation resolution before merging.
6. Não adicione bypass. Se houver a opção **Do not allow bypassing**, habilite-a.
7. Salve o ruleset.

Em repositório de organização, talvez só o administrador consiga criar a regra. Registre essa limitação se a opção não aparecer.

## 3. Criar a mudança real e executar o teste

O arquivo preparado neste workspace já inclui `test_texto_vazio_continua_vazio`. Em uma cópia ainda não alterada, acrescente ao final de `classificador/tests/test_texto.py`:

```python
def test_texto_vazio_continua_vazio():
    assert limpar("") == ""
```

Crie a branch e valide:

```bash
git switch -c lab/aula1-texto-vazio
pytest classificador/tests/test_texto.py -v
ruff check classificador
ruff format --check classificador
```

Resultado esperado: todos os testes passam, incluindo `test_texto_vazio_continua_vazio`.

Faça commit e abra o PR:

```bash
git add classificador/tests/test_texto.py
git commit -m "test: cobrir texto vazio"
git push -u origin lab/aula1-texto-vazio
gh pr create --base main --head lab/aula1-texto-vazio \
  --title "test: cobrir normalização de texto vazio" \
  --body $'## Evidências\n\n- `pytest classificador/tests/test_texto.py -v`: passou\n- CODEOWNERS: `.github/CODEOWNERS`\n\nO merge deve permanecer bloqueado até a aprovação do code owner.'
```

## 4. Comprovar o gate

1. Abra o PR e confirme que a pessoa de `CODEOWNERS` aparece em **Reviewers**.
2. Antes da aprovação, tire uma captura do merge bloqueado.
3. A pessoa revisora deve escrever uma melhoria concreta, por exemplo: “Inclua o nome do comportamento no teste para deixar a intenção explícita”.
4. A pessoa autora responde ao comentário ou envia ajuste.
5. A pessoa revisora aprova.
6. Confirme que o merge foi liberado e faça o merge.
7. Tire capturas da revisão e do ruleset.

Resposta para entregar:

> Revisor solicitado indica quem deve revisar, mas não bloqueia o merge sozinho. CODEOWNERS define responsabilidade; o ruleset da `main`, com aprovação obrigatória do code owner, transforma essa responsabilidade em um gate de merge.

Finalize:

```bash
git switch main
git pull --ff-only
```

---

# Aula 2 — CI/CD, testes de dados, model gate e AWS Lambda

## 5. Implementar o desafio do tamanho dos textos

O workspace já contém o teste em `classificador/tests/test_dados.py`. Ele compara a média de palavras por classe com a base de referência e aceita variação máxima de ±30%.

Crie a branch:

```bash
git switch main
git pull --ff-only
git switch -c lab/aula2-tamanho-texto
```

Valide a base saudável:

```bash
pytest classificador/tests/test_dados.py -v
```

Ela deve passar. Agora valide o lote novo:

```bash
DADOS=classificador/dados/lote-novo.csv \
  pytest classificador/tests/test_dados.py -v
```

Essa execução **deve falhar**. Entre os motivos esperados:

- mais de 10% dos textos contêm somente emojis;
- drift de distribuição de classe;
- classe neutra com média aproximada de 8,2 palavras contra 12,2 na referência, queda de cerca de 32,8%, acima do limite de 30%.

O erro dessa segunda execução é evidência do gate funcionando, não defeito no código.

## 6. Treinar e testar o model gate

Modelo saudável:

```bash
python classificador/treino.py
python classificador/model_gate.py artefatos/metricas.json
```

O gate deve aprovar se F1 macro ≥ 0,80, cada classe ≥ 0,70 e a queda contra produção ≤ 0,02.

Agora force a passagem pelo treino usando o lote ruim, apesar do teste de dados:

```bash
python classificador/treino.py --dados classificador/dados/lote-novo.csv
python classificador/model_gate.py artefatos/metricas.json
```

O segundo comando deve terminar com código diferente de zero e explicar a regressão. Isso comprova defesa em profundidade: teste de dados e model gate detectam problemas diferentes.

Restaure o artefato saudável antes de continuar:

```bash
python classificador/treino.py
python classificador/model_gate.py artefatos/metricas.json
```

## 7. Abrir o PR e acompanhar o CI

```bash
git add classificador/tests/test_dados.py
git commit -m "test: validar tamanho médio dos textos por classe"
git push -u origin lab/aula2-tamanho-texto
gh pr create --base main --head lab/aula2-tamanho-texto \
  --title "test: adicionar gate de tamanho dos textos" \
  --body $'## Decisão\n\nUsamos ±30% por classe para impedir que a média global esconda regressão em uma classe. A base padrão passa e o lote novo reprova.'
gh pr checks --watch
```

Peça revisão, faça o merge e atualize a cópia:

```bash
git switch main
git pull --ff-only
```

No GitHub, abra **Actions → Aula 2 · CI do classificador** e salve a tela do grafo com lint, testes, treino/gate e build verdes.

## 8. Preparar o AWS Academy

1. Abra o curso **AWS Academy Learner Lab**.
2. Clique em **Start Lab** e espere o indicador ficar verde.
3. Abra **AWS Details → AWS CLI → Show**.
4. Copie os três valores temporários: access key, secret key e session token.

No Codespace, configure sem commitar:

```bash
mkdir -p ~/.aws
aws configure set aws_access_key_id "COLE_A_ACCESS_KEY"
aws configure set aws_secret_access_key "COLE_A_SECRET_KEY"
aws configure set aws_session_token "COLE_O_SESSION_TOKEN"
aws configure set region us-east-1
aws sts get-caller-identity
```

O último comando deve mostrar a conta e a `LabRole`. Se aparecer `ExpiredToken`, reinicie o lab e copie novas credenciais.

## 9. Configurar GitHub Secrets e environment

No GitHub, abra **Settings → Environments → New environment** e crie `producao`.

No terminal, envie os três secrets diretamente do perfil AWS:

```bash
gh secret set AWS_ACCESS_KEY_ID --body "$(aws configure get aws_access_key_id)"
gh secret set AWS_SECRET_ACCESS_KEY --body "$(aws configure get aws_secret_access_key)"
gh secret set AWS_SESSION_TOKEN --body "$(aws configure get aws_session_token)"
```

Confirme apenas os nomes, nunca os valores:

```bash
gh secret list
```

Essas credenciais expiram após a sessão do Learner Lab. Atualize os secrets em todo novo deploy.

## 10. Fazer o deploy da Lambda

Dispare o workflow:

```bash
gh workflow run "Aula 2 · Deploy do classificador (AWS Lambda)"
gh run list --workflow "Aula 2 · Deploy do classificador (AWS Lambda)" --limit 1
gh run watch
```

Se houver vários runs, use o ID exibido:

```bash
gh run watch ID_DO_RUN
gh run view ID_DO_RUN --log-failed
```

No resumo do run haverá a URL pública da função. Teste substituindo a URL:

```bash
curl -X POST "https://SUA-URL.lambda-url.us-east-1.on.aws/" \
  -H 'content-type: application/json' \
  -d '{"texto":"Adorei, chegou rápido"}'
```

Resposta esperada:

```json
{"rotulo":"positiva","confianca":0.0,"versao":"..."}
```

O valor de confiança será real e pode variar. Guarde o resumo verde do workflow e a resposta do smoke test.

### Problemas comuns da Aula 2

- `ExpiredToken`: reinicie o Academy e atualize os três secrets.
- `AccessDenied` na role: confira se a função usa `LabRole` e a região `us-east-1`.
- environment não encontrado: crie `producao` exatamente com esse nome.
- workflow não aparece: o YAML precisa estar na branch `main`.
- URL retorna 403: atualize o AWS CLI e confira as duas permissões criadas por `trafego.sh`.

---

# Aula 3 — GitOps, promoção, drift, policy-as-code e rollback

## 11. Garantir pré-requisitos

Antes de subir o cluster:

```bash
git switch main
git pull --ff-only
git status
git remote get-url origin
```

O repositório precisa ser público e a URL de `origin` deve apontar para a cópia do grupo. Para observar o estado inicial do exercício, a `main` remota deve ter staging em `v12`, produção em `v11` e `selfHeal: false`. As alterações finais preparadas neste workspace ainda não devem ser mescladas antes da demonstração inicial.

## 12. Subir kind e Argo CD

```bash
gitops/scripts/subir-cluster.sh
gitops/scripts/consultar.sh
```

Espere até os dois ambientes aparecerem como `Synced` e `Healthy`. A saída inicial deve mostrar:

- staging: `prompt=v12`;
- produção: `prompt=v11`.

Confira o que ainda não foi promovido:

```bash
diff gitops/overlays/staging/inference-config.env \
     gitops/overlays/producao/inference-config.env
```

Para abrir o painel:

```bash
kubectl -n argocd port-forward svc/argocd-server 8443:443
```

Abra a porta encaminhada pelo Codespace. Usuário: `admin`; a senha foi mostrada por `subir-cluster.sh`. Em outro terminal, também é possível recuperá-la:

```bash
kubectl -n argocd get secret argocd-initial-admin-secret \
  -o jsonpath='{.data.password}' | base64 -d; echo
```

## 13. Promover o prompt v12 por PR

```bash
git switch -c lab/aula3-promover-v12
```

Em `gitops/overlays/producao/inference-config.env`, troque apenas:

```text
PROMPT_VERSAO=v11
```

por:

```text
PROMPT_VERSAO=v12
```

Valide:

```bash
kubectl kustomize gitops/overlays/staging >/dev/null
kubectl kustomize gitops/overlays/producao >/dev/null
python gitops/politicas/verificar.py
```

Commit e PR:

```bash
git add gitops/overlays/producao/inference-config.env
git commit -m "config: promover prompt v12 para producao"
git push -u origin lab/aula3-promover-v12
gh pr create --base main --head lab/aula3-promover-v12 \
  --title "config: promover prompt v12 para produção" \
  --body "Promove a versão já validada em staging. Rollback: reverter este commit."
gh pr checks --watch
```

Após revisão e merge:

```bash
git switch main
git pull --ff-only
```

Aguarde 30–60 segundos e consulte:

```bash
gitops/scripts/consultar.sh
```

Produção agora deve responder `prompt=v12`.

## 14. Demonstrar drift com self-heal desligado

No estado inicial, produção usa `selfHeal: false`:

```bash
kubectl -n agente-producao scale deploy/agente-suporte --replicas=5
sleep 35
gitops/scripts/consultar.sh
kubectl -n agente-producao get deploy agente-suporte \
  -o jsonpath='{.spec.replicas}'; echo
```

Resultado esperado: Argo CD marca produção como `OutOfSync`; o cluster tem cinco réplicas, enquanto o Git continua declarando três em `escala.patch.yaml`.

Não use essa alteração manual como estado final.

## 15. Habilitar self-heal em produção

Crie outra branch a partir da `main` atualizada:

```bash
git switch main
git pull --ff-only
git switch -c lab/aula3-self-heal
```

Em `gitops/apps/agente-producao.yaml`, troque `selfHeal: false` por `selfHeal: true`, valide, commite e abra PR:

```bash
git add gitops/apps/agente-producao.yaml
git commit -m "config: habilitar self-heal em producao"
git push -u origin lab/aula3-self-heal
gh pr create --base main --head lab/aula3-self-heal \
  --title "config: habilitar self-heal em produção" \
  --body "Mantém o Git como fonte única da verdade e reverte drift manual automaticamente."
gh pr checks --watch
```

Depois da revisão e merge:

```bash
git switch main
git pull --ff-only
```

O manifesto de `Application` não é observado por um app-of-apps; reaplique-o ao cluster:

```bash
REPO_URL=$(git remote get-url origin | sed -E 's#git@github.com:#https://github.com/#')
sed "s#REPO_URL#${REPO_URL}#" gitops/apps/agente-producao.yaml | kubectl apply -f -
```

Comprove a configuração:

```bash
kubectl -n argocd get application agente-producao \
  -o jsonpath='{.spec.syncPolicy.automated.selfHeal}'; echo
```

Deve imprimir `true`. Repita o drift:

```bash
kubectl -n agente-producao scale deploy/agente-suporte --replicas=5
sleep 35
kubectl -n agente-producao get deploy agente-suporte \
  -o jsonpath='{.spec.replicas}'; echo
gitops/scripts/consultar.sh
```

Resultado esperado: o Argo CD restaura três réplicas e a aplicação volta a `Synced`.

Decisão para entregar:

> Escolhemos self-heal em produção porque o Git é a fonte única da verdade. Alterações manuais não revisadas são revertidas; emergências devem usar um procedimento break-glass auditável seguido de commit/PR.

## 16. Quebrar a policy-as-code de propósito

Crie uma branch descartável:

```bash
git switch main
git pull --ff-only
git switch -c lab/aula3-policy-falha
```

Em `gitops/overlays/producao/inference-config.env`:

1. troque `PROMPT_VERSAO=v12` por `PROMPT_VERSAO=latest`;
2. acrescente `OPENAI_API_KEY=sk-123` — valor fictício, nunca uma chave real.

Execute:

```bash
python gitops/politicas/verificar.py
```

Resultado esperado: reprovação por versão não explícita e segredo em texto claro.

Abra o PR somente para registrar o check vermelho:

```bash
git add gitops/overlays/producao/inference-config.env
git commit -m "test: demonstrar bloqueios da policy as code"
git push -u origin lab/aula3-policy-falha
gh pr create --base main --head lab/aula3-policy-falha \
  --title "test: comprovar policy-as-code" \
  --body "PR deliberadamente inválido; não deve ser mesclado."
gh pr checks --watch
```

Tire a captura dos dois erros. **Não faça merge.** Feche e remova a branch remota:

```bash
gh pr close --delete-branch
git switch main
git pull --ff-only
```

## 17. Demonstrar rollback GitOps

Encontre o commit que promoveu v12:

```bash
git log --oneline -- gitops/overlays/producao/inference-config.env
```

Crie o revert em uma branch:

```bash
git switch -c lab/aula3-rollback
git revert SHA_DO_COMMIT_DA_PROMOCAO
git push -u origin lab/aula3-rollback
gh pr create --base main --head lab/aula3-rollback \
  --title "revert: voltar prompt de produção para v11" \
  --body "Rollback declarativo da promoção v12."
```

Após aprovação e merge, cronometre:

```bash
date
gitops/scripts/consultar.sh
```

Repita a consulta até produção mostrar `prompt=v11`. Com polling de 30 segundos, a reconciliação deve levar aproximadamente 30–60 segundos após o merge, além do tempo de atualização dos pods.

Se o estado final desejado for v12, abra um novo PR de promoção depois de registrar a evidência do rollback.

## 18. Respostas finais da Aula 3

- **Onde modelo e prompt são declarados?** Na base `gitops/base/agente-suporte/inference-config.env` e nas substituições de `gitops/overlays/staging` e `producao`.
- **Onde fica a chave do LLM?** Fora do Git e da ConfigMap, em Secrets Manager/Vault/External Secrets ou Kubernetes Secret provisionado de forma segura.
- **Quem muda produção sem revisão?** Ninguém no fluxo normal: CODEOWNERS, ruleset da `main` e checks obrigatórios bloqueiam o merge; o Argo CD aplica somente o estado aprovado.
- **Quanto demora o rollback?** Aproximadamente 30–60 segundos após o merge, mais o rollout dos pods e o tempo humano para revisar o PR.

---

# 19. O que entregar

## Aula 1

- link do repositório público;
- link do PR do teste;
- saída do pytest;
- captura do reviewer solicitado pelo CODEOWNERS;
- captura do merge bloqueado e depois liberado;
- captura do ruleset da `main`;
- resposta sobre reviewer solicitado versus gate de merge.

## Aula 2

- link do PR do teste de tamanho;
- base saudável passando e lote novo falhando;
- saída do model gate saudável e do lote ruim;
- execução verde do CI;
- execução verde do deploy da Lambda;
- URL e resposta do smoke test, sem expor credenciais.

## Aula 3

- PR de promoção v12;
- saída inicial v12/v11 e final v12/v12;
- drift `OutOfSync` com cinco réplicas;
- self-heal restaurando três réplicas;
- PR deliberadamente inválido com os dois erros, fechado sem merge;
- PR de rollback e tempo medido;
- decisão de self-heal e respostas sobre configuração, segredos e revisão.

## 20. Limpeza opcional

Quando não precisar mais do classificador na AWS:

```bash
aws lambda delete-function --function-name classificador-avaliacoes
aws ecr delete-repository --repository-name classificador-avaliacoes --force
```

Para remover o cluster local do Codespace:

```bash
kind delete cluster --name aie
```

Só execute a limpeza depois de salvar todas as evidências.
