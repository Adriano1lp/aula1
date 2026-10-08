"""Smoke test da API que vai para o Azure Web Apps."""

from fastapi.testclient import TestClient

import app
import llm


def test_saude():
    assert TestClient(app.app).get("/").json()["status"] == "ok"


def test_chamado(monkeypatch):
    monkeypatch.setattr(llm, "PROVEDOR", "simulado")
    resposta = TestClient(app.app).post("/chamado", json={"texto": "meu pedido está atrasado"})
    assert resposta.status_code == 200
    assert resposta.json()["categoria"] == "entrega"
