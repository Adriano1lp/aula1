#!/usr/bin/env bash
# Aponta o alias "producao" do Lambda do agente para uma versão e devolve a URL pública.
#
#   agente/deploy/trafego.sh 3        # 100% na versão 3 (rollback = apontar para a versão anterior)
#
# Na primeira vez cria o alias e a Function URL (pública, sem autenticação — adequado ao laboratório;
# em produção real use IAM ou um API Gateway). A função e a URL continuam disponíveis entre as sessões
# do Learner Lab; só as credenciais expiram.
#
# NÃO TESTADO contra um Learner Lab real.
set -euo pipefail

export AWS_REGION="${AWS_REGION:-us-east-1}" AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"
FUNCAO="${FUNCAO:-agente-atendimento}"
VERSAO="$1"

if aws lambda get-alias --function-name "$FUNCAO" --name producao >/dev/null 2>&1; then
  aws lambda update-alias --function-name "$FUNCAO" --name producao --function-version "$VERSAO" >/dev/null
else
  aws lambda create-alias --function-name "$FUNCAO" --name producao --function-version "$VERSAO" >/dev/null
  aws lambda create-function-url-config --function-name "$FUNCAO" --qualifier producao --auth-type NONE >/dev/null
  aws lambda add-permission --function-name "$FUNCAO" --qualifier producao --statement-id url-publica \
    --action lambda:InvokeFunctionUrl --principal "*" --function-url-auth-type NONE >/dev/null
  # Contas novas também exigem lambda:InvokeFunction restrito à Function URL
  aws lambda add-permission --function-name "$FUNCAO" --qualifier producao --statement-id url-publica-invoke \
    --action lambda:InvokeFunction --principal "*" --invoked-via-function-url >/dev/null 2>&1 \
    || echo "aviso: AWS CLI sem --invoked-via-function-url; se a URL der 403, atualize o CLI" >&2
fi

echo "producao → versão $VERSAO" >&2
aws lambda get-function-url-config --function-name "$FUNCAO" --qualifier producao --query FunctionUrl --output text
