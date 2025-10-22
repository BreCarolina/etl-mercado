# Ir para a pasta do script
Set-Location -Path $PSScriptRoot

# 1) Criar/ativar venv
if (-not (Test-Path -Path "venv")) {
  Write-Host "[setup] Criando venv..."
  py -3 -m venv venv
}

Write-Host "[setup] Ativando venv..."
& .\venv\Scripts\Activate.ps1

# 2) Instalar dependências
Write-Host "[setup] Instalando dependências..."
python -m pip install --upgrade pip setuptools wheel
if (Test-Path -Path "requirements.txt") {
  python -m pip install -r requirements.txt
}

# 3) PYTHONPATH na raiz do projeto
$env:PYTHONPATH = (Get-Location).Path

# 4) Conferir .env
if (-not (Test-Path -Path ".env")) {
  Write-Host "[erro] Arquivo .env não encontrado na raiz do projeto."
  Write-Host "Exemplo (sem aspas e sem comentários na mesma linha):"
  Write-Host "IQ_EMAIL=seu_email@dominio.com"
  Write-Host "IQ_PASSWORD=sua_senha"
  Write-Host "PAR=EURJPY"
  Write-Host "TIMEFRAME=300"
  Write-Host "DIAS=360"
  Write-Host "HORIZON=1"
  Write-Host "JANELA_SR=48"
  exit 1
}

Write-Host "[setup] Carregando variáveis do .env..."

# 5) Executar pipeline: extrair → transformar
$py = @'
import os, sys, traceback, io

ROOT = os.getcwd()
if ROOT not in sys.path:
    sys.path.append(ROOT)

ENV_PATH = os.path.join(ROOT, ".env")

def load_env_robusto(path: str):
    """
    Lê .env de forma robusta:
      - encoding utf-8-sig (remove BOM)
      - ignora CRLF (\r), linhas em branco e comentários (# ...)
      - aceita key = value (remove espaços e aspas ao redor do value)
    Preenche os pares em os.environ.
    """
    with io.open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        for raw in f:
            line = raw.strip().replace("\r", "")
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k:
                os.environ[k] = v

load_env_robusto(ENV_PATH)

def must(name: str, cast=None):
    v = os.getenv(name)
    if v is None or str(v).strip() == "":
        raise SystemExit(f"[erro] Variável {name} ausente no .env (lido de {ENV_PATH})")
    return cast(v) if cast else v.strip()

IQ_EMAIL  = must("IQ_EMAIL")
IQ_PASS   = must("IQ_PASSWORD")
PAR       = must("PAR")
TIMEFRAME = must("TIMEFRAME", int)
DIAS      = must("DIAS", int)
HORIZON   = must("HORIZON", int)
JANELA_SR = must("JANELA_SR", int)

print("[run] Parâmetros lidos do .env normalizado:")
print(f"   PAR={PAR}")
print(f"   TIMEFRAME={TIMEFRAME}")
print(f"   DIAS={DIAS}")
print(f"   HORIZON={HORIZON}")
print(f"   JANELA_SR={JANELA_SR}")
print("-------------------------------------------------------")

from scripts.extrair_dados import extrair_dados
from scripts.transformar_dados import transformar_dados

try:
    dados, path = extrair_dados(PAR, TIMEFRAME, DIAS, ROOT)
    print(f"[ok] RAW salvo em: {path}")

    res = transformar_dados(
        raw_path=path,
        par=PAR,
        timeframe=TIMEFRAME,
        dias=DIAS,
        horizon=HORIZON,
        janela_sr=JANELA_SR,
        root=ROOT,
    )
    print(f"[ok] TRANSFORM: {res['resumo']['arquivo']}  linhas: {res['resumo']['linhas']}")
except Exception:
    print("[erro] Falha na execução do pipeline:")
    traceback.print_exc()
    raise SystemExit(1)
'@

# Em PowerShell, usamos here-string piped para stdin do Python:
$py | python -

Write-Host "[done] Pipeline concluído."
