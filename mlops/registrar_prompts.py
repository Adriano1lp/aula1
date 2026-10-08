"""Aula 5 — registra os prompts do agente no Prompt Registry do MLflow.

    python mlops/registrar_prompts.py -m "v12: política de reembolso mais restrita"
    python mlops/registrar_prompts.py --alias producao --versao 3   # promove uma versão

O Git continua sendo a fonte do texto (é lá que o PR é revisado). O registry
guarda cada versão com o commit de origem e as métricas do agent gate, e os
aliases dizem qual versão cada ambiente usa: o agente carrega com
PROMPT_FONTE=mlflow e PROMPT_ALIAS=staging|producao.
"""

import argparse
import json
import os
import subprocess
from pathlib import Path

import mlflow

RAIZ = Path(__file__).parent.parent
PROMPTS = ["roteador", "especialista"]


def metricas_do_gate(caminho: Path) -> dict:
    """Médias por camada do último agent gate, se o resultado estiver disponível."""
    if not caminho.exists():
        return {}
    resultados = json.loads(caminho.read_text())["results"]["results"]
    medias = {}
    for camada in ["roteamento", "recuperacao", "resposta"]:
        acertos = sum((r.get("namedScores") or {}).get(camada, 0) for r in resultados)
        medias[f"gate_{camada}"] = f"{acertos / len(resultados):.2f}"
    return medias


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--mensagem", default="registro a partir do Git")
    parser.add_argument("--alias", help="só move o alias (staging|producao) para --versao")
    parser.add_argument("--versao", type=int)
    parser.add_argument("--resultado-gate", type=Path, default=RAIZ / "resultado-eval.json")
    args = parser.parse_args()

    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", f"sqlite:///{RAIZ / 'mlflow.db'}"))

    if args.alias:
        for nome in PROMPTS:
            mlflow.genai.set_prompt_alias(f"quantum-{nome}", alias=args.alias, version=args.versao)
        print(f"@{args.alias} → versão {args.versao} em {', '.join(PROMPTS)}")
        return

    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    tags = {"git_commit": commit or "desconhecido", **metricas_do_gate(args.resultado_gate)}
    for nome in PROMPTS:
        texto = (RAIZ / "agente" / "prompts" / f"{nome}.txt").read_text(encoding="utf-8")
        prompt = mlflow.genai.register_prompt(
            name=f"quantum-{nome}", template=texto, commit_message=args.mensagem, tags=tags
        )
        print(f"quantum-{nome} versão {prompt.version} · commit {tags['git_commit']}")


if __name__ == "__main__":
    main()
