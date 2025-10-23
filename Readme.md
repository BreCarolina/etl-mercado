(`start_mac.sh`, `start_win.ps1`), e ajustes de clareza e consistência técnica.

---

# README — Extrair & Transformar Dados (IQ Option)

Este projeto automatiza a **extração de candles brutos** da IQ Option e sua **transformação em dataset técnico** pronto para treino.
O objetivo é permitir que qualquer usuário — mesmo sem conhecimento técnico — gere dados completos com apenas **um comando:**

```
etd run
```

---

## 1) Pré-requisitos

* **Python 3.9+** (recomendado 3.11 ou superior)
* **Acesso à internet**
* Conta **IQ Option** com login e senha válidos

---

## 2) Estrutura do projeto

```
extrair-transformar-dados/
├─ data/
│  ├─ raw/           # CSVs brutos extraídos
│  └─ transformed/   # CSVs transformados (dataset final)
├─ iqoptionaapi/     # Biblioteca local usada na extração
├─ interface/
│  └─ cli.py         # CLI oficial (Typer)
├─ scripts/
│  ├─ extrair_dados.py
│  └─ transformar_dados.py
├─ .env              # Suas credenciais e parâmetros
├─ setup.cfg         # Metadados e entrypoint da CLI
└─ requirements.txt  # Dependências do projeto
```

> Se sua API estiver nomeada como `iqoptionapi/`, o projeto também funciona sem alterações.

---

## 3) Configuração do `.env`

Crie ou edite o arquivo **`.env`** na raiz do projeto:

```
IQ_EMAIL=seu_email@dominio.com
IQ_PASSWORD=sua_senha

# Parâmetros do pipeline
PAR=EURJPY
TIMEFRAME=300
DIAS=360
HORIZON=1
JANELA_SR=48
```

> **Regras:**
>
> * Não use aspas.
> * Cada variável deve estar em sua própria linha.
> * O arquivo deve estar salvo com codificação **UTF-8 (sem BOM)**.

---

## 4) Instalação

### macOS / Linux

```bash
cd /caminho/para/extrair-transformar-dados
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

### Windows (PowerShell)

```powershell
cd C:\caminho\para\extrair-transformar-dados
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

> Se o PowerShell bloquear a execução:
>
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

---

## 5) Uso da CLI `etd`

Depois de instalar (`pip install -e .`), o comando `etd` fica disponível no terminal.

### Comandos disponíveis

| Comando           | Descrição                                              |
| ----------------- | ------------------------------------------------------ |
| `etd extrair`     | Apenas extrai candles brutos                           |
| `etd transformar` | Apenas transforma os dados extraídos                   |
| `etd run`         | Executa o pipeline completo (extração + transformação) |

### Exemplo

```bash
etd run
```

---

## 6) Estrutura de saída

| Diretório           | Conteúdo                               |
| ------------------- | -------------------------------------- |
| `data/raw/`         | Arquivos brutos extraídos da IQ Option |
| `data/transformed/` | Datasets finais prontos para treino    |

Formato dos arquivos:

```
{PAR}_{TF}_{diasReais}d_{AAAAMMDD-AAAAMMDD}_n{linhas}_{timestamp}.csv
```

---

## 7) Parâmetros ajustáveis

| Parâmetro   | Tipo  | Descrição                                           |
| ----------- | ----- | --------------------------------------------------- |
| `PAR`       | `str` | Par de moedas (ex: `"EURJPY"`, `"EURUSD"`)          |
| `TIMEFRAME` | `int` | Intervalo em segundos (`300` = 5min, `60` = 1min)   |
| `DIAS`      | `int` | Quantidade de dias de histórico desejado            |
| `HORIZON`   | `int` | Horizonte para cálculo de alvo (1 = próximo candle) |
| `JANELA_SR` | `int` | Janela para suporte/resistência (padrão = 48)       |

---

## 8) O que cada script faz

### `scripts/extrair_dados.py`

* Conecta à IQ Option com credenciais do `.env`.
* Extrai candles históricos (até o último fechado).
* Aplica filtros automáticos (07h–21h UTC, sem candles futuros).
* Salva o CSV bruto em `data/raw`.

### `scripts/transformar_dados.py`

* Localiza o CSV bruto mais recente.
* Aplica saneamento e engenharia de features:

  * Corpo, pavios, pressões compradora/vendedora
  * Médias móveis (EMA7, EMA21)
  * RSI(14)
  * Suporte e resistência com janela deslizante
  * Volatilidade e retorno
  * Criação da variável-alvo `target_class`
* Remove períodos de warmup e horizonte futuro.
* Salva o dataset pronto em `data/transformed`.

---

## 9) Solução de erros comuns

### ❌ `Erro: não foi possível conectar à IQ Option`

**Causas:**

* Credenciais incorretas.
* Instabilidade na API da corretora.
* IP bloqueado temporariamente.

**Soluções:**

```bash
# Atualize dependências críticas de rede
pip install "requests==2.31.0" "urllib3==1.26.18"
```

ou aguarde alguns minutos antes de tentar novamente.

---

## 10) Reprodutibilidade — testar em outro ambiente

1. Clone ou descompacte o projeto.
2. Crie e ative a venv.
3. Instale as dependências.
4. Crie o `.env` com suas credenciais.
5. Execute:

   ```bash
   etd run
   ```
6. Verifique os arquivos em:

   * `data/raw/`
   * `data/transformed/`

---

## 11) Próximos passos

* Adicionar logging e barra de progresso completa.
* Integrar interface gráfica (GUI).
* Criar módulo PyPI (`pip install extrair-transformar-dados`).
* Documentar notebook de treino com o dataset final.

---

## 12) FAQ

**1. Posso mudar o timeframe?**
Sim, altere `TIMEFRAME` no `.env` (ex: `60` = M1).

**2. Onde os dados ficam salvos?**

* Brutos → `data/raw`
* Transformados → `data/transformed`

**3. Como recomeçar do zero?**
Remova a venv e recrie:

```bash
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**4. Posso usar em outro computador?**
Sim — copie o diretório inteiro e rode `etd run`.

**5. A API é local ou via pip?**
Ambas as opções funcionam. O projeto detecta automaticamente `iqoptionaapi/` ou `iqoptionapi/`.

---

## 13) Histórico e versão

* **Versão atual:** `v0.1.0`
* **Mudanças:**

  * Substituição dos scripts `start_mac.sh` e `start_win.ps1` pela CLI `etd`
  * Estrutura modular e portável (`pathlib`, `.env`, `typer`)
  * Compatível com macOS, Windows e Linux
  * Armazenamento automático em `data/raw` e `data/transformed`

