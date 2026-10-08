#!/usr/bin/env bash
# Aponta o alias "producao" do Lambda — é ele que recebe o tráfego da URL pública.
#
#   classificador/deploy/trafego.sh 3            # 100% na versão 3
#   classificador/deploy/trafego.sh 3 4 0.1      # canary: 90% na 3, 10% na 4
#
# Na primeira vez cria o alias e a Function URL (pública, sem autenticação —
# adequado para o laboratório; em produção real, use IAM ou um API Gateway).
set -euo pipefail

export AWS_REGION="${AWS_REGION:-us-east-1}" AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"
FUNCAO="${FUNCAO:-classificador-avaliacoes}"
ESTAVEL="$1"
CANARY="${2:-}"
PESO="${3:-0}"

if [[ -n "$CANARY" ]]; then
  ROTEAMENTO="AdditionalVersionWeights={$CANARY=$PESO}"
else
  ROTEAMENTO="AdditionalVersionWeights={}"
fi

if aws lambda get-alias --function-name "$FUNCAO" --name producao >/dev/null 2>&1; then
  aws lambda update-alias --function-name "$FUNCAO" --name producao \
    --function-version "$ESTAVEL" --routing-config "$ROTEAMENTO" >/dev/null
else
  aws lambda create-alias --function-name "$FUNCAO" --name producao \
    --function-version "$ESTAVEL" --routing-config "$ROTEAMENTO" >/dev/null
  aws lambda create-function-url-config --function-name "$FUNCAO" --qualifier producao \
    --auth-type NONE >/dev/null
  aws lambda add-permission --function-name "$FUNCAO" --qualifier producao \
    --statement-id url-publica --action lambda:InvokeFunctionUrl \
    --principal "*" --function-url-auth-type NONE >/dev/null
  # Contas novas também exigem lambda:InvokeFunction restrito à Function URL
  aws lambda add-permission --function-name "$FUNCAO" --qualifier producao \
    --statement-id url-publica-invoke --action lambda:InvokeFunction \
    --principal "*" --invoked-via-function-url >/dev/null 2>&1 \
    || echo "aviso: AWS CLI sem --invoked-via-function-url; se a URL der 403, atualize o CLI" >&2
fi

echo "producao → versão $ESTAVEL${CANARY:+ (+ $CANARY com peso $PESO)}" >&2
aws lambda get-function-url-config --function-name "$FUNCAO" --qualifier producao \
  --query FunctionUrl --output text
