#!/usr/bin/env python3
import argparse
import math, time
from pathlib import Path
import pandas as pd

from scripts import db_manager as dm
# OBS: enquanto não renomearmos os scripts, seguimos usando extrair_dados.
# Quando renomear para scripts/extracao.py, basta trocar o import abaixo.
from scripts import extracao as ext

def _now_aligned(tf:int) -> int:
    return int(time.time() // tf * tf)

def _pick(cols, *names):
    cl = {c.lower(): c for c in cols}
    for n in names:
        if n in cl: return cl[n]
    for c in cols:
        if c.lower() in names: return c
    raise KeyError(f"Esperava colunas {names}, mas achei {cols}")

def _to_epoch_seconds(series: pd.Series) -> pd.Series:
    """Converte uma série de timestamps (int/str/datetime) para epoch em segundos (int)."""
    s = series
    # datetime (com/sem tz)
    if pd.api.types.is_datetime64_any_dtype(s) or pd.api.types.is_datetime64tz_dtype(s):
        ts = pd.to_datetime(s, utc=True)
        return (ts.astype("int64") // 1_000_000_000).astype("int64")

    # numérico
    if pd.api.types.is_integer_dtype(s) or pd.api.types.is_float_dtype(s):
        s = pd.to_numeric(s, errors="coerce")
        vmax = float(pd.Series(s).dropna().max()) if len(pd.Series(s).dropna()) else 0.0
        if vmax >= 1e14:   # ns
            return (s / 1_000_000_000).round().astype("Int64").astype("int64")
        elif vmax >= 1e12: # ms
            return (s / 1_000).round().astype("Int64").astype("int64")
        else:              # s
            return s.round().astype("Int64").astype("int64")

    # string/obj
    ts = pd.to_datetime(s, utc=True, errors="coerce")
    return (ts.astype("int64") // 1_000_000_000).astype("Int64").astype("int64")

# === helper para decidir quantos dias extrair ===
def _resolve_dias(last_ts: int|None, tf: int, user_dias: int|None) -> int:
    # Regra:
    # - Primeira extração do par (last_ts is None):
    #       usa user_dias se informado, senão 360
    # - Demais extrações (incremental):
    #       se user_dias informado, respeita
    #       senão, calcula dias do last_ts até agora (mín. 1)
    if last_ts is None:
        return int(user_dias) if user_dias is not None else 360
    if user_dias is not None:
        return int(user_dias)
    nowa = _now_aligned(tf)
    delta_days = (nowa - int(last_ts)) // 86400
    return max(1, int(delta_days) or 1)

def _df_standardized(df: pd.DataFrame, pair: str, timeframe: int):
    """Retorna df com colunas padronizadas e coluna ts_epoch (int)."""
    if df.empty:
        return df.assign(ts_epoch=pd.Series(dtype="int64"))

    d = df.copy()
    d.columns = [c.lower() for c in d.columns]
    ts_col    = _pick(d.columns, "ts", "from", "timestamp")
    open_col  = _pick(d.columns, "open", "abertura")
    high_col  = _pick(d.columns, "high", "max", "maxima")
    low_col   = _pick(d.columns, "low", "min", "minima")
    close_col = _pick(d.columns, "close", "fechamento")
    vol_col   = _pick(d.columns, "volume",)

    d["ts_epoch"] = _to_epoch_seconds(d[ts_col])
    d = d.dropna(subset=["ts_epoch"]).copy()
    d["ts_epoch"] = d["ts_epoch"].astype("int64")

    # manter apenas candles fechados e alinhados
    d = d[(d["ts_epoch"] % timeframe) == 0].copy()
    d = d.rename(columns={
        ts_col: "ts_src",
        open_col: "abertura",
        high_col: "maxima",
        low_col: "minima",
        close_col: "fechamento",
        vol_col: "volume",
    })
    d = d[["ts_epoch", "abertura", "maxima", "minima", "fechamento", "volume"]].sort_values("ts_epoch")
    return d

def _df_to_rows(std_df: pd.DataFrame, pair: str, timeframe: int):
    if std_df.empty:
        return []
    return [
        (pair, timeframe, int(r.ts_epoch), float(r.abertura), float(r.maxima),
         float(r.minima), float(r.fechamento), float(r.volume), "iqoption")
        for r in std_df.itertuples(index=False)
    ]

def cmd_extrair(args: argparse.Namespace):
    pair = args.par.upper()
    tf   = args.timeframe
    last = dm.get_last_timestamp(pair, tf)
    dias = _resolve_dias(last, tf, args.dias)
    print(f"[INFO] extrair: {pair}/{tf}s | dias={dias}")

    df, csv_path = ext.extrair_dados(par=pair, timeframe=tf, dias=dias, email=args.email, senha=args.senha)
    print(f"[INFO] extraídos {len(df)} candles | csv={csv_path}")

    if args.to_db:
        std = _df_standardized(df, pair, tf)
        if last is not None:
            std = std[std["ts_epoch"] > int(last)]
        rows = _df_to_rows(std, pair, tf)
        if rows:
            inserted = dm.upsert_candles(rows)
            print(f"[INFO] upsert: {inserted} novas linhas.")
        else:
            print("[INFO] nada novo para inserir.")
        print(f"[INFO] MAX(ts) agora: {dm.get_last_timestamp(pair, tf)}")

def _try_transform(df_in: pd.DataFrame, csv_in: Path|None) -> pd.DataFrame:
    try:
        # Quando renomear para scripts/transformacao.py, trocar o import abaixo.
        from scripts import transformacao as tr
        if hasattr(tr, "transformar_dados"):
            try:
                return tr.transformar_dados(df_in)
            except TypeError:
                if csv_in is not None:
                    return tr.transformar_dados(str(csv_in))
        if hasattr(tr, "transform"):
            return tr.transform(df_in)
    except Exception as e:
        print(f"[WARN] transformação não aplicada: {e}")
    return df_in

def cmd_transformar(args: argparse.Namespace):
    src = Path(args.csv)
    if not src.exists():
        raise SystemExit(f"[ERRO] CSV não encontrado: {src}")
    df = pd.read_csv(src)
    out = _try_transform(df, src)
    print(f"[INFO] transformação: {len(out)} linhas resultantes")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(args.out, index=False)
        print(f"[INFO] salvo em {args.out}")

def cmd_carga(args: argparse.Namespace):
    src = Path(args.csv)
    if not src.exists():
        raise SystemExit(f"[ERRO] CSV não encontrado: {src}")
    df = pd.read_csv(src)
    pair = args.par.upper()
    tf   = args.timeframe
    std  = _df_standardized(df, pair, tf)
    rows = _df_to_rows(std, pair, tf)
    if not rows:
        print("[INFO] nenhum row para inserir.")
        return
    inserted = dm.upsert_candles(rows)
    print(f"[INFO] upsert: {inserted} novas linhas.")
    print(f"[INFO] MAX(ts) {pair}/{tf}s: {dm.get_last_timestamp(pair, tf)}")

def cmd_pipeline(args: argparse.Namespace):
    pair = args.par.upper()
    tf   = args.timeframe
    last = dm.get_last_timestamp(pair, tf)
    dias = _resolve_dias(last, tf, args.dias)
    print(f"[INFO] pipeline: {pair}/{tf}s | dias={dias}")

    df, csv_path = ext.extrair_dados(par=pair, timeframe=tf, dias=dias, email=args.email, senha=args.senha)
    print(f"[INFO] extraídos {len(df)} candles | csv={csv_path}")

    if args.transformar:
        df = _try_transform(df, Path(csv_path) if csv_path else None)
        print(f"[INFO] pós-transformação: {len(df)} linhas")

    if args.to_db:
        std = _df_standardized(df, pair, tf)
        rows = _df_to_rows(std, pair, tf)
        if rows:
            inserted = dm.upsert_candles(rows)
            print(f"[INFO] upsert: {inserted} novas linhas.")
        else:
            print("[INFO] nada a inserir.")
        print(f"[INFO] MAX(ts) {pair}/{tf}s: {dm.get_last_timestamp(pair, tf)}")

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="main", description="ETL de Mercado – CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    px = sub.add_parser("extrair", help="Extrai candles (opcionalmente grava no SQLite)")
    px.add_argument("--par", required=True)
    px.add_argument("--timeframe", type=int, required=True, help="em segundos (ex.: 300 para M5)")
    px.add_argument("--dias", type=int, default=None, help="se None, usa regra: 360 na primeira, incremental nas seguintes")
    px.add_argument("--email", default=None)
    px.add_argument("--senha", default=None)
    px.add_argument("--to-db", action="store_true")
    px.set_defaults(func=cmd_extrair)

    pt = sub.add_parser("transformar", help="Aplica transformação a partir de um CSV")
    pt.add_argument("--csv", required=True)
    pt.add_argument("--out", default=None, help="opcional: caminho de saída CSV")
    pt.set_defaults(func=cmd_transformar)

    pc = sub.add_parser("carga", help="Carrega um CSV no SQLite")
    pc.add_argument("--csv", required=True)
    pc.add_argument("--par", required=True)
    pc.add_argument("--timeframe", type=int, required=True)
    pc.set_defaults(func=cmd_carga)

    pp = sub.add_parser("pipeline", help="Extrai -> (transforma) -> carrega")
    pp.add_argument("--par", required=True)
    pp.add_argument("--timeframe", type=int, required=True)
    pp.add_argument("--dias", type=int, default=None)
    pp.add_argument("--email", default=None)
    pp.add_argument("--senha", default=None)
    pp.add_argument("--transformar", action="store_true", help="aplica transformação se módulo disponível")
    pp.add_argument("--to-db", action="store_true", help="carrega no SQLite ao final")
    pp.set_defaults(func=cmd_pipeline)

    return p

def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
