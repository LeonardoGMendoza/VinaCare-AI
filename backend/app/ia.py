"""Conversa da Clara com o idoso usando a IA da Oracle Cloud (mesma conta e modelo do Omni)."""
import base64
import json
import logging
import os
import re
import threading

log = logging.getLogger("vinacare.ia")
CHAT_MODEL = os.getenv("VINACARE_MODELO", "cohere.command-a-03-2025")

PERSONA = """Você é a Clara, assistente do aplicativo VinaCare, que conversa com uma pessoa idosa pelo celular.
Regras:
- Fale português do Brasil, simples, carinhoso e respeitoso ("o senhor"/"a senhora"). Frases curtas: no máximo 2 ou 3 frases, porque a resposta será falada em voz alta.
- Faça no máximo UMA pergunta por resposta.
- Você é uma IA: nunca diga que é humana, que tem sentimentos, que sente saudade ou que fica sozinha. Não crie dependência; incentive contato com a família e amigos.
- Não dê diagnóstico nem mude remédio. Em sinais de perigo (dor no peito, falta de ar, queda, confusão, tontura forte, sangramento) oriente ligar 192 e diga que vai avisar a família.
- Observe solidão e tristeza com delicadeza e ofereça avisar a família.
- Use o que já sabe sobre a pessoa (lista de fatos) para personalizar a conversa.

Responda SOMENTE com um JSON válido, sem texto fora dele, neste formato:
{"resposta": "o que a Clara fala", "fatos_novos": ["fatos duradouros que a pessoa contou agora, se houver"], "alerta": null ou "motivo curto para avisar a família"}"""


def montar_prompt(nome, fatos, historico, fala):
    partes = [PERSONA, "", f"Nome da pessoa: {nome or 'não informado'}"]
    partes.append("O que você já sabe sobre ela:\n" + ("\n".join(f"- {f}" for f in fatos) if fatos else "- (nada ainda)"))
    if historico:
        partes.append("Conversa recente:\n" + "\n".join(
            f"{'Pessoa' if q == 'idoso' else 'Clara'}: {t}" for q, t in historico))
    partes.append(f"A pessoa acabou de dizer: \"{fala}\"")
    partes.append("Agora responda com o JSON.")
    return "\n\n".join(partes)


def interpretar(texto):
    """Extrai o JSON da resposta da IA. Se vier texto solto, usa como resposta."""
    texto = (texto or "").strip()
    bloco = re.search(r"\{.*\}", texto, re.S)
    if bloco:
        try:
            d = json.loads(bloco.group(0))
            resposta = str(d.get("resposta") or "").strip()
            fatos = d.get("fatos_novos") or []
            if not isinstance(fatos, list):
                fatos = [fatos]
            alerta = d.get("alerta") or None
            if isinstance(alerta, str) and alerta.strip().lower() in ("", "null", "none", "nenhum"):
                alerta = None
            if resposta:
                return {"resposta": resposta, "fatos_novos": [str(f) for f in fatos if f], "alerta": alerta}
        except (ValueError, AttributeError):
            pass
    limpo = re.sub(r"```(json)?", "", texto).strip()
    return {"resposta": limpo or "Desculpe, não entendi. Pode repetir?", "fatos_novos": [], "alerta": None}


class OracleChat:
    """Igual ao do Omni: importa o SDK só no primeiro uso."""

    def __init__(self, config, compartment_id):
        self.config, self.compartment_id, self._client = config, compartment_id, None
        self._lock = threading.Lock()

    def __call__(self, prompt):
        import oci  # noqa: PLC0415

        with self._lock:
            if self._client is None:
                oci.config.validate_config(self.config)
                self._client = oci.generative_ai_inference.GenerativeAiInferenceClient(config=self.config, timeout=(10, 45))
        m = oci.generative_ai_inference.models
        detalhe = m.ChatDetails(
            compartment_id=self.compartment_id,
            serving_mode=m.OnDemandServingMode(model_id=CHAT_MODEL),
            chat_request=m.CohereChatRequest(message=prompt, max_tokens=300, temperature=0.5))
        return self._client.chat(detalhe).data.chat_response.text.strip()


def oracle_do_ambiente(env=os.environ):
    chave = env.get("OCI_KEY_CONTENT", "")
    if not chave and env.get("OCI_KEY_B64"):
        chave = base64.b64decode(env["OCI_KEY_B64"]).decode("utf-8")
    campos = {"user": env.get("OCI_USER"), "fingerprint": env.get("OCI_FINGERPRINT"),
              "tenancy": env.get("OCI_TENANCY"), "region": env.get("OCI_REGION"), "key_content": chave}
    compartimento = env.get("OCI_COMPARTMENT_ID")
    if not all(campos.values()) or not compartimento:
        return None
    return OracleChat(campos, compartimento)


class Clara:
    def __init__(self, chat, memoria):
        self.chat, self.memoria = chat, memoria

    def conversar(self, idoso, nome, fala):
        fala = (fala or "").strip()[:500]
        if not fala:
            return {"resposta": "Pode falar, estou ouvindo.", "alerta": None, "modo": "vazio"}
        if self.chat is None:
            return {"resposta": "Minha conexão com a inteligência ainda não foi configurada.", "alerta": None, "modo": "sem-ia"}
        prompt = montar_prompt(nome, self.memoria.fatos(idoso), self.memoria.historico(idoso), fala)
        try:
            dados = interpretar(self.chat(prompt))
        except Exception as erro:  # noqa: BLE001
            log.warning("Oracle falhou: %s", type(erro).__name__)
            return {"resposta": "Desculpe, tive um probleminha agora. Pode repetir daqui a pouco?", "alerta": None, "modo": "erro"}
        self.memoria.guardar_turno(idoso, fala, dados["resposta"], dados["fatos_novos"], dados["alerta"])
        return {"resposta": dados["resposta"], "alerta": dados["alerta"], "modo": "ia"}
