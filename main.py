"""
main.py — Orquestração simples para CLI/GUI.

Funções:
  - extract(params): roda extração e retorna caminho do CSV em data/raw.
  - transform(input_path, params): roda transformação e retorna caminho do CSV em data/transformed.
  - run_pipeline(extract_params, transform_params): extração + transformação.
  - check_connection(email, senha): testa credenciais e retorna True/False.
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Tuple
from pathlib import Path
import re

from scripts.extrair_dados import extrair_dados, conectar_api  # type: ignore
from scripts.transformar_dados import (  # type: ignore
    transformar_dados,
    PAR_DEFAULT as TR_PAR_DEFAULT,
    TIMEFRAME_DEFAULT as TR_TF_DEFAULT,
    DIAS_DEFAULT as TR_DIAS_DEFAULT,
    HORIZON_DEFAULT as TR_HOR_DEFAULT,
    JANELA_SR_DEFAULT as TR_SR_DEFAULT,
)


def _tf_to_seconds(tf: str | int) -> int:
    """Converte 'M5' → 300, 'M1' → 60."""
    if isinstance(tf, int):
        return tf
    tf = tf.strip().upper()
    if tf.startswith("M") and tf[1:].isdigit():
        return int(tf[1:]) * 60
    if tf.isdigit():
        return int(tf)
    raise ValueError(f"Timeframe inválido: {tf}")


def _infer_from_filename(p: Path) -> Tuple[str, int, int]:
    """
    Tenta inferir (par, timeframe[s], dias) de nomes como:
    EURJPY_M5_300d.csv
    """
    m = re.search(r"([A-Z]{6,7})_M(\d+)_([0-9]+)d", p.name.upper())
    if not m:
        return TR_PAR_DEFAULT, TR_TF_DEFAULT, TR_DIAS_DEFAULT
    par = m.group(1)
    tf_sec = int(m.group(2)) * 60
    dias = int(m.group(3))
    return par, tf_sec, dias


def extract(params: Dict[str, Any]) -> str:
    email = (params.get("email") or "").strip()
    senha = (params.get("senha") or "").strip()
    par = (params.get("ativo") or "EURJPY").strip().upper()
    timeframe = _tf_to_seconds(params.get("timeframe", "M5"))
    dias = int(params.get("dias", 360))

    df, path = extrair_dados(par, timeframe, dias, email=email, senha=senha)
    if not path:
        raise RuntimeError("Extração não retornou arquivo.")
    return str(path)


def transform(input_path: Path, params: Dict[str, Any]) -> str:
    janela_sr = int(params.get("janela_sr", TR_SR_DEFAULT))

    # tenta inferir par/timeframe/dias do nome
    par: str = (params.get("par") or "").upper()
    timeframe: Optional[int] = params.get("timeframe")
    dias: Optional[int] = params.get("dias")
    horizon: int = int(params.get("horizon", TR_HOR_DEFAULT))

    if not par or not timeframe or not dias:
        inf_par, inf_tf, inf_dias = _infer_from_filename(Path(input_path))
        par = par or inf_par
        timeframe = timeframe or inf_tf
        dias = dias or inf_dias

    out = transformar_dados(
        raw_path=Path(input_path),
        par=par,
        timeframe=int(timeframe),
        dias=int(dias),
        horizon=horizon,
        janela_sr=janela_sr,
    )
    return str(out["path"])


def run_pipeline(extract_params: Dict[str, Any], transform_params: Dict[str, Any]) -> str:
    raw_path = extract(extract_params)
    return transform(Path(raw_path), transform_params)


def check_connection(email: str, senha: str) -> bool:
    """Tenta conectar na corretora e fecha a sessão imediatamente."""
    try:
        api = conectar_api(email, senha)
        for meth in ("close", "disconnect", "api_close"):
            if hasattr(api, meth) and callable(getattr(api, meth)):
                try:
                    getattr(api, meth)()
                except Exception:
                    pass
        return True
    except Exception:
        return False
