"""Alias ponderado LOCAL — o plano B gratuito do canary da Aula 4 (sem AWS).

    python classificador/deploy/alias_local.py --peso 0.3 --erro-canary 0.2
    python classificador/deploy/canary_check.py http://127.0.0.1:9078/

Imita o que o alias do Lambda faz: sorteia, a cada requisição, entre a versão
estável (v1) e o canary (v2, com a fração de erro pedida) e responde com o mesmo
contrato do serviço. Precisa de artefatos/modelo.joblib (rode o treino antes).
"""

import argparse
import random
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import servico  # noqa: E402


def criar_handler(peso: float, erro_canary: float):
    class Alias(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            corpo = self.rfile.read(int(self.headers["content-length"])).decode()
            canary = random.random() < peso
            servico.VERSAO = "v2-canary" if canary else "v1"
            servico.ERRO_SIMULADO = erro_canary if canary else 0.0
            resposta = servico.handler({"body": corpo})
            self.send_response(resposta["statusCode"])
            self.end_headers()
            self.wfile.write(resposta["body"].encode())

    return Alias


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--peso", type=float, default=0.1, help="fração do tráfego para o canary")
    parser.add_argument("--erro-canary", type=float, default=0.0, help="fração de erros do canary")
    parser.add_argument("--porta", type=int, default=9078)
    args = parser.parse_args()
    print(f"alias local em http://127.0.0.1:{args.porta}/")
    print(f"canary com {args.peso:.0%} do tráfego e {args.erro_canary:.0%} de erros")
    HTTPServer(("127.0.0.1", args.porta), criar_handler(args.peso, args.erro_canary)).serve_forever()


if __name__ == "__main__":
    main()
