
# README — Extrair & Transformar Dados (IQ Option)

Este projeto automatiza a **extração de candles brutos** da IQ Option e sua **transformação em dataset técnico** pronto para treino.
O objetivo é permitir que qualquer usuário (mesmo sem conhecimento técnico) configure, rode e gere dados com apenas **um comando**.

---

## 1) Pré-requisitos

* **Python 3.9+** (recomendado 3.11 ou superior)
* Acesso à internet
* Conta **IQ Option** com login e senha válidos

---

## 2) Estrutura do projeto

```
extrair-transformar-dados/
├─ data/
│  ├─ raw/           # CSVs brutos extraídos
│  └─ transformed/   # CSVs transformados (dataset final)
├─ iqoptionapi/      # Biblioteca local usada na extração
├─ scripts/
│  ├─ extrair_dados.py
│  └─ transformar_dados.py
├─ start_mac.sh      # Executa todo o pipeline no macOS/Linux
├─ start_win.ps1     # Executa todo o pipeline no Windows
├─ .env              # Suas credenciais e parâmetros
└─ requirements.txt  # Dependências do projeto
```

---

## 3) Configuração do `.env`

Crie ou edite o arquivo **`.env`** na raiz do projeto com o seguinte conteúdo:

```
IQ_EMAIL=seu_email@dominio.com
IQ_PASSWORD=sua_senha

# Parâmetros do pipeline (podem ser alterados conforme desejar)
PAR=EURJPY
TIMEFRAME=300
DIAS=360
HORIZON=1
JANELA_SR=48
```

> **Importante:**
>
> * Não use aspas.
> * Evite comentários na mesma linha (`#` só pode iniciar uma linha inteira).
> * O `.env` deve estar salvo com codificação **UTF-8 sem BOM**.
> * Este arquivo é essencial para a autenticação e controle dos parâmetros.

---

## 4) Criar ambiente virtual e instalar dependências

### macOS / Linux

```bash
cd /caminho/para/extrair-transformar-dados
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
cd C:\caminho\para\extrair-transformar-dados
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

> Se aparecer erro sobre `websocket-client`, rode:
>
> ```bash
> python -m pip install websocket-client
> ```

---

## 5) Executar o projeto automaticamente (modo fácil)

Com o `.env` preenchido e o Python instalado, execute o fluxo completo (extração + transformação) com **um único comando**.

### macOS / Linux

```bash
chmod +x start_mac.sh
./start_mac.sh
```

### Windows (PowerShell)

```powershell
.\start_win.ps1
```

Esses scripts realizam automaticamente:

1. Criação e ativação do ambiente virtual (`venv`)
2. Instalação das dependências
3. Leitura automática do `.env`
4. Execução do pipeline completo (extração + transformação)

> **Dica (Windows):**
> Caso o PowerShell bloqueie a execução, habilite scripts com:
>
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

---

## 6) Parâmetros disponíveis

Os parâmetros são lidos automaticamente do `.env` e podem ser alterados livremente:

| Parâmetro   | Tipo  | Descrição                                                      |
| ----------- | ----- | -------------------------------------------------------------- |
| `PAR`       | `str` | Par de moedas (ex: `"EURJPY"`, `"EURUSD"`, etc.)               |
| `TIMEFRAME` | `int` | Intervalo em segundos (ex: `300` = 5 minutos, `60` = 1 minuto) |
| `DIAS`      | `int` | Quantidade de dias de candles para baixar                      |
| `HORIZON`   | `int` | Horizonte de previsão (1 = próximo candle)                     |
| `JANELA_SR` | `int` | Janela para cálculo de Suporte/Resistência (padrão = `48`)     |

Também é possível sobrescrever parâmetros temporariamente ao executar o script:

```bash
PAR=EURUSD TIMEFRAME=60 DIAS=10 HORIZON=3 JANELA_SR=72 ./start_mac.sh
```

---

## 7) O que cada script faz

### `scripts/extrair_dados.py`

* Conecta à IQ Option usando as credenciais do `.env`
* Extrai candles brutos do par e timeframe definidos
* Salva os dados em `data/raw/{PAR}_{TF}_{...}.csv`

### `scripts/transformar_dados.py`

* Localiza o arquivo bruto (ou o mais recente)
* Executa o pipeline completo:

  * Limpeza e normalização
  * Geração de features técnicas (EMA, RSI, pavios, corpo, pressão, S/R, volatilidade, etc.)
  * Cálculo da variável `target_class` (1 = alta, 0 = baixa)
  * Remoção automática de períodos iniciais (warmup) e horizonte de previsão
* Salva o dataset final em `data/transformed/{PAR}_{TF}_{diasReais}d_{inicio}-{fim}_n{linhas}_{timestamp}.csv`

---

## 8) Estrutura de saída

| Diretório           | Conteúdo                               |
| ------------------- | -------------------------------------- |
| `data/raw/`         | Arquivos brutos extraídos da IQ Option |
| `data/transformed/` | Datasets finais prontos para treino    |

Formato do arquivo final:

```
{PAR}_{TF}_{diasReais}d_{AAAAMMDD-AAAAMMDD}_n{linhas}_{timestamp}.csv
```

---

## 9) Erro comum e solução

**Problema:**

```
Erro: não foi possível conectar à IQ Option
```

**Causas possíveis:**

* Credenciais incorretas no `.env`
* Bloqueio temporário de IP pela IQ Option
* Problemas de SSL no macOS antigo

**Soluções:**

1. Verifique `IQ_EMAIL` e `IQ_PASSWORD` no `.env`
2. Atualize pacotes de rede:

   ```bash
   python -m pip install "requests==2.31.0" "urllib3==1.26.18"
   ```
3. Recrie a `venv` com Python 3.11 ou superior

---

## 10) Reprodutibilidade — simular um novo usuário

1. Baixe o projeto (ZIP ou Git clone)
2. Crie a `venv` e instale as dependências (passo 4)
3. Preencha o `.env` com credenciais e parâmetros
4. Execute `start_mac.sh` ou `start_win.ps1`
5. Verifique:

   * `data/raw` → contém o CSV bruto
   * `data/transformed` → contém o dataset final processado

---

## 11) Próximos passos

* Adicionar logs e métricas ao pipeline
* Criar interface gráfica simples (GUI)
* Empacotar o projeto como módulo Python (`setup.py`)
* Documentar exemplos de treino com o dataset final

---

## 12) FAQ — Perguntas Frequentes

**1. Posso mudar o timeframe?**
Sim, basta alterar `TIMEFRAME` no `.env` (ex: `TIMEFRAME=60` para M1).

**2. Onde ficam os dados?**

* Brutos → `data/raw/`
* Transformados → `data/transformed/`

**3. Como reiniciar o projeto do zero?**
Exclua a pasta `venv` e recrie:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**4. Posso rodar em outro computador?**
Sim, basta copiar o diretório do projeto (inclusive `.env`) e repetir o passo 4.

**5. Preciso instalar algo além do Python?**
Não. Tudo é configurado automaticamente.

**6. O que fazer se a IQ Option bloquear o login?**
Aguarde algumas horas ou conecte-se por outra rede (IP diferente).

---

## 13) Sobre os scripts de inicialização

Os arquivos **`start_mac.sh`** e **`start_win.ps1`** são atalhos automáticos que:

* Criam e ativam a venv
* Instalam as dependências
* Carregam o `.env`
* Executam todo o pipeline de forma autônoma

Eles eliminam a necessidade de comandos Python manuais e tornam o projeto **plug-and-play** para qualquer sistema operacional.

* **macOS/Linux:** `./start_mac.sh`
* **Windows:** `.\start_win.ps1`

