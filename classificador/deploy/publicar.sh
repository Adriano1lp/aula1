#!/usr/bin/env bash
# Publica uma NOVA VERSÃO do classificador no AWS Lambda (sem mudar o tráfego).
#
#   classificador/deploy/publicar.sh            # usa o SHA do commit como versão
#   ERRO_SIMULADO=0.2 classificador/deploy/publicar.sh   # Aula 4: versão "ruim"
#
# Pré-requisitos: credenciais do AWS Academy no ambiente (ver roteiros/setup-aws-academy.md),
# Docker e o modelo treinado em artefatos/modelo.joblib.
# Imprime o número da versão publicada na última linha.
set -euo pipefail

export AWS_REGION="${AWS_REGION:-us-east-1}" AWS_DEFAULT_REGION="${AWS_REGION:-us-east-1}"
FUNCAO="${FUNCAO:-classificador-avaliacoes}"
VERSAO="${MODELO_VERSAO:-$(git rev-parse --short HEAD)}"
ERRO_SIMULADO="${ERRO_SIMULADO:-0}"

# O Dockerfile copia o modelo treinado: sem ele o build falharia só depois do login no ECR.
if [ ! -f artefatos/modelo.joblib ]; then
  echo "ERRO: artefatos/modelo.joblib não existe (rode este script na raiz do repositório)." >&2
  echo "O Dockerfile copia o modelo treinado; gere-o antes:" >&2
  echo "  python -m venv .venv && source .venv/bin/activate" >&2
  echo "  pip install -r requirements.txt" >&2
  echo "  python classificador/treino.py" >&2
  exit 1
fi

CONTA=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="$CONTA.dkr.ecr.$AWS_REGION.amazonaws.com"
IMAGEM="$REGISTRY/$FUNCAO:$VERSAO"

# 1. Repositório de imagens (ECR), criado na primeira vez
aws ecr describe-repositories --repository-names "$FUNCAO" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "$FUNCAO" >/dev/null

# 2. Build e push — --provenance=false porque o Lambda não aceita índice OCI
aws ecr get-login-password | docker login --username AWS --password-stdin "$REGISTRY" >/dev/null
docker build --provenance=false -f classificador/Dockerfile --build-arg MODELO_VERSAO="$VERSAO" -t "$IMAGEM" . >&2
docker push "$IMAGEM" >&2

# 3. Função: cria na primeira vez (com a LabRole do Academy), senão atualiza o código
AMBIENTE="Variables={ERRO_SIMULADO=$ERRO_SIMULADO}"
if aws lambda get-function --function-name "$FUNCAO" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$FUNCAO" --image-uri "$IMAGEM" >/dev/null
  aws lambda wait function-updated-v2 --function-name "$FUNCAO"
  aws lambda update-function-configuration --function-name "$FUNCAO" --environment "$AMBIENTE" >/dev/null
  aws lambda wait function-updated-v2 --function-name "$FUNCAO"
else
  aws lambda create-function --function-name "$FUNCAO" --package-type Image \
    --code ImageUri="$IMAGEM" --role "arn:aws:iam::$CONTA:role/LabRole" \
    --memory-size 1024 --timeout 30 --environment "$AMBIENTE" >/dev/null
  aws lambda wait function-active-v2 --function-name "$FUNCAO"
fi

# 4. Versão imutável: código + configuração congelados com um número
aws lambda publish-version --function-name "$FUNCAO" --description "$VERSAO" \
  --query Version --output text
