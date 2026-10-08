"""Treina o classificador de avaliações e mede no conjunto de validação.

    python classificador/treino.py                       # base padrão
    python classificador/treino.py --dados classificador/dados/lote-novo.csv

Gera em artefatos/: modelo.joblib e metricas.json (lido pelo model gate).
"""

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline

from texto import limpar

PASTA = Path(__file__).parent
CLASSES = ["positiva", "negativa", "neutra"]
PARAMS = {"ngram_max": 2, "C": 4.0}


def treinar(dados: pd.DataFrame, params: dict = PARAMS) -> Pipeline:
    modelo = Pipeline(
        [
            ("tfidf", TfidfVectorizer(preprocessor=limpar, ngram_range=(1, params["ngram_max"]))),
            ("clf", LogisticRegression(C=params["C"], max_iter=1000)),
        ]
    )
    return modelo.fit(dados["texto"], dados["rotulo"])


def avaliar(modelo: Pipeline, dados: pd.DataFrame) -> dict:
    previsto = modelo.predict(dados["texto"])
    por_classe = f1_score(dados["rotulo"], previsto, labels=CLASSES, average=None)
    return {
        "f1_macro": round(float(f1_score(dados["rotulo"], previsto, average="macro")), 4),
        "f1_por_classe": {c: round(float(v), 4) for c, v in zip(CLASSES, por_classe)},
        "n_validacao": len(dados),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dados", default=PASTA / "dados" / "avaliacoes.csv")
    parser.add_argument("--validacao", default=PASTA / "dados" / "validacao.csv")
    parser.add_argument("--saida", default="artefatos")
    args = parser.parse_args()

    modelo = treinar(pd.read_csv(args.dados))
    metricas = avaliar(modelo, pd.read_csv(args.validacao))

    saida = Path(args.saida)
    saida.mkdir(exist_ok=True)
    joblib.dump(modelo, saida / "modelo.joblib")
    (saida / "metricas.json").write_text(json.dumps(metricas, indent=2))
    print(json.dumps(metricas, indent=2))


if __name__ == "__main__":
    main()
