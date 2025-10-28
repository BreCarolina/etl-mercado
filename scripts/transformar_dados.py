# -*- coding: utf-8 -*-
"""
transformar_dados.py — Transforma candles brutos (data/raw) em dataset técnico.
Etapas:
1. Saneia timestamps e OHLCV.
2. Gera features de candle, EMAs, suporte/resistência, RSI e volatilidade.
3. Cria target binário (1=alta, 0=baixa).
4. Aplica warmup e salva CSV em data/transformed/.
"""

import os
from pathlib import Path
from typing import Optional, List
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timezone

# Caminhos
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
TRANS_DIR = ROOT / "data" / "transformed"
TRANS_DIR.mkdir(parents=True, exist_ok=True)

# .env e parâmetros padrão
load_dotenv(dotenv_path=ROOT / ".env", override=True)
PAR_DEFAULT = os.getenv("PAR", "EURUSD")
TIMEFRAME_DEFAULT = int(os.getenv("TIMEFRAME", "300"))
DIAS_DEFAULT = int(os.getenv("DIAS", "360"))
JANELA_SR_DEFAULT = int(os.getenv("JANELA_SR", "48"))
HORIZON_DEFAULT = int(os.getenv("HORIZON", "1"))
RSI_PERIOD_DEFAULT = 14
VOL_WINDOW_DEFAULT = 10


# ------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------
def _tf_label(timeframe: int) -> str:
    return f"M{int(timeframe)//60}" if timeframe % 60 == 0 else f"S{int(timeframe)}"

def _latest_raw_path(par: str, timeframe: int) -> Path:
    """Busca o CSV mais recente em data/raw/."""
    tf = _tf_label(timeframe)
    prefix = f"{par}_{tf}_"
    files = list(RAW_DIR.glob(f"{prefix}*.csv"))
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo encontrado: {prefix}*.csv")
    return max(files, key=lambda p: p.stat().st_mtime)

def _ensure_columns(df: pd.DataFrame, cols: List[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes: {missing}")

def _sanitize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Remove inconsistências em OHLCV."""
    ohlc = ["abertura", "maxima", "minima", "fechamento", "volume"]
    df = df.dropna(subset=ohlc)
    ok_max = df["maxima"] >= df[["abertura", "fechamento"]].max(axis=1)
    ok_min = df["minima"] <= df[["abertura", "fechamento"]].min(axis=1)
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


# ------------------------------------------------------------
# Função principal
# ------------------------------------------------------------
def transformar_dados(
    raw_path: Optional[Path],
    par: str,
    timeframe: int,
    dias: int,
    horizon: int,
    janela_sr: int,
    rsi_period: int = RSI_PERIOD_DEFAULT,
    vol_window: int = VOL_WINDOW_DEFAULT,
) -> dict:
    """Transforma CSV bruto em dataset técnico e salva em data/transformed."""
    if not raw_path or str(raw_path).lower() in ("", "auto"):
        raw_path = _latest_raw_path(par, timeframe)
    raw_path = Path(raw_path)
    if not raw_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {raw_path}")

    df = pd.read_csv(raw_path)
    time_col = next((c for c in ("from", "datetime", "timestamp", "time") if c in df.columns), None)
    if time_col is None:
        raise RuntimeError("Coluna temporal ausente (ex.: 'from').")

    df["timestamp"] = pd.to_datetime(df[time_col], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
    _ensure_columns(df, ["abertura", "maxima", "minima", "fechamento", "volume"])
    df = _sanitize_ohlc(df)

    # Features de candle
    corpo = df["fechamento"] - df["abertura"]
    pavio_sup = (df["maxima"] - df[["fechamento", "abertura"]].max(axis=1)).clip(lower=0)
    pavio_inf = (df[["fechamento", "abertura"]].min(axis=1) - df["minima"]).clip(lower=0)
    df["corpo"] = corpo
    df["pavio_superior"] = pavio_sup
    df["pavio_inferior"] = pavio_inf
    df["pressao_compradora"] = df["pavio_inferior"] + corpo.clip(lower=0)
    df["pressao_vendedora"] = df["pavio_superior"] + (-corpo).clip(lower=0)

    # Tendência e níveis
    df["EMA_7"] = df["fechamento"].ewm(span=7, adjust=False).mean()
    df["EMA_21"] = df["fechamento"].ewm(span=21, adjust=False).mean()
    df["resistencia"] = df["maxima"].rolling(window=janela_sr, min_periods=janela_sr).max()
    df["suporte"] = df["minima"].rolling(window=janela_sr, min_periods=janela_sr).min()
    df["dist_resistencia"] = (df["resistencia"] - df["fechamento"]).clip(lower=0)
    df["dist_suporte"] = (df["fechamento"] - df["suporte"]).clip(lower=0)

    # Momentum e volatilidade
    df["retorno"] = df["fechamento"].pct_change()
    df["volatilidade"] = _rolling_vol(df["retorno"], window=vol_window)
    df["RSI_14"] = _rsi_wilder(df["fechamento"], period=rsi_period)

    # Target binário
    df["fechamento_futuro"] = df["fechamento"].shift(-horizon)
    df["target_class"] = np.where(
        df["fechamento_futuro"] > df["fechamento"], 1.0,
        np.where(df["fechamento_futuro"] < df["fechamento"], 0.0, np.nan)
    )

    # Warmup e corte
    warmup = max(21, rsi_period, vol_window, janela_sr)
    df = df.iloc[warmup:].copy()
    if horizon > 0:
        df = df[:-horizon]
    df = df.dropna().reset_index(drop=True)

    # Saída
    dias_reais = int(df["timestamp"].dt.normalize().nunique())
    inicio = df["timestamp"].min().strftime("%Y%m%d")
    fim = df["timestamp"].max().strftime("%Y%m%d")
    ts_now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    tf_label = _tf_label(timeframe)
    out_name = f"{par}_{tf_label}_{dias_reais}d_{inicio}-{fim}_n{len(df)}_{ts_now}.csv"
    out_path = TRANS_DIR / out_name
    df.to_csv(out_path, index=False)

    print(f"✔ Transformação concluída: {out_path}")
    return {"path": str(out_path), "linhas": len(df), "dias_reais": dias_reais, "janela_sr": janela_sr}

if __name__ == "__main__":
    resultado = transformar_dados(
        raw_path=None,
        par=PAR_DEFAULT,
        timeframe=TIMEFRAME_DEFAULT,
        dias=DIAS_DEFAULT,
        horizon=HORIZON_DEFAULT,
        janela_sr=JANELA_SR_DEFAULT,
    )
    print(resultado)
