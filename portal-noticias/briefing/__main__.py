"""Linha de comando.

    python -m briefing senha <usuario>        define usuário e senha do portal (pede a senha)
    python -m briefing executar [tema ...]    roda o fluxo diário agora (todos os temas ativos por padrão)
    python -m briefing servidor [--porta N]   sobe o portal, o painel e o agendamento
"""
import argparse
import getpass
import json
import sys

from . import db, pipeline


def main() -> None:
    ap = argparse.ArgumentParser(prog="python -m briefing")
    sub = ap.add_subparsers(dest="comando", required=True)
    s = sub.add_parser("senha")
    s.add_argument("usuario")
    e = sub.add_parser("executar")
    e.add_argument("temas", nargs="*")
    v = sub.add_parser("servidor")
    v.add_argument("--porta", type=int, default=8000)
    v.add_argument("--host", default="0.0.0.0")
    a = ap.parse_args()
    db.iniciar()
    if a.comando == "senha":
        senha = sys.stdin.readline().rstrip("\n") if not sys.stdin.isatty() else getpass.getpass("Senha: ")
        if len(senha) < 10:
            sys.exit("Use uma senha com pelo menos 10 caracteres.")
        from .web import definir_senha
        definir_senha(a.usuario, senha)
        print("Senha definida.")
    elif a.comando == "executar":
        print(json.dumps({"execucao": pipeline.executar("linha_de_comando", a.temas or None)}))
    else:
        import uvicorn
        uvicorn.run("briefing.web:app", host=a.host, port=a.porta, proxy_headers=True, forwarded_allow_ips="*")


if __name__ == "__main__":
    main()
