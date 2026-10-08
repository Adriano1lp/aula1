"""Agente de atendimento da Quantum Commerce (versão mínima para os laboratórios).

Roteador (LLM) → recuperação (RAG por palavras sobre politicas/) → especialista (LLM).

É um substituto simples do multiagente LangGraph/CrewAI construído nas outras
disciplinas do MBA: o que importa aqui é a ESTEIRA que testa o agente, não o
agente em si. Para plugar o agente do seu grupo, mantenha a função atender()
devolvendo o mesmo dicionário.
"""

import json
import os
import re
import unicodedata
from functools import cache
from pathlib import Path

import llm

PASTA = Path(__file__).parent
CATEGORIAS = [
    "entrega",
    "divergente_defeito",
    "fraude_vendedor",
    "falsificado",
    "artigo_proibido",
    "devolucao_ressarcimento",
]
# Versão do prompt ativa — no GitOps (Aula 3) ela vem do inference-config
PROMPT_VERSAO = os.environ.get("PROMPT_VERSAO", "arquivo")
_STOPWORDS = set(
    "a o e de da do das dos em no na nos nas um uma para por com que se eu me meu minha ja ou".split()
)


def normalizar(texto: str) -> set[str]:
    texto = "".join(c for c in unicodedata.normalize("NFKD", texto.lower()) if not unicodedata.combining(c))
    return {p for p in re.findall(r"[a-z0-9]+", texto) if len(p) > 2 and p not in _STOPWORDS}


@cache
def politicas() -> dict[str, str]:
    return {a.name: a.read_text(encoding="utf-8") for a in sorted((PASTA / "politicas").glob("*.md"))}


def recuperar(chamado: str, categoria: str) -> dict:
    """RAG mínimo: o documento de política com mais palavras em comum com o chamado.

    O documento da categoria escolhida pelo roteador ganha bônus — é o
    sub-agente especialista consultando primeiro a sua própria política.
    Troque por embeddings + base vetorial quando a base crescer.
    """
    palavras = normalizar(chamado)

    def pontos(documento: str) -> float:
        bonus = 3 if documento == f"{categoria}.md" else 0
        return len(palavras & normalizar(politicas()[documento])) + bonus

    melhor = max(politicas(), key=pontos)
    return {"documento": melhor, "texto": politicas()[melhor]}


@cache
def prompt(nome: str) -> str:
    """Lê o template. Com PROMPT_FONTE=mlflow, vem do Prompt Registry (Aula 5)."""
    if os.environ.get("PROMPT_FONTE") == "mlflow":
        import mlflow

        alias = os.environ.get("PROMPT_ALIAS", "producao")
        return mlflow.genai.load_prompt(f"prompts:/quantum-{nome}@{alias}").template
    return (PASTA / "prompts" / f"{nome}.txt").read_text(encoding="utf-8")


def preencher(template: str, **variaveis: str) -> str:
    for chave, valor in variaveis.items():
        template = template.replace("{{" + chave + "}}", valor)
    return template


def classificar(chamado: str) -> str:
    saida = llm.completar(preencher(prompt("roteador"), chamado=chamado), max_tokens=30)
    achado = re.search(r'"categoria"\s*:\s*"([a-z_]+)"', saida)
    categoria = achado.group(1) if achado else ""
    return categoria if categoria in CATEGORIAS else "indefinida"


def atender(chamado: str) -> dict:
    categoria = classificar(chamado)
    trecho = recuperar(chamado, categoria)
    resposta = llm.completar(
        preencher(
            prompt("especialista"),
            categoria=categoria,
            documento=trecho["documento"],
            contexto=trecho["texto"],
            chamado=chamado,
        ),
        max_tokens=160,
    )
    return {
        "categoria": categoria,
        "documento": trecho["documento"],
        "resposta": resposta.strip(),
        "prompt_versao": PROMPT_VERSAO,
        "modelo": f"{llm.PROVEDOR}:{llm.MODELO}",
    }


if __name__ == "__main__":
    import sys

    chamado = " ".join(sys.argv[1:]) or "Meu pedido está atrasado"
    print(json.dumps(atender(chamado), ensure_ascii=False, indent=2))
