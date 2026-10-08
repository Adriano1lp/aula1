# Imagem do agente para o AWS Lambda (deploy da Aula 6 no AWS Academy).
# Build a partir da raiz do repositório:
#   docker build --provenance=false -f agente/Dockerfile -t agente .
FROM public.ecr.aws/lambda/python:3.12

COPY agente/requirements-lambda.txt .
RUN pip install --no-cache-dir -r requirements-lambda.txt

# Só o que roda em produção: o agente, os prompts e as políticas (nada de testes, gate ou promptfoo)
COPY agente/atendimento.py agente/llm.py agente/lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY agente/prompts ${LAMBDA_TASK_ROOT}/prompts
COPY agente/politicas ${LAMBDA_TASK_ROOT}/politicas

ARG PROMPT_VERSAO=local
ENV PROMPT_VERSAO=${PROMPT_VERSAO}

CMD ["lambda_handler.handler"]
