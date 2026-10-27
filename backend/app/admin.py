"""Administração das contas premium (roda no servidor, dentro do container).

    docker exec -it vinacare-api python -m app.admin criar voce@email.com "Seu Nome" --premium
    docker exec -it vinacare-api python -m app.admin premium voce@email.com sim|nao
    docker exec -it vinacare-api python -m app.admin senha voce@email.com
    docker exec -it vinacare-api python -m app.admin desativar voce@email.com

A senha é digitada escondida (não aparece na tela nem fica no histórico do terminal).
"""
import getpass
import sys

from .config import carregar_env

carregar_env()
from .contas import contas_do_ambiente  # noqa: E402


def pedir_senha():
    s1 = getpass.getpass("Senha (mínimo 8 caracteres): ")
    s2 = getpass.getpass("Repita a senha: ")
    if s1 != s2:
        sys.exit("As senhas não são iguais.")
    return s1


def main(args):
    contas = contas_do_ambiente()
    if contas is None:
        sys.exit("VINACARE_DB_URL não configurado.")
    if len(args) >= 2 and args[0] == "criar":
        nome = args[2] if len(args) > 2 and not args[2].startswith("--") else ""
        contas.criar(args[1], pedir_senha(), nome, premium="--premium" in args)
        print("Conta criada:", args[1], "(premium)" if "--premium" in args else "")
    elif len(args) == 3 and args[0] == "premium":
        contas.definir(args[1], premium=args[2].lower() in ("sim", "s", "yes", "true", "1"))
        print("Premium atualizado.")
    elif len(args) == 2 and args[0] == "senha":
        contas.definir(args[1], senha=pedir_senha())
        print("Senha trocada.")
    elif len(args) == 2 and args[0] == "desativar":
        contas.definir(args[1], ativo=False)
        print("Conta desativada.")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
