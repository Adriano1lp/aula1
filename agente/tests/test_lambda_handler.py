"""Testes do handler do Lambda: contrato HTTP sem rede e sem LLM (provedor simulado)."""

import json

import pytest

import lambda_handler
import llm


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    monkeypatch.setattr(llm, "PROVEDOR", "simulado")


def evento(metodo, caminho="/", corpo=None):
    return {
        "rawPath": caminho,
        "requestContext": {"http": {"method": metodo, "path": caminho}},
        "body": json.dumps(corpo) if corpo is not None else None,
    }


def test_saude():
    resposta = lambda_handler.handler(evento("GET"))
    assert resposta["statusCode"] == 200
    assert json.loads(resposta["body"])["status"] == "ok"


def test_chamado_valido():
    resposta = lambda_handler.handler(evento("POST", "/chamado", {"texto": "meu pedido está atrasado"}))
    corpo = json.loads(resposta["body"])
    assert resposta["statusCode"] == 200
    assert corpo["categoria"] == "entrega"


def test_post_na_raiz_tambem_atende():
    assert (
        lambda_handler.handler(evento("POST", "/", {"texto": "meu pedido está atrasado"}))["statusCode"]
        == 200
    )


@pytest.mark.parametrize("corpo", [{}, {"outro": 1}])
def test_corpo_invalido(corpo):
    assert lambda_handler.handler(evento("POST", "/chamado", corpo))["statusCode"] == 400


def test_rota_inexistente():
    assert lambda_handler.handler(evento("POST", "/nada", {"texto": "x"}))["statusCode"] == 404


def test_falha_do_llm_vira_502(monkeypatch):
    def quebra(*args, **kwargs):
        raise RuntimeError("limite do provedor")

    monkeypatch.setattr(llm, "completar", quebra)
    resposta = lambda_handler.handler(evento("POST", "/chamado", {"texto": "meu pedido está atrasado"}))
    assert resposta["statusCode"] == 502
    assert "limite do provedor" in json.loads(resposta["body"])["erro"]
