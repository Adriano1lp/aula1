"""Provedor do juiz de fidelidade para o promptfoo (grader do `llm-rubric`).

Lê a configuração de variáveis de ambiente, porque o promptfoo não renderiza `{{ env... }}` dentro
da configuração do provedor-juiz:

    LLM_JUIZ_BASE_URL   endpoint compatível com a API da OpenAI (padrão: Ollama local)
    LLM_JUIZ_MODELO     modelo juiz (padrão: qwen2.5:3b — fraco; prefira um modelo maior)
    LLM_JUIZ_API_KEY    chave (padrão: "ollama")
"""

import os

_cliente = None


def call_api(prompt, options, context):
    global _cliente
    try:
        if _cliente is None:
            from openai import OpenAI

            _cliente = OpenAI(
                base_url=os.environ.get("LLM_JUIZ_BASE_URL") or "http://localhost:11434/v1",
                api_key=os.environ.get("LLM_JUIZ_API_KEY") or "ollama",
            )
        resposta = _cliente.chat.completions.create(
            model=os.environ.get("LLM_JUIZ_MODELO") or "qwen2.5:3b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=300,
        )
        return {"output": resposta.choices[0].message.content or ""}
    except Exception as erro:  # erro do juiz vira reprovação, não derruba a avaliação inteira
        return {"error": f"{type(erro).__name__}: {erro}"}
