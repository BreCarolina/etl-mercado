

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


