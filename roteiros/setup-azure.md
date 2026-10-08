# Setup — Azure Web Apps (Aula 6 · capstone)

O agente de atendimento pode ir para um **Azure Web App** (Linux, Python 3.12) pelo GitHub Actions, só depois de
passar no *agent gate*. É a **alternativa** ao deploy padrão no AWS Academy (Lambda, ver
`roteiros/setup-aws-academy.md`, passo 4): use este caminho se preferir o Azure e tiver o Azure for Students.
O workflow é **manual** (*Aula 6 · Deploy do agente (Azure Web Apps)*).

> **Fonte das regras abaixo:** reunião Microsoft × FIAP de 28/09/2026 (transcrição em
> `02_Apoio_Referencia/04_MBA_AIE_CICD/` do repositório do curso). **Testado de ponta a ponta em 2026-10-02**
> com uma assinatura Visual Studio (que **não tem** a política de regiões do Azure for Students): criação do
> Web App, workflow de deploy (gate → `azure/webapps-deploy`, ~130 s) e o agente respondendo. **Não foi testado
> com uma assinatura Azure for Students real**, nem com a política de regiões, nem com um LLM do Foundry.

## 1. As regras da parceria (leia antes de criar qualquer coisa)

A assinatura do Azure for Students da parceria **limita onde e o que você pode criar**. Nada disso é erro seu:

1. **Cadastro.** Você se inscreve no Azure for Students como sempre, com o e-mail da FIAP. A Microsoft confirmou
   que o cadastro e a licença da parceria estão certos. A assinatura é **sua**: uma conta `@fiap.com.br` sem esse
   cadastro existe no diretório da FIAP mas **não tem assinatura** (`az account list` mostra só
   "tenant level account").
2. **Regiões: cada aluno tem a sua lista, e ela é imposta.** Uma política da assinatura só deixa criar recursos
   em algumas regiões (na demonstração, 5: França, Bélgica, Canadá, Espanha e US North Central). Fora delas a
   criação **falha na validação**. A lista é **por usuário**: a do professor ou a do colega não vale para você, e
   pode mudar com a capacidade ociosa dos datacenters. Veja a sua **antes de começar** (seção 2).
3. **Região permitida não é capacidade garantida.** O programa usa capacidade ociosa: uma região da sua lista pode
   estar sem máquinas ou sem cota naquele dia. Tente as outras da lista. No portal, ao escolher o tamanho,
   clique em **"Ver todos os tamanhos"**: as primeiras opções às vezes aparecem indisponíveis e a lista completa
   tem mais.
4. **Não use as ofertas gratuitas do portal** (menu "Serviços gratuitos", opções "Free"/"Oferta gratuita"). Elas
   valem para qualquer assinatura e têm limites próprios (tipo de máquina, uso). Escolha a opção **normal**: ela
   consome o **crédito do Azure for Students**. Por isso este roteiro usa o plano **B1 (Basic)**, não o F1.
5. **Vale para todo serviço**, não só para máquina virtual: App Service, banco de dados, Foundry...
6. **Isso é a vida real.** A Microsoft frisou que, em projetos reais, falta de capacidade numa região é rotina;
   a solução é escolher outra região e tentar de novo (às vezes na semana seguinte).

## 2. Descubra as suas regiões

**No portal** (o caminho que a Microsoft mostrou): **Assinaturas** → a assinatura **Azure for Students ativa**
(se você já teve outras, só uma está ativa) → **Configurações → Políticas** → a política **"Allowed resource
deployment regions"** → **Exibir atribuição** → o parâmetro **"Allowed locations"** lista as suas regiões.

**Na linha de comando** (funciona se a sua conta tiver permissão de leitura da política):

```bash
az login
az account list -o table                     # tem de aparecer uma assinatura "Enabled" (não só "tenant level")
az policy assignment list --query "[].parameters.listOfAllowedLocations.value[]" -o tsv
```

Anote as regiões. O script da seção 3 lê essa mesma política sozinho; se não conseguir, você passa a lista com
`REGIOES="..."`.

## 2b. Diagnóstico: faça cedo, antes da Aula 6

Para descobrir **agora**, e não no dia da entrega, se você consegue criar o Web App:

```bash
az login --use-device-code                    # no Codespace
azure/criar-webapp.sh --diagnostico
```

Ele **não cria o Web App**: tenta criar e apagar um plano B1 em cada região (leva alguns minutos) e imprime um
relatório (conta, assinaturas, e por região: `OK`, `PROIBIDA pela política` ou `sem cota/capacidade`).
**Copie o relatório e mande ao professor.** Se nenhuma região der `OK`, avise já: é a informação que permite
ajudar você (ou oferecer outra forma de entregar) a tempo.

## 3. Criar o Web App (automático)

```bash
azure/criar-webapp.sh                          # descobre a região, cria tudo e liga o GitHub
REGIOES="spaincentral francecentral" azure/criar-webapp.sh   # força as regiões a tentar (nomes técnicos)
```

O script: confere que a conta tem assinatura; tenta **região por região** (as da sua política ou, se não
conseguir ler, uma lista comum) e em cada uma diz se está **proibida pela política**, **sem cota/capacidade** ou
deu outro erro; cria o grupo de recursos, o plano **B1** e o Web App; liga a autenticação básica do SCM; e, se
você estiver no repositório do GitHub, cadastra o secret `AZURE_WEBAPP_PUBLISH_PROFILE` e a variável
`AZURE_WEBAPP_NAME`. No fim imprime a região, o nome e o comando para apagar tudo.

> Se nenhuma região funcionar, peça ao professor e **mande a sua lista de regiões** (seção 2). Não adianta usar a
> lista de outra pessoa.

## 4. Criar o Web App (manual, para entender cada passo)

```bash
REGIAO=spaincentral                            # UMA região da SUA lista (seção 2)
GRUPO=rg-aie-capstone
APP=agente-quantum-$RANDOM                     # vira <nome>.azurewebsites.net e precisa ser único

az group create -n $GRUPO -l $REGIAO
az appservice plan create -g $GRUPO -n plano-aie -l $REGIAO --is-linux --sku B1
az webapp create -g $GRUPO -p plano-aie -n $APP --runtime "PYTHON:3.12"

# Comando de inicialização: o FastAPI do agente, na porta que o App Service espera
az webapp config set -g $GRUPO -n $APP \
  --startup-file "gunicorn app:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120"
az webapp config appsettings set -g $GRUPO -n $APP --settings \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true WEBSITES_PORT=8000 LLM_PROVEDOR=simulado

# Novos Web Apps vêm com a autenticação básica do SCM DESLIGADA; sem ela o deploy dá 401
az resource update -g $GRUPO --namespace Microsoft.Web --resource-type basicPublishingCredentialsPolicies \
  --parent sites/$APP -n scm --set properties.allow=true

# Liga o GitHub (rode no repositório do seu grupo)
az webapp deployment list-publishing-profiles -g $GRUPO -n $APP --xml > perfil.xml
gh secret set AZURE_WEBAPP_PUBLISH_PROFILE < perfil.xml
rm perfil.xml                                  # não deixe a credencial no disco
gh variable set AZURE_WEBAPP_NAME --body "$APP"
```

Erros que você pode ver no `plan create`:

- `RequestDisallowedByPolicy` → a região **não está na sua lista**. Use outra da lista.
- `Amount required for this deployment ... quota` → a região está na lista mas **sem cota/capacidade** agora.
  Tente outra da lista (ou a mesma outro dia).

## 5. O LLM do agente em produção (Foundry)

O Web App **não roda o Ollama**. No começo o app sobe com `LLM_PROVEDOR=simulado` (responde por regras, só para
provar o deploy). Para um LLM real, use **Microsoft Foundry / Azure OpenAI** na mesma assinatura:

- O recurso do Foundry **também** só pode ser criado numa região da sua lista, e a validação falha fora dela.
- **Cota por modelo:** antes de tentar implantar, abra **Gerenciar → Cota**, escolha a assinatura ativa e filtre por
  **Global Standard**. Modelos com `0/0` **não podem ser implantados** (aparece "solicitar cota"); use um que
  tenha cota. **O modelo disponível varia por aluno e por região**: não conte com um modelo específico
  (descreva no relatório qual você usou).
- Depois de implantar, configure o app com o endpoint e o **nome da implantação** (não o nome do modelo):

```bash
az webapp config appsettings set -g $GRUPO -n $APP --settings \
  LLM_PROVEDOR=openai LLM_BASE_URL=https://<seu-recurso>.openai.azure.com/openai/v1/ \
  LLM_MODELO=<nome-da-implantacao> LLM_API_KEY=<chave>
```

> A configuração de `LLM_BASE_URL` para Azure OpenAI segue a documentação, mas **não foi testada** aqui.

## 6. Conferir

```bash
gh workflow run "Aula 6 · Deploy do agente (Azure Web Apps)"
curl https://$APP.azurewebsites.net/
curl -X POST https://$APP.azurewebsites.net/chamado -H 'content-type: application/json' \
  -d '{"texto": "Meu pedido está atrasado há 6 dias úteis"}'
```

## 7. Custo e limpeza

O plano **B1** custa cerca de **US$ 13 por mês** (confira o preço atual na página do App Service) e sai do seu
crédito do Azure for Students: para o capstone são alguns dólares. **Apague ao terminar:**

```bash
az group delete -n <seu-grupo> --yes
```

## Fora do escopo

O Azure DevOps (repositórios e pipelines) só exige o link específico que a Microsoft envia ao professor, senão
pede cartão de crédito. Esta disciplina usa **GitHub Actions**, então não é necessário.
