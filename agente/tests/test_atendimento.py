"""Testes unitários do agente: determinísticos, sem LLM (provedor simulado), rodam em todo PR."""

import json

import pytest

import atendimento
import llm


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    monkeypatch.setattr(llm, "PROVEDOR", "simulado")


def test_todas_as_categorias_tem_politica():
    for categoria in atendimento.CATEGORIAS:
        assert f"{categoria}.md" in atendimento.politicas()


def test_prompts_tem_as_variaveis_esperadas():
    assert "{{chamado}}" in atendimento.prompt("roteador")
    for variavel in ["categoria", "documento", "contexto", "chamado"]:
        assert "{{" + variavel + "}}" in atendimento.prompt("especialista")


def test_preencher_substitui_todas_as_variaveis():
    texto = atendimento.preencher("{{a}} e {{b}}", a="1", b="2")
    assert texto == "1 e 2"


def test_recuperacao_encontra_a_politica_certa():
    trecho = atendimento.recuperar("quero devolver, me arrependi da compra", "devolucao_ressarcimento")
    assert trecho["documento"] == "devolucao_ressarcimento.md"


@pytest.mark.parametrize("saida", ['{"categoria": "xyz"}', "não sei", ""])
def test_categoria_invalida_vira_indefinida(monkeypatch, saida):
    monkeypatch.setattr(llm, "completar", lambda *a, **k: saida)
    assert atendimento.classificar("qualquer coisa") == "indefinida"


def test_categoria_com_texto_em_volta(monkeypatch):
    monkeypatch.setattr(llm, "completar", lambda *a, **k: 'Claro! {"categoria": "entrega"}')
    assert atendimento.classificar("cadê meu pedido") == "entrega"


def test_atender_devolve_o_contrato_esperado():
    resultado = atendimento.atender("Abri a caixa e estava vazia")
    assert set(resultado) == {"categoria", "documento", "resposta", "prompt_versao", "modelo"}
    assert json.dumps(resultado)  # serializável para o promptfoo e para a API
