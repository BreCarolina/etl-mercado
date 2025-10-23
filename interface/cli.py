from __future__ import annotations
import os, sys, subprocess, shlex, time
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv

app = typer.Typer(add_completion=False)
console = Console()
ROOT = Path(__file__).resolve().parents[1]

def _load_env() -> None:
    """Carrega e valida variáveis do .env (mínimo: email e senha)."""
    load_dotenv(dotenv_path=ROOT / ".env", override=True, encoding="utf-8")
    miss = [k for k in ("IQ_EMAIL", "IQ_PASSWORD") if not os.getenv(k)]
    if miss:
        raise RuntimeError(f"Faltam variáveis no .env: {', '.join(miss)}")

def _run_step(title: str, script_rel: str) -> None:
    """Executa um script Python na pasta scripts/ e checa retorno."""
    console.rule(f"[bold]{title}")
    cmd = [sys.executable, str(ROOT / "scripts" / script_rel)]
    console.print(f"[dim]$ {' '.join(shlex.quote(c) for c in cmd)}[/dim]")
    proc = subprocess.Popen(cmd, cwd=ROOT)
    ret = proc.wait()
    if ret != 0:
        raise RuntimeError(f"Falha em '{title}' (exit={ret})")

@app.command(help="Executa pipeline completo: extrair → transformar.")
def run():
    _load_env()
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as p:
        p.add_task(description="Preparando...", total=None)
        time.sleep(0.2)
    _run_step("Extração", "extrair_dados.py")
    _run_step("Transformação", "transformar_dados.py")
    console.print("\n[bold green]Pipeline concluído com sucesso.[/bold green]")

@app.command(help="Apenas extrai candles.")
def extrair():
    _load_env()
    _run_step("Extração", "extrair_dados.py")

@app.command(help="Apenas transforma dados já baixados.")
def transformar():
    _load_env()
    _run_step("Transformação", "transformar_dados.py")

if __name__ == "__main__":
    app()
