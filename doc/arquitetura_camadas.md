===========================================================
                 ENGENHARIA DE CAMADAS
             Sistema ETL de Mercado Financeiro
===========================================================

+-----------------------------------------------------------+
|                     CAMADA 1 — INTERFACE (UI)             |
|-----------------------------------------------------------|
| [ gui.py ]                                                |
|  → Interface PySide6 com abas: Credenciais, Pipeline,     |
|    Exportar Dados.                                        |
|  → Executa pipeline completo ou etapas isoladas.           |
|                                                           |
| [ cli.py ]                                                |
|  → Alternativa por linha de comando.                      |
|  → Permite executar o pipeline sem GUI.                   |
+-----------------------------------------------------------+
                              │
                              ▼
+-----------------------------------------------------------+
|                 CAMADA 2 — ORQUESTRAÇÃO                   |
|-----------------------------------------------------------|
| [ main.py ]                                               |
|  → Ponto de entrada do sistema.                           |
|  → Coordena o fluxo ETL: extrair → transformar → carregar  |
|    → exportar.                                             |
|  → Chama funções dos módulos em /scripts.                 |
+-----------------------------------------------------------+
                              │
                              ▼
+-----------------------------------------------------------+
|            CAMADA 3 — REGRAS DE NEGÓCIO (ETL)             |
|-----------------------------------------------------------|
| [ scripts/extracao.py ]                                   |
|  → Conecta na IQ Option API.                              |
|  → Coleta candles e salva em data/raw/<PAR>_<TF>.csv.     |
|                                                           |
| [ scripts/transformacao.py ]                              |
|  → Lê data/raw, calcula indicadores técnicos:              |
|      EMA7, EMA21, RSI14, SR e volatilidade.               |
|  → Salva resultado em data/transformed/<PAR>_<TF>.csv.    |
|                                                           |
| [ scripts/carga.py ]                                      |
|  → Lê arquivos transformados.                             |
|  → Insere ou atualiza candles no banco SQLite via          |
|    db_manager.upsert().                                   |
|  → Limpa data/transformed após carga.                     |
|                                                           |
| [ scripts/db_manager.py ]                                 |
|  → Funções de exportação (export_to_csv).                 |
|  → Acesso direto ao banco SQLite.                         |
+-----------------------------------------------------------+
                              │
                              ▼
+-----------------------------------------------------------+
|            CAMADA 4 — ACESSO A DADOS (DATA LAYER)         |
|-----------------------------------------------------------|
| [ scripts/db_manager.py ]                                 |
|  → init_db() — Cria tabelas e índices.                    |
|  → upsert() — Insere/atualiza candles.                    |
|  → get_last_timestamp() — Consulta incremental.            |
|  → export_to_csv() — Exporta para CSV.                    |
|  → Usa SQLite local: data/market_data.db (modo WAL).       |
+-----------------------------------------------------------+
                              │
                              ▼
+-----------------------------------------------------------+
|           CAMADA 5 — INFRA / INTEGRAÇÕES EXTERNAS         |
|-----------------------------------------------------------|
| [ iqoptionaapi/ ]                                         |
|  → SDK customizado da IQ Option (autenticação e dados).   |
|                                                           |
| File System                                               |
|  → data/raw/ → CSVs brutos extraídos.                     |
|  → data/transformed/ → CSVs transformados (temporários).  |
|  → data/exported/ → CSVs exportados da base.              |
|                                                           |
| [ data/market_data.db ]                                   |
|  → Banco SQLite local para persistência final.            |
+-----------------------------------------------------------+

===========================================================
                SUPORTE E UTILITÁRIOS
===========================================================
| [ .env ] → credenciais e parâmetros                      |
| [ assets/icone.png / icone.icns ] → ícones do app        |
| [ requirements.txt ] → dependências                      |
| [ pyproject.toml ] → metadados do projeto                |
| [ doc/escopo.md ] → documentação funcional               |
===========================================================


FLUXO GERAL DO SISTEMA
-----------------------------------------------------------
[ GUI (gui.py) / CLI (cli.py) ]
          │
          ▼
[ MAIN (main.py) ]
          │
          ├──► [ Extração (scripts/extracao.py) ]
          │         ↓
          │         IQ Option API → data/raw/*.csv
          │
          ├──► [ Transformação (scripts/transformacao.py) ]
          │         ↓
          │         data/raw → indicadores → data/transformed
          │
          ├──► [ Carga (scripts/carga.py) ]
          │         ↓
          │         data/transformed → SQLite (db_manager)
          │
          └──► [ Exportação (scripts/db_manager.py) ]
                    ↓
                    data/exported/*.csv
-----------------------------------------------------------

