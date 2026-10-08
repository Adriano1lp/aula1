#!/usr/bin/env bash
# Publica uma NOVA VERSÃO do agente no AWS Lambda (sem mudar o tráfego) — Aula 6, AWS Academy.
#
#   agente/deploy/publicar.sh                       # usa o SHA do commit como versão do prompt
#   LLM_PROVEDOR=bedrock agente/deploy/publicar.sh  # LLM pelo Bedrock, se o seu Learner Lab liberar
#   LLM_PROVEDOR=openai LLM_BASE_URL=... LLM_MODELO=... LLM_API_KEY=... agente/deploy/publicar.sh
#
# Pré-requisitos: credenciais do Learner Lab no ambiente (roteiros/setup-aws-academy.md), Docker.
# Imprime o número da versão publicada na última linha. As chaves de LLM ficam nas variáveis de
# ambiente da função (aceitável no laboratório; em produção real use o Secrets Manager).
#
# NÃO TESTADO contra um Learner Lab real (a imagem foi testada no emulador de runtime do Lambda).
set -euo pipefail

export AWS_REGION="${AWS_REGION:-us-east-1}" AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"
FUNCAO="${FUNCAO:-agente-atendimento}"
VERSAO="${PROMPT_VERSAO:-$(git rev-parse --short HEAD)}"

CONTA=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="$CONTA.dkr.ecr.$AWS_REGION.amazonaws.com"
IMAGEM="$REGISTRY/$FUNCAO:$VERSAO"

# Variáveis de ambiente da função, em JSON (evita problemas de aspas com URLs e chaves)
AMBIENTE=$(mktemp); trap 'rm -f "$AMBIENTE"' EXIT
python3 - "$AMBIENTE" <<PY
import json, os, sys
variaveis = {
    "LLM_PROVEDOR": os.environ.get("LLM_PROVEDOR", "simulado"),
    "LLM_BASE_URL": os.environ.get("LLM_BASE_URL", ""),
    "LLM_MODELO": os.environ.get("LLM_MODELO", ""),
    "LLM_API_KEY": os.environ.get("LLM_API_KEY", ""),
}
json.dump({"Variables": {k: v for k, v in variaveis.items() if v}}, open(sys.argv[1], "w"))
PY

# 1. Repositório de imagens (ECR), criado na primeira vez
aws ecr describe-repositories --repository-names "$FUNCAO" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "$FUNCAO" >/dev/null

# 2. Build e push — --provenance=false porque o Lambda não aceita índice OCI
aws ecr get-login-password | docker login --username AWS --password-stdin "$REGISTRY" >/dev/null
docker build --provenance=false -f agente/Dockerfile --build-arg PROMPT_VERSAO="$VERSAO" -t "$IMAGEM" . >&2
docker push "$IMAGEM" >&2

# 3. Função: cria na primeira vez (com a LabRole do Academy), senão atualiza código e configuração
if aws lambda get-function --function-name "$FUNCAO" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$FUNCAO" --image-uri "$IMAGEM" >/dev/null
  aws lambda wait function-updated-v2 --function-name "$FUNCAO"
  aws lambda update-function-configuration --function-name "$FUNCAO" --environment "file://$AMBIENTE" >/dev/null
  aws lambda wait function-updated-v2 --function-name "$FUNCAO"
else
  aws lambda create-function --function-name "$FUNCAO" --package-type Image \
    --code ImageUri="$IMAGEM" --role "arn:aws:iam::$CONTA:role/LabRole" \
    --memory-size 1024 --timeout 60 --environment "file://$AMBIENTE" >/dev/null
  aws lambda wait function-active-v2 --function-name "$FUNCAO"
fi

# 4. Versão imutável: código + configuração congelados com um número
aws lambda publish-version --function-name "$FUNCAO" --description "$VERSAO" --query Version --output text
