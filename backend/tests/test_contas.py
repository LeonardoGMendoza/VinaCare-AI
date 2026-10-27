import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.contas import Contas, confere_senha, hash_senha


class TestContas(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        db = str(Path(self.dir.name) / "t.db")

        def conectar():
            c = sqlite3.connect(db)
            c.execute("PRAGMA foreign_keys = ON")
            return c
        self.contas = Contas(conectar, "sqlite")

    def tearDown(self):
        self.dir.cleanup()

    def test_hash_nao_guarda_a_senha(self):
        h = hash_senha("minhasenha123")
        self.assertNotIn("minhasenha123", h)
        self.assertTrue(confere_senha("minhasenha123", h))
        self.assertFalse(confere_senha("errada", h))

    def test_login_premium(self):
        self.contas.criar("Leo@Email.com", "senha-forte-1", "Leo", premium=True)
        token, u = self.contas.entrar("leo@email.com", "senha-forte-1")
        self.assertTrue(u["premium"])
        self.assertEqual(self.contas.usuario(token)["nome"], "Leo")

    def test_senha_errada_e_sem_conta(self):
        self.contas.criar("a@b.com", "senha-forte-1")
        self.assertIsNone(self.contas.entrar("a@b.com", "outra-senha"))
        self.assertIsNone(self.contas.entrar("ninguem@b.com", "senha-forte-1"))

    def test_sair_e_desativar(self):
        self.contas.criar("a@b.com", "senha-forte-1", premium=True)
        token, _ = self.contas.entrar("a@b.com", "senha-forte-1")
        self.contas.sair(token)
        self.assertIsNone(self.contas.usuario(token))
        token, _ = self.contas.entrar("a@b.com", "senha-forte-1")
        self.contas.definir("a@b.com", ativo=False)
        self.assertIsNone(self.contas.usuario(token))

    def test_senha_curta(self):
        with self.assertRaises(ValueError):
            self.contas.criar("a@b.com", "123")


if __name__ == "__main__":
    unittest.main()
