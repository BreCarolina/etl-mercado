

# ETL de Mercado

Aplicação para extração, transformação, carga e exportação de dados de mercado obtidos da IQ Option.

---

## 1. Visão Geral

O **ETL de Mercado** é um aplicativo desktop que automatiza o ciclo completo de **extração, transformação e carga (ETL)** de candles financeiros, salvando os dados em uma base local **SQLite/WAL**.
A interface gráfica (GUI) é a principal forma de uso, permitindo realizar todo o processo de forma visual, sem necessidade de linha de comando.

---

## 2. Requisitos

### Para o aplicativo GUI

* macOS (Intel ou Apple Silicon com Rosetta)
* Conexão com a internet
* Conta ativa na IQ Option

### Para uso avançado (CLI / desenvolvimento)

* Python 3.12+
* Ambiente virtual configurado

---

## 3. Instalação — Aplicativo GUI (recomendado)

### 3.1. Download

1. Acesse a seção **Releases** do repositório.
2. Baixe o artefato para o seu sistema operacional:

   * `etl-mercado-gui.app.zip` (macOS)

### 3.2. Primeira execução

1. Extraia o `.zip`.

2. Clique com o botão direito em `etl-mercado-gui.app` e selecione **Abrir**.

3. Caso o macOS bloqueie a execução, remova o atributo de quarentena:

   ```bash
   xattr -dr com.apple.quarantine etl-mercado-gui.app
   ```

4. Abra novamente com duplo clique.

---

## 4. Login e Configuração de Credenciais

A interface já possui uma aba **Credenciais** para inserir **email e senha da IQ Option** diretamente.
O arquivo `.env` **não é obrigatório** para uso do aplicativo, é opcional e serve apenas se o usuário desejar login automático sem digitar credenciais toda vez:

```bash
IQ_EMAIL=seu_email@dominio.com
IQ_PASSWORD=sua_senha
```

Esse arquivo, se usado, deve ficar no mesmo diretório do aplicativo.

---

## 5. Uso da intrface (GUI)

Após abrir o aplicativo, as seguintes abas estarão disponíveis:

### 1. Credenciais

Efetua login na IQ Option manualmente ou carrega do `.env` se existir.

### 2. Pipeline

Permite executar etapas individuais ou o fluxo completo:

* **Extração** – coleta candles brutos.
* **Transformação** – gera indicadores técnicos.
* **Carga** – grava os dados processados no banco SQLite.
* **Completo** – executa todo o ciclo ETL.

### 3. Exportar

Permite filtrar dados no banco e exportar para CSV com as features desejadas.

---

## 6. Estrutura de Arquivos

```
etl-mercado/
├── assets/                 # Ícones e recursos gráficos
├── data/
│   ├── raw/                # Dados brutos (extração)
│   ├── transformed/        # Dados transformados (features)
│   ├── exported/           # Dados exportados (CSV final)
│   └── market_data.db      # Banco SQLite (MVP3+)
├── doc/                    # Documentação técnica
├── iqoptionaapi/           # Biblioteca local da API IQ Option
├── scripts/                # Módulos ETL (extração, transformação, carga)
├── cli.py                  # Interface CLI
├── gui.py                  # Interface GUI (PySide6)
├── main.py
├── pyproject.toml
├── Readme.md
└── requirements.txt
```

---

## 7. Uso via Linha de Comando (opcional)

O modo CLI é indicado para automação e testes de desenvolvimento.

### 7.1. Configuração do ambiente

```bash
python3 -m venv venv
source venv/bin/activate
./venv/bin/python -m pip install --upgrade pip setuptools wheel
./venv/bin/python -m pip install -e .
```

### 7.2. Exemplos de uso

Ajuda geral:

```bash
etl-mercado-cli --help
```

Pipeline completo:

```bash
etl-mercado-cli run --pair EURJPY --timeframe M5 --days 30 --janela-sr 50
```

Etapas isoladas:

```bash
etl-mercado-cli extract --pair EURJPY --timeframe M5 --days 10
etl-mercado-cli transform --pair EURJPY --timeframe M5
etl-mercado-cli load --pair EURJPY --timeframe M5
```

Exportação:

```bash
etl-mercado-cli export --pair EURJPY --timeframe M5 \
  --from "2025-01-01" --to "2025-01-31" \
  --features EMA_7,EMA_21,RSI_14
```

---

## 8. Pipeline ETL (Fluxo)

1. **Extração:** Baixa candles brutos → `data/raw/PAIR_TF.csv`
2. **Transformação:** Gera features técnicas → `data/transformed/PAIR_TF.csv`
3. **Carga:**

   * MVP1–2: CSV direto
   * MVP3+: grava via UPSERT em `data/market_data.db` (SQLite/WAL)
4. **Exportação:** Filtros e seleção de features → `data/exported/*.csv`

---

## 9. Features Técnicas

* corpo
* pavio_superior
* pavio_inferior
* pressao_compradora
* pressao_vendedora
* EMA_7
* EMA_21
* RSI_14
* suporte
* resistencia
* dist_suporte
* dist_resistencia
* volatilidade
* retorno
* fechamento_futuro
* target_class

---

## 10. Versionamento

**Branches**

* `main` — versão estável
* `mvp1` — CLI + CSV
* `mvp2` — GUI + exportação CSV
* `mvp3` — SQLite/WAL + UPSERT + export via DB
* `mvp3.1` — documentação e empacotamento
* `hotfix/*` — correções urgentes

**Releases**

* `v0.1.0` — MVP1
* `v0.2.0` — MVP2
* `v0.3.0` — MVP3
* `v0.3.1` — MVP3.1

---

## 11. Empacotamento

Empacotado com **PyInstaller** para distribuição independente de ambiente Python.

### CLI

```bash
pyinstaller --name etl-mercado-cli --onefile --clean \
  --add-data "assets/icone.png:assets" cli.py
```

### GUI

```bash
pyinstaller --name etl-mercado-gui --windowed --clean \
  --icon assets/icone.icns \
  --add-data "assets/icone.png:assets" \
  --collect-all iqoptionaapi \
  gui.py
```

Os artefatos são gerados em `dist/` e podem ser distribuídos como `.zip`.

---

## 12. Licença

**MIT License** — uso livre, com proibição de redistribuição comercial sem autorização prévia.

---


