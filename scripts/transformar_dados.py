# -*- coding: utf-8 -*-
"""
Script: scripts/transformar_dados.py

Pipeline:
1) Saneamento de timestamps e OHLCV (duplicatas, ordem, volume ≥ 0)
2) Features de candle (corpo, pavios, pressões)
3) EMAs (7, 21); Suporte/Resistência (janela_sr) e distâncias
4) RSI(14) (Wilder), retorno e volatilidade (janela fixa)
5) Warmup automático (máx: 21, rsi_period, vol_window, janela_sr) + corte por horizon
6) target_class binário (empate = NaN → removido)
7) Salva em data/transformed:
   {PAR}_{TF}_{diasReais}d_{AAAAMMDD-AAAAMMDD}_n{linhas}_{timestamp}.csv
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timezone

# --------------------------------------------------------------------------------
# Caminhos do projeto (portátil)
# --------------------------------------------------------------------------------
ROOT: Path = Path(__file__).resolve().parents[1]
DATA_DIR: Path = ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"
TRANS_DIR: Path = DATA_DIR / "transformed"
TRANS_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------------
# .env e parâmetros padrão
# --------------------------------------------------------------------------------
load_dotenv(dotenv_path=ROOT / ".env", override=True)

PAR_DEFAULT: str = os.getenv("PAR", "EURUSD")
TIMEFRAME_DEFAULT: int = int(os.getenv("TIMEFRAME", "300"))  # em segundos
DIAS_DEFAULT: int = int(os.getenv("DIAS", "360"))
HORIZON_DEFAULT: int = int(os.getenv("HORIZON", "1"))
JANELA_SR_DEFAULT: int = int(os.getenv("JANELA_SR", "48"))

RSI_PERIOD_DEFAULT: int = 14
VOL_WINDOW_DEFAULT: int = 10


# --------------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------------
def _tf_label(timeframe: int) -> str:
    return f"M{int(timeframe)//60}" if timeframe % 60 == 0 else f"S{int(timeframe)}"


def _latest_raw_path(par: str, timeframe: int) -> Path:
    """Localiza o CSV bruto mais recente em data/raw/ para {par,timeframe}."""
    tf = _tf_label(timeframe)
    prefix = f"{par}_{tf}_"
    candidates: List[Path] = [p for p in RAW_DIR.glob(f"{prefix}*.csv")]
    if not candidates:
        raise FileNotFoundError(f"Nenhum RAW encontrado com padrão {prefix}*.csv em {RAW_DIR}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _ensure_columns(df: pd.DataFrame, cols: List[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes no CSV: {missing}")


def _sanitize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Regras básicas de coerência para OHLCV."""
    ohlc = ["abertura", "maxima", "minima", "fechamento", "volume"]
    df = df.dropna(subset=ohlc)

    ok_max = df["maxima"] >= df[["abertura", "fechamento"]].max(axis=1)
    ok_min = df["minima"] <= df[["abertura", "fechamento"]].min(axis=1)
    df = df[ok_max & ok_min]
    df = df[df["volume"] >= 0]
    return df.sort_values("timestamp").reset_index(drop=True)


def _rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace({0: np.nan})
    rsi = 100 - (100 / (1 + rs))
    rsi[: period - 1] = np.nan
    return rsi


def _rolling_vol(ret: pd.Series, window: int = 10) -> pd.Series:
    return ret.rolling(window=window, min_periods=window).std()


# --------------------------------------------------------------------------------
# Função principal
# --------------------------------------------------------------------------------
def transformar_dados(
    raw_path: Optional[Path],
    par: str,
    timeframe: int,
    dias: int,
    horizon: int,
    janela_sr: int,
    rsi_period: int = RSI_PERIOD_DEFAULT,
    vol_window: int = VOL_WINDOW_DEFAULT,
    drop_duplicates: bool = True,
) -> dict:
    """
    Transforma CSV bruto OHLCV em dataset técnico pronto para treino.

    Se `raw_path` for None / "" / "auto", busca automaticamente o arquivo mais
    recente em data/raw/ para o par/timeframe informados.
    """
    # RAW automático
    if not raw_path or str(raw_path).strip().lower() in ("", "auto"):
        raw_path = _latest_raw_path(par, timeframe)

    raw_path = Path(raw_path)
    if not raw_path.exists():
        raise FileNotFoundError(f"Arquivo bruto não encontrado: {raw_path}")

    # Leitura
    df = pd.read_csv(raw_path)

    # Detectar coluna temporal
    time_col = None
    for c in ("from", "datetime", "timestamp", "time"):
        if c in df.columns:
            time_col = c
            break
    if time_col is None:
        raise RuntimeError("Nenhuma coluna temporal encontrada no CSV (ex.: 'from').")

    # Normalizar timestamp (UTC)
    ts = pd.to_datetime(df[time_col], utc=True, errors="coerce")
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize("UTC")
    else:
        ts = ts.dt.tz_convert("UTC")

    df = (
        df.assign(timestamp=ts)
          .dropna(subset=["timestamp"])
          .drop(columns=[c for c in (time_col,) if c != "timestamp"])
          .sort_values("timestamp")
          .reset_index(drop=True)
    )
    if drop_duplicates:
        df = df.drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    # Validar OHLCV esperadas
    _ensure_columns(df, ["abertura", "maxima", "minima", "fechamento", "volume"])
    df = _sanitize_ohlc(df)

    # ---------------- Features de candle ----------------
    corpo = df["fechamento"] - df["abertura"]
    pavio_sup = (df["maxima"] - df[["fechamento", "abertura"]].max(axis=1)).clip(lower=0)
    pavio_inf = (df[["fechamento", "abertura"]].min(axis=1) - df["minima"]).clip(lower=0)

    df["corpo"] = corpo
    df["pavio_superior"] = pavio_sup
    df["pavio_inferior"] = pavio_inf
    df["pressao_compradora"] = df["pavio_inferior"] + corpo.clip(lower=0)
    df["pressao_vendedora"] = df["pavio_superior"] + (-corpo).clip(lower=0)

    # ---------------- Tendência / Níveis ----------------
    df["EMA_7"] = df["fechamento"].ewm(span=7, adjust=False).mean()
    df["EMA_21"] = df["fechamento"].ewm(span=21, adjust=False).mean()

    df["resistencia"] = df["maxima"].rolling(window=janela_sr, min_periods=janela_sr).max()
    df["suporte"] = df["minima"].rolling(window=janela_sr, min_periods=janela_sr).min()
    df["dist_resistencia"] = (df["resistencia"] - df["fechamento"]).clip(lower=0)
    df["dist_suporte"] = (df["fechamento"] - df["suporte"]).clip(lower=0)

    # ---------------- Momentum / Vol ----------------
    df["retorno"] = df["fechamento"].pct_change()
    df["volatilidade"] = _rolling_vol(df["retorno"], window=vol_window)
    df["RSI_14"] = _rsi_wilder(df["fechamento"], period=rsi_period)

    # ---------------- Time features ----------------
    df["hora_num"] = df["timestamp"].dt.hour
    df["minuto"] = df["timestamp"].dt.minute
    df["dia_semana"] = df["timestamp"].dt.dayofweek

    # ---------------- Target ----------------
    df["fechamento_futuro"] = df["fechamento"].shift(-horizon)
    df["target_class"] = np.where(
        df["fechamento_futuro"] > df["fechamento"], 1.0,
        np.where(df["fechamento_futuro"] < df["fechamento"], 0.0, np.nan)
    )

    # Warmup e corte por horizonte
    warmup = max(21, rsi_period, vol_window, janela_sr)
    df = df.iloc[warmup:].copy()
    if horizon > 0:
        df = df[:-horizon]
    crit = [
        "corpo", "pavio_superior", "pavio_inferior",
        "pressao_compradora", "pressao_vendedora",
        "EMA_7", "EMA_21", "resistencia", "suporte",
        "dist_resistencia", "dist_suporte",
        "retorno", "volatilidade", "RSI_14",
        "hora_num", "minuto", "dia_semana",
        "fechamento_futuro", "target_class"
    ]
    df = df.dropna(subset=crit).reset_index(drop=True)

    # ---------------- Saída ----------------
    n_linhas = int(len(df))
    dias_reais = int(df["timestamp"].dt.normalize().nunique())
    inicio = df["timestamp"].min().strftime("%Y%m%d")
    fim = df["timestamp"].max().strftime("%Y%m%d")
    ts_now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    tf_label = _tf_label(timeframe)

    # Remove antigos com o mesmo prefixo (opcional, mantemos 1 arquivo “atual”)
    base_prefix = f"{par}_{tf_label}_"
    for f in TRANS_DIR.glob(f"{base_prefix}*.csv"):
        try:
            f.unlink()
        except Exception as e:
            print(f"[WARN] não consegui remover {f.name}: {e}")

    out_name = f"{par}_{tf_label}_{dias_reais}d_{inicio}-{fim}_n{n_linhas}_{ts_now}.csv"
    out_path = TRANS_DIR / out_name
    df.to_csv(out_path, index=False)

    resumo = {
        "arquivo": out_name,
        "path": str(out_path),
        "linhas": n_linhas,
        "colunas": df.shape[1],
        "dias_reais": dias_reais,
        "periodo": (str(df["timestamp"].min()), str(df["timestamp"].max())),
        "features": list(df.columns),
        "warmup_removido": warmup,
        "horizon": horizon,
        "janela_sr": janela_sr,
        "rsi_period": rsi_period,
        "vol_window": vol_window,
    }

    print(f"✔ Transformação concluída: {out_path}")
    print("Resumo:", resumo)
    return {"path": str(out_path), "resumo": resumo}


# --------------------------------------------------------------------------------
# Execução direta (usa .env por padrão)
# --------------------------------------------------------------------------------
if __name__ == "__main__":
    resultado = transformar_dados(
        raw_path=None,                       # None → busca automático em data/raw
        par=PAR_DEFAULT,
        timeframe=TIMEFRAME_DEFAULT,
        dias=DIAS_DEFAULT,
        horizon=HORIZON_DEFAULT,
        janela_sr=JANELA_SR_DEFAULT,
        rsi_period=RSI_PERIOD_DEFAULT,
        vol_window=VOL_WINDOW_DEFAULT,
    )
    print(resultado)
