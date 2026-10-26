import tempfile
import unittest

from app.dataset import Dataset, validar

QUADRO = [0.5] * 132


class TestDataset(unittest.TestCase):
    def test_valida(self):
        self.assertIsNone(validar("levantar_bracos", "certo", [QUADRO] * 20))
        self.assertIsNotNone(validar("pular", "certo", [QUADRO] * 20))
        self.assertIsNotNone(validar("levantar_bracos", "talvez", [QUADRO] * 20))
        self.assertIsNotNone(validar("levantar_bracos", "certo", [QUADRO] * 3))
        self.assertIsNotNone(validar("levantar_bracos", "certo", [[1, 2]] * 20))

    def test_salva_e_resume(self):
        with tempfile.TemporaryDirectory() as d:
            ds = Dataset(d)
            ds.salvar("levantar_bracos", "certo", [QUADRO] * 20)
            ds.salvar("levantar_bracos", "errado", [QUADRO] * 20)
            r = ds.resumo()
            self.assertEqual(r["levantar_bracos"]["certo"], 1)
            self.assertEqual(r["levantar_bracos"]["errado"], 1)
            self.assertEqual(len(ds.exportar()), 2)


if __name__ == "__main__":
    unittest.main()
