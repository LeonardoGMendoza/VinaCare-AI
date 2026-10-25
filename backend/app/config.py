"""Le o arquivo .env (sem biblioteca extra) e devolve as configuracoes."""
import os
from pathlib import Path


def carregar_env(caminho=None):
    caminho = Path(caminho or Path(__file__).resolve().parent.parent / ".env")
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        chave, valor = chave.strip(), valor.strip().strip('"').strip("'")
        if valor and chave not in os.environ:
            os.environ[chave] = valor
