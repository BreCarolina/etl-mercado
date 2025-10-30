# -*- coding: utf-8 -*-
"""
carga.py — Carrega dados transformados em SQLite (UPSERT).
API pública:
    - load_transformed(pair, timeframe_s, csv_path=None) -> dict
      Se csv_path for None, usa o arquivo mais recente em data/transformed/
"""
from __future__ import annotations
from pathlib import Path
from typing import Iterable, Tuple, Optional
import pandas as pd
from . import db_manager as dm

ROOT = Path(__file__).resolve().parents[1]
TRANS_DIR = ROOT / "data" / "transformed"

def _tf_label(tf: int) -> str:
    return f"M{tf//60}" if tf % 60 == 0 else f"S{tf}"

def _latest_transformed(pair: str, timeframe_s: int) -> Path:
    tf = _tf_label(timeframe_s)
    pats = [f"{pair}_{tf}_*.csv", f"{pair}_{tf}.csv"]
    files = []
    for pat in pats:
        files.extend(TRANS_DIR.glob(pat))
    if not files:
        raise FileNotFoundError(f"Nenhum CSV transformado para {pair}/{tf} em {TRANS_DIR}")
    return max(files, key=lambda p: p.stat().st_mtime)

def _rows_from_csv(csv_path: Path, pair: str, timeframe_s: int) -> Iterable[Tuple[str,int,int,float,float,float,float,float,str]]:
    df = pd.read_csv(csv_path)
    # Campos esperados do transformado: timestamp (ou equivalente) + OHLCV
    # Garantimos 'timestamp' UTC e os numéricos necessários
    time_col = next((c for c in ("timestamp","datetime","time","from") if c in df.columns), None)
    if time_col is None:
        raise RuntimeError("Coluna temporal não encontrada no CSV transformado.")
    ts = pd.to_datetime(df[time_col], utc=True, errors="coerce")
    df = df.assign(timestamp=ts).dropna(subset=["timestamp"]).sort_values("timestamp")
    # Mapeia para OHLCV (nomes já normalizados na transformação)
    for col in ["abertura","maxima","minima","fechamento","volume"]:
        if col not in df.columns:
            raise RuntimeError(f"Coluna obrigatória ausente no transformado: {col}")
    # Converte datetime -> epoch int
    secs = (df["timestamp"].view("int64") // 1_000_000_000).astype("int64")
    for ts_i, a, h, l, c, v in zip(secs, df["abertura"], df["maxima"], df["minima"], df["fechamento"], df["volume"]):
        yield (pair, int(timeframe_s), int(ts_i), float(a), float(h), float(l), float(c), float(v), "iqoption")

def load_transformed(pair: str, timeframe_s: int, csv_path: Optional[str|Path] = None) -> dict:
    """
    Carrega um CSV transformado para SQLite (UPSERT).
    Se csv_path=None, pega o mais recente de data/transformed/ para (pair,timeframe).
    Retorna: {"upserts": int, "csv": str, "max_ts": int|None}
    """
    if csv_path is None:
        csv = _latest_transformed(pair, timeframe_s)
    else:
        csv = Path(csv_path)
        if not csv.exists():
            raise FileNotFoundError(str(csv))
    rows = _rows_from_csv(csv, pair, timeframe_s)
    n = dm.upsert_candles(rows)
    max_ts = dm.get_last_timestamp(pair, timeframe_s)
    return {"upserts": n, "csv": str(csv), "max_ts": max_ts}
