"""Voz da Clara pela nuvem da Oracle (OCI Speech, texto para fala em pt-BR)."""
import logging
import os
import threading
from collections import OrderedDict

log = logging.getLogger("vinacare.voz")


class OracleVoz:
    """Transforma texto em áudio MP3. Importa o SDK só no primeiro uso."""

    def __init__(self, config, compartment_id, env=os.environ):
        self.config = dict(config)
        if env.get("VINACARE_TTS_REGION"):
            self.config["region"] = env["VINACARE_TTS_REGION"]
        self.compartment_id = compartment_id
        self.voz = env.get("VINACARE_TTS_VOZ") or None
        self.modelo = env.get("VINACARE_TTS_MODELO", "TTS_2_NATURAL")
        self._client, self._lock = None, threading.Lock()
        self._cache, self._cache_max = OrderedDict(), 64

    def _cliente(self):
        import oci  # noqa: PLC0415
        with self._lock:
            if self._client is None:
                oci.config.validate_config(self.config)
                self._client = oci.ai_speech.AIServiceSpeechClient(config=self.config, timeout=(10, 45))
        return self._client

    def vozes(self):
        import oci  # noqa: PLC0415
        resp = self._cliente().list_voices(compartment_id=self.compartment_id)
        return oci.util.to_dict(resp.data)

    def __call__(self, texto, voz=None):
        texto = (texto or "").strip()[:600]
        if texto in self._cache:
            self._cache.move_to_end(texto)
            return self._cache[texto]
        import oci  # noqa: PLC0415
        m = oci.ai_speech.models
        detalhes_modelo = {"model_name": self.modelo, "language_code": "pt-BR"}
        if self.voz:
            detalhes_modelo["voice_id"] = self.voz
        Modelo = m.TtsOracleTts2NaturalModelDetails if self.modelo == "TTS_2_NATURAL" else m.TtsOracleTts1StandardModelDetails
        pedido = m.SynthesizeSpeechDetails(
            text=texto,
            is_stream_enabled=False,
            compartment_id=self.compartment_id,
            configuration=m.TtsOracleConfiguration(
                model_family="ORACLE",
                model_details=Modelo(**detalhes_modelo),
                speech_settings=m.TtsOracleSpeechSettings(text_type="TEXT", sample_rate_in_hz=24000, output_format="MP3")))
        dados = self._cliente().synthesize_speech(pedido).data
        audio = dados.content if hasattr(dados, "content") else dados.read()
        self._cache[texto] = audio
        if len(self._cache) > self._cache_max:
            self._cache.popitem(last=False)
        return audio


class AzureVoz:
    """Voz neural da Microsoft Azure (pt-BR) pela API REST, sem SDK extra."""

    def __init__(self, chave, regiao, voz="pt-BR-FranciscaNeural"):
        self.chave, self.regiao, self.voz = chave, regiao, voz
        self.url = f"https://{regiao}.tts.speech.microsoft.com/cognitiveservices/v1"
        self._cache, self._cache_max = OrderedDict(), 128

    def vozes(self):
        import json
        import urllib.request
        req = urllib.request.Request(f"https://{self.regiao}.tts.speech.microsoft.com/cognitiveservices/voices/list",
                                     headers={"Ocp-Apim-Subscription-Key": self.chave})
        with urllib.request.urlopen(req, timeout=20) as r:
            todas = json.loads(r.read().decode("utf-8"))
        return [{"nome": v.get("ShortName"), "genero": v.get("Gender")} for v in todas if v.get("Locale") == "pt-BR"]

    def __call__(self, texto, voz=None):
        import urllib.request
        from xml.sax.saxutils import escape
        texto = (texto or "").strip()[:600]
        voz = voz or self.voz
        chave = (voz, texto)
        if chave in self._cache:
            self._cache.move_to_end(chave)
            return self._cache[chave]
        lingua = "-".join(voz.split("-")[:2]) or "pt-BR"   # ex.: es-PE-CamilaNeural -> es-PE
        ssml = (f'<speak version="1.0" xml:lang="{lingua}"><voice name="{voz}">'
                f'<prosody rate="-8%">{escape(texto)}</prosody></voice></speak>')
        req = urllib.request.Request(self.url, data=ssml.encode("utf-8"), method="POST", headers={
            "Ocp-Apim-Subscription-Key": self.chave,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
            "User-Agent": "VinaCare"})
        with urllib.request.urlopen(req, timeout=30) as r:
            audio = r.read()
        self._cache[chave] = audio
        if len(self._cache) > self._cache_max:
            self._cache.popitem(last=False)
        return audio


def voz_do_ambiente(chat, env=os.environ):
    """Azure se houver chave; senão tenta a voz da Oracle (mesmas credenciais da conversa)."""
    if env.get("AZURE_SPEECH_KEY") and env.get("AZURE_SPEECH_REGION"):
        return AzureVoz(env["AZURE_SPEECH_KEY"], env["AZURE_SPEECH_REGION"], env.get("AZURE_SPEECH_VOZ", "pt-BR-FranciscaNeural"))
    return voz_oracle(chat)


def voz_oracle(chat):
    """Reaproveita as mesmas credenciais da IA de conversa."""
    if chat is None:
        return None
    return OracleVoz(chat.config, chat.compartment_id)
