"""Resume o juiz de fidelidade por categoria e aplica o piso de limites.yaml.

    python agente/juiz_resumo.py resultado-juiz.json

É um extra opcional e, por padrão, **só informa**: um juiz de 3B local erra (no teste: pegou a
contradição real, mas deu 2 alarmes falsos em 6 casos). Com JUIZ_BLOQUEIA=true, sai com código 1 se
alguma categoria ficar abaixo de `juiz.piso_fidelidade` — use só com um modelo juiz maior.
Erro de execução do juiz (formato da nota, timeout) conta como reprovado.
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import yaml

PASTA = Path(__file__).parent


def fidelidade_por_categoria(resultado: dict) -> dict[str, float]:
    soma, casos = defaultdict(float), defaultdict(int)
    for r in resultado["results"]["results"]:
        categoria = r["vars"]["categoria"]
        casos[categoria] += 1
        soma[categoria] += (r.get("namedScores") or {}).get("fidelidade", 0)
    return {c: round(soma[c] / casos[c], 3) for c in sorted(casos)}


def avaliar(taxas: dict[str, float], piso: float) -> list[str]:
    return [f"{c}: fidelidade {t:.0%} abaixo do piso de {piso:.0%}" for c, t in taxas.items() if t < piso]


def main() -> None:
    piso = yaml.safe_load((PASTA / "limites.yaml").read_text())["juiz"]["piso_fidelidade"]
    taxas = fidelidade_por_categoria(json.loads(Path(sys.argv[1]).read_text()))
    motivos = avaliar(taxas, piso)

    linhas = ["## Juiz de fidelidade", "", "| Categoria | Fidelidade |", "|---|---|"]
    linhas += [f"| {c} | {t:.0%} |" for c, t in taxas.items()]
    bloqueia = os.environ.get("JUIZ_BLOQUEIA") == "true"
    if not motivos:
        veredito = "**✅ Aprovado**"
    elif bloqueia:
        veredito = "**❌ Reprovado**"
    else:
        veredito = "**⚠️ Abaixo do piso, mas o juiz é só informativo** (JUIZ_BLOQUEIA=true para bloquear)"
    linhas += ["", veredito] + [f"- {m}" for m in motivos]
    texto = "\n".join(linhas) + "\n"
    print(texto)
    if destino := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(destino, "a", encoding="utf-8") as f:
            f.write(texto)
    if motivos and bloqueia:
        sys.exit(1)


if __name__ == "__main__":
    main()
