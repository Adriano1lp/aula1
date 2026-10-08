"""Aula 5 — treina o classificador, registra no MLflow e marca como "candidato".

    python mlops/registrar_modelo.py                    # hiperparâmetros padrão
    python mlops/registrar_modelo.py --C 1.0 --ngram 1  # outro experimento

Onde fica o MLflow (MLFLOW_TRACKING_URI):
- http://<ip-do-ec2>:5000   servidor no AWS Academy (mlops/servidor-mlflow-ec2.sh)
- sem a variável           arquivo local mlflow.db (100% gratuito, no Codespaces)
"""

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import mlflow
import pandas as pd
from mlflow import MlflowClient

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ / "classificador"))

import treino  # noqa: E402

NOME = "classificador-avaliacoes"


def sha256(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()[:12]


def commit_atual() -> str:
    resultado = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    return resultado.stdout.strip() or "desconhecido"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dados", type=Path, default=RAIZ / "classificador" / "dados" / "avaliacoes.csv")
    parser.add_argument("--C", type=float, default=treino.PARAMS["C"])
    parser.add_argument("--ngram", type=int, default=treino.PARAMS["ngram_max"])
    args = parser.parse_args()

    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", f"sqlite:///{RAIZ / 'mlflow.db'}"))
    mlflow.set_experiment("classificador-avaliacoes")
    validacao = RAIZ / "classificador" / "dados" / "validacao.csv"
    params = {"C": args.C, "ngram_max": args.ngram}

    with mlflow.start_run() as run:
        modelo = treino.treinar(pd.read_csv(args.dados), params)
        metricas = treino.avaliar(modelo, pd.read_csv(validacao))

        mlflow.log_params(params)
        mlflow.log_metric("f1_macro", metricas["f1_macro"])
        for classe, f1 in metricas["f1_por_classe"].items():
            mlflow.log_metric(f"f1_{classe}", f1)
        # Linhagem: de qual código e de quais dados este modelo saiu
        mlflow.set_tags(
            {
                "git_commit": commit_atual(),
                "dados_arquivo": args.dados.name,
                "dados_sha256": sha256(args.dados),
                "validacao_sha256": sha256(validacao),
            }
        )
        # O MLflow 3 serializa com skops e só aceita funções declaradas como confiáveis:
        # a limpeza de texto é nossa, então ela entra na lista explicitamente.
        info = mlflow.sklearn.log_model(
            modelo, name="modelo", registered_model_name=NOME, skops_trusted_types=["texto.limpar"]
        )

    versao = info.registered_model_version
    MlflowClient().set_registered_model_alias(NOME, "candidato", versao)
    print(f"Run {run.info.run_id} · F1 macro {metricas['f1_macro']} · {metricas['f1_por_classe']}")
    print(f"Registrado: {NOME} versão {versao} → alias @candidato")


if __name__ == "__main__":
    main()
