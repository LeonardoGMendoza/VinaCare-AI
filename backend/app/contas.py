"""Contas premium do VinaCare: login com e-mail e senha, sessão por token.

- Senha guardada só como hash scrypt (biblioteca padrão do Python), com sal próprio por usuário.
- O token de sessão vai para o aparelho; no banco fica só o hash dele (se o banco vazar, os tokens não servem).
- Banco: PostgreSQL do servidor (VINACARE_DB_URL). Nos testes usa SQLite.
"""
import hashlib
import hmac
import os
import secrets
import time

SESSAO_DIAS = 180   # o aparelho do idoso fica conectado por bastante tempo; dá para sair a qualquer momento


def hash_senha(senha, sal=None):
    sal = sal or secrets.token_bytes(16)
    h = hashlib.scrypt(senha.encode("utf-8"), salt=sal, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${sal.hex()}${h.hex()}"


def confere_senha(senha, guardado):
    try:
        _, sal, h = guardado.split("$")
        return hmac.compare_digest(hash_senha(senha, bytes.fromhex(sal)), guardado)
    except (ValueError, AttributeError):
        return False


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class Contas:
    def __init__(self, conectar, dialeto="postgres"):
        self.conectar, self.p = conectar, ("%s" if dialeto == "postgres" else "?")
        id_col = "SERIAL PRIMARY KEY" if dialeto == "postgres" else "INTEGER PRIMARY KEY AUTOINCREMENT"
        with self.conectar() as c:
            cur = c.cursor()
            cur.execute(f"""CREATE TABLE IF NOT EXISTS vinacare_usuarios (
                id {id_col}, email VARCHAR(200) UNIQUE NOT NULL, nome VARCHAR(100) NOT NULL DEFAULT '',
                senha_hash VARCHAR(200) NOT NULL, premium BOOLEAN NOT NULL DEFAULT FALSE,
                ativo BOOLEAN NOT NULL DEFAULT TRUE, criado_em BIGINT NOT NULL)""")
            cur.execute("""CREATE TABLE IF NOT EXISTS vinacare_sessoes (
                token_hash CHAR(64) PRIMARY KEY, usuario_id INTEGER NOT NULL REFERENCES vinacare_usuarios(id) ON DELETE CASCADE,
                criada_em BIGINT NOT NULL, expira_em BIGINT NOT NULL)""")
            c.commit()

    def _um(self, sql, args=()):
        with self.conectar() as c:
            cur = c.cursor()
            cur.execute(sql.replace("?", self.p), args)
            return cur.fetchone()

    def _executar(self, sql, args=()):
        with self.conectar() as c:
            cur = c.cursor()
            cur.execute(sql.replace("?", self.p), args)
            c.commit()

    def criar(self, email, senha, nome="", premium=False):
        email = email.strip().lower()
        if len(senha) < 8:
            raise ValueError("A senha precisa ter pelo menos 8 caracteres.")
        self._executar("INSERT INTO vinacare_usuarios (email, nome, senha_hash, premium, ativo, criado_em) VALUES (?, ?, ?, ?, ?, ?)",
                       (email, nome.strip(), hash_senha(senha), bool(premium), True, int(time.time())))

    def definir(self, email, premium=None, ativo=None, senha=None):
        email = email.strip().lower()
        if premium is not None:
            self._executar("UPDATE vinacare_usuarios SET premium = ? WHERE email = ?", (bool(premium), email))
        if ativo is not None:
            self._executar("UPDATE vinacare_usuarios SET ativo = ? WHERE email = ?", (bool(ativo), email))
        if senha is not None:
            self._executar("UPDATE vinacare_usuarios SET senha_hash = ? WHERE email = ?", (hash_senha(senha), email))

    def entrar(self, email, senha):
        """Devolve (token, usuario) ou None. Sempre faz o cálculo do hash, para não revelar se o e-mail existe."""
        linha = self._um("SELECT id, nome, senha_hash, premium, ativo FROM vinacare_usuarios WHERE email = ?", (email.strip().lower(),))
        guardado = linha[2] if linha else hash_senha("x")
        if not confere_senha(senha, guardado) or not linha or not linha[4]:
            return None
        token, agora = secrets.token_urlsafe(32), int(time.time())
        self._executar("INSERT INTO vinacare_sessoes (token_hash, usuario_id, criada_em, expira_em) VALUES (?, ?, ?, ?)",
                       (_hash_token(token), linha[0], agora, agora + SESSAO_DIAS * 86400))
        return token, {"id": linha[0], "nome": linha[1], "premium": bool(linha[3])}

    def usuario(self, token):
        if not token:
            return None
        linha = self._um("""SELECT u.id, u.nome, u.premium FROM vinacare_sessoes s JOIN vinacare_usuarios u ON u.id = s.usuario_id
                            WHERE s.token_hash = ? AND s.expira_em > ? AND u.ativo = ?""", (_hash_token(token), int(time.time()), True))
        return {"id": linha[0], "nome": linha[1], "premium": bool(linha[2])} if linha else None

    def sair(self, token):
        self._executar("DELETE FROM vinacare_sessoes WHERE token_hash = ?", (_hash_token(token),))


def contas_do_ambiente(env=os.environ):
    url = env.get("VINACARE_DB_URL")
    if not url:
        return None
    import psycopg  # noqa: PLC0415  (só no servidor)
    return Contas(lambda: psycopg.connect(url), "postgres")
