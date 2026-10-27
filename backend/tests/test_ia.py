import tempfile
import unittest

from app.ia import Clara, interpretar, montar_prompt
from app.memoria import Memoria


class TestIA(unittest.TestCase):
    def test_interpreta_json(self):
        d = interpretar('```json\n{"resposta": "Que bom!", "fatos_novos": ["gosta de futebol"], "alerta": null}\n```')
        self.assertEqual(d["resposta"], "Que bom!")
        self.assertEqual(d["fatos_novos"], ["gosta de futebol"])
        self.assertIsNone(d["alerta"])

    def test_texto_solto(self):
        self.assertEqual(interpretar("Olá, tudo bem?")["resposta"], "Olá, tudo bem?")

    def test_prompt_tem_fatos(self):
        p = montar_prompt("Etelvina", ["tem uma neta chamada Ana"], [("idoso", "oi")], "dormi mal")
        self.assertIn("neta chamada Ana", p)
        self.assertIn("dormi mal", p)

    def test_memoria_e_conversa(self):
        with tempfile.TemporaryDirectory() as d:
            mem = Memoria(d)
            falso = lambda prompt: '{"resposta": "Sinto muito. Quer que eu avise sua filha?", "fatos_novos": ["mora sozinha"], "alerta": "sentindo-se sozinha"}'
            r = Clara(falso, mem).conversar("demo", "Etelvina", "estou me sentindo sozinha")
            self.assertEqual(r["modo"], "ia")
            self.assertEqual(r["alerta"], "sentindo-se sozinha")
            self.assertEqual(mem.fatos("demo"), ["mora sozinha"])
            self.assertEqual(len(mem.historico("demo")), 2)
            mem.db.close()

    def test_alerta_nao_repete(self):
        with tempfile.TemporaryDirectory() as d:
            mem = Memoria(d)
            falso = lambda prompt: '{"resposta": "Deixei um aviso.", "fatos_novos": [], "alerta": "saudade"}'
            c = Clara(falso, mem)
            self.assertEqual(c.conversar("x1", "", "saudade")["alerta"], "saudade")
            self.assertIsNone(c.conversar("x1", "", "muita saudade")["alerta"])
            mem.db.close()

    def test_sem_nome_pede_nome(self):
        self.assertIn("pergunte como ela prefere ser chamada", montar_prompt("", [], [], "oi"))

    def test_idioma_e_tratamento_neutro(self):
        p = montar_prompt("", [], [], "hola", "Rafael", "es")
        self.assertIn("español", p)
        self.assertIn("106", p)
        self.assertIn("NÃO suponha idade nem gênero", p)
        self.assertIn("English", montar_prompt("", [], [], "hi", "Clara", "en"))

    def test_humor(self):
        self.assertEqual(interpretar('{"resposta": "Que pena.", "humor": "triste"}')["humor"], "triste")
        self.assertEqual(interpretar('{"resposta": "Oi", "humor": "furioso"}')["humor"], "neutro")

    def test_erro_no_idioma(self):
        with tempfile.TemporaryDirectory() as d:
            mem = Memoria(d)
            r = Clara(None, mem).conversar("demo", "", "hello", "Clara", "en")
            self.assertIn("AI", r["resposta"])
            mem.db.close()

    def test_sem_ia(self):
        with tempfile.TemporaryDirectory() as d:
            mem = Memoria(d)
            self.assertEqual(Clara(None, mem).conversar("demo", "", "oi")["modo"], "sem-ia")
            mem.db.close()


class TestVoz(unittest.TestCase):
    def test_escolhe_azure(self):
        from app.voz import AzureVoz, voz_do_ambiente
        v = voz_do_ambiente(None, {"AZURE_SPEECH_KEY": "k", "AZURE_SPEECH_REGION": "brazilsouth"})
        self.assertIsInstance(v, AzureVoz)
        self.assertIn("brazilsouth.tts.speech.microsoft.com", v.url)

    def test_sem_nada(self):
        from app.voz import voz_do_ambiente
        self.assertIsNone(voz_do_ambiente(None, {}))


if __name__ == "__main__":
    unittest.main()
