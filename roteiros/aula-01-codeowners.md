# Aula 1 — laboratório de CODEOWNERS

**Tempo:** 40–45 min · **Formato:** duplas · **Entrega:** um Pull Request
com mudança real em código, teste executado e revisão do *code owner*.

## Objetivo

Construir e comprovar este fluxo no GitHub:

```text
branch → código + teste → Pull Request → CODEOWNERS → revisão → merge protegido
```

## 1. Criar a cópia da dupla

1. Abra o repositório público `aie-devops-labs`.
2. Clique em **Use this template → Create a new repository** e crie uma cópia
   pública na conta de uma pessoa da dupla.
3. Adicione a outra pessoa como colaboradora com permissão de escrita.

A pessoa que criou a cópia é **owner/admin** e poderá configurar a proteção da
`main`. A proteção da branch não é copiada pelo template.

## 2. Configurar o `CODEOWNERS`

Na cópia da dupla, abra `.github/CODEOWNERS` e troque
`@guilherme-argentino` pelo *handle* da pessoa revisora:

```text
# Toda mudança pede revisão da outra pessoa
* @pessoa-revisora

# Áreas de maior risco têm regra explícita
/agente/prompts/** @pessoa-revisora
/gitops/overlays/producao/** @pessoa-revisora
```

Faça commit e envie a branch:

```bash
git switch -c lab/codeowners
git add .github/CODEOWNERS
git commit -m "chore: define code owners da dupla"
git push -u origin lab/codeowners
```

## 3. Alterar código e rodar o teste

Em `classificador/tests/test_texto.py`, acrescente:

```python
def test_texto_vazio_continua_vazio():
    assert limpar("") == ""
```

Execute:

```bash
pytest classificador/tests/test_texto.py
```

Se passar, faça commit e push:

```bash
git add classificador/tests/test_texto.py
git commit -m "test: cobrir texto vazio"
git push
```

## 4. Abrir e revisar o Pull Request

1. Abra um PR de `lab/codeowners` para `main`.
2. Confira **Reviewers**: o GitHub deve solicitar a pessoa revisora.
3. Registre no PR a saída do `pytest` e o caminho do `CODEOWNERS`.
4. A pessoa revisora comenta uma melhoria concreta e depois aprova.
5. A pessoa autora responde ou envia um novo commit na mesma branch.

O autor não pode aprovar o próprio PR.

## 5. Proteger a `main`

Como owner/admin, abra **Settings → Rules → Rulesets** (ou **Settings →
Branches**) e crie uma regra para `main` com:

- Pull Request obrigatório antes do merge;
- pelo menos uma aprovação;
- aprovação de *code owner*;
- sem push direto e sem exclusão da `main`;
- **Do not allow bypassing the above settings**, se disponível.

## 6. Provar o gate

Façam uma segunda mudança pequena e abram outro PR. Antes da aprovação, o
GitHub deve indicar a revisão pendente e bloquear o merge. Depois da aprovação,
o merge fica disponível.

Se o administrador ainda conseguir ignorar a regra, verifique a opção de
bypass e registre a limitação no PR.

## Entrega

No PR, incluam:

- link do repositório criado a partir do template;
- link do PR;
- saída do teste;
- evidência da revisão solicitada pelo `CODEOWNERS`;
- captura ou descrição da proteção da `main`;
- resposta: qual é a diferença entre revisor solicitado e merge bloqueado?

## Critério de sucesso

A dupla demonstra uma mudança de código em branch, teste passando, revisão de
outra pessoa e merge condicionado à aprovação.
