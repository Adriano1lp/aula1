"""Ponte entre o promptfoo e o agente: cada caso do golden dataset vira uma chamada a atender()."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import atendimento  # noqa: E402


def call_api(prompt, options, context):
    try:
        resultado = atendimento.atender(context["vars"]["chamado"])
    except Exception as erro:  # o erro vira resultado reprovado, não derruba a avaliação inteira
        return {"error": f"{type(erro).__name__}: {erro}"}
    return {"output": json.dumps(resultado, ensure_ascii=False)}
