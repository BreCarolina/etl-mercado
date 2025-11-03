

# Documento de Escopo do Projeto

## ETL de Mercado — Extração, Transformação e Carga de Dados Financeiros (Planejamento)

---

## Visão Geral

Construir uma aplicação para **ETL de dados de mercado** obtidos da **API da IQ Option**, com operação via **CLI** e **GUI**, **exportação CSV** e evolução de persistência **de arquivos (MVP1–2) para SQLite em modo WAL (a partir do MVP3)**. Arquitetura modular com camadas de **interface**, **aplicação (ETL)**, **persistência** e **integração com API**.

---

## Objetivo

Automatizar o ciclo completo de **extração**, **transformação**, **carga** e **exportação** de candles financeiros, garantindo reprodutibilidade e robustez.

* Extrair candles com **coleta incremental**.
* Gerar **features técnicas** na transformação.
* Carregar em **banco de dados SQLite** (MVP3+).
* Exportar **CSV** filtrado por par/período/features.
* Disponibilizar **CLI** e **GUI** com logs e validações.
* **Empacotar** binários (CLI/GUI) para distribuição.

---

## Arquitetura Técnica

| Componente    | Tecnologia                                           |
| ------------- | ---------------------------------------------------- |
| Linguagem     | **Python 3.12**                                      |
| Interface     | PySide6                                              |
| Persistência  | Arquivos (MVP1–2) → Banco SQLite em modo WAL (MVP3+) |
| API           | API construída localmente via módulo `iqoptionaapi`  |
| Empacotamento | PyInstaller                                          |
| Configuração  | `python-dotenv` (.env)                               |

---

## Estrutura de Diretórios

```
etl-mercado/
├── .gitignore
├── .env
├── assets/
│   ├── icone.icns
│   ├── icone.iconset/...
│   └── icone.png
├── cli.py
├── data/
│   ├── exported/
│   ├── market_data.db          # surge no MVP3+
│   ├── raw/
│   └── transformed/
├── doc/
│   ├── arquitetura_camadas.md
│   ├── escopo_banco_dados.md
│   └── escopo.md               # este arquivo
├── gui.py
├── iqoptionaapi/
│   ├── __init__.py
│   ├── api.py
│   ├── constants.py
│   ├── country_id.py
│   ├── expiration.py
│   ├── global_value.py
│   ├── http/...
│   ├── stable_api/ stable_api.py
│   ├── stable_api.py
│   ├── version_control.py
│   └── ws/...
├── main.py
├── pyproject.toml
├── Readme.md
├── requirements.txt
└── scripts/
    ├── __init__.py
    ├── carga.py
    ├── db_manager.py
    ├── extracao.py
    └── transformacao.py
```

---

## Descrição dos Arquivos-Chave

| Caminho                      | Finalidade                                                                            |
| ---------------------------- | ------------------------------------------------------------------------------------- |
| `cli.py`                     | Entrada CLI; orquestra pipeline e etapas por parâmetros.                              |
| `main.py`                    | Entrada principal para orquestração (CLI).                                            |
| `gui.py`                     | Interface PySide6 (Credenciais, Pipeline, Exportar) com logs.                         |
| `scripts/extracao.py`        | Extração incremental; grava CSV em `data/raw/`.                                       |
| `scripts/transformacao.py`   | Geração das **features** da transformação; grava em `data/transformed/`.              |
| `scripts/carga.py`           | MVP1–2: opcional; **MVP3+**: UPSERT no SQLite; limpeza do `transformed/`.             |
| `scripts/db_manager.py`      | MVP1–2: utilidades mínimas; **MVP3+**: init DB, índices, último `ts`, exportação CSV. |
| `iqoptionaapi/stable_api.py` | Fachada (login, candles, sessão).                                                     |
| `iqoptionaapi/http/*`        | Autenticação/REST (login/2FA/tokens, perfis, recursos).                               |
| `iqoptionaapi/ws/*`          | Cliente WebSocket (canais, objetos e eventos recebidos).                              |
| `assets/icone.*`             | Ícones do aplicativo para empacotamento.                                              |
| `data/*`                     | Artefatos de execução (ignorar no versionamento).                                     |
| `doc/arquitetura_camadas.md` | Documento de arquitetura de camadas (separado).                                       |
| `doc/escopo_banco_dados.md`  | Documento de arquitetura do banco de dados (separado).                                |
| `pyproject.toml`             | Metadados, dependências e entry points.                                               |
| `requirements.txt`           | Pinagem de dependências.                                                              |
| `Readme.md`                  | Visão geral e uso (será refinado separadamente).                                      |

---

## Funcionalidades

### Conexão

* Autenticação do usuário via e-mail e senha diretamente na GUI ou CLI.
* Uso da API local `iqoptionaapi` para login, mantendo sessão ativa e segura.
* Feedback visual ao conectar/desconectar, com logs e mensagens informativas.

---

### Extração

* Coleta de candles históricos para um par e timeframe especificados.
* Capacidade de coleta incremental com base nos dados locais (CSV ou DB).
* Conexão com a API IQ Option via `stable_api.py`.
* Exportação para CSV em `data/raw/`.
* Tratamento de erros (ex: tentativas de reconexão, falha de autenticação).

---

## Construção da API (módulo `iqoptionaapi`)

* **Objetivo:** interface estável para coleta de candles (HTTP/WebSocket), encapsulando **autenticação**, **sessão**, **paginação**, **retentativas** e **ordenação**.

* **Camadas internas:**

  * `http/` — autenticação (login/2FA/tokens), perfis e endpoints REST.
  * `ws/` — cliente WebSocket (canais de subscrição, objetos e eventos).
  * `stable_api.py` — **fachada** de alto nível (login, `get_candles`, estado de sessão).

* **Uso pela aplicação:**

  * `scripts/extracao.py` autentica e obtém candles por intervalo (`from_ts`, `to_ts`, `timeframe`).
  * Coleta incremental baseada no dado existente:

    * **MVP1–2:** arquivos locais.
    * **MVP3+:** último `ts` existente no banco, via `db_manager.get_last_timestamp()`.

---

## Transformação

* Processa os arquivos de `data/raw/` para inserir colunas calculadas de indicadores técnicos.
* Gera arquivo intermediário em `data/transformed/`.
* Valida ausência de nulos e formatação de tipos antes da carga.
* Utiliza bibliotecas como `pandas` e `numpy` para cálculo eficiente das features.

### Features geradas:

* **Candle/forma:** `corpo`, `pavio_superior`, `pavio_inferior`
* **Pressões:** `pressao_compradora`, `pressao_vendedora`
* **Médias/oscilares:** `EMA_7`, `EMA_21`, `RSI_14`
* **SR e distâncias:** `suporte`, `resistencia`, `dist_suporte`, `dist_resistencia`
* **Risco/retorno:** `volatilidade`, `retorno`
* **Alvos:** `fechamento_futuro`, `target_class`

A saída em `data/transformed/` inclui os campos base `pair, timeframe_s, ts, open, high, low, close, volume` mais todas as features acima.

---

## Carga

* Realiza a carga dos arquivos transformados em `data/market_data.db` (a partir do MVP3).
* Comportamento:

  * **MVP1–2:** carga opcional apenas usando arquivos CSV.
  * **MVP3+**: UPSERT no SQLite com remoção segura dos arquivos em `data/transformed/`.
* Contém tratamento de duplicatas e índices para acesso rápido.
* Logs detalhados por lote carregado e quantidade de registros inseridos.

---

## Exportação

* Disponível tanto na **CLI** quanto na **GUI** (aba **Exportar**).
* Capaz de filtrar dados por:

  * par
  * timeframe
  * período
  * features selecionadas
* Exporta diretamente para CSV no diretório `data/exported/`.

---

### CLI

* Executa **pipeline completo** ou **etapas isoladas** com parâmetros definidos pelo usuário.
* Permite uso contínuo via automação (ex: scripts externos, crontab).
* Exibe logs estruturados por etapa, com codificação de sucesso/erro.

---

### GUI

* Aplicação desktop PySide6 com abas:

  * **Credenciais**, **Pipeline**, e **Exportar**.
* Esconde campos de login após autenticação bem-sucedida.
* Exibe logs em tempo real e feedback visual (ex: pop-ups).
* Possui ícone próprio (`assets/icone.icns`) para empacotamento.

---

## Arquitetura Completa (Fluxograma em Markdown)

```
               +---------------+
               |     GUI       |
               +-------+-------+
                       |
               +-------v-------+
               |      CLI      |
               +-------+-------+
                       |
               +-------v-------+
               |     MAIN      |
                       |
                       |
   +-------------------+-------------------+
   |                                       |
+--v--+                               +----v----+
|EXTRA|                               | TRANSF. |
|CAO  |                               |ORMACAO |
+--+--+                               +----+----+
   |                                        |
   |                                        |
+--v--------------------+        +----------v-----------------+
|    IQOption API via   |        |  Colunas técnicas e base   |
|    stable_api.py      |        |  geradas com pandas/numpy  |
+-----------------------+        +----------------------------+
   |                                        |
   |                                        |
+--v---------------------------+ +----------v---------------+
| Carga (CSV→DB ou CSV→CSV)   | |   Exportação (DB→CSV)     |
+-----------------------------+ +---------------------------+
```

---

## Pipeline

| Etapa         | Entrada                 | Saída                      | Versão (MVP) |
| ------------- | ----------------------- | -------------------------- | ------------ |
| Extração      | Conexão API             | CSV em `data/raw/`         | 1, 2, 3      |
| Transformação | CSV `data/raw/`         | CSV em `data/transformed/` | 1, 2, 3      |
| Carga         | CSV `data/transformed/` | CSV ou DB (`sqlite`)       | 3+           |
| Exportação    | DB após Carga           | CSV em `data/exported/`    | 3+           |

---

## Critérios de Aceitação por MVP

| Versão     | Critérios                                                                                                            |
| ---------- | -------------------------------------------------------------------------------------------------------------------- |
| **MVP1**   | CLI funcional, coleta e transformação para CSV, logs básicos, escopo inicial definido.                               |
| **MVP2**   | GUI completa, exportação de CSV por GUI, validação de parâmetros, logs visuais.                                      |
| **MVP3**   | Banco SQLite com modo WAL integrado, UPSERT funcional, exportação por filtros, transform `.csv` removido após carga. |
| **MVP3.1** | Documentação refinada, padronização do nome "ETL de Mercado", empacotamento para macOS, Windows, Linux.              |

---

## Versionamento (branches, tags, releases)

### Branches

* **main** — linha estável; recebe apenas merges validados.
* **mvp1** — **MVP 1**: base CLI, extração e transformação com **arquivos CSV** (sem DB).
* **mvp2** — **MVP 2**: GUI + exportação **CSV a partir dos arquivos** transformados (sem DB).
* **mvp3** — **MVP 3**: introdução do **SQLite/WAL**, UPSERT, exportação a partir do DB e limpeza de `transformed/` após carga.
* **mvp3.1** — incrementos pós-MVP3 (documentação, padronização “ETL de Mercado”, empacotamento).
* **hotfix/<descr>** — correções urgentes aplicadas sobre `main`.

### Tags e Releases

* **`v0.1.0` — MVP 1:** CLI operante; extração e transformação para **CSV**; exportação **CSV** baseada em arquivos; logs básicos.
* **`v0.2.0` — MVP 2:** GUI funcional; exportação **CSV** a partir de arquivos transformados; validações e UX.
* **`v0.3.0` — MVP 3:** **SQLite (WAL)** integrado; **UPSERT**; exportação a partir do **DB**; limpeza automática do `transformed/`.
* **`v0.3.1` — MVP 3.1:** padronização do nome **ETL de Mercado**, revisão de docs e **empacotamento** (artefatos anexados à release).

---

## Empacotamento

* Baseado em **PyInstaller**, gera duas distribuições binárias:

  * Linha de comando (`etl-mercado-cli`)
  * Interface gráfica (`etl-mercado-gui`)
* Inclui ícone personalizado (`assets/icone.icns`/`.png`)
* Os binários gerados são anexados nas respectivas **releases** do GitHub (`v0.3.1` e posteriores)
* Garante compatibilidade para:

  * macOS (`.app` e `.zip`)
  * Windows (`.exe`)
  * Linux (`binário ELF`)

---
# **Documento de Escopo do Projeto**

### Projeto: *ETL de Mercado – Extração, Transformação e Carga de Dados Financeiros*

### Versão: 2.2

### Data: [Atualização – Estrutura Final GUI + Arquitetura Modular Consolidada]

### Responsável Técnica: Equipe de Ciência de Dados e Desenvolvimento

---

## **1. Visão Geral**

O **ETL de Mercado** é uma aplicação em **Python 3.12** que automatiza o ciclo completo de **extração**, **transformação** e **carga** de **dados de candles financeiros** provenientes da **API da IQ Option**, com persistência em **SQLite3** e exportação personalizável em **CSV**.

O sistema foi projetado sob uma **arquitetura modular**, com separação clara entre camadas de dados, lógica e interface, oferecendo duas formas de operação:

* **CLI (linha de comando)** para automação e integração.
* **GUI (interface gráfica em PySide6)** com tema escuro profissional (preto/laranja).

A aplicação serve como modelo base para pipelines ETL reutilizáveis e compatíveis com múltiplos provedores de dados.

---

## **2. Objetivos**

### 2.1. Objetivo Geral

Automatizar o fluxo ETL de dados de mercado financeiro, garantindo coleta incremental, armazenamento persistente e exportação flexível em formato estruturado.

### 2.2. Objetivos Específicos

* Extrair candles históricos de múltiplos pares e timeframes via API.
* Realizar transformações com indicadores técnicos essenciais (EMA, RSI, SR, volatilidade).
* Persistir os dados em banco local SQLite no modo WAL.
* Gerar CSVs consolidados, configuráveis por features e período.
* Operar com robustez, controle de duplicação e logs em tempo real.

---

## **3. Arquitetura e Tecnologias**

### 3.1. Estrutura Modular

| Módulo                     | Função                                                        | Local      |
| -------------------------- | ------------------------------------------------------------- | ---------- |
| `scripts/extracao.py`      | Coleta de candles via IQ Option API                           | `/scripts` |
| `scripts/transformacao.py` | Geração de features e cálculo de indicadores técnicos         | `/scripts` |
| `scripts/carga.py`         | Carga incremental no banco SQLite e controle de duplicação    | `/scripts` |
| `scripts/db_manager.py`    | Interface de persistência e exportação de dados               | `/scripts` |
| `main.py`                  | Interface CLI de orquestração completa do pipeline            | Raiz       |
| `gui.py`                   | Interface gráfica moderna (PySide6) com controle total do ETL | Raiz       |

### 3.2. Tecnologias

| Componente    | Tecnologia                     |
| ------------- | ------------------------------ |
| Linguagem     | Python 3.12                    |
| ETL           | pandas, numpy                  |
| Banco Local   | SQLite3 (modo WAL)             |
| Interface     | CLI (argparse) e GUI (PySide6) |
| Empacotamento | PyInstaller / Py2App           |
| API Broker    | IQ Option API                  |
| Configuração  | python-dotenv                  |

---

## **4. Escopo Funcional**

### **4.1 – Estrutura da GUI**

A interface gráfica foi desenvolvida em **PySide6**, com design limpo, tema escuro e acentuação laranja.
Todas as operações ETL podem ser realizadas visualmente, com feedback em tempo real no painel de log.

#### **Abas e Funções**

| Aba                | Função e Recursos Principais                                                                                                                                                                |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Credenciais**    | Autenticação com e-mail e senha da corretora. Botão **“Conectar”** inicia sessão e, após sucesso, oculta os campos. Botão **“Desconectar”** restaura o estado.                              |
| **Pipeline**       | Parâmetros únicos do pipeline: Par, Timeframe, Dias (histórico) e Janela SR. Inclui botões empilhados: **Extração**, **Transformação**, **Carga**, **Pipeline Completo** e **Desconectar**. |
| **Exportar Dados** | Exporta candles do banco SQLite com seleção de Par, Timeframe, Dias e Features. Exibe janela nativa para o usuário escolher onde salvar o CSV.                                              |

#### **Comportamento de Diretórios**

* **`data/raw/`**: armazena apenas **um CSV por par/timeframe**, sobrescrevendo versões antigas.
* **`data/transformed/`**: contém dados transformados **temporariamente**, sendo **apagados após a carga** no banco.
* **`data/exported/`**: destino padrão para exportações manuais (ajustável pelo diálogo de salvamento).
* **`data/market_data.db`**: banco SQLite local persistente.

#### **Validações e Feedback**

* Verificação automática de **colunas e estrutura de CSV** antes da transformação.
* Tratamento explícito de pares inválidos (ex.: alerta “use USDCAD em vez de CADUSD”).
* Logs contínuos e pop-ups de sucesso/erro em todas as operações.
* Conexão pode ser feita com tecla **Enter** após preencher credenciais.

---

## **5. Lógica ETL (Resumo de Operações)**

### **Extração**

* Recolhe dados da API conforme `par`, `timeframe`, `dias`.
* Se já existir histórico no banco, executa **extração incremental**.
* Salva em `data/raw/PAR_TF.csv`, sobrescrevendo arquivos antigos.

### **Transformação**

* Localiza automaticamente o CSV bruto.
* Calcula indicadores técnicos (EMA7, EMA21, RSI14, SR, volatilidade).
* Gera `data/transformed/PAR_TF.csv` (temporário).

### **Carga**

* Lê o CSV transformado e executa **UPSERT incremental** no SQLite.
* Após a carga, limpa automaticamente `data/transformed/`.

### **Pipeline Completo**

* Executa **Extração → Transformação → Carga** em sequência.
* Apresenta logs e pop-up de conclusão.
* Bloqueia execução se algum estágio anterior falhar.

### **Exportar Dados**

* Lê do banco `data/market_data.db`.
* Permite escolher Features e período (em dias).
* Abre diálogo nativo para o usuário selecionar onde salvar o arquivo CSV.

---

## **6. Persistência e Banco de Dados**

| Tabela             | Finalidade                   | Principais Campos                                                        |
| ------------------ | ---------------------------- | ------------------------------------------------------------------------ |
| `candles`          | Armazena candles brutos      | pair, timeframe_s, ts, abertura, máxima, mínima, fechamento, volume      |
| `candles_features` | Armazena dados transformados | pair, timeframe_s, ts, ema7, ema21, rsi14, volatilidade, sr_high, sr_low |
| `extractions`      | Registro de execuções ETL    | run_id, pair, timeframe_s, from_ts, to_ts, rows_saved, created_at        |

**Funções principais (`db_manager.py`):**

* `init_db()` – inicializa banco e tabelas.
* `get_conn()` – fornece conexão segura (modo WAL).
* `upsert_candles()` – inserção incremental sem duplicatas.
* `get_last_timestamp()` – timestamp máximo para controle incremental.
* `export_to_csv()` – exporta datasets filtrados, integrando features.

---

## **7. Requisitos Não Funcionais**

| Categoria       | Requisito                                            |
| --------------- | ---------------------------------------------------- |
| Código          | Conformidade PEP8 e modularidade                     |
| Compatibilidade | macOS, Windows e Linux                               |
| Performance     | < 5 minutos para 300 dias (timeframe M5)             |
| Segurança       | Credenciais locais (.env) e ocultação na GUI         |
| UX              | Tema escuro responsivo com destaque laranja          |
| Robustez        | Validação de dados, logs contínuos e rollback seguro |
| Portabilidade   | Empacotamento autônomo com PyInstaller / Py2App      |

---

## **8. Cronograma de Entregas**

| Fase  | Entrega Principal                  | Duração   |
| ----- | ---------------------------------- | --------- |
| MVP 1 | CLI modular e banco SQLite         | 2 semanas |
| MVP 2 | GUI completa (tema preto/laranja)  | 3 semanas |
| MVP 3 | Persistência final + empacotamento | 2 semanas |

---

## **9. Critérios de Sucesso**

* Pipeline ETL executável ponta a ponta via CLI e GUI.
* Armazenamento incremental sem duplicação.
* Exportação flexível e interface responsiva.
* Logs e alertas em todas as etapas.
* Estrutura modular e reutilizável para novos projetos.

---

## **10. Encerramento**

Esta versão **2.2** consolida a **arquitetura final e estável** do *ETL de Mercado*, unindo robustez técnica e interface fluida em um pipeline modular e automatizado.
O projeto reflete a maturidade do ciclo ETL, com controle completo de extração, transformação, carga e exportação — pronto para empacotamento e uso profissional.


