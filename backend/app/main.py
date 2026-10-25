"""API do VinaCare: a Clara conversa com o idoso usando a IA da Oracle."""
import os
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import carregar_env

carregar_env()

from .ia import Clara, oracle_do_ambiente  # noqa: E402
from .memoria import Memoria  # noqa: E402

app = FastAPI(title="VinaCare API", version="0.1.0")
origens = [o.strip() for o in os.getenv("VINACARE_ORIGENS", "http://localhost:5173,https://leonardogmendoza.github.io").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origens, allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])

memoria = Memoria(os.getenv("VINACARE_DATA_DIR", "./data"))
clara = Clara(oracle_do_ambiente(), memoria)
ID_OK = re.compile(r"^[a-zA-Z0-9_-]{1,40}$")


class Fala(BaseModel):
    idoso: str = Field("demo", max_length=40)
    nome: str = Field("", max_length=60)
    texto: str = Field(..., min_length=1, max_length=500)


def checar(idoso):
    if not ID_OK.match(idoso):
        raise HTTPException(422, "Identificador inválido.")


@app.get("/api/saude")
def saude():
    return {"ok": True, "ia": clara.chat is not None}


@app.post("/api/conversa")
def conversa(f: Fala):
    checar(f.idoso)
    return clara.conversar(f.idoso, f.nome, f.texto)


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
