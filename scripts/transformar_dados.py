# transformar_dados.py

"""
Pipeline:
1) Saneamento de timestamps e OHLCV (duplicatas, ordem lógica, volume ≥ 0)
2) Features de candle (pavios ≥ 0, pressões coerentes)
3) EMAs (7, 21), S/R com janela_sr, distâncias ≥ 0
4) RSI(14) (Wilder), retorno e volatilidade (janela fixa, min_periods completos)
5) Warmup automático (max de janelas e janela_sr) + corte final por horizon
6) target_class binário (empate = NaN removido)
7) Salva em /data/transformed: {PAR}_{TF}_{diasReais}d_{AAAAMMDD-AAAAMMDD}_n{linhas}_{timestamp}.csv
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import List

# -----------------------------
# Utilidades
# -----------------------------

def _tf_label(timeframe: int) -> str:
    return f"M{int(timeframe)//60}" if timeframe % 60 == 0 else f"S{int(timeframe)}"


def _latest_raw_path(par: str, timeframe: int, root: str) -> str:
    """Localiza o CSV bruto mais recente para {par,timeframe} em ROOT/data/raw.
    Critério: começa com "{PAR}_{TF}_" e termina com ".csv"; desempate por mtime.
    """
    raw_dir = os.path.join(root, "data", "raw")
    if not os.path.isdir(raw_dir):
        raise FileNotFoundError(f"Pasta de RAW não encontrada: {raw_dir}")

    tf = _tf_label(timeframe)
    prefix = f"{par}_{tf}_"
    candidates: List[str] = [
        os.path.join(raw_dir, f) for f in os.listdir(raw_dir)
        if f.startswith(prefix) and f.endswith(".csv")
    ]
    if not candidates:
        raise FileNotFoundError(f"Nenhum RAW encontrado com padrão {prefix}*.csv em {raw_dir}")

    latest = max(candidates, key=lambda p: os.path.getmtime(p))
    return latest


def _ensure_columns(df: pd.DataFrame, cols):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes no CSV: {missing}")


def _sanitize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    ohlc_cols = ["abertura", "maxima", "minima", "fechamento", "volume"]
    df = df.dropna(subset=ohlc_cols)

    ok_max = df["maxima"] >= df[["abertura", "fechamento"]].max(axis=1)
    ok_min = df["minima"] <= df[["abertura", "fechamento"]].min(axis=1)
    df = df[ok_max & ok_min]

    df = df[df["volume"] >= 0]
    return df.reset_index(drop=True)


def _rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace({0: np.nan})
    rsi = 100 - (100 / (1 + rs))
    rsi[:period-1] = np.nan
    return rsi


def _rolling_vol(ret: pd.Series, window: int = 10) -> pd.Series:
    return ret.rolling(window=window, min_periods=window).std()


# -----------------------------
# Função principal (assinatura compatível com a chamada existente)
# -----------------------------

def transformar_dados(
    raw_path: str,
    par: str,
    timeframe: int,
    dias: int,
    horizon: int,          # <- obrigatório
    janela_sr: int,        # <- obrigatório
    root: str,             # <- obrigatório
    rsi_period: int = 14,
    vol_window: int = 10,
    drop_duplicates: bool = True,
):
    """Transforma CSV bruto OHLCV em dataset pronto para treino.

    Observação: se `raw_path` for None, "" (vazio) ou "auto", será feita uma busca
    automática no diretório ROOT/data/raw para o arquivo mais recente do par/timeframe.
    """

    transformed_dir = os.path.join(root, "data", "transformed")
    os.makedirs(transformed_dir, exist_ok=True)

    # RAW automático
    if raw_path in (None, "", "auto"):
        raw_path = _latest_raw_path(par, timeframe, root)

    if not os.path.exists(raw_path):
        raise FileNotFoundError(f"Arquivo bruto não encontrado em {raw_path}")

    df = pd.read_csv(raw_path)

    # Detectar coluna de tempo
    time_col = None
    for candidate in ["from", "datetime", "timestamp", "time"]:
        if candidate in df.columns:
            time_col = candidate
            break
    if time_col is None:
        raise RuntimeError("Nenhuma coluna de tempo encontrada no CSV.")

    df[time_col] = pd.to_datetime(df[time_col], utc=True, errors="coerce")
    df = (
        df.rename(columns={time_col: "timestamp"})
          .dropna(subset=["timestamp"])
          .sort_values("timestamp")
          .reset_index(drop=True)
    )

    if drop_duplicates:
        df = df.drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    # Validar colunas OHLCV esperadas
    _ensure_columns(df, ["abertura", "maxima", "minima", "fechamento", "volume"]) 
    df = _sanitize_ohlc(df)

    # Features de candle
    corpo = df["fechamento"] - df["abertura"]
    pavio_sup_raw = df["maxima"] - df[["fechamento", "abertura"]].max(axis=1)
    pavio_inf_raw = df[["fechamento", "abertura"]].min(axis=1) - df["minima"]

    df["corpo"] = corpo
    df["pavio_superior"] = np.clip(pavio_sup_raw, 0, None)
    df["pavio_inferior"] = np.clip(pavio_inf_raw, 0, None)

    # Pressões coerentes
    df["pressao_compradora"] = df["pavio_inferior"] + np.clip(df["corpo"], 0, None)
    df["pressao_vendedora"] = df["pavio_superior"] + np.clip(-df["corpo"], 0, None)

    # EMAs
    df["EMA_7"] = df["fechamento"].ewm(span=7, adjust=False).mean()
    df["EMA_21"] = df["fechamento"].ewm(span=21, adjust=False).mean()

    # Suporte/Resistência (rolling completo)
    df["resistencia"] = df["maxima"].rolling(window=janela_sr, min_periods=janela_sr).max()
    df["suporte"] = df["minima"].rolling(window=janela_sr, min_periods=janela_sr).min()
    df["dist_resistencia"] = np.clip(df["resistencia"] - df["fechamento"], 0, None)
    df["dist_suporte"] = np.clip(df["fechamento"] - df["suporte"], 0, None)

    # Retorno e volatilidade
    df["retorno"] = df["fechamento"].pct_change()
    df["volatilidade"] = _rolling_vol(df["retorno"], window=vol_window)

    # RSI (Wilder)
    df["RSI_14"] = _rsi_wilder(df["fechamento"], period=rsi_period)

    # Variáveis temporais (UTC)
    ts = (
        df["timestamp"].dt.tz_convert("UTC")
        if df["timestamp"].dt.tz is not None
        else df["timestamp"].dt.tz_localize("UTC")
    )
    df["hora_num"] = ts.dt.hour
    df["minuto"] = ts.dt.minute
    df["dia_semana"] = ts.dt.dayofweek

    # Alvo com horizonte
    df["fechamento_futuro"] = df["fechamento"].shift(-horizon)
    df["target_class"] = np.where(
        df["fechamento_futuro"] > df["fechamento"], 1.0,
        np.where(df["fechamento_futuro"] < df["fechamento"], 0.0, np.nan)
    )

    # Warmup: remover início sem janelas completas e fim sem rótulo
    warmup = max(21, rsi_period, vol_window, janela_sr)
    df = df.iloc[warmup:].copy()
    if horizon > 0:
        df = df[:-horizon]

    # Drop de NaN remanescentes em features críticas
    crit_cols = [
        "corpo", "pavio_superior", "pavio_inferior",
        "pressao_compradora", "pressao_vendedora",
        "EMA_7", "EMA_21", "resistencia", "suporte",
        "dist_resistencia", "dist_suporte",
        "retorno", "volatilidade", "RSI_14",
        "hora_num", "minuto", "dia_semana",
        "fechamento_futuro", "target_class"
    ]
    df = df.dropna(subset=crit_cols).reset_index(drop=True)

    # Medidas reais
    n_linhas = int(len(df))
    dias_reais = int(df["timestamp"].dt.normalize().nunique())
    inicio = df["timestamp"].min().strftime("%Y%m%d")
    fim = df["timestamp"].max().strftime("%Y%m%d")
    ts_now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Rótulo de timeframe
    tf_label = _tf_label(timeframe)

    # Nome final e substituição de antigos
    base_prefix = f"{par}_{tf_label}_"
    for antigo in [f for f in os.listdir(transformed_dir) if f.startswith(base_prefix)]:
        try:
            os.remove(os.path.join(transformed_dir, antigo))
        except Exception as e:
            print(f"Aviso: não consegui remover {antigo}: {e}")

    transformed_fname = f"{par}_{tf_label}_{dias_reais}d_{inicio}-{fim}_n{n_linhas}_{ts_now}.csv"
    transformed_path = os.path.join(transformed_dir, transformed_fname)
    df.to_csv(transformed_path, index=False)

    resumo = {
        "arquivo": transformed_fname,
        "path": transformed_path,
        "linhas": n_linhas,
        "colunas": df.shape[1],
        "dias_reais": dias_reais,
        "periodo": (str(df['timestamp'].min()), str(df['timestamp'].max())),
        "features": list(df.columns),
        "warmup_removido": warmup,
        "horizon": horizon,
        "janela_sr": janela_sr,
        "rsi_period": rsi_period,
        "vol_window": vol_window,
    }

    print(f"✔ Dados transformados salvos em {transformed_path}")
    print("Resumo:", resumo)
    return {"path": transformed_path, "resumo": resumo}
