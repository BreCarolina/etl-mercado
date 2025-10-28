

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

---

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

---

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

