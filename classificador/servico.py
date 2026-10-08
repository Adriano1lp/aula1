"""Serviço de inferência: handler do AWS Lambda (Function URL).

POST {"texto": "..."}  →  {"rotulo": "...", "confianca": 0.93, "versao": "..."}

A variável MODELO_VERSAO vem do pipeline (SHA do commit) e aparece na
resposta — é como, no canary da Aula 4, se vê qual versão atendeu.
"""

import json
import os
import random
from pathlib import Path

import joblib

VERSAO = os.environ.get("MODELO_VERSAO", "local")
# Aula 4: fração de requisições que falham de propósito, para ver o canary dar rollback
ERRO_SIMULADO = float(os.environ.get("ERRO_SIMULADO", "0"))
_modelo = None


def modelo():
    global _modelo
    if _modelo is None:
        caminho = Path(os.environ.get("MODELO_CAMINHO", "artefatos/modelo.joblib"))
        _modelo = joblib.load(caminho)
    return _modelo


def classificar(texto: str) -> dict:
    probs = modelo().predict_proba([texto])[0]
    melhor = probs.argmax()
    return {
        "rotulo": str(modelo().classes_[melhor]),
        "confianca": round(float(probs[melhor]), 4),
        "versao": VERSAO,
    }


def handler(evento, contexto=None):
    if random.random() < ERRO_SIMULADO:
        return {"statusCode": 500, "body": json.dumps({"erro": "falha simulada", "versao": VERSAO})}
    try:
        corpo = json.loads(evento.get("body") or "{}")
        texto = corpo["texto"]
    except (KeyError, json.JSONDecodeError):
        return {"statusCode": 400, "body": json.dumps({"erro": 'envie {"texto": "..."}'})}
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json", "x-modelo-versao": VERSAO},
        "body": json.dumps(classificar(texto), ensure_ascii=False),
    }
