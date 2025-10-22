# @title Script de Extração de dados IqOption✅

from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

import time
import pandas as pd
from datetime import datetime, timezone
import sys

"""
Script: extrair_dados.py

Descrição:
-----------
Conecta-se à API da IQ Option e extrai candles históricos do par configurado,
sempre até o último candle fechado (sem puxar dados futuros).

Repetição automática em chamadas vazias (até 3 tentativas).
Log informativo mostrando progresso durante coleta.
Mensagem clara quando histórico realmente termina.
Impressão do total de dias e candles coletados.

"""

# -------------------- Configurações -------------------- #

PAR = "EURUSD"             # Ativo
TIMEFRAME = 300            # 5 minutos
DIAS = 360                 # Quantos dias de histórico (máximo desejado)
ROOT = "/content/drive/MyDrive/Projetos/extrair-transformar-dados"

# Carrega credenciais do arquivo .env na pasta raiz do projeto
load_dotenv(os.path.join(ROOT, ".env"))
IQ_EMAIL = os.getenv("IQ_EMAIL")
IQ_PASSWORD = os.getenv("IQ_PASSWORD")

# Import robusto da API (usando o diretório pai que contém 'iqoptionapi')
# Além disso, criamos um alias 'iqoptionaapi' -> 'iqoptionapi' para compatibilidade
local_pkg_root = ROOT
if os.path.isdir(os.path.join(local_pkg_root, "iqoptionapi")) and local_pkg_root not in sys.path:
    sys.path.insert(0, local_pkg_root)

try:
    import importlib
    try:
        import iqoptionapi as _iqapi_local
        sys.modules.setdefault("iqoptionaapi", _iqapi_local)
    except Exception:
        pass

    from iqoptionapi.stable_api import IQ_Option
    import iqoptionapi.stable_api as _iqmod
    print(f"[INFO] IQ Option API carregada de: {_iqmod.__file__}")
except Exception as e_local:
    try:
        import iqoptionapi as _iqapi_pip
        sys.modules.setdefault("iqoptionaapi", _iqapi_pip)

        from iqoptionapi.stable_api import IQ_Option
        import iqoptionapi.stable_api as _iqmod
        print(f"[INFO] IQ Option API (pip) carregada de: {_iqmod.__file__}")
    except Exception as e_pip:
        raise ImportError(
            "Não foi possível importar 'IQ_Option'. "
            f"Verifique o diretório local '{os.path.join(local_pkg_root, 'iqoptionapi')}' "
            "ou instale via pip: pip install iqoptionapi. "
            f"Erros: local={e_local} | pip={e_pip}"
        )

# -------------------- Funções -------------------- #

# Conecta à API da IQ Option usando as credenciais fornecidas
def conectar_api():
    api = IQ_Option(IQ_EMAIL, IQ_PASSWORD)
    conectado, _ = api.connect()
    if not conectado:
        raise SystemExit("Erro: não foi possível conectar à IQ Option.")
    print("Conectado com sucesso.")
    return api


# Busca candles em blocos de até 1000, alinhados ao último candle fechado
# Retorna DataFrame com colunas padronizadas em ordem cronológica
def buscar_candles(api, par, timeframe, total_candles):
    max_por_chamada = 1000
    todos_candles = []

    agora = int(time.time())
    agora -= agora % timeframe

    restante = int(total_candles)
    while restante > 0:
        qtd = min(max_por_chamada, restante)
        tentativas = 3
        candles = None

        while tentativas > 0:
            candles = api.get_candles(par, timeframe, qtd, agora)
            if candles:
                break
            tentativas -= 1
            print(f"[WARN] Chamada vazia, tentando novamente... ({3 - tentativas}/3)")
            time.sleep(1)

        if not candles:
            print("[INFO] Histórico terminou. Nenhum candle adicional disponível.")
            break

        todos_candles.extend(candles)
        agora = candles[0]["from"] - 1
        restante -= qtd
        print(f"[INFO] Coletados {len(todos_candles)} candles até agora...")

    df = pd.DataFrame(todos_candles)
    if df.empty:
        return df

    df["from"] = pd.to_datetime(df["from"], unit="s", utc=True)

    df = df.rename(columns={
        "open": "abertura",
        "max": "maxima",
        "min": "minima",
        "close": "fechamento"
    })
    df = df[["from", "abertura", "maxima", "minima", "fechamento", "volume"]]

    df = df.drop_duplicates(subset=["from"]).sort_values("from").reset_index(drop=True)

    # Descarta candles futuros (garante que o último esteja fechado)
    agora_ts = pd.Timestamp.now(tz="UTC")
    antes = len(df)
    df = df[df["from"] + pd.to_timedelta(timeframe, unit="s") <= agora_ts]
    descartados = antes - len(df)
    if descartados > 0:
        print(f"[INFO] {descartados} candles futuros descartados.")

    return df


# Filtra o período líquido 07h–21h UTC (independente do timeframe)
def filtrar_periodo_liquido(df):
    df = df.set_index("from")
    df = df.between_time("07:00", "21:00")
    return df.reset_index()


# Extrai candles e salva/mescla em CSV dentro de {root}/data/raw
# Não usa valores padrão: exige par, timeframe, dias e root explicitamente
def extrair_dados(par, timeframe, dias, root):
    if par is None or timeframe is None or dias is None or root is None:
        print("(PARAMETROS NAO FORNECIDOS, INCLUA O TIMEFRAME , DIAS , E PATH RAIZ DO PROJETO)")
        return pd.DataFrame(), None

    raw_dir = os.path.join(root, "data", "raw")
    os.makedirs(raw_dir, exist_ok=True)

    candles_por_dia = int((24 * 60) / (timeframe / 60))
    total_candles = dias * candles_por_dia
    print(f"[INFO] Baixando {dias} dias solicitados (~{total_candles} candles em M{timeframe//60})...")

    api = conectar_api()
    df = buscar_candles(api, par, timeframe, total_candles)

    if df.empty:
        print("[AVISO] Nenhum candle retornado.")
        return df, None

    # Filtro período líquido 07h–21h UTC
    df = filtrar_periodo_liquido(df)

    # Calcula a quantidade REAL de dias coletados
    dias_coletados = (df["from"].max() - df["from"].min()).days

    # Agora sim define o caminho de saída usando os dias REAIS
    caminho_csv = os.path.join(raw_dir, f"{par}_M{timeframe//60}_{dias_coletados}d.csv")

    # Mescla incremental se já existir arquivo com o mesmo nome (mesma faixa efetiva)
    if os.path.exists(caminho_csv):
        antigo = pd.read_csv(caminho_csv, parse_dates=["from"])
        df = pd.concat([antigo, df], ignore_index=True)
        df = df.drop_duplicates(subset=["from"]).sort_values("from").reset_index(drop=True)

    df.to_csv(caminho_csv, index=False)
    print(f"[OK] Dados salvos em {caminho_csv}")
    print(f"[INFO] Dias solicitados: {dias} | Dias efetivos: {dias_coletados} | Candles: {len(df)}.")

    return df, caminho_csv


# Execução direta: parâmetros configuráveis passados explicitamente
if __name__ == "__main__":
    PAR = "EURGBP"            # Ativo
    TIMEFRAME = 300           # 5 minutos
    DIAS = 360                # Histórico solicitado em dias
    ROOT = "/content/drive/MyDrive/Projetos/extrair-transformar-dados"

    dados, path = extrair_dados(PAR, TIMEFRAME, DIAS, ROOT)
    if isinstance(dados, pd.DataFrame) and not dados.empty:
        print(dados.tail())
