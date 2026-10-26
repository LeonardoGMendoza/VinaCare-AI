"""API do VinaCare: a Clara conversa com o idoso usando a IA da Oracle."""
import os
import re
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import carregar_env

carregar_env()

from .ia import Clara, oracle_do_ambiente  # noqa: E402
from .memoria import Memoria  # noqa: E402
from .voz import voz_do_ambiente  # noqa: E402

app = FastAPI(title="VinaCare API", version="0.1.0")
origens = [o.strip() for o in os.getenv("VINACARE_ORIGENS", "http://localhost:5173,https://leonardogmendoza.github.io").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origens, allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])

memoria = Memoria(os.getenv("VINACARE_DATA_DIR", "./data"))
clara = Clara(oracle_do_ambiente(), memoria)
voz = voz_do_ambiente(clara.chat)
ID_OK = re.compile(r"^[a-zA-Z0-9_-]{1,40}$")
_pedidos = defaultdict(deque)


def limitar(request: Request, maximo=30, janela=60):
    """Protege o custo da Oracle: no máximo 30 pedidos por minuto por pessoa (IP)."""
    ip = request.headers.get("cf-connecting-ip") or request.headers.get("x-real-ip") or (request.client.host if request.client else "?")
    agora, fila = time.time(), _pedidos[ip]
    while fila and agora - fila[0] > janela:
        fila.popleft()
    if len(fila) >= maximo:
        raise HTTPException(429, "Muitos pedidos. Espere um minuto.")
    fila.append(agora)


VOZES = {"Clara": "pt-BR-FranciscaNeural", "Rafael": "pt-BR-AntonioNeural"}


class TextoVoz(BaseModel):
    texto: str = Field(..., min_length=1, max_length=600)
    assistente: str = Field("Clara", max_length=20)


class Fala(BaseModel):
    idoso: str = Field("demo", max_length=40)
    nome: str = Field("", max_length=60)
    texto: str = Field(..., min_length=1, max_length=500)
    assistente: str = Field("Clara", max_length=20)


def checar(idoso):
    if not ID_OK.match(idoso):
        raise HTTPException(422, "Identificador inválido.")


@app.get("/api/saude")
def saude():
    return {"ok": True, "ia": clara.chat is not None, "voz": voz is not None}


@app.post("/api/conversa")
def conversa(f: Fala, request: Request):
    limitar(request)
    checar(f.idoso)
    return clara.conversar(f.idoso, f.nome, f.texto, f.assistente)


@app.get("/api/alertas/{idoso}")
def alertas(idoso: str):
    checar(idoso)
    return {"alertas": memoria.alertas(idoso)}


@app.get("/api/memoria/{idoso}")
def ver_memoria(idoso: str):
    checar(idoso)
    return {"fatos": memoria.fatos(idoso)}


@app.delete("/api/memoria/{idoso}")
def apagar_memoria(idoso: str):
    checar(idoso)
    memoria.esquecer(idoso)
    return {"ok": True}


@app.post("/api/voz")
def falar(t: TextoVoz, request: Request):
    limitar(request)
    if voz is None:
        raise HTTPException(503, "Voz da nuvem não configurada.")
    try:
        audio = voz(t.texto, VOZES.get(t.assistente))
    except Exception as erro:  # noqa: BLE001
        import logging
        logging.getLogger("vinacare").warning("Voz da Oracle falhou: %s: %s", type(erro).__name__, str(erro)[:300])
        raise HTTPException(503, "Voz da nuvem indisponível.") from erro
    return Response(content=audio, media_type="audio/mpeg", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/api/vozes")
def listar_vozes():
    """Diagnóstico: mostra as vozes que a sua conta Oracle oferece."""
    if voz is None:
        raise HTTPException(503, "Voz da nuvem não configurada.")
    try:
        return voz.vozes()
    except Exception as erro:  # noqa: BLE001
        raise HTTPException(503, f"{type(erro).__name__}: {str(erro)[:300]}") from erro
