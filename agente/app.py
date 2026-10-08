"""API do agente — é o que vai para o Azure Web Apps (Aula 6).

uvicorn app:app --reload            (de dentro de agente/)
POST /chamado {"texto": "..."}
"""

from fastapi import FastAPI
from pydantic import BaseModel

import atendimento
import llm

app = FastAPI(title="Atendimento Quantum Commerce")


class Chamado(BaseModel):
    texto: str


@app.get("/")
def saude() -> dict:
    modelo = f"{llm.PROVEDOR}:{llm.MODELO}"
    return {"status": "ok", "prompt_versao": atendimento.PROMPT_VERSAO, "modelo": modelo}


@app.post("/chamado")
def chamado(dados: Chamado) -> dict:
    return atendimento.atender(dados.texto)
