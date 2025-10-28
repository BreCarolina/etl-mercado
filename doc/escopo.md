

# **Documento de Escopo do Projeto**

### Projeto: *ETL de Mercado – Coleta, Transformação e Carga de Dados Financeiros*  
### Versão: 1.1  
### Data: [Planejamento Inicial]  
### Responsável Técnica: Equipe de Ciência de Dados e Desenvolvimento  

---

## **1. Visão Geral**

O **ETL de Mercado** é uma aplicação desktop multiplataforma desenvolvida em **Python 3.12** que automatiza a coleta, transformação e persistência de **dados de candles financeiros** obtidos via **API da corretora IQ Option**.

A ferramenta visa oferecer uma solução de fácil uso para analistas e traders, permitindo criar datasets prontos para **modelagem preditiva** ou análise exploratória, com foco em automação e reprodutibilidade.

O projeto será desenvolvido de forma incremental (MVPs), com entregas progressivas, testáveis e tecnicamente documentadas.

---

## **2. Objetivos**

### 2.1. Objetivo Geral
Desenvolver uma aplicação local capaz de **extrair dados de mercado em tempo real**, **transformá-los automaticamente** e **armazená-los de forma persistente** para uso em análises e modelos preditivos.

### 2.2. Objetivos Específicos
- Extrair e armazenar candles de ativos financeiros via API.  
- Aplicar transformações e cálculos de indicadores técnicos (EMA, RSI, SR, volatilidade).  
- Fornecer uma interface gráfica intuitiva (PySide6) para operação manual.  
- Garantir persistência de dados incremental em banco **SQLite3**.  
- Permitir exportação de datasets em **CSV**.  
- Empacotar a aplicação como executável autônomo para macOS e Windows.  

---

## **3. Arquitetura e Tecnologias**

### 3.1. Estrutura Modular
O sistema será organizado em camadas independentes e reutilizáveis:

| Camada | Função Principal |
|--------|------------------|
| **Extração** | Comunicação com API e coleta de candles |
| **Transformação** | Cálculo de indicadores e limpeza de dados |
| **Persistência** | Salvamento incremental em CSV e SQLite |
| **Interface (GUI/CLI)** | Interação com o usuário |
| **Empacotamento** | Geração de executável desktop autônomo |

### 3.2. Tecnologias Base
| Componente | Tecnologia |
|-------------|-------------|
| Linguagem | Python 3.12 |
| Interface | PySide6 (Qt) |
| ETL | pandas, numpy |
| Configuração | python-dotenv |
| Banco Local | SQLite3 |
| Empacotamento | PyInstaller / Py2App |
| API Broker | IQ Option API |

---

## **4. Escopo Funcional por Etapa (MVPs)**

### **MVP 1 – CLI Funcional (Protótipo Técnico)**
**Objetivo:** validar a pipeline de extração e transformação de dados em ambiente de terminal.

#### Entregas:
1. **Extração (`extrair_dados.py`)**
   - Conexão com API da IQ Option.  
   - Parâmetros: `par`, `timeframe`, `dias`.  
   - Geração de arquivo CSV em `data/raw/`.  
   - Logs detalhados no terminal.

2. **Transformação (`transformar_dados.py`)**
   - Leitura de CSV bruto.  
   - Cálculo de indicadores (EMA, RSI, Volatilidade, SR).  
   - Normalização e limpeza.  
   - Salvamento em `data/transformed/`.

3. **Interface de Linha de Comando (`cli.py` / `main.py`)**
   - Execuções possíveis:
     ```
     python main.py --extrair
     python main.py --transformar
     python main.py --pipeline
     ```
   - Logs coloridos e estruturados.

#### Critérios de Aceitação:
- Execução sem falhas em extração e transformação.  
- Geração correta de arquivos CSV.  
- Execução média < 5 minutos para 300 dias (M5).  

---

### **MVP 2 – Interface Gráfica (PySide6)**
**Objetivo:** permitir operação por interface desktop, sem depender do terminal.

#### Entregas:
1. **Interface Qt (`gui.py`)**
   - Layout moderno (tema escuro preto/laranja).  
   - Ícone próprio (`assets/icone.icns`).  
   - Login via credenciais IQ Option (manual ou `.env`).  
   - Abas funcionais:
     - **Extração:** parâmetros (ativo, timeframe, dias).  
     - **Transformação:** seleção de arquivo e execução.  
     - **Pipeline:** execução completa (extração + transformação).  
     - **Arquivos:** listagem, abertura e gerenciamento.  

2. **Funcionalidades**
   - Logs em tempo real exibidos na interface.  
   - Status de conexão dinâmico (conectado / erro).  
   - Mensagens modais de sucesso ou falha.  
   - Atualização automática da aba “Arquivos”.  
   - Abertura direta de pastas no sistema operacional.

3. **UX e Design**
   - Layout responsivo e escalável.  
   - Paleta e tipografia consistentes.  
   - Feedback visual em todos os botões.

#### Critérios de Aceitação:
- Interface executa as três rotinas sem erros.  
- Status e logs atualizam em tempo real.  
- Navegação fluida e sem travamentos.  

---

### **MVP 3 – Banco de Dados e Distribuição**

#### **3.1 – Persistência com SQLite**
**Objetivo:** permitir salvamento incremental e persistente dos candles.

#### Entregas:
1. Banco local criado automaticamente:
````

data/market_data.db

```
2. Tabelas por par/timeframe:
```

candles_EURJPY_M5
candles_USDJPY_M1

```
3. Estrutura de campos:
| Campo | Tipo | Descrição |
|--------|------|------------|
| id | INTEGER | PK |
| timestamp | TEXT | UTC |
| open | REAL | Abertura |
| high | REAL | Máxima |
| low | REAL | Mínima |
| close | REAL | Fechamento |
| volume | REAL | Volume |
| extracao_id | TEXT | Identificador da sessão |

4. Módulo `db_manager.py`:
- `init_db()` – inicializa banco.  
- `save_candles()` – grava incrementalmente.  
- `get_last_timestamp()` – busca último registro.  
- `export_to_csv()` – exporta dataset.  

5. Aba “Banco de Dados” na GUI:
- Lista de tabelas disponíveis.  
- Contagem de registros.  
- Botões: *Exportar CSV*, *Abrir pasta*, *Limpar tabela*.  

#### Critérios de Aceitação:
- Inserções incrementais sem duplicatas.  
- Exportação funcional via interface.  
- Consultas instantâneas (< 1s).  

---

#### **3.2 – Empacotamento e Distribuição**
**Objetivo:** criar executáveis autônomos para distribuição local.

#### Entregas:
- **macOS:** `ETL_de_Mercado.app` via Py2App  
- **Windows/Linux:** `ETL_de_Mercado.exe` via PyInstaller  
- Inclusões:
- Ícone, assets e `.env`  
- Banco SQLite integrado  
- Criação automática de pastas `data/` no primeiro uso  

#### Critérios de Aceitação:
- Execução com duplo clique.  
- Sem necessidade de instalação de dependências externas.  
- Logs e banco persistentes entre sessões.  

---

## **5. Requisitos Não Funcionais**

| Categoria | Requisito |
|------------|------------|
| **Código** | Seguir padrão PEP8 e docstrings completas |
| **Compatibilidade** | macOS, Windows e Linux |
| **Operação** | Offline após autenticação inicial |
| **Logs** | Padronizados e legíveis |
| **Tolerância a Falhas** | Tentativas automáticas de reconexão em erros de rede |
| **Performance** | Processamento em < 5 min para 300 dias M5 |
| **Segurança** | Credenciais armazenadas apenas localmente (.env) |

---

## **6. Cronograma Iterativo**

| Fase | Entregas Principais | Duração Estimada |
|------|----------------------|------------------|
| MVP 1 | Pipeline CLI completa | 2 semanas |
| MVP 2 | Interface gráfica integrada | 3 semanas |
| MVP 3.1 | Banco de dados SQLite | 2 semanas |
| MVP 3.2 | Empacotamento final | 1 semana |

---

## **7. Critérios de Sucesso**

- Aplicação extrai, transforma e armazena dados de qualquer ativo disponível.  
- Interface intuitiva e estável, acessível a usuários sem experiência técnica.  
- Pipeline ETL automatizada, testável e modular.  
- Banco de dados local persistente e exportável.  
- Aplicação distribuível sem dependências externas.  

---


## **8. Encerramento**

Este documento formaliza a visão técnica, os objetivos e as entregas do **ETL de Mercado**, garantindo rastreabilidade e clareza entre desenvolvimento, testes e implantação.  
Serve como **referência de engenharia e gestão técnica**, norteando a evolução futura do produto e suas integrações com sistemas analíticos.

---