# ## Status do projeto

MVP de Engenharia de Dados com interface desktop em desenvolvimento. A transformação, a carga no SQLite e a exportação para CSV foram validadas separadamente com dados simulados. Repetir a carga não gerou duplicatas.

Antes de apresentar, falta corrigir a inicialização e o empacotamento, definir como os indicadores serão armazenados e validar uma demonstração completa com um CSV de exemplo.


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


```markdown
# ETL de Mercado — Coleta e Transformação de Dados de Mercado

### Versão atual: MVP 2 (GUI Desktop com PySide6)

Aplicação ETL voltada à extração e transformação de dados de candles financeiros via IQ Option API.  
Desenvolvida em **Python 3.12** com **interface gráfica (PySide6)** e arquitetura modular, o projeto permite obter, tratar e salvar dados de mercado de forma automatizada e visual.

---

## 1. Objetivo do Projeto

O **ETL de Mercado** foi criado para simplificar o processo de manipulação de dados financeiros, automatizando todas as etapas necessárias para análises e modelagem de estratégias.

O nome **ETL** vem de **Extract → Transform → Load**, que define as três etapas principais:

1. **Extração** — coleta candles históricos diretamente da corretora IQ Option.  
2. **Transformação** — aplica indicadores técnicos (EMA, RSI, volatilidade, suportes, resistências).  
3. **Carregamento e Visualização** — organiza os dados em pastas locais ou banco SQLite (nas próximas versões).

A aplicação pode ser usada tanto por **usuários não técnicos**, via interface gráfica, quanto por **desenvolvedores**, via linha de comando.

---

## 2. Estrutura do Projeto

```

extrair-transformar-dados/
├── scripts/
│   ├── extrair_dados.py        # Extração via IQ Option API
│   ├── transformar_dados.py    # Transformação e cálculo de indicadores
│   └── **init**.py
├── gui.py                      # Interface gráfica PySide6
├── main.py                     # Pipeline principal (CLI)
├── cli.py                      # Versão CLI (MVP1)
├── assets/                     # Ícones e temas visuais
│   └── icone.png
├── data/
│   ├── raw/                    # Dados extraídos (brutos)
│   └── transformed/            # Dados transformados
├── doc/                        # Documentação técnica
│   └── escopo.md
├── requirements.txt            # Lista de dependências
├── pyproject.toml              # Metadados e configuração
└── README.md                   # Este arquivo

````

---

## 3. Instalação e Primeiro Uso

Se você **recebeu o projeto zipado**, siga o passo a passo abaixo.

### Passo 1 — Descompactar o arquivo

1. Clique com o botão direito sobre o arquivo `extrair-transformar-dados.zip`.  
2. Escolha **“Extrair tudo”** ou equivalente.  
3. Após a extração, você terá uma pasta com o mesmo nome do projeto.

---

### Passo 2 — Instalar o Python

Certifique-se de ter o **Python 3.12** instalado no sistema.

- **Windows:**  
  Baixe em [python.org/downloads](https://www.python.org/downloads/) e, durante a instalação, marque a opção **“Add Python to PATH”**.  

- **macOS/Linux:**  
  O Python geralmente já vem instalado. Verifique com:
  ```bash
  python3 --version
````

Se a versão for anterior a 3.10, atualize para 3.12.

---

### Passo 3 — Abrir o terminal dentro da pasta do projeto

* **Windows:**
  Abra o explorador de arquivos, entre na pasta do projeto, clique na barra de endereço e digite `cmd`, depois pressione Enter.
* **macOS/Linux:**
  Clique com o botão direito na pasta e selecione “Abrir no Terminal”.

Você verá o terminal aberto no caminho:

```
.../extrair-transformar-dados/
```

---

### Passo 4 — Criar o ambiente virtual

Crie um ambiente isolado para instalar as dependências do projeto:

```bash
python -m venv venv
```

Ative o ambiente:

* **Windows:**

  ```bash
  venv\Scripts\activate
  ```
* **macOS/Linux:**

  ```bash
  source venv/bin/activate
  ```

O nome `(venv)` aparecerá no início da linha do terminal, indicando que o ambiente está ativo.

---

### Passo 5 — Instalar dependências

Com o ambiente ativo, instale os pacotes necessários:

```bash
pip install -r requirements.txt
```

Isso instalará:

* PySide6 (interface gráfica)
* pandas, numpy (ETL)
* python-dotenv (configurações)
* iqoptionapi (conexão com corretora)

---

### Passo 6 — Criar o arquivo `.env`

Crie, na raiz do projeto, um arquivo chamado `.env` contendo suas credenciais e parâmetros:

```
IQ_EMAIL=seu_email@dominio.com
IQ_PASSWORD=sua_senha
PAR=EURJPY
TIMEFRAME=300
DIAS=360
```

**Observações:**

* O e-mail e a senha são os mesmos da sua conta da **IQ Option**.
* `PAR` define o ativo (ex: EURJPY, USDJPY).
* `TIMEFRAME` é o período de cada candle em segundos (ex: 60 = 1 min, 300 = 5 min).
* `DIAS` define quantos dias de histórico serão extraídos.

---

## 4. Uso da Aplicação

O sistema oferece dois modos de execução: **Interface Gráfica (GUI)** e **Linha de Comando (CLI)**.

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
### Modo 1 — Interface Gráfica (recomendado)

Inicie a interface com:

```bash
python gui.py
```

#### 1. Tela Inicial

A janela principal exibe três abas:

* **Extração**
* **Transformação**
* **Pipeline Completo**

Se o `.env` estiver configurado, o login será automático.

---

#### 2. Aba “Extração”

Nessa aba, o usuário escolhe:

* Par de moedas (ex: EURJPY)
* Timeframe (ex: 300 = M5)
* Quantidade de dias para extrair

Após clicar em **“Iniciar Extração”**, o sistema:

1. Conecta-se à IQ Option API.
2. Coleta os candles históricos.
3. Salva o arquivo CSV em `data/raw/`.

Exemplo de log:

```
Extraindo EURJPY M5 (últimos 360 dias)...
Progresso: 82%
Arquivo salvo em data/raw/EURJPY_M5_360d.csv
```

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
#### 3. Aba “Transformação”

Usada para processar arquivos já extraídos.

1. Selecione o arquivo dentro de `data/raw/`.
2. Clique em **“Transformar Dados”**.

O sistema:

* Calcula médias móveis (EMA7, EMA21)
* Aplica RSI14 e volatilidade
* Detecta suportes e resistências
* Normaliza e limpa os dados

O resultado é salvo em `data/transformed/`, por exemplo:

```
data/transformed/EURJPY_M5_360d_transformed.csv
```

---

#### 4. Aba “Pipeline Completo”

Executa **extração + transformação** de uma só vez.
Ideal para gerar um dataset completo automaticamente.

Exemplo de saída:

```
Iniciando pipeline...
Extraindo EURJPY M5...
Transformando dados...
Pipeline concluído com sucesso!
```

---

#### 5. Dicas Importantes

* Verifique se suas credenciais estão corretas no `.env`.
* Evite períodos muito longos com timeframes curtos (demora ou pode gerar timeouts).
* As pastas `data/raw/` e `data/transformed/` são criadas automaticamente.
* Os logs de execução ficam visíveis na interface e podem ser copiados.

---

### Modo 2 — Linha de Comando (avançado)

Ideal para automações, scripts agendados ou integração com notebooks.

```bash
python main.py --extrair
python main.py --transformar
python main.py --pipeline
```

#### Exemplos práticos:

**Extrair apenas dados:**

```bash
python main.py --extrair --par EURJPY --timeframe 300 --dias 360
```

**Transformar arquivo específico:**

```bash
python main.py --transformar --input data/raw/EURJPY_M5_360d.csv
```

**Executar pipeline completo:**

```bash
python main.py --pipeline
```

---

## 5. Estrutura de Saída

| Tipo                         | Localização           | Exemplo de Nome                     |
| ---------------------------- | --------------------- | ----------------------------------- |
| Dados brutos                 | `data/raw/`           | `EURJPY_M5_360d.csv`                |
| Dados transformados          | `data/transformed/`   | `EURJPY_M5_360d_transformed.csv`    |
| Banco de dados (futuro MVP3) | `data/market_data.db` | `candles_EURJPY_M5` (tabela SQLite) |

---

## 6. Resumo do Fluxo Completo

1. Baixe e extraia o projeto.
2. Instale o Python 3.12.
3. Crie e ative o ambiente virtual.
4. Instale as dependências.
5. Crie o arquivo `.env`.
6. Execute `python gui.py`.
7. Configure os parâmetros e rode o pipeline.
8. Confira os resultados em `data/`.

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

## 7. MVPs e Evolução

| Fase        | Entrega       | Status    | Descrição                                     |
| ----------- | ------------- | --------- | --------------------------------------------- |
| **MVP 1**   | CLI           | Concluído | Extração e transformação via terminal         |
| **MVP 2**   | GUI           | Concluído | Interface desktop com PySide6                 |
| **MVP 3.1** | Banco SQLite  | Planejado | Armazenamento incremental por ativo/timeframe |
| **MVP 3.2** | Empacotamento | Planejado | Distribuição local (PyInstaller / Py2App)     |

---

## 8. Banco de Dados (Planejado — MVP 3.1)

Banco **SQLite3** local, criado automaticamente em `data/market_data.db`.

Cada par/timeframe terá uma tabela, como:

```
candles_EURJPY_M5
candles_USDJPY_M1
```

Campos principais:

* timestamp
* abertura, máxima, mínima, fechamento, volume
* indicadores calculados (EMA7, EMA21, RSI14, volatilidade, pressões, suportes, resistências)

---

## 9. Empacotamento (Planejado — MVP 3.2)

Será possível gerar executáveis independentes:

* **macOS:** Py2App
* **Windows/Linux:** PyInstaller

Gerará:

```
ETL_de_Mercado.app
ETL_de_Mercado.exe
```

Incluindo:

* Ícone personalizado (`assets/icone.icns`)
* Banco SQLite embutido
* Dependências pré-instaladas
* Criação automática das pastas `data/` no primeiro uso

---

## 10. Tecnologias Principais

| Categoria     | Tecnologia           |
| ------------- | -------------------- |
| Linguagem     | Python 3.12          |
| GUI           | PySide6 (Qt)         |
| ETL           | pandas, numpy        |
| Persistência  | SQLite3              |
| API Broker    | IQ Option API        |
| Configuração  | python-dotenv        |
| Empacotamento | PyInstaller / Py2App |

---

## 11. Contribuição

Contribuições são bem-vindas.

1. Faça um fork do projeto.
2. Crie uma branch para sua feature.
3. Commit com descrição clara.
4. Envie um Pull Request para análise.

---

## 12. Licença

Distribuição comercial não autorizada sem consentimento prévio da autora.

---

## 13. Autoria

**Carolina Brescowitt**
Cientista de Dados
GitHub: [@BreCarolina](https://github.com/BreCarolina)

```

