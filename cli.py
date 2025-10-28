"""
cli.py — Interface de linha de comando para o pipeline.
Comandos: extract, transform, pipeline.
"""

import argparse
from pathlib import Path
import json
import sys
import main


def _parse_json(s: str):
    """Converte string JSON em dict; retorna {} se vazio."""
    if not s or s.strip() == "":
        return {}
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        print("Erro: parâmetro deve ser JSON válido.")
        sys.exit(2)


def cmd_extract(args: argparse.Namespace):
    params = _parse_json(args.params)
    out = main.extract(params)
    print(out)


def cmd_transform(args: argparse.Namespace):
    params = _parse_json(args.params)
    out = main.transform(Path(args.input), params)
    print(out)


def cmd_pipeline(args: argparse.Namespace):
    eparams = _parse_json(args.extract_params)
    tparams = _parse_json(args.transform_params)
    out = main.run_pipeline(eparams, tparams)
    print(out)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="etl",
        description="ETL de mercado: extração e transformação."
    )
    sub = p.add_subparsers(dest="command", required=True)

    p_ext = sub.add_parser("extract", help="Roda apenas a extração")
    p_ext.add_argument("--params", default="", help="JSON com parâmetros")
    p_ext.set_defaults(func=cmd_extract)

    p_tr = sub.add_parser("transform", help="Roda apenas a transformação")
    p_tr.add_argument("--input", required=True, help="Arquivo de entrada")
    p_tr.add_argument("--params", default="", help="JSON com parâmetros")
    p_tr.set_defaults(func=cmd_transform)

    p_pipe = sub.add_parser("pipeline", help="Roda extração + transformação")
    p_pipe.add_argument("--extract-params", default="", help="JSON da extração")
    p_pipe.add_argument("--transform-params", default="", help="JSON da transformação")
    p_pipe.set_defaults(func=cmd_pipeline)

    return p


def main_cli(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main_cli()
