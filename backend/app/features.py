"""Transforma uma gravação (quadros do MediaPipe Pose) em um vetor de características para o modelo.

O MESMO arquivo é usado no notebook do OCI Data Science (treino) e no back-end (previsão),
para que o modelo sempre receba os números calculados do mesmo jeito.
"""
import numpy as np

# Índices do MediaPipe Pose
OMBRO_E, OMBRO_D, COTOVELO_E, COTOVELO_D, PULSO_E, PULSO_D = 11, 12, 13, 14, 15, 16
QUADRIL_E, QUADRIL_D, JOELHO_E, JOELHO_D, TORNOZELO_E, TORNOZELO_D = 23, 24, 25, 26, 27, 28

SINAIS = [
    "ombro_e", "ombro_d", "cotovelo_e", "cotovelo_d",        # ângulos dos braços (graus)
    "quadril_e", "quadril_d", "joelho_e", "joelho_d",         # ângulos das pernas (graus)
    "pulso_alt_e", "pulso_alt_d", "pulso_lado_e", "pulso_lado_d",  # posição dos pulsos (em "troncos")
    "quadril_alt", "joelho_alt_e", "joelho_alt_d",            # altura do quadril e dos joelhos
]
ESTATISTICAS = ["min", "max", "media", "desvio", "amplitude", "inicio", "fim", "velocidade"]
AMOSTRAS = 10   # pontos da curva reamostrada de cada sinal


def _pontos(quadros):
    a = np.asarray(quadros, dtype=float)
    return a.reshape(len(a), 33, 4)          # (quadros, pontos, x/y/z/visibilidade)


def _angulo(a, b, c):
    """Ângulo em b (graus), quadro a quadro, usando x e y."""
    ba, bc = a - b, c - b
    cos = (ba * bc).sum(-1) / (np.linalg.norm(ba, axis=-1) * np.linalg.norm(bc, axis=-1) + 1e-9)
    return np.degrees(np.arccos(np.clip(cos, -1, 1)))


def sinais(quadros):
    """Curvas no tempo (quadros x len(SINAIS)), já sem depender do tamanho da pessoa nem da posição na tela."""
    p = _pontos(quadros)[:, :, :2]
    meio_quadril = (p[:, QUADRIL_E] + p[:, QUADRIL_D]) / 2
    meio_ombro = (p[:, OMBRO_E] + p[:, OMBRO_D]) / 2
    tronco = np.median(np.linalg.norm(meio_ombro - meio_quadril, axis=-1)) + 1e-6
    n = (p - meio_quadril[:, None, :]) / tronco          # centro no quadril, escala = tamanho do tronco
    y = -n[..., 1]                                        # para cima = positivo

    col = [
        _angulo(n[:, QUADRIL_E], n[:, OMBRO_E], n[:, COTOVELO_E]),
        _angulo(n[:, QUADRIL_D], n[:, OMBRO_D], n[:, COTOVELO_D]),
        _angulo(n[:, OMBRO_E], n[:, COTOVELO_E], n[:, PULSO_E]),
        _angulo(n[:, OMBRO_D], n[:, COTOVELO_D], n[:, PULSO_D]),
        _angulo(n[:, OMBRO_E], n[:, QUADRIL_E], n[:, JOELHO_E]),
        _angulo(n[:, OMBRO_D], n[:, QUADRIL_D], n[:, JOELHO_D]),
        _angulo(n[:, QUADRIL_E], n[:, JOELHO_E], n[:, TORNOZELO_E]),
        _angulo(n[:, QUADRIL_D], n[:, JOELHO_D], n[:, TORNOZELO_D]),
        y[:, PULSO_E] - y[:, OMBRO_E],
        y[:, PULSO_D] - y[:, OMBRO_D],
        np.abs(n[:, PULSO_E, 0] - n[:, OMBRO_E, 0]),
        np.abs(n[:, PULSO_D, 0] - n[:, OMBRO_D, 0]),
        -(p[:, QUADRIL_E, 1] + p[:, QUADRIL_D, 1]) / 2 / tronco,   # altura absoluta do quadril (sentar/levantar)
        y[:, JOELHO_E],
        y[:, JOELHO_D],
    ]
    s = np.stack(col, axis=1)
    s[:, 12] -= s[0, 12]                                  # quadril: variação desde o começo
    return s


def _reamostrar(s, k):
    x = np.linspace(0, 1, len(s))
    xn = np.linspace(0, 1, k)
    return np.stack([np.interp(xn, x, s[:, j]) for j in range(s.shape[1])], axis=1)


def caracteristicas(quadros, fps=30):
    """Vetor fixo para uma gravação: estatísticas de cada sinal + a curva resumida em AMOSTRAS pontos."""
    s = sinais(quadros)
    s = _reamostrar(s, max(len(s), 2))
    dt = 1.0 / max(fps, 1)
    vel = np.abs(np.diff(s, axis=0)).mean(0) / dt if len(s) > 1 else np.zeros(s.shape[1])
    est = np.concatenate([s.min(0), s.max(0), s.mean(0), s.std(0), s.max(0) - s.min(0), s[0], s[-1], vel])
    curva = _reamostrar(s, AMOSTRAS).T.ravel()
    return np.concatenate([est, curva]).astype(float)


def nomes():
    n = [f"{e}_{s}" for e in ESTATISTICAS for s in SINAIS]
    n += [f"{s}_t{i}" for s in SINAIS for i in range(AMOSTRAS)]
    return n


def visibilidade(quadros):
    """Média de visibilidade de ombros, cotovelos e quadril: abaixo de ~0,5 a gravação não pegou o corpo."""
    p = _pontos(quadros)
    return float(p[:, [OMBRO_E, OMBRO_D, COTOVELO_E, COTOVELO_D, QUADRIL_E, QUADRIL_D], 3].mean())
