"""Model gate: decide se o modelo candidato pode seguir para o deploy.

    python classificador/model_gate.py artefatos/metricas.json

Três regras, todas avaliáveis por máquina (o "if" da Aula 2):
1. F1 macro mínimo absoluto
2. piso por classe — a média não esconde uma classe ruim
3. não piorar a produção além da tolerância

Sai com código 1 se reprovar, e o pipeline para.
"""

import json
import os
import sys
from pathlib import Path

LIMITES = {
    "f1_macro_minimo": 0.80,
    "f1_minimo_por_classe": 0.70,
    "tolerancia_vs_producao": 0.02,
}
PRODUCAO = Path(__file__).parent / "producao.json"


def avaliar(candidato: dict, producao: dict, limites: dict = LIMITES) -> list[str]:
    """Devolve a lista de motivos de reprovação (vazia = aprovado)."""
    motivos = []
    if candidato["f1_macro"] < limites["f1_macro_minimo"]:
        motivos.append(f"F1 macro {candidato['f1_macro']} < {limites['f1_macro_minimo']}")
    for classe, f1 in candidato["f1_por_classe"].items():
        if f1 < limites["f1_minimo_por_classe"]:
            motivos.append(f"F1 da classe '{classe}' {f1} < {limites['f1_minimo_por_classe']}")
    queda = producao["f1_macro"] - candidato["f1_macro"]
    if queda > limites["tolerancia_vs_producao"]:
        motivos.append(f"piora de {queda:.4f} no F1 macro em relação à produção ({producao['f1_macro']})")
    return motivos


def resumo(candidato: dict, producao: dict, motivos: list[str]) -> None:
    """Tabela no resumo da execução do GitHub Actions (aba Summary)."""
    destino = os.environ.get("GITHUB_STEP_SUMMARY")
    if not destino:
        return
    linhas = ["## Model gate", "", "| Métrica | Candidato | Produção |", "|---|---|---|"]
    linhas.append(f"| F1 macro | {candidato['f1_macro']} | {producao['f1_macro']} |")
    for classe, f1 in candidato["f1_por_classe"].items():
        linhas.append(f"| F1 {classe} | {f1} | {producao['f1_por_classe'].get(classe, '—')} |")
    veredito = "❌ reprovado: " + "; ".join(motivos) if motivos else "✅ aprovado"
    linhas += ["", f"**{veredito}**", ""]
    with open(destino, "a", encoding="utf-8") as f:
        f.write("\n".join(linhas))


def main() -> None:
    candidato = json.loads(Path(sys.argv[1]).read_text())
    producao = json.loads(PRODUCAO.read_text())
    motivos = avaliar(candidato, producao)

    resumo(candidato, producao, motivos)
    print(f"Candidato: F1 macro {candidato['f1_macro']} · por classe {candidato['f1_por_classe']}")
    print(f"Produção:  F1 macro {producao['f1_macro']}")
    if motivos:
        print("❌ MODEL GATE REPROVOU:")
        for m in motivos:
            print(f"   - {m}")
        sys.exit(1)
    print("✅ MODEL GATE APROVOU")


if __name__ == "__main__":
    main()
