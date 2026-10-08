"""Aula 5 — promove o @candidato a @producao se passar no model gate.

    python mlops/promover.py              # tenta promover
    python mlops/promover.py --rollback   # @producao volta para a versão @anterior

Os aliases substituem os antigos "stages" (Staging/Production/Archived) do MLflow:
@candidato → @producao, e a versão que saiu de produção fica como @anterior.
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import mlflow
from mlflow import MlflowClient
from mlflow.exceptions import MlflowException

RAIZ = Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ / "classificador"))

import model_gate  # noqa: E402

NOME = "classificador-avaliacoes"
CLASSES = ["positiva", "negativa", "neutra"]


def versao(client: MlflowClient, alias: str):
    try:
        return client.get_model_version_by_alias(NOME, alias)
    except MlflowException:
        return None


def metricas(client: MlflowClient, mv) -> dict:
    m = client.get_run(mv.run_id).data.metrics
    return {"f1_macro": m["f1_macro"], "f1_por_classe": {c: m[f"f1_{c}"] for c in CLASSES}}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rollback", action="store_true")
    args = parser.parse_args()

    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", f"sqlite:///{RAIZ / 'mlflow.db'}"))
    client = MlflowClient()
    producao = versao(client, "producao")

    if args.rollback:
        anterior = versao(client, "anterior")
        if not anterior:
            sys.exit("Não há versão @anterior para voltar.")
        client.set_registered_model_alias(NOME, "producao", anterior.version)
        print(f"↩️  Rollback: @producao agora é a versão {anterior.version} (era {producao.version})")
        return

    candidato = versao(client, "candidato")
    if not candidato:
        sys.exit("Nenhuma versão @candidato — rode mlops/registrar_modelo.py antes.")
    if producao and producao.version == candidato.version:
        sys.exit(f"A versão {candidato.version} já está em produção.")

    # Sem produção ainda: compara só com os mínimos absolutos
    referencia = metricas(client, producao) if producao else {"f1_macro": 0, "f1_por_classe": {}}
    motivos = model_gate.avaliar(metricas(client, candidato), referencia)
    if motivos:
        print(f"❌ Versão {candidato.version} NÃO promovida:")
        print("\n".join(f"   - {m}" for m in motivos))
        sys.exit(1)

    if producao:
        client.set_registered_model_alias(NOME, "anterior", producao.version)
    client.set_registered_model_alias(NOME, "producao", candidato.version)
    quem = os.environ.get("GITHUB_ACTOR") or os.environ.get("USER", "desconhecido")
    client.set_model_version_tag(NOME, candidato.version, "aprovado_por", quem)
    client.set_model_version_tag(
        NOME, candidato.version, "promovido_em", datetime.now(timezone.utc).isoformat()
    )
    print(
        f"✅ Versão {candidato.version} promovida a @producao"
        + (f" (@anterior = {producao.version})" if producao else "")
    )
    print(f'   Carregar em produção: mlflow.sklearn.load_model("models:/{NOME}@producao")')


if __name__ == "__main__":
    main()
