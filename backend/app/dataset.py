"""Dataset de exercícios: guarda as gravações (pontos do corpo do MediaPipe) para treinar o modelo no OCI Data Science."""
import json
import os
import time
import uuid
from pathlib import Path

EXERCICIOS = {
    "levantar_bracos": "Levantar os braços",
    "abrir_bracos": "Abrir os braços",
    "sentar_levantar": "Sentar e levantar da cadeira",
    "marcha_parado": "Marchar parado",
}
QUALIDADES = {"certo", "errado"}
PONTOS, VALORES = 33, 4          # MediaPipe Pose: 33 pontos com x, y, z, visibilidade
MAX_QUADROS = 180                # ~6 s a 30 fps


def validar(exercicio, qualidade, quadros):
    if exercicio not in EXERCICIOS:
        return "Exercício desconhecido."
    if qualidade not in QUALIDADES:
        return "Qualidade deve ser 'certo' ou 'errado'."
    if not isinstance(quadros, list) or not (10 <= len(quadros) <= MAX_QUADROS):
        return f"A gravação precisa ter entre 10 e {MAX_QUADROS} quadros."
    for q in quadros:
        if not isinstance(q, list) or len(q) != PONTOS * VALORES:
            return f"Cada quadro precisa ter {PONTOS * VALORES} números."
        if not all(isinstance(v, (int, float)) for v in q):
            return "Os quadros só podem ter números."
    return None


class Dataset:
    def __init__(self, pasta):
        self.pasta = Path(pasta) / "dataset"
        self.pasta.mkdir(parents=True, exist_ok=True)

    def salvar(self, exercicio, qualidade, quadros, pessoa="anonimo", fps=30):
        pasta = self.pasta / exercicio
        pasta.mkdir(exist_ok=True)
        nome = f"{int(time.time())}-{qualidade}-{uuid.uuid4().hex[:6]}.json"
        dados = {"exercicio": exercicio, "qualidade": qualidade, "pessoa": pessoa[:40], "fps": fps,
                 "formato": "33 pontos x (x, y, z, visibilidade) por quadro - MediaPipe Pose",
                 "criado": time.time(), "quadros": [[round(v, 5) for v in q] for q in quadros]}
        (pasta / nome).write_text(json.dumps(dados), encoding="utf-8")
        return nome

    def resumo(self):
        r = {}
        for ex in EXERCICIOS:
            arquivos = list((self.pasta / ex).glob("*.json")) if (self.pasta / ex).exists() else []
            r[ex] = {"nome": EXERCICIOS[ex],
                     "certo": sum(1 for a in arquivos if "-certo-" in a.name),
                     "errado": sum(1 for a in arquivos if "-errado-" in a.name)}
        return r

    def exportar(self):
        tudo = []
        for arq in sorted(self.pasta.glob("*/*.json")):
            tudo.append(json.loads(arq.read_text(encoding="utf-8")))
        return tudo
