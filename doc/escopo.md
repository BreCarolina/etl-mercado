

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


