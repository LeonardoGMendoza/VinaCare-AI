import numpy as np

from app.features import caracteristicas, nomes, sinais, visibilidade


def gravacao(n=90, braco_alto=True, escala=1.0, desloc=0.0):
    quadros = []
    for t in range(n):
        p = np.zeros((33, 4))
        p[:, 3] = 1
        fase = np.sin(np.pi * t / n) if braco_alto else 0.3 * np.sin(np.pi * t / n)
        base = {11: (0.45, 0.4), 12: (0.55, 0.4), 23: (0.46, 0.7), 24: (0.54, 0.7),
                25: (0.46, 0.85), 26: (0.54, 0.85), 27: (0.46, 1.0), 28: (0.54, 1.0)}
        for i, (x, y) in base.items():
            p[i, :2] = (x, y)
        for lado, (ix_c, ix_p, x) in {0: (13, 15, 0.45), 1: (14, 16, 0.55)}.items():
            p[ix_c, :2] = (x, 0.55 - 0.3 * fase)
            p[ix_p, :2] = (x, 0.7 - 0.6 * fase)
        p[:, :2] = p[:, :2] * escala + desloc
        quadros.append(p.ravel().tolist())
    return quadros


def test_tamanho_do_vetor_bate_com_os_nomes():
    assert len(caracteristicas(gravacao())) == len(nomes())


def test_nao_depende_do_tamanho_nem_da_posicao():
    a = caracteristicas(gravacao())
    b = caracteristicas(gravacao(escala=0.5, desloc=0.2))
    assert np.allclose(a, b, atol=1e-6)


def test_braco_alto_tem_angulo_de_ombro_maior():
    alto = sinais(gravacao(braco_alto=True))[:, 0].max()
    meio = sinais(gravacao(braco_alto=False))[:, 0].max()
    assert alto > 150 and meio < 120


def test_visibilidade():
    assert visibilidade(gravacao()) == 1.0
