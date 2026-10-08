"""Gera as avaliações sintéticas de produto usadas nos laboratórios.

Rode só se quiser recriar os CSVs (eles já vêm versionados):

    python classificador/dados/gerar_dados.py

Saídas:
- avaliacoes.csv  base de treino (proporção saudável entre as classes)
- validacao.csv   conjunto fixo do model gate (nunca entra no treino)
- lote-novo.csv   o lote "que parece normal" da Aula 2, proposta B:
                  30% dos textos só com emojis e a classe neutra em ~8%
"""

import csv
import random
from pathlib import Path

PASTA = Path(__file__).parent

PRODUTOS = [
    "fone de ouvido",
    "notebook",
    "cafeteira",
    "tênis",
    "mochila",
    "celular",
    "smartwatch",
    "liquidificador",
    "cadeira gamer",
    "teclado",
    "monitor",
    "air fryer",
    "camiseta",
    "panela",
    "carregador",
    "mouse",
    "livro",
]

POSITIVAS = [
    "Adorei o {p}, superou minhas expectativas",
    "O {p} chegou antes do prazo e funciona perfeitamente",
    "Excelente {p}, recomendo para todo mundo",
    "Qualidade muito boa, o {p} vale cada centavo",
    "Comprei o {p} e estou muito satisfeito",
    "Ótimo custo-benefício, o {p} é bem acabado",
    "Melhor {p} que já tive, nota dez",
    "O {p} é lindo e muito confortável",
    "Entrega rápida e o {p} veio impecável",
    "Gostei bastante do {p}, compraria de novo",
]

NEGATIVAS = [
    "O {p} quebrou na primeira semana, péssimo",
    "Horrível, o {p} veio com defeito e ninguém responde",
    "Não recomendo esse {p}, dinheiro jogado fora",
    "O {p} chegou atrasado e com a caixa amassada",
    "Produto ruim, o {p} parou de funcionar em dois dias",
    "Me arrependi de comprar o {p}, qualidade péssima",
    "O {p} é muito diferente da foto, decepcionante",
    "Pedi reembolso do {p}, não funciona direito",
    "Pior {p} que já comprei, esquenta demais",
    "O {p} veio faltando peça e o suporte é lento",
]

NEUTRAS = [
    "O {p} chegou dentro do prazo, ainda estou testando",
    "É um {p} comum, faz o que promete e nada além",
    "O {p} é ok para o preço, nada de especial",
    "Recebi o {p}, a embalagem estava normal",
    "O {p} tem pontos bons e ruins, achei mediano",
    "Uso o {p} há uma semana, por enquanto sem opinião formada",
    "O {p} é igual ao que eu tinha antes",
    "Produto conforme descrito, o {p} é básico",
    "O {p} atende, mas poderia ser um pouco melhor",
    "Nem bom nem ruim, o {p} cumpre o básico",
]

EXTRAS = ["", "", "", " 😀", " 👍", " 😡", " !!!", " kkk", " https://loja.exemplo/p/123"]
SO_EMOJIS = ["😍😍😍", "👍", "😡😡", "🙂", "💔", "🔥🔥", "😐", "👎👎", "⭐⭐⭐⭐⭐", "🤔"]


def frase(modelos: list[str], rng: random.Random) -> str:
    texto = rng.choice(modelos).format(p=rng.choice(PRODUTOS))
    # ruído realista: caixa, extras e, às vezes, mistura de sentimento
    if rng.random() < 0.15:
        texto = texto.lower()
    return texto + rng.choice(EXTRAS)


def gerar(n: int, pesos: dict[str, float], frac_emojis: float, rng: random.Random) -> list[dict]:
    modelos = {"positiva": POSITIVAS, "negativa": NEGATIVAS, "neutra": NEUTRAS}
    linhas = []
    for _ in range(n):
        rotulo = rng.choices(list(pesos), weights=list(pesos.values()))[0]
        if rng.random() < frac_emojis:
            texto = rng.choice(SO_EMOJIS)
        else:
            texto = frase(modelos[rotulo], rng)
            # 30% das avaliações misturam um trecho de outra classe (ambiguidade real)
            if rng.random() < 0.30:
                outra = rng.choice([r for r in modelos if r != rotulo])
                texto += ", mas " + frase(modelos[outra], rng).lower()
        # 8% de rótulo trocado: anotação humana nunca é perfeita
        if rng.random() < 0.08:
            rotulo = rng.choice([r for r in modelos if r != rotulo])
        linhas.append({"texto": texto, "rotulo": rotulo})
    return linhas


def salvar(nome: str, linhas: list[dict]) -> None:
    with open(PASTA / nome, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["texto", "rotulo"])
        w.writeheader()
        w.writerows(linhas)
    print(f"{nome}: {len(linhas)} linhas")


if __name__ == "__main__":
    rng = random.Random(42)
    saudavel = {"positiva": 0.40, "negativa": 0.35, "neutra": 0.25}
    salvar("avaliacoes.csv", gerar(900, saudavel, 0.02, rng))
    salvar("validacao.csv", gerar(300, saudavel, 0.02, rng))
    salvar("lote-novo.csv", gerar(600, {"positiva": 0.52, "negativa": 0.40, "neutra": 0.04}, 0.30, rng))
