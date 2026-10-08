"""Agent gate (Aula 6): decide se a mudança no agente pode ir para produção.

    python agente/agent_gate.py resultado-eval.json
    python agente/agent_gate.py resultado-eval.json --salvar-baseline   # na main, depois do deploy

Lê a saída do promptfoo e calcula, POR CATEGORIA de chamado, a taxa de acerto
de cada camada (roteamento, recuperação, resposta). Reprova se:
1. alguma categoria fica abaixo do piso (limites.yaml), ou
2. alguma categoria piora em relação à baseline além da tolerância de ruído —
   MESMO QUE A MÉDIA GERAL MELHORE (o caso fraude_vendedor do enunciado).

Override: com OVERRIDE_AGENT_GATE=<justificativa> o gate não bloqueia, mas
registra a exceção e quem a pediu no resumo da execução.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import yaml

PASTA = Path(__file__).parent
CAMADAS = ["roteamento", "recuperacao", "resposta"]


def taxas_por_categoria(resultado: dict) -> dict[str, dict[str, float]]:
    soma = defaultdict(lambda: defaultdict(float))
    casos = defaultdict(int)
    for r in resultado["results"]["results"]:
        categoria = r["vars"]["categoria"]
        casos[categoria] += 1
        for camada in CAMADAS:
            # erro de execução (timeout, limite do provedor) conta como reprovado
            soma[categoria][camada] += (r.get("namedScores") or {}).get(camada, 0)
    return {c: {k: round(soma[c][k] / casos[c], 3) for k in CAMADAS} for c in sorted(casos)}


def avaliar(taxas: dict, baseline: dict, limites: dict) -> list[str]:
    motivos = []
    for categoria, por_camada in taxas.items():
        for camada, taxa in por_camada.items():
            piso = limites["piso"][camada]
            if taxa < piso:
                motivos.append(f"{categoria}/{camada}: {taxa:.0%} abaixo do piso de {piso:.0%}")
            anterior = baseline.get(categoria, {}).get(camada)
            if anterior is not None and anterior - taxa > limites["tolerancia_ruido"]:
                motivos.append(f"{categoria}/{camada}: regrediu de {anterior:.0%} para {taxa:.0%}")
    return motivos


def media(taxas: dict, camada: str) -> float:
    return sum(t[camada] for t in taxas.values()) / len(taxas)


def resumo(taxas: dict, baseline: dict, motivos: list[str], override: str) -> str:
    linhas = ["## Agent gate", "", "| Categoria | Roteamento | Recuperação | Resposta |", "|---|---|---|---|"]
    for categoria, t in taxas.items():
        celulas = []
        for camada in CAMADAS:
            antes = baseline.get(categoria, {}).get(camada)
            delta = f" ({t[camada] - antes:+.0%})" if antes is not None and antes != t[camada] else ""
            celulas.append(f"{t[camada]:.0%}{delta}")
        linhas.append(f"| {categoria} | " + " | ".join(celulas) + " |")
    linhas.append("| **média** | " + " | ".join(f"**{media(taxas, c):.0%}**" for c in CAMADAS) + " |")
    linhas.append("")
    if not motivos:
        linhas.append("**✅ Aprovado**")
    elif override:
        linhas.append(f"**⚠️ Reprovado, mas liberado por OVERRIDE:** {override}")
    else:
        linhas.append("**❌ Reprovado**")
    linhas += [f"- {m}" for m in motivos]
    return "\n".join(linhas) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("resultado")
    parser.add_argument("--salvar-baseline", action="store_true")
    args = parser.parse_args()

    limites = yaml.safe_load((PASTA / "limites.yaml").read_text())
    caminho_baseline = PASTA / "baseline.json"
    baseline = json.loads(caminho_baseline.read_text()) if caminho_baseline.exists() else {}
    taxas = taxas_por_categoria(json.loads(Path(args.resultado).read_text()))
    motivos = avaliar(taxas, baseline, limites)
    override = os.environ.get("OVERRIDE_AGENT_GATE", "").strip()

    texto = resumo(taxas, baseline, motivos, override)
    print(texto)
    if destino := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(destino, "a", encoding="utf-8") as f:
            f.write(texto)

    if args.salvar_baseline:
        caminho_baseline.write_text(json.dumps(taxas, indent=2, ensure_ascii=False) + "\n")
        print(f"Baseline salva em {caminho_baseline}")
    if motivos and not override:
        sys.exit(1)


if __name__ == "__main__":
    main()
