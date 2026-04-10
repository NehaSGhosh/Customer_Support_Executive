# Customer Support Multi-Agent System

A practical Generative AI project for the TCS pre-qualification assignment. The system answers customer-support questions over:
- **Structured data** in SQLite (customers, tickets, refunds)
- **Unstructured policy PDFs** in a FAISS vector store
- **Multi-agent orchestration** using LangGraph
- **MCP server** exposing tools for SQL lookup and policy retrieval
- **UI** with Streamlit

This directly maps to the assignment requirements for natural language querying over SQL data and policy PDFs, plus LangChain/LangGraph, SQL DB, Vector DB, MCP server, and a UI. See the uploaded assignment PDF for the required scope. 

## Architecture

```text
Streamlit UI
   -> LangGraph Orchestrator
      -> Intent Router
      -> SQL Agent / Tool
      -> Policy RAG Agent / Tool
      -> Answer Synthesizer

Shared Resources:
- SQLite database: structured customer data
- FAISS vector store: embedded PDF chunks
- MCP server: exposes sql_lookup and policy_search tools
```

## Project structure

```text
app/
  config.py
  llm.py
  state.py
  graph.py
  retriever.py
  db.py
  mcp_server.py
  tools/
    sql_tool.py
    policy_tool.py
    response_tool.py
scripts/
  setup_data.py
  ingest_policies.py
streamlit_app.py
requirements.txt
.env.example
```

## Quick start

### 1) Create environment and install
```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# add OPENAI_API_KEY to .env
```

### 2) Generate synthetic SQL data and sample PDFs
```bash
python scripts/setup_data.py
```
psql -U postgres -f setup_database.sql -v customers_path="C:/path/to/customers_clean.csv" -v orders_path="C:/path/to/orders_clean.csv" -v tickets_path="C:/path/to/support_tickets_clean.csv"
This creates:
- `data/support.db`
- sample policy PDFs under `policies/`

### 3) Ingest PDFs into FAISS
```bash
python -m scripts.ingest_policies
```

This creates:
- `data/faiss_index/`

### 4) Run the Streamlit UI
```bash
streamlit run streamlit_app.py
```

### 5) Run the MCP server
```bash
python -m app.mcp_server
```

## Example questions
- What is the current refund policy?
- Give me a quick overview of customer Ema Johnson's profile and past support ticket details.
- Does Ema's latest complaint qualify for refund under the current refund policy?

## Methodology / design choices
- **SQLite** for fast prototype setup. In production, this can be PostgreSQL or MySQL.
- **FAISS** for a local vector DB. In production, this can be Pinecone, Weaviate, or Azure AI Search.
- **LangGraph** for explicit control over routing and multi-step execution.
- **MCP** for tool standardization and separation between the agent and external capabilities.

## Tradeoffs
- Multi-agent orchestration is more modular and explainable than a single monolithic prompt, but adds some latency.
- Rule-based intent routing is simpler and faster, but LLM-based routing handles more natural variations. This project uses a lightweight hybrid approach.
- Local FAISS is quick for demonstration, but managed vector stores scale better in production.

## Demo video checklist
Use these steps in your demo recording:
1. Show generated tables in `data/support.db`
2. Show sample PDFs under `policies/`
3. Run `python scripts/ingest_policies.py`
4. Run Streamlit app
5. Ask one policy-only, one SQL-only, and one hybrid question
6. Optionally show MCP server startup command

## Notes for interview / submission
If time is limited, submit the GitHub repo with:
- working code
- README
- short Loom video URL added into README after recording

