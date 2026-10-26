from app.modelo import avaliar, avaliador_do_ambiente, mensagem
from tests.test_features import gravacao


def test_mensagem_certo_e_errado():
    assert mensagem("levantar_bracos", "levantar_bracos|certo")[0] == "certo"
    assert mensagem("levantar_bracos", "levantar_bracos|errado")[0] == "errado"
    assert mensagem("levantar_bracos", "abrir_bracos|certo")[0] == "errado"


def test_avaliar_chama_o_modelo_com_o_vetor():
    recebido = {}

    def falso(vetor):
        recebido["n"] = len(vetor)
        return "levantar_bracos|certo"

    r = avaliar(falso, "levantar_bracos", gravacao(), 20)
    assert r["qualidade"] == "certo" and recebido["n"] == 270


def test_corpo_fora_da_camera_nao_chama_o_modelo():
    q = gravacao()
    for quadro in q:
        for i in range(33):
            quadro[i * 4 + 3] = 0.1
    r = avaliar(lambda v: 1 / 0, "levantar_bracos", q)
    assert r["qualidade"] == "fora"


def test_sem_configuracao():
    assert avaliador_do_ambiente({}) is None
    assert avaliar(None, "levantar_bracos", gravacao())["ok"] is False
