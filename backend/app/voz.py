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

    def __call__(self, texto):
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


def voz_do_ambiente(chat):
    """Reaproveita as mesmas credenciais da IA de conversa."""
    if chat is None:
        return None
    return OracleVoz(chat.config, chat.compartment_id)
