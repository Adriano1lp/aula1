"""Policy-as-code dos PRs de configuração (Aula 3): roda no CI antes do merge.

    python gitops/politicas/verificar.py

Renderiza cada overlay com o kustomize e aplica as regras abaixo.
Sai com código 1 se alguma regra for violada.
"""

import re
import subprocess
import sys
from pathlib import Path

import yaml

OVERLAYS = Path(__file__).parent.parent / "overlays"
OBRIGATORIOS = ["MODELO", "PROMPT_VERSAO", "RAG_INDICE"]
# sufixo do nome, não substring: MAX_TOKENS é configuração, OPENAI_API_KEY é segredo
SEGREDO = re.compile(r"(^|_)(KEY|TOKEN|SECRET|SENHA|PASSWORD)$")
MIN_REPLICAS_PRODUCAO = 2


def renderizar(overlay: Path) -> list[dict]:
    saida = subprocess.run(["kubectl", "kustomize", str(overlay)], capture_output=True, text=True, check=True)
    return [doc for doc in yaml.safe_load_all(saida.stdout) if doc]


def verificar(ambiente: str, docs: list[dict]) -> list[str]:
    erros = []
    for doc in docs:
        if doc["kind"] == "ConfigMap":
            dados = doc.get("data", {})
            for campo in OBRIGATORIOS:
                valor = dados.get(campo, "")
                if not valor or valor.lower() in {"latest", "ultimo", "último"}:
                    erros.append(f"{campo} precisa de versão explícita (está '{valor}')")
            for chave in dados:
                if SEGREDO.search(chave.upper()):
                    erros.append(f"'{chave}' parece segredo em texto claro — use um Secret externo")
        if doc["kind"] == "Deployment" and ambiente == "producao":
            if doc["spec"].get("replicas", 1) < MIN_REPLICAS_PRODUCAO:
                erros.append(f"produção precisa de pelo menos {MIN_REPLICAS_PRODUCAO} réplicas")
    return [f"[{ambiente}] {e}" for e in erros]


def main() -> None:
    erros = []
    for overlay in sorted(p for p in OVERLAYS.iterdir() if p.is_dir()):
        erros += verificar(overlay.name, renderizar(overlay))
    if erros:
        print("❌ Políticas violadas:")
        print("\n".join(f"   - {e}" for e in erros))
        sys.exit(1)
    print("✅ Todas as políticas passaram")


if __name__ == "__main__":
    main()
