# -*- coding: utf-8 -*-
"""
extrair_dados.py — Extrai candles da IQ Option e salva em data/raw.
- Filtra 07h–21h UTC.
- Descarta candles ainda em formação.
- Usa credenciais do .env ou passadas pela GUI.
"""

import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple
import pandas as pd
from dotenv import load_dotenv

# --- log em tempo real no terminal/GUI ---
import sys, os
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    os.environ["PYTHONUNBUFFERED"] = "1"
except Exception:
    pass


# Caminhos
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# .env e defaults
load_dotenv(dotenv_path=ROOT / ".env", override=True)
IQ_EMAIL_ENV = os.getenv("IQ_EMAIL")
IQ_PASSWORD_ENV = os.getenv("IQ_PASSWORD")
PAR_DEFAULT = os.getenv("PAR", "EURUSD")
TIMEFRAME_DEFAULT = int(os.getenv("TIMEFRAME", "300"))  # 300 = M5
DIAS_DEFAULT = int(os.getenv("DIAS", "360"))

# API IQ Option
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg_name = "iqoptionaapi" if (ROOT / "iqoptionaapi").is_dir() else "iqoptionapi"
try:
    if pkg_name == "iqoptionaapi":
        from iqoptionaapi.stable_api import IQ_Option
        import iqoptionaapi.stable_api as _iqmod
    else:
        from iqoptionapi.stable_api import IQ_Option
        import iqoptionapi.stable_api as _iqmod
    print(f"[INFO] IQ Option API carregada de: {_iqmod.__file__}", flush=True)
except Exception as e:
    raise ImportError(f"Falha ao importar IQ_Option. Detalhe: {e}")

# ------------------------------------------------------------
# Funções auxiliares
# ------------------------------------------------------------
def _agora_alinhado(timeframe: int) -> int:
    """Epoch do último candle fechado."""
    agora = int(time.time())
    return agora - (agora % timeframe)

def _descarta_futuros(df: pd.DataFrame, timeframe: int) -> pd.DataFrame:
    """Remove candles cujo fechamento ainda não ocorreu."""
    if df.empty:
        return df
    limite = pd.Timestamp.now(tz="UTC")
    df = df[df["from"] + pd.to_timedelta(timeframe, unit="s") <= limite]
    return df

def conectar_api(email: Optional[str], senha: Optional[str]) -> "IQ_Option":
    """Conecta à IQ Option usando e-mail/senha (GUI ou .env)."""
    email = email or IQ_EMAIL_ENV
    senha = senha or IQ_PASSWORD_ENV
    if not email or not senha:
        raise RuntimeError("Credenciais ausentes.")
    api = IQ_Option(email, senha)
    ok, _ = api.connect()
    if not ok:
        raise RuntimeError("Falha na conexão com a IQ Option.")
    print("[INFO] Conectado com sucesso.", flush=True)
    return api

def buscar_candles(api: "IQ_Option", par: str, timeframe: int, total: int) -> pd.DataFrame:
    """Baixa candles em blocos de até 1000."""
    max_por_chamada = 1000
    todos = []
    cursor = _agora_alinhado(timeframe)

    while total > 0:
        qtd = min(max_por_chamada, total)
        candles = None
        for _ in range(3):
            candles = api.get_candles(par, timeframe, qtd, cursor)
            if candles:
                break
            time.sleep(1.0)
        if not candles:
            break
        todos.extend(candles)
        cursor = candles[0]["from"] - 1
        total -= qtd
        print(f"[INFO] {len(todos)} candles acumulados...", flush=True)

    if not todos:
        return pd.DataFrame()

    df = pd.DataFrame(todos)
    df["from"] = pd.to_datetime(df["from"], unit="s", utc=True)
    df = df.rename(columns={"open": "abertura", "max": "maxima", "min": "minima", "close": "fechamento"})
    df = df[["from", "abertura", "maxima", "minima", "fechamento", "volume"]]
    df = df.drop_duplicates(subset=["from"]).sort_values("from").reset_index(drop=True)
    return _descarta_futuros(df, timeframe)

def filtrar_periodo_liquido(df: pd.DataFrame) -> pd.DataFrame:
    """Mantém 07:00–21:00 UTC."""
    if df.empty:
        return df
    return df.set_index("from").between_time("07:00", "21:00").reset_index()

def extrair_dados(par: str, timeframe: int, dias: int,
                  email: Optional[str] = None, senha: Optional[str] = None) -> Tuple[pd.DataFrame, Optional[Path]]:
    """Extrai candles e salva CSV em data/raw."""
    if not par or not timeframe or not dias:
        print("[ERRO] Parâmetros inválidos.", flush=True)
        return pd.DataFrame(), None

    candles_dia = int((24 * 60) / (timeframe / 60))
    total = dias * candles_dia
    print(f"[INFO] {dias} dias (~{total} candles) em M{timeframe // 60} de {par}", flush=True)

    api = conectar_api(email, senha)
    df = buscar_candles(api, par, timeframe, total)
    if df.empty:
        print("[AVISO] Nenhum candle retornado.", flush=True)
        return df, None

    df = filtrar_periodo_liquido(df)
    dias_efetivos = (df["from"].max() - df["from"].min()).days
    saida = RAW_DIR / f"{par}_M{timeframe // 60}_{dias_efetivos}d.csv"

    if saida.exists():
        antigo = pd.read_csv(saida, parse_dates=["from"])
        df = pd.concat([antigo, df], ignore_index=True)
        df = df.drop_duplicates(subset=["from"]).sort_values("from").reset_index(drop=True)

    df.to_csv(saida, index=False)
    print(f"[OK] salvo: {saida}", flush=True)
    return df, saida

if __name__ == "__main__":
    dados, caminho = extrair_dados(PAR_DEFAULT, TIMEFRAME_DEFAULT, DIAS_DEFAULT, IQ_EMAIL_ENV, IQ_PASSWORD_ENV)
    if not dados.empty:
        print(dados.tail(), flush=True)
