#!/usr/bin/env bash
# Cria o Web App do capstone (Aula 6) descobrindo uma REGIÃO em que a sua conta pode criar recursos.
#
#   azure/criar-webapp.sh                 # cria e já liga o GitHub (secret + variável) no repositório atual
#   REGIOES="brazilsouth eastus" azure/criar-webapp.sh   # força a lista de regiões a tentar
#   SEM_GITHUB=1 azure/criar-webapp.sh    # só cria no Azure
#   azure/criar-webapp.sh --diagnostico   # NÃO cria o Web App: testa TODAS as regiões e imprime um relatório
#                                         # para você colar e mandar ao professor (rode antes da Aula 6)
#
# Por que existe: no Azure for Students da parceria FIAP × Microsoft a assinatura de CADA aluno só pode criar
# recursos em algumas regiões (política "Allowed resource deployment regions", em geral ~5, diferentes por
# aluno e que mudam com a capacidade ociosa dos datacenters). Mesmo dentro da lista, uma região pode estar
# sem capacidade. Região fixa no roteiro quebraria para o aluno. O script tenta, na ordem:
#   1. as regiões da política "Allowed locations", se a sua conta conseguir lê-la;
#   2. senão, uma lista de regiões comuns.
# e, em cada uma, distingue "proibida pela política" de "sem cota de F1" de outro erro.
#
# Pré-requisitos: `az login` com uma conta que TENHA assinatura (a conta @fiap.com.br sozinha não tem;
# ative o Azure for Students) e, para ligar o GitHub, `gh auth login`.
set -uo pipefail

DIAGNOSTICO="${DIAGNOSTICO:-}"
if [ "${1:-}" = "--diagnostico" ]; then DIAGNOSTICO=1; shift; fi

GRUPO_BASE="${GRUPO:-rg-aie-capstone}"
APP="${1:-agente-quantum-$RANDOM}"      # vira <nome>.azurewebsites.net e precisa ser único
PLANO="plano-aie"
# B1 (Basic): consome o crédito do Azure for Students. NÃO use o F1 "gratuito": a Microsoft orientou os
# professores a evitar as ofertas gratuitas do portal (são para qualquer assinatura e têm limites próprios).
SKU="${SKU:-B1}"
limpa() { tr -d '\r'; }                 # o az do Windows (WSL) devolve CRLF

az account show >/dev/null 2>&1 || { echo "❌ Você não está logado: rode 'az login' antes."; exit 1; }

# A conta precisa de uma assinatura de verdade: só estar no diretório da FIAP não basta.
NASSIN=$(az account list --query "length([?state=='Enabled' && name!='N/A(tenant level account)'])" -o tsv | limpa)
if [ "${NASSIN:-0}" -lt 1 ]; then
  echo "❌ Nenhuma assinatura Azure nesta conta (só o diretório). Ative o Azure for Students:"
  echo "   https://azure.microsoft.com/free/students  (e-mail da FIAP) e rode 'az login' de novo."
  exit 1
fi

# 1. Regiões candidatas
if [ -n "${REGIOES:-}" ]; then
  CANDIDATAS="$REGIOES"; ORIGEM="variável REGIOES"
else
  PERMITIDAS=$(az policy assignment list --query "[].parameters.listOfAllowedLocations.value[]" -o tsv 2>/dev/null | limpa | sort -u | grep -v '^global$' || true)
  if [ -n "$PERMITIDAS" ]; then
    CANDIDATAS="$PERMITIDAS"; ORIGEM="política Allowed locations da sua conta"
  else
    CANDIDATAS="spaincentral francecentral belgiumcentral canadacentral northcentralus brazilsouth eastus eastus2 centralus westus2 southcentralus westeurope northeurope"
    ORIGEM="lista de regiões comuns (não consegui ler a política de regiões; veja no portal: Assinaturas → sua assinatura → Configurações → Políticas → \"Allowed resource deployment regions\" → Exibir atribuição, e use REGIOES=...)"
  fi
fi
echo "Regiões a tentar (${ORIGEM}):"; echo "$CANDIDATAS" | tr ' ' '\n' | sed 's/^/  - /'

# 2. Tenta região por região: grupo de recursos + plano. O grupo também obedece à política de regiões.
REGIAO=""; GRUPO=""; RESULTADOS=()
[ -n "$DIAGNOSTICO" ] && echo "(modo diagnóstico: testo cada região criando e apagando um plano; leva alguns minutos)"
for loc in $CANDIDATAS; do
  g="${GRUPO_BASE}-${loc}"
  printf '\n→ %s ... ' "$loc"
  saida=$(az group create -n "$g" -l "$loc" -o none 2>&1) || {
    if echo "$saida" | grep -qi "RequestDisallowedByPolicy\|disallowed by policy"; then
      echo "proibida pela política de regiões (grupo de recursos)"; RESULTADOS+=("$loc|PROIBIDA pela política de regiões")
    else echo "não consegui criar o grupo: $(echo "$saida" | tail -1 | cut -c1-120)"; RESULTADOS+=("$loc|erro ao criar o grupo"); fi
    continue
  }
  saida=$(az appservice plan create -g "$g" -n "$PLANO" -l "$loc" --is-linux --sku "$SKU" -o none 2>&1) && {
    echo "ok"; RESULTADOS+=("$loc|OK (tem cota de $SKU)")
    if [ -n "$DIAGNOSTICO" ]; then az group delete -n "$g" --yes --no-wait >/dev/null 2>&1; continue; fi
    REGIAO="$loc"; GRUPO="$g"; break
  }
  if echo "$saida" | grep -qi "RequestDisallowedByPolicy\|disallowed by policy"; then
    echo "proibida pela política de regiões (plano)"; RESULTADOS+=("$loc|PROIBIDA pela política de regiões")
  elif echo "$saida" | grep -qi "Amount required for this deployment\|quota"; then
    echo "sem cota/capacidade de $SKU nesta região"; RESULTADOS+=("$loc|sem cota/capacidade de $SKU")
  else
    echo "erro: $(echo "$saida" | tail -1 | cut -c1-140)"; RESULTADOS+=("$loc|erro: $(echo "$saida" | tail -1 | cut -c1-60)")
  fi
  az group delete -n "$g" --yes --no-wait >/dev/null 2>&1   # limpa o grupo vazio da tentativa
done

if [ -n "$DIAGNOSTICO" ]; then
  echo; echo "=========== RELATÓRIO — copie tudo daqui até a linha final e mande ao professor ==========="
  echo "data (UTC):          $(date -u +%F)"
  echo "conta:               $(az account show --query user.name -o tsv | limpa)"
  echo "assinaturas ativas:  $(az account list --query "[?state=='Enabled'].name" -o tsv | limpa | paste -sd ';' -)"
  echo "regiões lidas de:    $ORIGEM" | cut -c1-110
  echo "SKU testado:         $SKU"
  echo "-------------------------------------------------------------------------------------------"
  printf '%-18s %s\n' "REGIÃO" "RESULTADO"
  for r in "${RESULTADOS[@]}"; do printf '%-18s %s\n' "${r%%|*}" "${r#*|}"; done
  echo "==========================================================================================="
  exit 0
fi

if [ -z "$REGIAO" ]; then
  echo; echo "❌ Nenhuma região funcionou. Causas prováveis: política de regiões da sua conta, cota de $SKU"
  echo "   zerada em todas, ou assinatura sem permissão. Peça ao professor a(s) região(ões) liberada(s) para"
  echo "   você e rode:  REGIOES=\"<regiao>\" azure/criar-webapp.sh   (veja roteiros/setup-azure.md)"
  exit 1
fi

# 3. Web App, inicialização e configurações
echo; echo "Criando o Web App '$APP' em $REGIAO ..."
az webapp create -g "$GRUPO" -p "$PLANO" -n "$APP" --runtime "PYTHON:3.12" -o none || { echo "❌ falha ao criar o Web App"; exit 1; }
az webapp config set -g "$GRUPO" -n "$APP" -o none \
  --startup-file "gunicorn app:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120"
az webapp config appsettings set -g "$GRUPO" -n "$APP" -o none --settings \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true WEBSITES_PORT=8000 LLM_PROVEDOR="${LLM_PROVEDOR:-simulado}"

# Novos Web Apps vêm com a autenticação básica do SCM DESLIGADA; sem ela o deploy por publish profile dá 401.
az resource update -g "$GRUPO" --namespace Microsoft.Web --resource-type basicPublishingCredentialsPolicies \
  --parent "sites/$APP" -n scm --set properties.allow=true -o none

# 4. GitHub: secret com o publish profile e variável com o nome do app
if [ -z "${SEM_GITHUB:-}" ] && command -v gh >/dev/null 2>&1 && gh repo view >/dev/null 2>&1; then
  PERFIL=$(mktemp); trap 'rm -f "$PERFIL"' EXIT
  az webapp deployment list-publishing-profiles -g "$GRUPO" -n "$APP" --xml > "$PERFIL"
  gh secret set AZURE_WEBAPP_PUBLISH_PROFILE < "$PERFIL" && gh variable set AZURE_WEBAPP_NAME --body "$APP" \
    && echo "✅ GitHub ligado: secret AZURE_WEBAPP_PUBLISH_PROFILE e variável AZURE_WEBAPP_NAME"
else
  echo "(GitHub não ligado. Faça o passo 2 de roteiros/setup-azure.md com GRUPO=$GRUPO e APP=$APP)"
fi

cat <<FIM

✅ Web App criado
   Região:   $REGIAO
   Grupo:    $GRUPO
   App:      $APP
   Site:     https://$APP.azurewebsites.net/
   Depois do deploy:  curl https://$APP.azurewebsites.net/

   Para apagar tudo no fim:  az group delete -n $GRUPO --yes
FIM
