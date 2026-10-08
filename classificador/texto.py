"""Limpeza de texto compartilhada entre treino e serviço.

Ser o MESMO código no treino e na inferência evita o bug clássico de
"features reescritas em produção" (training-serving skew) da Aula 1.
"""

import re
import unicodedata

_URL = re.compile(r"https?://\S+")
_NAO_PALAVRA = re.compile(r"[^a-z0-9 ]+")
_ESPACOS = re.compile(r"\s+")


def remover_acentos(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normal if not unicodedata.combining(c))


def limpar(texto: str) -> str:
    """Minúsculas, sem URL, sem acento, sem emoji/pontuação, espaços únicos."""
    texto = _URL.sub(" ", texto.lower())
    texto = remover_acentos(texto)
    texto = _NAO_PALAVRA.sub(" ", texto)
    return _ESPACOS.sub(" ", texto).strip()


def so_emojis(texto: str) -> bool:
    """True quando não sobra nenhuma palavra depois da limpeza."""
    return limpar(texto) == ""
