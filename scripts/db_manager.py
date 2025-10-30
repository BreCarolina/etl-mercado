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

# ============================================================
# Função utilitária adicionada para leitura incremental
# ============================================================
import sqlite3
from contextlib import closing
from typing import Optional

def get_last_timestamp(pair: str, timeframe_s: int, db_path: str = "data/market_data.db") -> Optional[int]:
    """
    Retorna o maior timestamp (UTC epoch) existente em candles para (pair, timeframe_s).
    Se não houver registros, retorna None.
    """
    with closing(sqlite3.connect(db_path)) as con:
        cur = con.cursor()
        row = cur.execute(
            "SELECT MAX(ts) FROM candles WHERE pair=? AND timeframe_s=?",
            (pair, timeframe_s),
        ).fetchone()
        return row[0] if row else None

# ============================================================
# Exportar dados do banco para CSV
# ============================================================
import pandas as pd

def export_to_csv(
    pair: str,
    timeframe_s: int,
    dias: int = 30,
    features: Optional[list[str]] = None,
    db_path: Path | str = DB_PATH_DEFAULT
) -> Path:
    """
    Exporta candles (e opcionalmente features) de (pair, timeframe_s) 
    dos últimos N dias para um CSV em data/exported/.
    """
    db_path = Path(db_path)
    out_dir = Path("data/exported")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{pair}_{timeframe_s}_{dias}d.csv"

    with get_conn(db_path) as conn:
        # Seleciona candles básicos
        base_query = """
            SELECT pair, timeframe_s, ts, abertura, maxima, minima, fechamento, volume
            FROM candles
            WHERE pair=? AND timeframe_s=? 
              AND ts >= strftime('%s','now') - (? * 86400)
            ORDER BY ts DESC
        """
        df = pd.read_sql_query(base_query, conn, params=(pair, timeframe_s, dias))

        # Se houver tabela de features e o usuário quiser colunas extras
        if features:
            try:
                feat_df = pd.read_sql_query(
                    f"SELECT * FROM candles_features WHERE pair=? AND timeframe_s=?",
                    conn,
                    params=(pair, timeframe_s),
                )
                if not feat_df.empty:
                    # junta por ts
                    df = df.merge(feat_df, on=["pair", "timeframe_s", "ts"], how="left")
                    # mantém apenas colunas desejadas
                    cols_keep = [c for c in df.columns if (c in features) or c in ["pair", "timeframe_s", "ts"]]
                    df = df[cols_keep]
            except Exception as e:
                print(f"Aviso: não foi possível juntar features ({e})")

        df.to_csv(out_path, index=False)
        print(f"✔ Exportado para {out_path}")
        return out_path
