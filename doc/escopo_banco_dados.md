# Escopo do Banco de Dados (MVP3)

## 1. Objetivo

Integrar um **banco de dados SQLite** ao projeto ETL de Mercado para armazenar candles e dados transformados, permitindo consultas rápidas, reprocessamentos incrementais e exportação direta pela interface.

O banco substituirá o uso exclusivo de CSVs como fonte de dados, mantendo compatibilidade com o formato atual.

---

## 2. Arquivo e Conexão

* **Arquivo:** `data/market_data.db`
* **Banco:** SQLite com **modo WAL** habilitado para melhor desempenho.
* **Acesso:** via módulo `db_manager.py`, centralizando leitura e escrita.

---

## 3. Esquema de Dados

### 3.1. Tabela `candles`

Tabela principal para armazenamento dos candles brutos extraídos da corretora.

**Colunas:**

| Campo       | Tipo    | Origem     | Descrição                               |
| ----------- | ------- | ---------- | --------------------------------------- |
| pair        | TEXT    | -          | Ativo (ex: EURJPY)                      |
| timeframe_s | INTEGER | -          | Timeframe em segundos (ex: 300 para M5) |
| ts          | INTEGER | from       | Timestamp UNIX (UTC)                    |
| abertura    | REAL    | abertura   | Preço de abertura                       |
| maxima      | REAL    | maxima     | Preço máximo                            |
| minima      | REAL    | minima     | Preço mínimo                            |
| fechamento  | REAL    | fechamento | Preço de fechamento                     |
| volume      | REAL    | volume     | Volume negociado                        |
| source      | TEXT    | -          | Origem dos dados (padrão: iqoption)     |

**Restrições:**

* `UNIQUE (pair, timeframe_s, ts)` para evitar duplicatas.

**Índice:**

* `(pair, timeframe_s, ts)` para buscas rápidas.

---

### 3.2. Tabela `candles_features` (opcional)

Tabela para armazenar os candles já transformados, contendo features técnicas.

**Colunas:**

| Campo                                             | Tipo    | Descrição                     |
| ------------------------------------------------- | ------- | ----------------------------- |
| pair                                              | TEXT    | Par de moedas                 |
| timeframe_s                                       | INTEGER | Timeframe em segundos         |
| ts                                                | INTEGER | Timestamp (UTC)               |
| ema7, ema21, rsi14, volatilidade, sr_low, sr_high | REAL    | Indicadores calculados        |
| features_ver                                      | TEXT    | Versão do cálculo de features |

**Restrições:**

* `UNIQUE (pair, timeframe_s, ts)`

---

### 3.3. Tabela `extractions` (opcional)

Registro de cada execução de extração para auditoria e controle de incrementos.

**Colunas:**

| Campo       | Tipo    | Descrição                  |
| ----------- | ------- | -------------------------- |
| run_id      | TEXT    | Identificador único (UUID) |
| pair        | TEXT    | Par extraído               |
| timeframe_s | INTEGER | Timeframe                  |
| from_ts     | INTEGER | Início da coleta           |
| to_ts       | INTEGER | Fim da coleta              |
| rows_saved  | INTEGER | Linhas inseridas           |
| created_at  | INTEGER | Data de criação            |

---

## 4. Política de Escrita

* Inserção **incremental** com `UPSERT` ("INSERT ... ON CONFLICT DO NOTHING").
* Escrita em **lotes** de 5.000 linhas com transação aberta.
* Evita duplicatas e garante idempotência das operações.

---

## 5. Integração com o ETL

### Extração

1. Extrai os dados da API IQ Option.
2. Salva o CSV em `data/raw/`.
3. Persiste no banco via `db_manager.upsert_candles()`.
4. Caso já existam candles para o par/timeframe, o sistema continua a partir do `MAX(ts)` existente.

### Transformação

* Leitura preferencial do banco (`SELECT * FROM candles WHERE pair=? AND timeframe_s=?`).
* Escrita opcional em `candles_features`.
* Exportação em CSV sob demanda.

### CLI e GUI

* CLI: comandos `--extrair` e `--transformar` passam a gravar no banco.
* GUI: nova aba **"Banco de Dados"** com estatísticas, exportação e backup do `.db`.

---

## 6. Operações e Manutenção

* **Backup:** cópia automática para `data/backups/`.
* **VACUUM:** limpeza periódica automática ou via GUI.
* **Compatibilidade:** CSV continua funcionando como opção de exportação.

---

## 7. Entregáveis

* Banco criado automaticamente em `data/market_data.db`.
* Integração com o pipeline ETL (extração + transformação).
* GUI atualizada com aba **Banco de Dados**.
* Testes de inserção e leitura validados.
* Tag de release: **v0.3.0-mvp3**.



---

