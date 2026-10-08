"""Cliente de LLM com troca de provedor por variável de ambiente.

LLM_PROVEDOR (na ordem de preferência da disciplina):
- bedrock    1º AWS Academy, se o Bedrock estiver liberado no seu Learner Lab.
             Usa as credenciais AWS do ambiente. LLM_MODELO padrão: amazon.nova-micro-v1:0
- openai     Qualquer API compatível com OpenAI, via LLM_BASE_URL e LLM_API_KEY:
             2º Microsoft Foundry / Azure OpenAI (crédito do Azure for Students):
                LLM_BASE_URL=https://<recurso>.openai.azure.com/openai/v1/
             3º Ollama — 100% gratuito, roda no runner do Actions e no Codespaces
                (é o padrão: LLM_BASE_URL=http://localhost:11434/v1)
- simulado   Sem rede: regras por palavra-chave. Serve para testes e para ver um
             "modelo ruim" sendo barrado pelo agent gate.

(O GitHub Models foi aposentado em 30/07/2026 e não é mais uma opção.)
"""

import json
import os
import re

PROVEDOR = os.environ.get("LLM_PROVEDOR", "openai")
_PADRAO = {
    "bedrock": "amazon.nova-micro-v1:0",
    "openai": "qwen2.5:3b",
    "simulado": "regras-v1",
}
MODELO = os.environ.get("LLM_MODELO", _PADRAO.get(PROVEDOR, ""))
_cliente = None


def completar(prompt: str, temperatura: float = 0.0, max_tokens: int = 400) -> str:
    if PROVEDOR == "simulado":
        return _simulado(prompt)
    if PROVEDOR == "bedrock":
        return _bedrock(prompt, temperatura, max_tokens)
    if PROVEDOR == "openai":
        return _openai(prompt, temperatura, max_tokens)
    raise ValueError(f"LLM_PROVEDOR desconhecido: {PROVEDOR}")


def _openai(prompt: str, temperatura: float, max_tokens: int) -> str:
    global _cliente
    if _cliente is None:
        from openai import OpenAI

        _cliente = OpenAI(
            base_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.environ.get("LLM_API_KEY", "ollama"),
        )
    resposta = _cliente.chat.completions.create(
        model=MODELO,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperatura,
        max_tokens=max_tokens,
        seed=int(os.environ.get("LLM_SEED", "42")),  # reduz o ruído entre execuções do gate
    )
    return resposta.choices[0].message.content or ""


def _bedrock(prompt: str, temperatura: float, max_tokens: int) -> str:
    global _cliente
    if _cliente is None:
        import boto3

        _cliente = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    resposta = _cliente.converse(
        modelId=MODELO,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"temperature": temperatura, "maxTokens": max_tokens},
    )
    return resposta["output"]["message"]["content"][0]["text"]


# --- provedor simulado -------------------------------------------------------

_PALAVRAS = {
    "fraude_vendedor": ["golpe", "pix", "transferencia", "caixa vazia", "vazia", "enganado", "fraude"],
    "falsificado": ["falso", "falsificad", "replica", "pirata", "imitacao", "original"],
    "artigo_proibido": ["proibid", "remedio", "anvisa", "munic", "arma", "papagaio", "denunciar um anuncio"],
    "devolucao_ressarcimento": ["arrependi", "devolver", "devolvi", "estorno", "etiqueta", "reembolso"],
    "divergente_defeito": ["defeito", "quebrad", "parou", "errado", "veio", "diferente"],
    "entrega": ["atras", "rastreio", "rastreamento", "prazo", "chega", "despach"],
}


def _sem_acento(texto: str) -> str:
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c))


def _simulado(prompt: str) -> str:
    if "Responda APENAS com JSON" in prompt:
        chamado = _sem_acento(prompt.rsplit("Chamado:", 1)[-1])
        for categoria, palavras in _PALAVRAS.items():
            if any(p in chamado for p in palavras):
                return json.dumps({"categoria": categoria})
        return json.dumps({"categoria": "entrega"})
    # especialista: devolve a frase da política com mais palavras em comum com o chamado
    politica = re.search(r"\):\n(.+?)\n\nChamado do cliente: (.+)", prompt, re.S)
    if not politica:
        return "Vou encaminhar seu chamado para um atendente humano."
    texto, chamado = politica.groups()
    palavras = set(_sem_acento(chamado).split())
    linhas = [linha for linha in texto.splitlines() if not linha.startswith("#")]
    frases = [f.strip() for linha in linhas for f in linha.split(". ")]
    melhor = max((f for f in frases if f), key=lambda f: len(palavras & set(_sem_acento(f).split())))
    return melhor.rstrip(".") + "."
