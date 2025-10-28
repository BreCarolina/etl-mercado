from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Iterable, Tuple, Optional

DB_PATH_DEFAULT = Path("data/market_data.db")

def get_conn(db_path: Path | str = DB_PATH_DEFAULT) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db(db_path: Path | str = DB_PATH_DEFAULT) -> None:
    with get_conn(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS candles (
              pair         TEXT    NOT NULL,
              timeframe_s  INTEGER NOT NULL,
              ts           INTEGER NOT NULL,      -- epoch UTC (coluna 'from' do CSV)
              abertura     REAL    NOT NULL,
              maxima       REAL    NOT NULL,
              minima       REAL    NOT NULL,
              fechamento   REAL    NOT NULL,
              volume       REAL    NOT NULL,
              source       TEXT    NOT NULL DEFAULT 'iqoption',
              UNIQUE (pair, timeframe_s, ts)
            );
            CREATE INDEX IF NOT EXISTS idx_candles_pair_tf_ts
              ON candles (pair, timeframe_s, ts);

            -- Tabela de features é opcional neste MVP inicial; criamos o esqueleto sem obrigatoriedade.
            CREATE TABLE IF NOT EXISTS candles_features (
              pair         TEXT    NOT NULL,
              timeframe_s  INTEGER NOT NULL,
              ts           INTEGER NOT NULL,
              ema7         REAL,
              ema21        REAL,
              rsi14        REAL,
              volatilidade REAL,
              sr_low       REAL,
              sr_high      REAL,
              features_ver TEXT    NOT NULL DEFAULT 'v1',
              UNIQUE (pair, timeframe_s, ts)
            );
            CREATE INDEX IF NOT EXISTS idx_feat_pair_tf_ts
              ON candles_features (pair, timeframe_s, ts);

            -- Auditoria (opcional)
            CREATE TABLE IF NOT EXISTS extractions (
              run_id       TEXT    NOT NULL UNIQUE,
              pair         TEXT    NOT NULL,
              timeframe_s  INTEGER NOT NULL,
              from_ts      INTEGER NOT NULL,
              to_ts        INTEGER NOT NULL,
              rows_saved   INTEGER NOT NULL,
              created_at   INTEGER NOT NULL DEFAULT (strftime('%s','now'))
            );
            """
        )

def get_max_ts(pair: str, timeframe_s: int, db_path: Path | str = DB_PATH_DEFAULT) -> Optional[int]:
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "SELECT MAX(ts) FROM candles WHERE pair=? AND timeframe_s=?",
            (pair, timeframe_s),
        )
        row = cur.fetchone()
        return row[0] if row and row[0] is not None else None

def upsert_candles(
    rows: Iterable[Tuple[str, int, int, float, float, float, float, float, str]],
    db_path: Path | str = DB_PATH_DEFAULT
) -> int:
    """
    rows: iterável de tuplas no formato:
      (pair, timeframe_s, ts, abertura, maxima, minima, fechamento, volume, source)
    Retorna quantidade de linhas inseridas (exclui as que 'baterem' em UNIQUE).
    """
    with get_conn(db_path) as conn:
        sql = """
        INSERT INTO candles
          (pair, timeframe_s, ts, abertura, maxima, minima, fechamento, volume, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(pair, timeframe_s, ts) DO NOTHING;
        """
        cur = conn.executemany(sql, rows)
        return cur.rowcount if cur.rowcount is not None else 0

if __name__ == "__main__":
    init_db()
    print(f"Banco inicializado em {DB_PATH_DEFAULT}")
