# -*- coding: utf-8 -*-
"""
transformacao.py — Transforma candles brutos (data/raw) em dataset técnico.
Fluxo:
1) Localiza CSV mais recente de data/raw para (par,timeframe)
2) Saneia OHLCV e timestamps
3) Calcula features (EMAs, RSI, SR, volatilidade, candle stats)
4) Gera target binário (horizon)
5) Warmup e salva em data/transformed/
Assinatura (compatível com GUI):
    transformar_dados(par, timeframe, dias=0, horizon=1, janela_sr=48, rsi_period=14, vol_window=10, raw_path=None)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, List, Union
from datetime import datetime, timezone

import numpy as np
import pandas as pd
# Colunas de features geradas pelo transformador (para UI/Export)
FEATURE_COLUMNS = [
    "corpo",
    "pavio_superior",
    "pavio_inferior",
    "pressao_compradora",
    "pressao_vendedora",
    "EMA_7",
    "EMA_21",
    "resistencia",
    "suporte",
    "dist_resistencia",
    "dist_suporte",
    "retorno",
    "volatilidade",
    "RSI_14",
    "fechamento_futuro",
    "target_class",
]


# Caminhos
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
TRANS_DIR = ROOT / "data" / "transformed"
TRANS_DIR.mkdir(parents=True, exist_ok=True)

# Defaults
PAR_DEFAULT = os.getenv("PAR", "EURUSD")
TIMEFRAME_DEFAULT = int(os.getenv("TIMEFRAME", "300"))
DIAS_DEFAULT = int(os.getenv("DIAS", "0"))
JANELA_SR_DEFAULT = int(os.getenv("JANELA_SR", "48"))
HORIZON_DEFAULT = int(os.getenv("HORIZON", "1"))
RSI_PERIOD_DEFAULT = int(os.getenv("RSI_PERIOD", "14"))
VOL_WINDOW_DEFAULT = int(os.getenv("VOL_WINDOW", "10"))

# ----------------------------- util -----------------------------
def _tf_from_any(tf: Union[int, str]) -> int:
    if isinstance(tf, int):
        return tf
    t = str(tf).strip().upper()
    if t.startswith("M") and t[1:].isdigit():
        return int(t[1:]) * 60
    if t.startswith("H") and t[1:].isdigit():
        return int(t[1:]) * 3600
    try:
        return int(t)
    except Exception:
        return 300

def _tf_label(tf: int) -> str:
    if tf % 60 == 0:
        m = tf // 60
        return f"M{m}" if m < 60 else f"H{m//60}"
    return f"S{tf}"

def _latest_raw_path(par: str, timeframe_s: int) -> Path:
    tf = _tf_label(timeframe_s)
    pats = [f"{par}_{tf}_*.csv", f"{par}_{tf}.csv"]
    files = []
    for pat in pats:
        files.extend(RAW_DIR.glob(pat))
    if not files:
        raise FileNotFoundError(f"Nenhum CSV em data/raw para {par}/{tf}")
    return max(files, key=lambda p: p.stat().st_mtime)

def _ensure_columns(df: pd.DataFrame, cols: List[str]) -> None:
    miss = [c for c in cols if c not in df.columns]
    if miss:
        raise ValueError(f"Colunas ausentes: {miss}")

def _sanitize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    ohlc = ["abertura", "maxima", "minima", "fechamento", "volume"]
    df = df.dropna(subset=ohlc)
    ok_max = df["maxima"] >= df[["abertura","fechamento"]].max(axis=1)
    ok_min = df["minima"] <= df[["abertura","fechamento"]].min(axis=1)
    df = df[ok_max & ok_min & (df["volume"] >= 0)]
    return df.sort_values("timestamp").reset_index(drop=True)

def _rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace({0: np.nan})
    return 100 - (100 / (1 + rs))

def _rolling_vol(ret: pd.Series, window: int = 10) -> pd.Series:
    return ret.rolling(window=window, min_periods=window).std()

# -------------------------- principal --------------------------
def transformar_dados(
    par: str,
    timeframe: Union[int, str],
    dias: int = 0,
    horizon: int = 1,
    janela_sr: int = JANELA_SR_DEFAULT,
    rsi_period: int = RSI_PERIOD_DEFAULT,
    vol_window: int = VOL_WINDOW_DEFAULT,
    raw_path: Optional[Union[str, Path]] = None,
) -> str:
    """
    Transforma candle bruto em dataset técnico e salva CSV.
    - dias = 0  -> usa todo o CSV disponível
    - dias > 0  -> recorta pelos últimos N dias dentro do CSV
    Retorna caminho do CSV salvo (str).
    """
    tf_s = _tf_from_any(timeframe)

    # localizar CSV (auto ou caminho informado)
    if raw_path is None or str(raw_path).lower() in ("", "auto"):
        raw = _latest_raw_path(par, tf_s)
    else:
        raw = Path(raw_path)
        if not raw.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {raw}")

    df = pd.read_csv(raw)
    time_col = next((c for c in ("from","datetime","timestamp","time") if c in df.columns), None)
    if time_col is None:
        raise RuntimeError("Coluna temporal ausente (ex.: 'from').")

    # timestamp -> datetime UTC
    ts = pd.to_datetime(df[time_col], utc=True, errors="coerce")
    df = df.assign(timestamp=ts).dropna(subset=["timestamp"])
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    # garante OHLCV esperado
    _ensure_columns(df, ["abertura","maxima","minima","fechamento","volume"])
    df = _sanitize_ohlc(df)

    # opcional: recorte pelos últimos N dias
    if dias and int(dias) > 0:
        max_ts = df["timestamp"].max()
        start = max_ts - pd.Timedelta(days=int(dias))
        df = df[df["timestamp"] >= start].reset_index(drop=True)

    # features básicas de candle
    corpo = df["fechamento"] - df["abertura"]
    pavio_sup = (df["maxima"] - df[["fechamento","abertura"]].max(axis=1)).clip(lower=0)
    pavio_inf = (df[["fechamento","abertura"]].min(axis=1) - df["minima"]).clip(lower=0)
    df["corpo"] = corpo
    df["pavio_superior"] = pavio_sup
    df["pavio_inferior"] = pavio_inf
    df["pressao_compradora"] = df["pavio_inferior"] + corpo.clip(lower=0)
    df["pressao_vendedora"] = df["pavio_superior"] + (-corpo).clip(lower=0)

    # tendência e níveis
    df["EMA_7"] = df["fechamento"].ewm(span=7, adjust=False).mean()
    df["EMA_21"] = df["fechamento"].ewm(span=21, adjust=False).mean()
    df["resistencia"] = df["maxima"].rolling(window=janela_sr, min_periods=janela_sr).max()
    df["suporte"] = df["minima"].rolling(window=janela_sr, min_periods=janela_sr).min()
    df["dist_resistencia"] = (df["resistencia"] - df["fechamento"]).clip(lower=0)
    df["dist_suporte"] = (df["fechamento"] - df["suporte"]).clip(lower=0)

    # momentum/vol
    df["retorno"] = df["fechamento"].pct_change()
    df["volatilidade"] = _rolling_vol(df["retorno"], window=vol_window)
    df["RSI_14"] = _rsi_wilder(df["fechamento"], period=rsi_period)

    # target
    df["fechamento_futuro"] = df["fechamento"].shift(-int(horizon))
    df["target_class"] = np.where(
        df["fechamento_futuro"] > df["fechamento"], 1.0,
        np.where(df["fechamento_futuro"] < df["fechamento"], 0.0, np.nan)
    )

    # warmup + corte horizonte
    warmup = max(21, rsi_period, vol_window, int(janela_sr))
    df = df.iloc[warmup:].copy()
    if int(horizon) > 0:
        df = df[:-int(horizon)]
    df = df.dropna().reset_index(drop=True)

    # saída
    dias_reais = int(df["timestamp"].dt.normalize().nunique()) if not df.empty else 0
    inicio = df["timestamp"].min().strftime("%Y%m%d") if not df.empty else "NA"
    fim = df["timestamp"].max().strftime("%Y%m%d") if not df.empty else "NA"
    ts_now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    tf_label = _tf_label(tf_s)
    out_name = f"{par}_{tf_label}_{dias_reais}d_{inicio}-{fim}_n{len(df)}_{ts_now}.csv"
    out_path = TRANS_DIR / out_name
    df.to_csv(out_path, index=False)

    print(f"✔ Transformação concluída: {out_path}")
    return str(out_path)

if __name__ == "__main__":
    out = transformar_dados(PAR_DEFAULT, TIMEFRAME_DEFAULT, dias=DIAS_DEFAULT, horizon=HORIZON_DEFAULT, janela_sr=JANELA_SR_DEFAULT)
    print(out)
