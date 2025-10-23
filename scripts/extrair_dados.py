# -*- coding: utf-8 -*-
"""
Script: scripts/extrair_dados.py
Extrai candles da IQ Option de forma portátil (sem /content) e salva em data/raw/.
Filtra 07h–21h UTC e descarta candles “futuros” (candle ainda em formação).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
from dotenv import load_dotenv

# ------------------------------------------------------------
# Caminhos do projeto (portátil)
# ------------------------------------------------------------
ROOT: Path = Path(__file__).resolve().parents[1]
DATA_DIR: Path = ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"
TRANS_DIR: Path = DATA_DIR / "transformed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
TRANS_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# .env e parâmetros
# ------------------------------------------------------------
load_dotenv(dotenv_path=ROOT / ".env", override=True)

IQ_EMAIL: Optional[str] = os.getenv("IQ_EMAIL")
IQ_PASSWORD: Optional[str] = os.getenv("IQ_PASSWORD")
PAR_DEFAULT: str = os.getenv("PAR", "EURUSD")
TIMEFRAME_DEFAULT: int = int(os.getenv("TIMEFRAME", "300"))  # seg (300 = M5)
DIAS_DEFAULT: int = int(os.getenv("DIAS", "360"))

# ------------------------------------------------------------
# Import da API: aceita 'iqoptionaapi' OU 'iqoptionapi'
# Preferência: pacote local no repositório; senão, o que estiver instalado.
# ------------------------------------------------------------
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg_name = None
if (ROOT / "iqoptionaapi").is_dir():
    pkg_name = "iqoptionaapi"
elif (ROOT / "iqoptionapi").is_dir():
    pkg_name = "iqoptionapi"
else:
    # tenta qualquer um instalado via pip
    try:
        import iqoptionaapi  # type: ignore
        pkg_name = "iqoptionaapi"
    except Exception:
        pkg_name = "iqoptionapi"

try:
    if pkg_name == "iqoptionaapi":
        from iqoptionaapi.stable_api import IQ_Option  # type: ignore
        import iqoptionaapi.stable_api as _iqmod      # type: ignore
    else:
        from iqoptionapi.stable_api import IQ_Option  # type: ignore
        import iqoptionapi.stable_api as _iqmod       # type: ignore
    print(f"[INFO] IQ Option API carregada de: {_iqmod.__file__}")
except Exception as e:
    raise ImportError(
        "Não foi possível importar 'IQ_Option' de iqoptionaapi/iqoptionapi. "
        "Confirme a pasta no projeto ou instale via pip. "
        f"Detalhe: {e}"
    )

# ------------------------------------------------------------
# Utilitários
# ------------------------------------------------------------
def _agora_alinhado(timeframe: int) -> int:
    """Epoch (segundos) do último candle fechado, alinhado ao timeframe."""
    agora = int(time.time())
    return agora - (agora % timeframe)

def _descarta_futuros(df: pd.DataFrame, timeframe: int) -> pd.DataFrame:
    """
    Garante que o último candle esteja fechado (sem dados futuros).
    Remove candles cujo fechamento ainda não ocorreu (ex.: candle em formação).
    """
    if df.empty:
        return df
    limite = pd.Timestamp.now(tz="UTC")  # timezone-aware em UTC
    df_filtrado = df[df["from"] + pd.to_timedelta(timeframe, unit="s") <= limite]
    removidos = len(df) - len(df_filtrado)
    if removidos > 0:
        print(f"[INFO] {removidos} candles futuros descartados.")
    return df_filtrado

def conectar_api(email: str, senha: str) -> "IQ_Option":
    if not email or not senha:
        raise RuntimeError("Faltam IQ_EMAIL e/ou IQ_PASSWORD no .env.")
    api = IQ_Option(email, senha)
    ok, _ = api.connect()
    if not ok:
        raise RuntimeError("Falha na conexão com a IQ Option.")
    print("[INFO] Conectado com sucesso.")
    return api

def buscar_candles(api: "IQ_Option", par: str, timeframe: int, total_candles: int) -> pd.DataFrame:
    """
    Busca candles em blocos (máx 1000 por chamada), retrocedendo a partir do último fechado.
    Faz até 3 tentativas quando a chamada vem vazia.
    """
    max_por_chamada = 1000
    todos = []
    cursor = _agora_alinhado(timeframe)
    restante = int(total_candles)

    while restante > 0:
        qtd = min(max_por_chamada, restante)

        tentativas = 3
        candles = None
        while tentativas > 0:
            candles = api.get_candles(par, timeframe, qtd, cursor)
            if candles:
                break
            tentativas -= 1
            print(f"[WARN] chamada vazia; nova tentativa ({3 - tentativas}/3)")
            time.sleep(1.0)

        if not candles:
            print("[INFO] Histórico terminou (sem novos candles).")
            break

        todos.extend(candles)
        cursor = candles[0]["from"] - 1
        restante -= qtd
        print(f"[INFO] acumulado: {len(todos)} candles...")

    if not todos:
        return pd.DataFrame()

    df = pd.DataFrame(todos)
    df["from"] = pd.to_datetime(df["from"], unit="s", utc=True)

    df = df.rename(
        columns={"open": "abertura", "max": "maxima", "min": "minima", "close": "fechamento"}
    )
    df = df[["from", "abertura", "maxima", "minima", "fechamento", "volume"]]
    df = df.drop_duplicates(subset=["from"]).sort_values("from").reset_index(drop=True)
    df = _descarta_futuros(df, timeframe)
    return df

def filtrar_periodo_liquido(df: pd.DataFrame) -> pd.DataFrame:
    """Mantém 07:00–21:00 UTC independente do timeframe."""
    if df.empty:
        return df
    return df.set_index("from").between_time("07:00", "21:00").reset_index()

def extrair_dados(par: str, timeframe: int, dias: int) -> Tuple[pd.DataFrame, Optional[Path]]:
    """
    Extrai candles, filtra 07–21 UTC e salva/mescla CSV em data/raw/.
    Retorna (DataFrame, caminho_csv|None).
    """
    if not par or not timeframe or not dias:
        print("[ERRO] Parâmetros inválidos. Informe par, timeframe e dias.")
        return pd.DataFrame(), None

    candles_por_dia = int((24 * 60) / (timeframe / 60))
    total = dias * candles_por_dia
    print(f"[INFO] alvo: {dias} dias (~{total} candles) em M{timeframe // 60} de {par}")

    api = conectar_api(IQ_EMAIL, IQ_PASSWORD)
    df = buscar_candles(api, par, timeframe, total)
    if df.empty:
        print("[AVISO] Nenhum candle retornado.")
        return df, None

    df = filtrar_periodo_liquido(df)

    dias_efetivos = (df["from"].max() - df["from"].min()).days
    saida = RAW_DIR / f"{par}_M{timeframe // 60}_{dias_efetivos}d.csv"

    # Mescla incremental caso já exista um arquivo com mesmo prefixo (mesma faixa efetiva)
    if saida.exists():
        antigo = pd.read_csv(saida, parse_dates=["from"])
        df = pd.concat([antigo, df], ignore_index=True)
        df = df.drop_duplicates(subset=["from"]).sort_values("from").reset_index(drop=True)

    df.to_csv(saida, index=False)
    print(f"[OK] salvo: {saida}")
    print(f"[INFO] dias_solicitados={dias} | dias_efetivos={dias_efetivos} | candles={len(df)}")
    return df, saida

# ------------------------------------------------------------
# Execução direta
# ------------------------------------------------------------
if __name__ == "__main__":
    par = PAR_DEFAULT
    timeframe = TIMEFRAME_DEFAULT
    dias = DIAS_DEFAULT

    dados, caminho = extrair_dados(par, timeframe, dias)
    if isinstance(dados, pd.DataFrame) and not dados.empty:
        print(dados.tail())
