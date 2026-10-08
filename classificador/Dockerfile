# Imagem do classificador para o AWS Lambda (etapa "build" do pipeline).
# Build a partir da raiz do repositório, depois do treino:
#   docker build --provenance=false -f classificador/Dockerfile -t classificador .
FROM public.ecr.aws/lambda/python:3.12

COPY classificador/requirements-lambda.txt .
RUN pip install --no-cache-dir -r requirements-lambda.txt

# texto.py precisa estar junto: o modelo serializado chama texto.limpar
COPY classificador/texto.py classificador/servico.py ${LAMBDA_TASK_ROOT}/
COPY artefatos/modelo.joblib ${LAMBDA_TASK_ROOT}/artefatos/modelo.joblib

ARG MODELO_VERSAO=local
ENV MODELO_VERSAO=${MODELO_VERSAO} \
    MODELO_CAMINHO=${LAMBDA_TASK_ROOT}/artefatos/modelo.joblib

CMD ["servico.handler"]
