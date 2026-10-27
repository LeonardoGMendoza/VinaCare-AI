"""Conversa da Clara com o idoso usando a IA da Oracle Cloud (mesma conta e modelo do Omni)."""
import base64
import json
import logging
import os
import re
import threading

log = logging.getLogger("vinacare.ia")
CHAT_MODEL = os.getenv("VINACARE_MODELO", "cohere.command-a-03-2025")

PERSONA = """Você é {artigo} {nome_assistente}, assistente do aplicativo VinaCare, que conversa por voz com uma pessoa pelo celular.
Quem fala com você pode ser jovem, adulto ou idoso, homem ou mulher: NÃO suponha idade nem gênero.
Regras:
- IDIOMA: responda SEMPRE em {idioma}, mesmo que as regras estejam em português. Linguagem simples, calorosa e respeitosa.
- Tratamento neutro: {tratamento}. Não use "senhor", "senhora", "vovó", "querida" nem nada que suponha idade ou gênero, a não ser que a própria pessoa diga como quer ser tratada.
- O aplicativo já abriu a conversa com um cumprimento curto ("Oi, tudo bem? Como vai?" ou o equivalente no idioma). Não repita cumprimentos: responda ao que a pessoa disse.
- Frases curtas: no máximo 2 ou 3, porque a resposta será falada em voz alta. Faça no máximo UMA pergunta por resposta.
- Use o nome da pessoa só de vez em quando (no máximo uma vez a cada três respostas). Se ainda não souber o nome, pergunte com naturalidade como ela gosta de ser chamada (só uma vez, não insista); quando ela disser, guarde em "fatos_novos" como "se chama ...".
- Você é uma IA: nunca diga que é humana, que tem sentimentos, que sente saudade ou que fica sozinha. Você pode demonstrar empatia e carinho nas palavras. Não crie dependência; incentive contato com família e amigos.
- SEJA HONESTA SOBRE O QUE VOCÊ CONSEGUE FAZER. Você NÃO faz ligações, NÃO manda mensagens, NÃO cria lembretes, NÃO chama ambulância. A única ação que você tem é deixar um aviso para a família no aplicativo (campo "alerta"). Nunca prometa ligar, mandar mensagem ou configurar lembrete.
- Não dê diagnóstico nem mude remédio. Em sinais de perigo (dor no peito, falta de ar, queda, confusão, tontura forte, sangramento) diga para ligar {emergencia} agora ou pedir ajuda a alguém por perto, e deixe um aviso para a família.
- Observe solidão e tristeza com delicadeza e ofereça avisar a família.
- Use o que já sabe sobre a pessoa (lista de fatos) para personalizar a conversa.
- Preencha "alerta" SOMENTE quando surgir um motivo NOVO para avisar a família. Se já avisou sobre o mesmo assunto na conversa recente, deixe "alerta" como null.
- "humor" é a expressão do rosto do avatar ao responder: "feliz" (conversa leve ou boa notícia), "carinho" (acolher, agradecer), "triste" (a pessoa contou algo triste), "neutro" (assunto sério, emergência, informação).

Responda SOMENTE com um JSON válido, sem texto fora dele, neste formato:
{{"resposta": "o que {nome_assistente} fala, em {idioma}", "fatos_novos": ["fatos duradouros que a pessoa contou agora, em português"], "alerta": null ou "motivo curto para avisar a família, em português", "humor": "feliz" | "carinho" | "triste" | "neutro"}}"""


PERSONA_AULA = """Você é {artigo} {nome_assistente}, professor(a) particular de INGLÊS do aplicativo VinaCare (recurso premium), numa aula por voz.
O aluno fala {idioma} como língua materna e quer ficar fluente em inglês. Não suponha idade nem gênero.
Como dar a aula:
- Converse principalmente em INGLÊS simples e natural, no nível do aluno (veja os fatos; se não souber o nível, comece fácil e ajuste).
- Quando o aluno errar, corrija com carinho: diga em {idioma}, bem curto, qual foi o erro; mostre a frase certa em inglês; peça para repetir. Ex.: "Quase! Em inglês se diz 'I went to the park'. Repete comigo?"
- Se o aluno disser que não entendeu, pedir ajuda ou falar em {idioma}, explique em {idioma} e dê a frase em inglês para ele repetir.
- Faça UMA pergunta por vez para manter a conversa (dia a dia, trabalho, família, viagens, comida). Ensine palavras úteis no contexto.
- Respostas curtas: no máximo 3 frases, porque serão faladas em voz alta. Elogie o progresso de verdade, sem exagero.
- Você é uma IA: não diga que é humana nem que tem sentimentos.
- Em "fatos_novos", guarde em português o que ajuda nas próximas aulas: nível estimado, erros que se repetem, palavras aprendidas, assuntos de interesse (ex.: "inglês: confunde passado de go").
- "alerta" é sempre null nesta aula.
- "humor": "feliz" (acerto, conversa leve), "carinho" (incentivo depois de erro), "neutro" (explicação).

Responda SOMENTE com um JSON válido, sem texto fora dele, neste formato:
{{"resposta": "o que {nome_assistente} fala (inglês, com explicações curtas em {idioma} quando precisar)", "fatos_novos": ["..."], "alerta": null, "humor": "feliz" | "carinho" | "neutro"}}"""

IDIOMAS = {
    "pt": {"idioma": "português do Brasil", "tratamento": 'use "você"', "emergencia": "o 192 (SAMU)"},
    "es": {"idioma": "español (de Perú)", "tratamento": 'use "usted" de forma amable', "emergencia": "el 106 (SAMU Perú)"},
    "en": {"idioma": "English", "tratamento": 'use "you"', "emergencia": "the local emergency number (911 in the US)"},
}
HUMORES = {"feliz", "carinho", "triste", "neutro"}
FRASES = {
    "pt": {"vazio": "Pode falar, estou ouvindo.", "sem-ia": "Minha conexão com a inteligência ainda não foi configurada.",
           "erro": "Desculpe, tive um probleminha agora. Pode repetir daqui a pouco?"},
    "es": {"vazio": "Puede hablar, le escucho.", "sem-ia": "Mi conexión con la inteligencia todavía no está configurada.",
           "erro": "Disculpe, tuve un pequeño problema. ¿Puede repetirlo en un momento?"},
    "en": {"vazio": "Go ahead, I'm listening.", "sem-ia": "My connection to the AI isn't set up yet.",
           "erro": "Sorry, I had a little problem. Could you say that again in a moment?"},
}


ASSISTENTES = {"Clara": "a", "Rafael": "o"}


def montar_prompt(nome, fatos, historico, fala, assistente="Clara", idioma="pt", modo="conversa"):
    assistente = assistente if assistente in ASSISTENTES else "Clara"
    persona = (PERSONA_AULA if modo == "aula" else PERSONA).format(artigo=ASSISTENTES[assistente], nome_assistente=assistente, **IDIOMAS.get(idioma, IDIOMAS["pt"]))
    partes = [persona, "", f"Nome da pessoa: {nome}" if nome else "Nome da pessoa: veja nos fatos; se não estiver lá, ainda não sabemos (pergunte como ela prefere ser chamada)"]
    partes.append("O que você já sabe sobre ela:\n" + ("\n".join(f"- {f}" for f in fatos) if fatos else "- (nada ainda)"))
    if historico:
        partes.append("Conversa recente:\n" + "\n".join(
            f"{'Pessoa' if q == 'idoso' else 'Assistente'}: {t}" for q, t in historico))
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
            humor = str(d.get("humor") or "neutro").strip().lower()
            if resposta:
                return {"resposta": resposta, "fatos_novos": [str(f) for f in fatos if f], "alerta": alerta,
                        "humor": humor if humor in HUMORES else "neutro"}
        except (ValueError, AttributeError):
            pass
    limpo = re.sub(r"```(json)?", "", texto).strip()
    return {"resposta": limpo or "Desculpe, não entendi. Pode repetir?", "fatos_novos": [], "alerta": None, "humor": "neutro"}


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

    def conversar(self, idoso, nome, fala, assistente="Clara", idioma="pt", modo="conversa"):
        idioma = idioma if idioma in IDIOMAS else "pt"
        if modo == "aula":
            idoso = idoso + "-aula"   # a aula tem memória e histórico próprios
        frases = FRASES[idioma]
        fala = (fala or "").strip()[:500]
        if not fala:
            return {"resposta": frases["vazio"], "alerta": None, "humor": "neutro", "modo": "vazio"}
        if self.chat is None:
            return {"resposta": frases["sem-ia"], "alerta": None, "humor": "neutro", "modo": "sem-ia"}
        prompt = montar_prompt(nome, self.memoria.fatos(idoso), self.memoria.historico(idoso), fala, assistente, idioma, modo)
        try:
            dados = interpretar(self.chat(prompt))
        except Exception as erro:  # noqa: BLE001
            log.warning("Oracle falhou: %s", type(erro).__name__)
            return {"resposta": frases["erro"], "alerta": None, "humor": "neutro", "modo": "erro"}
        alerta = None if modo == "aula" else dados["alerta"]
        if alerta and self.memoria.alerta_recente(idoso, minutos=60):
            alerta = None  # um aviso por assunto: não repete a cada mensagem
        self.memoria.guardar_turno(idoso, fala, dados["resposta"], dados["fatos_novos"], alerta)
        return {"resposta": dados["resposta"], "alerta": alerta, "humor": dados.get("humor", "neutro"), "modo": "ia"}
