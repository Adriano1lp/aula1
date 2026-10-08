"""Handler do AWS Lambda (Function URL) para o agente — o deploy do capstone no AWS Academy.

    GET  /          → saúde (versão do prompt e do modelo)
    POST /chamado   → {"texto": "..."}  →  o dicionário de atendimento.atender()

É o mesmo contrato da API FastAPI (app.py, usada no Azure), só que sem servidor: uma função que
continua disponível entre as sessões do Learner Lab (só as EC2 são paradas no "End Lab").
"""

import json

import atendimento
import llm


def _resposta(status: int, corpo: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(corpo, ensure_ascii=False),
    }


def _metodo_e_caminho(evento: dict) -> tuple[str, str]:
    http = (evento.get("requestContext") or {}).get("http") or {}
    metodo = (http.get("method") or evento.get("httpMethod") or "GET").upper()
    caminho = http.get("path") or evento.get("rawPath") or evento.get("path") or "/"
    return metodo, caminho.rstrip("/") or "/"


def handler(evento, contexto=None):
    metodo, caminho = _metodo_e_caminho(evento)

    if metodo == "GET":
        modelo = f"{llm.PROVEDOR}:{llm.MODELO}"
        return _resposta(200, {"status": "ok", "prompt_versao": atendimento.PROMPT_VERSAO, "modelo": modelo})

    if metodo == "POST" and caminho in ("/", "/chamado"):
        try:
            texto = json.loads(evento.get("body") or "{}")["texto"]
        except (KeyError, TypeError, json.JSONDecodeError):
            return _resposta(400, {"erro": 'envie {"texto": "..."}'})
        try:
            return _resposta(200, atendimento.atender(texto))
        except Exception as erro:  # falha do LLM não pode virar 502 sem explicação
            return _resposta(502, {"erro": f"falha ao atender: {type(erro).__name__}: {erro}"})

    return _resposta(404, {"erro": "rota não encontrada"})
