# Escopo do Banco de Dados (MVP3)

## 1. Objetivo

Integrar um **banco de dados SQLite** ao projeto **ETL de Mercado** para armazenar candles brutos e dados transformados, permitindo **consultas rápidas**, **extrações incrementais** e **exportações diretas** pela interface gráfica.

O banco substitui o uso isolado de arquivos CSV, mantendo compatibilidade total com o formato e garantindo persistência local em disco.

---

## 2. Arquivo e Conexão

- **Arquivo:** `data/market_data.db`  
- **Banco:** SQLite3 com **modo WAL (Write-Ahead Logging)** ativado.  
- **Acesso:** via módulo centralizado `scripts/db_manager.py`.  

A conexão é aberta e encerrada de forma segura em cada operação, com controle de transação e rollback automático em caso de falha.

---

## 3. Esquema de Dados

### 3.1. Tabela `candles`

Tabela principal para armazenar candles brutos extraídos da IQ Option.

| Campo       | Tipo    | Origem     | Descrição                               |
| ------------ | ------- | ---------- | --------------------------------------- |
| pair         | TEXT    | API        | Ativo (ex: EURJPY, USDCAD)              |
| timeframe_s  | INTEGER | API        | Timeframe em segundos (ex: 300 para M5) |
| ts           | INTEGER | API        | Timestamp UNIX UTC                      |
| abertura     | REAL    | API        | Preço de abertura                       |
| maxima       | REAL    | API        | Preço máximo                            |
| minima       | REAL    | API        | Preço mínimo                            |
| fechamento   | REAL    | API        | Preço de fechamento                     |
| volume       | REAL    | API        | Volume negociado                        |
| source       | TEXT    | Sistema    | Origem dos dados (padrão: iqoption)     |

**Restrições:**
- `UNIQUE (pair, timeframe_s, ts)` para evitar duplicatas.  

**Índices:**
- Índice principal: `(pair, timeframe_s, ts)` para buscas e joins rápidos.  

---

### 3.2. Tabela `candles_features`

Tabela de armazenamento dos candles transformados, incluindo indicadores técnicos e métricas derivadas.

| Campo         | Tipo    | Descrição                                 |
| -------------- | ------- | ----------------------------------------- |
| pair           | TEXT    | Par de moedas                             |
| timeframe_s    | INTEGER | Timeframe em segundos                     |
| ts             | INTEGER | Timestamp UNIX UTC                        |
| ema7           | REAL    | Média móvel exponencial de 7 períodos     |
| ema21          | REAL    | Média móvel exponencial de 21 períodos    |
| rsi14          | REAL    | Índice de Força Relativa (14 períodos)    |
| volatilidade   | REAL    | Desvio percentual de variação dos candles |
| sr_low         | REAL    | Nível de suporte identificado             |
| sr_high        | REAL    | Nível de resistência identificado         |
| features_ver   | TEXT    | Versão do cálculo de features             |

**Restrições:**
- `UNIQUE (pair, timeframe_s, ts)`

**Observações:**
- Atualizada somente após execução da transformação (`scripts/transformacao.py`).
- Pode ser limpa ou recalculada conforme versão de features.

---

### 3.3. Tabela `extractions`

Tabela de auditoria e histórico de execuções ETL.  
Armazena dados sobre cada execução de extração.

| Campo       | Tipo    | Descrição                              |
| ------------ | ------- | -------------------------------------- |
| run_id       | TEXT    | Identificador único (UUID)             |
| pair         | TEXT    | Par de moedas                          |
| timeframe_s  | INTEGER | Timeframe em segundos                  |
| from_ts      | INTEGER | Timestamp inicial da coleta            |
| to_ts        | INTEGER | Timestamp final da coleta              |
| rows_saved   | INTEGER | Número de registros inseridos          |
| created_at   | INTEGER | Data e hora de execução (timestamp UTC) |

**Restrições:**
- `UNIQUE (run_id)`

---

## 4. Política de Escrita

- Inserção **incremental** com `UPSERT` (`INSERT ... ON CONFLICT DO NOTHING`).  
- Escrita em **batches** de até 5.000 registros com transação aberta.  
- Garantia de **idempotência** (execuções repetidas não duplicam dados).  
- Uso de **savepoints** internos para rollback parcial em caso de falha.  

---

## 5. Integração com o ETL

### **Extração (`scripts/extracao.py`)**
1. Coleta candles da IQ Option API.  
2. Gera CSV em `data/raw/`.  
3. Envia para o banco via `db_manager.upsert_candles()`.  
4. Caso já exista histórico, coleta apenas registros com `ts > MAX(ts)`.

### **Transformação (`scripts/transformacao.py`)**
1. Lê candles diretamente do banco (`SELECT * FROM candles ...`).  
2. Calcula indicadores técnicos (EMA, RSI, SR, volatilidade).  
3. Salva resultados temporários em `data/transformed/` e opcionalmente na tabela `candles_features`.

### **Carga (`scripts/carga.py`)**
1. Lê CSV transformado (caso não tenha sido inserido diretamente).  
2. Realiza `UPSERT` no banco.  
3. Apaga os arquivos temporários após conclusão bem-sucedida.  

### **Exportação (`db_manager.export_to_csv`)**
1. Consulta o banco conforme par, timeframe e filtros selecionados.  
2. Gera CSV em `data/exported/` ou no local escolhido via diálogo GUI.  

---

## 6. Operações e Manutenção

| Função                     | Descrição                                                                 |
| --------------------------- | ------------------------------------------------------------------------ |
| `init_db()`                 | Cria tabelas e índices necessários.                                      |
| `get_last_timestamp()`      | Retorna o timestamp mais recente por par/timeframe.                      |
| `upsert_candles()`          | Insere novos candles ou ignora duplicados.                              |
| `export_to_csv()`           | Exporta candles e features filtrados.                                   |
| `vacuum_db()` *(futuro)*    | Executa limpeza (`VACUUM`) para reduzir fragmentação.                   |
| `backup_db()` *(futuro)*    | Cria cópia do banco em `data/backups/market_data_<data>.db`.            |

---

## 7. Integração com Interface

### **GUI (`gui.py`)**
- O pipeline completo (`Extração → Transformação → Carga`) insere dados diretamente no banco.
- O botão **Exportar Dados** utiliza a função `export_to_csv()` do `db_manager`.
- Logs de escrita no banco aparecem em tempo real no painel de status.

### **CLI (`main.py` / `cli.py`)**
- Argumentos `--extrair`, `--transformar`, `--carga`, `--pipeline` executam as etapas ETL.
- Todas as operações de escrita e leitura passam pelo `db_manager`.

---

## 8. Backup e Recuperação

- **Backups automáticos** criados em `data/backups/` a cada exportação ou operação manual.  
- **VACUUM automático** opcional após grandes inserções (> 500.000 registros).  
- **Restaurar banco**: substituir manualmente `market_data.db` por qualquer backup.  

---

## 9. Entregáveis

- Banco SQLite criado automaticamente em `data/market_data.db`.  
- Integração completa com o pipeline ETL (Extração, Transformação, Carga).  
- Exportação nativa via GUI e CLI.  
- Backup automático e manutenção simplificada.  
- Testes unitários validados para inserção, leitura e exportação.  
- Tag de release: **v3.0 – MVP3 (Banco de Dados Integrado e GUI Final)**

---
