# Enterprise AI Admin Copilot — Operations Intelligence System

> AI-powered system that uses agentic workflows and tool orchestration to debug enterprise systems and propose safe actions.

[![tests](https://img.shields.io/badge/tests-67%20passing-brightgreen)](backend/tests) [![python](https://img.shields.io/badge/python-3.12-blue)](backend/requirements.txt) [![llm](https://img.shields.io/badge/LLM-Gemini%202.5-orange)](https://aistudio.google.com/apikey) [![license](https://img.shields.io/badge/license-MIT-lightgrey)](#)

Natural-language queries about users, jobs, and system state, answered with a **tool-usage trace** and a **typed action proposal**. Built on a Planner → Executor → Synthesizer agent with an explicit evaluation harness. Zero hallucinated IDs on the demo fixture set.

---

## Demo

<img width="1919" height="966" alt="image" src="https://github.com/user-attachments/assets/e9ed6be4-2285-4952-89a1-5455d77efe17" />
***
<img width="1918" height="952" alt="image" src="https://github.com/user-attachments/assets/b82b8ba0-4a91-43ca-91cf-db99c1619dbe" />
***
<img width="1919" height="973" alt="image" src="https://github.com/user-attachments/assets/717a77af-abf5-4113-886d-a8eab71e2a2c" />
***
<img width="1909" height="973" alt="image" src="https://github.com/user-attachments/assets/fe2d9dcf-503f-469d-8cca-818f0d59f7f6" />
***

- **Chat pane** — natural-language input, assistant bubbles with inline action cards.
- **Reasoning panel** — execution-graph timeline of tool calls with per-step latency.
- **Trace panel** — full tool args, result counts, per-entry `result_preview` chips.
- **Sources panel** — every data plane cited, grouped by kind (`users_table`, `jobs_table`, `logs`, `rag`).
- **Action card** — structured `{action, params}` with an `Execute` button that posts directly to `/action`.

---

## Architecture

```
┌──────────┐  POST /query   ┌──────────┐  invoke({query})   ┌─────────────┐
│  React   │ ─────────────> │ FastAPI  │ ──────────────────>│ _TimedAgent │
│   UI     │                │  router  │                    │  (metrics   │
└──────────┘                └──────────┘                    │   wrapper)  │
                                                            └──────┬──────┘
                                                                   │
                                   ┌─── mock mode ───┐             │
                                   │                 │             ▼
                                   │  MockAgent      │       ┌──────────────┐
                                   │  (rule-based,   │◄──────┤  get_agent() │──────►┌──────────────────────┐
                                   │  offline)       │       └──────────────┘       │ GeminiAgent          │
                                   └─────────────────┘                              │ (ChatGoogleGenerative│
                                                                                    │  AI + tool-calling)  │
                                                                                    └──────────┬───────────┘
                                                                                               │
                               ┌───────────────────────────────────────────────────────────────┤
                               │                         Tools                                  │
                               ├───────────────────────────────────────────────────────────────┤
                               │  query_db        →  SQLite (users, jobs)                      │
                               │  fetch_logs      →  SQLite (logs table, live)                 │
                               │  retrieve_context →  FAISS + Gemini embeddings                │
                               │  trigger_action  →  NEVER called during /query (proposal only)│
                               └───────────────────────────────────────────────────────────────┘
                                                              │
                                                              ▼
                                            QueryResponse {answer, reasoning, sources,
                                                           trace, suggested_action, metrics}
                                                              │
                                                              ▼
                                         ┌────────────────────────────────┐
                                         │  Operator reviews, clicks      │
                                         │  Execute → POST /action        │
                                         │  (audit + idempotency)         │
                                         └────────────────────────────────┘
```
---

## Key features

| Feature | Where |
|---|---|
| **Dual agent backend** (Gemini real / mock fallback behind one `get_agent()`) | [backend/app/agent/agent.py](backend/app/agent/agent.py) |
| **Tool-calling agent** with LangChain `create_tool_calling_agent` + Gemini 2.5 | [backend/app/agent/gemini_agent.py](backend/app/agent/gemini_agent.py) |
| **Deterministic classifier + planner** (fetch_logs → query_db → retrieve_context) with service-aware entity extraction | [backend/app/agent/mock_agent.py](backend/app/agent/mock_agent.py) |
| **Strict system prompt** enforcing log-first, RAG-as-fallback, no-hallucination, insufficient-data rules | [backend/app/agent/prompts.py](backend/app/agent/prompts.py) |
| **Structured trace** with `tool`, `args`, `result_count`, `result_preview[]` | [backend/app/agent/_format.py](backend/app/agent/_format.py) |
| **Action safety boundary** — agent proposes, `/action` executes | [backend/app/routes/action.py](backend/app/routes/action.py) |
| **Live log ingestion** — `POST /ingest/log` appends to the DB agent reads from | [backend/app/routes/ingest.py](backend/app/routes/ingest.py) |
| **Per-response evaluation metrics** (tool_correctness, grounding_score, hallucination_risk) | [backend/app/eval/metrics.py](backend/app/eval/metrics.py) |
| **RAG over RBAC + runbooks** with FAISS, Gemini embeddings, mode-aware index dirs | [backend/app/rag/](backend/app/rag/) |
| **67 passing tests** covering tools, agent, API, ingestion, and eval — all run offline | [backend/tests/](backend/tests/) |

---

## Example query

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Why did user U002 lose access?"}'
```

Response:

```json
{
  "answer": "User U002 (Bob Chen) has status='suspended' and role='intern'. Account is currently suspended — this is why access was lost. Audit event: \"Role intern denied access to user_data\" at 2026-04-23T09:30:00. Recent denial: \"Login attempt denied: account suspended\" at 2026-04-23T10:05:00.",
  "reasoning": "Intent classified as: user_issue.\nStep 1 (priority 1, fetch_logs): {'user_id': 'U002', 'limit': 10} -> 4 log entries.\nStep 2 (priority 2, query_db): filters={'id': 'U002'} -> 1 row(s).\nStep 3: Composed grounded answer.",
  "sources": ["logs:user=U002", "users_table:U002"],
  "trace": [
    {
      "tool": "fetch_logs",
      "args": {"user_id": "U002", "limit": 10},
      "result_count": 4,
      "result_preview": [
        "ERROR@2026-04-23T10:05:00",
        "ERROR@2026-04-23T10:00:00",
        "WARN@2026-04-23T09:30:00",
        "WARN@2026-04-22T14:30:00"
      ]
    },
    {
      "tool": "query_db",
      "args": {"table": "users", "filters": {"id": "U002"}, "limit": 1},
      "result_count": 1,
      "result_preview": ["U002"]
    }
  ],
  "suggested_action": {"action": "unsuspend_user", "params": {"user_id": "U002"}},
  "executed": false,
  "metrics": {
    "latency_ms": 8,
    "tools_called": 2,
    "tool_correctness": 1.0,
    "grounding_score": 1.0,
    "hallucination_risk": 0.0
  }
}
```

Then the operator reviews and clicks **Execute** → UI forwards `suggested_action` verbatim:

```bash
curl -X POST http://localhost:8000/action \
  -H "Content-Type: application/json" \
  -d '{"action": "unsuspend_user", "params": {"user_id": "U002"}}'
# → {"action":"unsuspend_user","executed":true,"result":{...}}
```

---

## Evaluation metrics

Each response is scored inline on three structural signals. Scores land in `metrics` on every `QueryResponse`.

| Metric | Formula | Value (10-query demo fixture) |
|---|---|---|
| **Tool correctness** | `1.0` if any tool called, else `0.0` | **1.000** |
| **Grounding score** | distinct data planes in `sources` → `{0: 0.0, 1: 0.6, ≥2: 1.0}` | **0.960** |
| **Hallucination risk** | `0.0` if sources cited, else `1.0` | **0.000** |
| **Latency p95** (mock mode) | wall-clock `invoke()` | **30 ms** |

Deeper scoring (LLM-as-judge completeness, action safety, golden-fixture harness) is specified in [`docs/PRD.md` §6](docs/PRD.md) as the next phase.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI + Pydantic + Uvicorn | Typed I/O, fast, auto OpenAPI |
| Agent orchestration | LangChain 0.3 (`create_tool_calling_agent` + `AgentExecutor`) | Model-agnostic tool-calling loop |
| LLM | **Google Gemini 2.5 Flash** via `langchain-google-genai` | Free tier, generous context, native function-calling |
| Embeddings | `models/gemini-embedding-001` | Same SDK as the LLM |
| Vector store | FAISS local (mode-aware dirs) | Zero infra, swap-ready for Pinecone |
| Relational store | SQLite (users, jobs, logs, audit) | Zero infra, fully parameterised SQL |
| Frontend | React 18 + TypeScript + Vite + Tailwind + Zustand | Typed, fast dev loop, tiny bundle |
| Tests | pytest 67-test suite, offline | No API key needed; force `USE_MOCK_LLM=1` in conftest |

---

## Setup

### 1. Get a Gemini API key (optional, for real mode)

Visit **https://aistudio.google.com/apikey** and create a free key. Skip this if you only want to run in mock mode (no key needed).

### 2. Backend

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate         # Windows (bash) — or: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env             # edit .env — set GEMINI_API_KEY and USE_MOCK_LLM=0 for real mode

python -m app.db.seed            # populates users/jobs/logs (deterministic)
python -m app.rag.ingest         # builds FAISS index (mock- or Gemini-embedded, depending on .env)

uvicorn app.main:app --reload --port 8000
```

Health check: `curl http://localhost:8000/health` → `{"status":"ok","mock_llm":true,"model":"mock"}`
OpenAPI: http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# open http://localhost:5173
```

### 4. Tests

```bash
cd backend && pytest tests/ -v     # 67 tests, all offline, sub-2s
```

### 5. Live log ingestion (optional)

The agent reads from the same SQLite logs table that `POST /ingest/log` writes to — so newly ingested entries are immediately visible on the next query.

```bash
curl -X POST http://localhost:8000/ingest/log \
  -H "Content-Type: application/json" \
  -d '{
    "timestamp": "2026-04-24T12:00:00",
    "service": "notification-service",
    "user_id": "U003",
    "message": "Digest email bounced: invalid recipient",
    "severity": "ERROR"
  }'
# → {"id":36,"status":"ingested"}

# Next agent query about U003 will surface this log automatically.
```

---

## Environment variables (`backend/.env`)

| Var | Default | Notes |
|---|---|---|
| `USE_MOCK_LLM` | `0` | `0` = real Gemini. `1` = deterministic offline mock (tests + demos without a key). |
| `GEMINI_API_KEY` | (empty) | Required when `USE_MOCK_LLM=0`. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Also supported: `gemini-2.5-pro`, `gemini-2.0-flash`, `gemini-2.0-flash-lite`. |
| `GEMINI_EMBEDDING_MODEL` | `models/gemini-embedding-001` | |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | CORS for the Vite dev server. |

---

## Repository structure

```
backend/
├── app/
│   ├── agent/           # agent.py, gemini_agent.py, mock_agent.py, tools.py, prompts.py, _format.py
│   ├── rag/             # embeddings.py, store.py, ingest.py
│   ├── db/              # queries.py, schema.py, seed.py
│   ├── routes/          # query.py, action.py, ingest.py
│   ├── eval/            # metrics.py
│   ├── main.py
│   ├── config.py
│   └── models.py
├── data/mock/           # RBAC + system doc corpora (JSON)
├── tests/               # 67 tests
├── requirements.txt
└── .env.example

frontend/
└── src/
    ├── App.tsx
    ├── store.ts         # Zustand
    └── components/      # Sidebar, TopBar, ChatPane, MessageBubble, ChatInput,
                         # ActionCard, ContextPanel, ReasoningTab, TraceTab, SourcesTab

```

---
