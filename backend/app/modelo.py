"""Avaliação do exercício pelo modelo treinado no OCI Data Science e publicado no Model Deployment."""
import base64
import logging
import os

from .dataset import EXERCICIOS
from .features import caracteristicas, visibilidade

log = logging.getLogger("vinacare")

ELOGIOS = {
    "levantar_bracos": "Muito bem! Os braços subiram direitinho.",
    "abrir_bracos": "Muito bem! Os braços abriram na altura certa.",
    "sentar_levantar": "Muito bem! Sentou e levantou com firmeza.",
    "marcha_parado": "Muito bem! Boa marcha, joelhos subindo.",
}
DICAS = {
    "levantar_bracos": "Quase lá! Tente subir os dois braços até o alto, devagar.",
    "abrir_bracos": "Quase lá! Abra os dois braços até a altura dos ombros.",
    "sentar_levantar": "Quase lá! Vá devagar e use a cadeira como apoio.",
    "marcha_parado": "Quase lá! Tente levantar um pouco mais os joelhos.",
}


def mensagem(exercicio, previsao):
    """Transforma 'exercicio|qualidade' do modelo numa frase para a pessoa."""
    ex_prev, _, qualidade = (previsao or "").partition("|")
    if qualidade == "certo" and ex_prev == exercicio:
        return "certo", ELOGIOS.get(exercicio, "Muito bem!")
    return "errado", DICAS.get(exercicio, "Quase lá! Vamos tentar de novo, com calma.")


class AvaliadorOCI:
    def __init__(self, url, config):
        import oci  # import aqui para os testes não precisarem do SDK
        import requests
        self.url = url.rstrip("/") + "/predict"
        self.requests = requests
        self.signer = oci.signer.Signer(config["tenancy"], config["user"], config["fingerprint"],
                                        private_key_file_location=None, private_key_content=config["key_content"])

    def __call__(self, vetor):
        r = self.requests.post(self.url, json=[list(map(float, vetor))], auth=self.signer, timeout=20)
        r.raise_for_status()
        return r.json()["prediction"][0]


def avaliador_do_ambiente(env=os.environ):
    url = env.get("VINACARE_MODELO_URL")
    chave = env.get("OCI_KEY_CONTENT", "")
    if not chave and env.get("OCI_KEY_B64"):
        chave = base64.b64decode(env["OCI_KEY_B64"]).decode("utf-8")
    config = {"user": env.get("OCI_USER"), "fingerprint": env.get("OCI_FINGERPRINT"),
              "tenancy": env.get("OCI_TENANCY"), "key_content": chave}
    if not url or not all(config.values()):
        return None
    return AvaliadorOCI(url, config)


def avaliar(prever, exercicio, quadros, fps=30):
    """Retorna o resultado para o app. 'prever' é o modelo da Oracle (ou None se não configurado)."""
    if exercicio not in EXERCICIOS:
        return {"ok": False, "erro": "Exercício desconhecido."}
    if visibilidade(quadros) < 0.5:
        return {"ok": True, "qualidade": "fora", "previsao": None,
                "mensagem": "Não consegui ver seu corpo inteiro. Afaste-se um pouco da câmera."}
    if prever is None:
        return {"ok": False, "erro": "Modelo não configurado."}
    previsao = prever(caracteristicas(quadros, fps))
    qualidade, texto = mensagem(exercicio, previsao)
    return {"ok": True, "qualidade": qualidade, "previsao": previsao, "mensagem": texto}
