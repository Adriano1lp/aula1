"""Smoke test do serviço com o modelo recém-treinado (roda depois do treino)."""

import json
from pathlib import Path

import pytest

import servico

pytestmark = pytest.mark.skipif(not Path("artefatos/modelo.joblib").exists(), reason="rode o treino antes")


def test_classifica_texto_valido():
    resposta = servico.handler({"body": json.dumps({"texto": "Adorei, chegou rápido"})})
    corpo = json.loads(resposta["body"])
    assert resposta["statusCode"] == 200
    assert corpo["rotulo"] in {"positiva", "negativa", "neutra"}
    assert 0 <= corpo["confianca"] <= 1


def test_rejeita_corpo_invalido():
    assert servico.handler({"body": "{}"})["statusCode"] == 400
