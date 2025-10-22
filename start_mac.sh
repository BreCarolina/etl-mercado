#!/usr/bin/env bash
set -euo pipefail

# Ir para a raiz do projeto (onde o script está)
cd "$(dirname "$0")"

# 1) Criar/ativar venv
if [ ! -d "venv" ]; then
  echo "[setup] Criando venv..."
  python3 -m venv venv
fi

echo "[setup] Ativando venv..."
# shellcheck disable=SC1091
source venv/bin/activate

# 2) Instalar dependências
echo "[setup] Instalando dependências..."
python -m pip install --upgrade pip setuptools wheel
if [ -f "requirements.txt" ]; then
  python -m pip install -r requirements.txt
fi

# 3) Garantir PYTHONPATH apenas com a raiz do projeto
export PYTHONPATH="$PWD"

# 4) Conferir .env
if [ ! -f ".env" ]; then
  echo "[erro] Arquivo .env não encontrado na raiz do projeto."
  echo "Exemplo de conteúdo (sem aspas e sem comentários na mesma linha):"
  echo "IQ_EMAIL=seu_email@dominio.com"
  echo "IQ_PASSWORD=sua_senha"
  echo "PAR=EURJPY"
  echo "TIMEFRAME=300"
  echo "DIAS=360"
  echo "HORIZON=1"
  echo "JANELA_SR=48"
  exit 1
fi

echo "[setup] Carregando variáveis do .env..."

# 5) Executar pipeline: extrair → transformar
python - <<'PY'
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

# Agora lemos do ambiente (já normalizado)
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
PY

echo "[done] Pipeline concluído."
