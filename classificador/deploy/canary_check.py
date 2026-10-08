"""Análise do canary (Aula 4): manda tráfego para a URL e compara as versões.

    python classificador/deploy/canary_check.py https://xxxx.lambda-url.us-east-1.on.aws/ --requisicoes 200

Critérios de avanço (todos precisam passar para o canary ser promovido):
- taxa de erro do canary ≤ 2% e não mais que 1 p.p. acima da estável
- latência p95 do canary ≤ 1,5 × a da estável
- distribuição das previsões do canary a até 15 p.p. da estável, por classe

Sai com código 1 se o canary deve sofrer rollback.
"""

import argparse
import csv
import json
import random
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

TEXTOS = Path(__file__).parent.parent / "dados" / "validacao.csv"


def chamar(url: str, texto: str) -> tuple[int, dict, float]:
    corpo = json.dumps({"texto": texto}).encode()
    req = urllib.request.Request(url, data=corpo, headers={"content-type": "application/json"})
    inicio = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status, dados = resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as erro:
        status, dados = erro.code, json.loads(erro.read() or b"{}")
    return status, dados, (time.perf_counter() - inicio) * 1000


def p95(valores: list[float]) -> float:
    return statistics.quantiles(valores, n=20)[-1] if len(valores) >= 2 else (valores or [0])[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--requisicoes", type=int, default=200)
    args = parser.parse_args()

    with open(TEXTOS, encoding="utf-8") as f:
        textos = [linha["texto"] for linha in csv.DictReader(f)]

    stats = defaultdict(lambda: {"n": 0, "erros": 0, "latencias": [], "rotulos": Counter()})
    for _ in range(args.requisicoes):
        status, dados, ms = chamar(args.url, random.choice(textos))
        s = stats[dados.get("versao", "?")]
        s["n"] += 1
        s["latencias"].append(ms)
        if status >= 500:
            s["erros"] += 1
        else:
            s["rotulos"][dados.get("rotulo")] += 1

    print(f"{'versão':<12}{'req.':>6}{'erro %':>9}{'p95 ms':>9}  previsões")
    for versao, s in stats.items():
        ok = sum(s["rotulos"].values()) or 1
        dist = {r: f"{c / ok:.0%}" for r, c in s["rotulos"].most_common()}
        print(f"{versao:<12}{s['n']:>6}{s['erros'] / s['n']:>9.1%}{p95(s['latencias']):>9.0f}  {dist}")

    if len(stats) < 2:
        print("Só uma versão respondeu — confira o peso do canary ou aumente --requisicoes.")
        raise SystemExit(1)

    # a versão com mais tráfego é a estável; a outra é o canary
    estavel, canary = sorted(stats.values(), key=lambda s: s["n"], reverse=True)[:2]
    erro_e, erro_c = estavel["erros"] / estavel["n"], canary["erros"] / canary["n"]
    motivos = []
    if erro_c > 0.02 or erro_c - erro_e > 0.01:
        motivos.append(f"taxa de erro do canary {erro_c:.1%} (estável {erro_e:.1%})")
    if p95(canary["latencias"]) > 1.5 * p95(estavel["latencias"]):
        motivos.append("latência p95 do canary acima de 1,5× a estável")
    ok_e, ok_c = sum(estavel["rotulos"].values()) or 1, sum(canary["rotulos"].values()) or 1
    for rotulo in set(estavel["rotulos"]) | set(canary["rotulos"]):
        diff = abs(estavel["rotulos"][rotulo] / ok_e - canary["rotulos"][rotulo] / ok_c)
        if diff > 0.15:
            motivos.append(f"previsões '{rotulo}' diferem {diff:.0%} entre as versões")

    if motivos:
        print("❌ ROLLBACK:", "; ".join(motivos))
        raise SystemExit(1)
    print("✅ CANARY SAUDÁVEL — pode avançar")


if __name__ == "__main__":
    main()
