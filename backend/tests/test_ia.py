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

    def test_sem_ia(self):
        with tempfile.TemporaryDirectory() as d:
            mem = Memoria(d)
            self.assertEqual(Clara(None, mem).conversar("demo", "", "oi")["modo"], "sem-ia")
            mem.db.close()


if __name__ == "__main__":
    unittest.main()
