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
from .dataset import Dataset, validar, EXERCICIOS  # noqa: E402
from .modelo import avaliador_do_ambiente, avaliar  # noqa: E402
from .contas import contas_do_ambiente  # noqa: E402

app = FastAPI(title="VinaCare API", version="0.1.0")
origens = [o.strip() for o in os.getenv("VINACARE_ORIGENS", "http://localhost:5173,https://leonardogmendoza.github.io").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origens, allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])

memoria = Memoria(os.getenv("VINACARE_DATA_DIR", "./data"))
dataset = Dataset(os.getenv("VINACARE_DATA_DIR", "./data"))
clara = Clara(oracle_do_ambiente(), memoria)
voz = voz_do_ambiente(clara.chat)
avaliador = avaliador_do_ambiente()
try:
    contas = contas_do_ambiente()
except Exception as erro:  # noqa: BLE001  (sem banco a API continua no ar; só o login fica desligado)
    import logging
    logging.getLogger("vinacare").warning("Contas desligadas: %s: %s", type(erro).__name__, str(erro)[:200])
    contas = None
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


VOZES = {  # vozes neurais da Azure por idioma
    "pt": {"Clara": "pt-BR-FranciscaNeural", "Rafael": "pt-BR-AntonioNeural"},
    "es": {"Clara": "es-PE-CamilaNeural", "Rafael": "es-PE-AlexNeural"},
    "en": {"Clara": "en-US-JennyNeural", "Rafael": "en-US-GuyNeural"},
    # aula de inglês: vozes multilíngues (falam inglês e português/espanhol na mesma frase)
    "aula": {"Clara": "en-US-AvaMultilingualNeural", "Rafael": "en-US-AndrewMultilingualNeural"},
}


class TextoVoz(BaseModel):
    texto: str = Field(..., min_length=1, max_length=600)
    assistente: str = Field("Clara", max_length=20)
    idioma: str = Field("pt", max_length=5)
    modo: str = Field("conversa", max_length=10)


class Fala(BaseModel):
    idoso: str = Field("demo", max_length=40)
    nome: str = Field("", max_length=60)
    texto: str = Field(..., min_length=1, max_length=500)
    assistente: str = Field("Clara", max_length=20)
    idioma: str = Field("pt", max_length=5)
    modo: str = Field("conversa", max_length=10)


def checar(idoso):
    if not ID_OK.match(idoso):
        raise HTTPException(422, "Identificador inválido.")


def usuario_logado(request: Request):
    auth = request.headers.get("authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    return contas.usuario(token) if (contas and token) else None


def checar_premium(request: Request):
    u = usuario_logado(request)
    if not u or not u["premium"]:
        raise HTTPException(403, "Recurso premium.")
    return u


class Login(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)
    senha: str = Field(..., min_length=1, max_length=200)


@app.post("/api/login")
def login(d: Login, request: Request):
    limitar(request, maximo=5)          # protege contra quem tenta adivinhar senha
    if contas is None:
        raise HTTPException(503, "Login indisponível.")
    r = contas.entrar(d.email, d.senha)
    if r is None:
        raise HTTPException(401, "E-mail ou senha incorretos.")
    token, u = r
    return {"token": token, "nome": u["nome"], "premium": u["premium"]}


@app.get("/api/eu")
def eu(request: Request):
    u = usuario_logado(request)
    if not u:
        raise HTTPException(401, "Não conectado.")
    return {"nome": u["nome"], "premium": u["premium"]}


@app.post("/api/logout")
def logout(request: Request):
    auth = request.headers.get("authorization", "")
    if contas and auth.lower().startswith("bearer "):
        contas.sair(auth[7:].strip())
    return {"ok": True}


@app.get("/api/saude")
def saude():
    return {"ok": True, "contas": contas is not None, "modelo": avaliador is not None, "ia": clara.chat is not None, "voz": voz is not None}


@app.post("/api/conversa")
def conversa(f: Fala, request: Request):
    limitar(request)
    checar(f.idoso)
    modo = "aula" if f.modo == "aula" else "conversa"
    idoso = f.idoso
    if modo == "aula":
        idoso = f"u{checar_premium(request)['id']}"   # a aula acompanha a conta, em qualquer aparelho
    return clara.conversar(idoso, f.nome, f.texto, f.assistente, f.idioma, modo)


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
        nome_voz = VOZES.get(t.idioma, VOZES["pt"]).get(t.assistente, VOZES["pt"]["Clara"])
        # na aula de inglês fala mais devagar, para dar tempo de entender
        audio = voz(t.texto, nome_voz, "-25%") if t.idioma == "aula" else voz(t.texto, nome_voz)
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


class Gravacao(BaseModel):
    exercicio: str = Field(..., max_length=40)
    qualidade: str = Field(..., max_length=10)
    pessoa: str = Field("anonimo", max_length=40)
    fps: float = Field(30, ge=1, le=120)
    quadros: list


def checar_codigo(request: Request):
    """Só quem tem o código de coleta (definido no servidor) pode gravar e exportar o dataset."""
    codigo = os.getenv("VINACARE_COLETA_CODIGO", "")
    if not codigo or request.headers.get("x-coleta-codigo") != codigo:
        raise HTTPException(403, "Código de coleta inválido.")


@app.get("/api/dataset/exercicios")
def exercicios():
    return EXERCICIOS


@app.get("/api/dataset/resumo")
def resumo_dataset():
    return dataset.resumo()


@app.post("/api/dataset")
def gravar(g: Gravacao, request: Request):
    checar_codigo(request)
    limitar(request, maximo=20)
    erro = validar(g.exercicio, g.qualidade, g.quadros)
    if erro:
        raise HTTPException(422, erro)
    return {"ok": True, "arquivo": dataset.salvar(g.exercicio, g.qualidade, g.quadros, g.pessoa, g.fps),
            "resumo": dataset.resumo()}


@app.get("/api/dataset/exportar")
def exportar(request: Request):
    """Usado pelo notebook do OCI Data Science para baixar todas as gravações."""
    checar_codigo(request)
    return dataset.exportar()


class Exercicio(BaseModel):
    exercicio: str = Field(..., max_length=40)
    fps: float = Field(30, ge=1, le=120)
    quadros: list


@app.post("/api/exercicio/avaliar")
def avaliar_exercicio(e: Exercicio, request: Request):
    """Manda a gravação para o modelo treinado no OCI Data Science (Model Deployment) e devolve a frase para a Clara."""
    limitar(request, maximo=12)
    erro = validar(e.exercicio, "certo", e.quadros)
    if erro:
        raise HTTPException(422, erro)
    try:
        r = avaliar(avaliador, e.exercicio, e.quadros, e.fps)
    except Exception as falha:  # noqa: BLE001
        import logging
        logging.getLogger("vinacare").warning("Model Deployment falhou: %s: %s", type(falha).__name__, str(falha)[:200])
        raise HTTPException(503, "O avaliador de exercícios está desligado agora.") from falha
    if not r["ok"]:
        raise HTTPException(503, r["erro"])
    return r
