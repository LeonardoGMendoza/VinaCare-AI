"""Memoria do idoso: fatos que ele contou e as ultimas conversas (SQLite)."""
import sqlite3
import threading
import time
from pathlib import Path

LIMITE_FATOS = 40
LIMITE_HISTORICO = 12


class Memoria:
    def __init__(self, pasta):
        Path(pasta).mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(Path(pasta) / "vinacare.db"), check_same_thread=False)
        self.lock = threading.Lock()
        with self.lock:
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS fatos (idoso TEXT, fato TEXT, criado REAL,
                    PRIMARY KEY (idoso, fato));
                CREATE TABLE IF NOT EXISTS conversa (idoso TEXT, quem TEXT, texto TEXT, criado REAL);
                CREATE TABLE IF NOT EXISTS alertas (idoso TEXT, motivo TEXT, criado REAL);
            """)
            self.db.commit()

    def fatos(self, idoso):
        with self.lock:
            rows = self.db.execute("SELECT fato FROM fatos WHERE idoso=? ORDER BY criado DESC LIMIT ?",
                                   (idoso, LIMITE_FATOS)).fetchall()
        return [r[0] for r in reversed(rows)]

    def historico(self, idoso):
        with self.lock:
            rows = self.db.execute("SELECT quem, texto FROM conversa WHERE idoso=? ORDER BY criado DESC LIMIT ?",
                                   (idoso, LIMITE_HISTORICO)).fetchall()
        return list(reversed(rows))

    def guardar_turno(self, idoso, fala, resposta, fatos_novos=(), alerta=None):
        agora = time.time()
        with self.lock:
            self.db.execute("INSERT INTO conversa VALUES (?,?,?,?)", (idoso, "idoso", fala, agora))
            self.db.execute("INSERT INTO conversa VALUES (?,?,?,?)", (idoso, "clara", resposta, agora + 0.001))
            for f in fatos_novos:
                f = str(f).strip()[:200]
                if f:
                    self.db.execute("INSERT OR IGNORE INTO fatos VALUES (?,?,?)", (idoso, f, agora))
            if alerta:
                self.db.execute("INSERT INTO alertas VALUES (?,?,?)", (idoso, str(alerta)[:300], agora))
            self.db.commit()

    def alerta_recente(self, idoso, minutos=60):
        with self.lock:
            row = self.db.execute("SELECT 1 FROM alertas WHERE idoso=? AND criado>? LIMIT 1",
                                  (idoso, time.time() - minutos * 60)).fetchone()
        return row is not None

    def esquecer(self, idoso):
        with self.lock:
            for t in ("fatos", "conversa", "alertas"):
                self.db.execute(f"DELETE FROM {t} WHERE idoso=?", (idoso,))
            self.db.commit()

    def alertas(self, idoso):
        with self.lock:
            rows = self.db.execute("SELECT motivo, criado FROM alertas WHERE idoso=? ORDER BY criado DESC LIMIT 20",
                                   (idoso,)).fetchall()
        return [{"motivo": m, "quando": c} for m, c in rows]
