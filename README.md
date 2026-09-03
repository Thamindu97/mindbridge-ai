# MindBridge AI

A production-grade LLM engineering system that detects cognitive distortions in written reflections and generates evidence-grounded reframes combining a fine-tuned classifier with LLM reasoning, hybrid retrieval, confidence-based model routing, and safety guardrails.

> ⚠️ **Research and engineering project — not a clinical service.**
> MindBridge AI exists to demonstrate production AI engineering practice. It is **not** a medical device, not therapy, and not a substitute for professional mental health care. The public demo runs on synthetic and worked examples only. It does not diagnose, treat, or provide clinical advice.

---

## Why this project

Most LLM demos are a prompt and a text box. This project is about the parts that make an AI system *reliable in production*:

- **Constraining the unreliable component** — LLM output is forced into a validated schema, never trusted as free text.
- **Deciding what belongs to a model vs. plain code** — deterministic logic stays deterministic; the LLM is used only where reasoning genuinely helps.
- **Grounding, not inventing** — reframes are retrieved from a curated knowledge base, not hallucinated.
- **Routing by confidence** — cheap model first, escalate to a frontier model only when needed.
- **Measuring, not asserting** — quality, cost, and latency are instrumented and evaluated.

---

## Status

**Current:** Phase 1 complete (Week 1) · pre-0.1

| Release | Criteria | Status |
|---|---|---|
| 0.1 | Live deployment · MCP tool · hybrid RAG · classification | In progress |
| 0.2 | Memory · routing · feedback · guardrails · cost controls | Planned |
| 1.0 | Frontend · eval framework · analytics dashboard · demo | Planned |

---

## Features

**Implemented**
- FastAPI backend with health check and auto-generated OpenAPI docs
- PostgreSQL 16 + `pgvector`, running via Docker Compose
- SQLAlchemy schema: `users`, `conversations`, `messages`, `classifications`
- `POST /classify` — distortion classification with **schema-validated structured output** (via tool-calling, not prompt-and-parse)
- Dual provider integration: Anthropic (Claude) + OpenAI

**Planned**
- Live deployment + per-request latency/cost instrumentation (Phase 1, Week 2)
- Hybrid RAG (vector + BM25 + reranker) over a therapeutic-technique KB (Phase 2)
- MCP server exposing the classifier as a tool callable from Claude (Phase 2)
- Conversation + long-term memory; confidence-based model routing (Phase 3)
- Guardrails, crisis detection, human feedback, cost circuit breaker (Phase 4)
- Evaluation framework (LLM-as-judge, regression detection) + observability (Phase 5)
- Next.js + TypeScript frontend (Phase 6)

---

## Architecture 

```
Next.js Frontend
      |
      v
FastAPI Backend --> Auth
      |
      |--> Conversation Memory
      |--> MCP Server (classifier as a tool)
      |--> Analytics (latency . cost . uptime . errors)
      |
      v
  LangGraph  (only where orchestration earns its place;
      |       deterministic steps stay plain Python)
      v
Confidence Routing --> cheap model  <->  frontier model
      |
      v
Hybrid Retrieval (vector + BM25 + reranker)
      |
      v
BERT Distortion Classifier
      |
      v
Guardrails --> crisis detection / refusal
      |         + rate limits + cost circuit breaker
      v
Response --> Evaluation + Feedback --> Analytics
```

**Infrastructure:** PostgreSQL . pgvector . Docker . AWS (or VPS + nginx + Cloudflare) . GitHub Actions
**Observability:** LangSmith . MLflow . cost / token / latency / uptime tracking
**Redis** enters in Phase 4, when caching / rate-limiting create a real need.

---

## Tech stack

| Layer | Technology |
|---|---|
| API | FastAPI . Pydantic . Uvicorn |
| Database | PostgreSQL 16 . pgvector . SQLAlchemy |
| LLM providers | Anthropic (Claude) . OpenAI |
| Infrastructure | Docker . Docker Compose |
| Language | Python 3.11+ |


---

## Getting started

**Prerequisites:** Python 3.11+, Docker Desktop, API keys for Anthropic and/or OpenAI.

```bash
# 1. Clone
git clone https://github.com/Thamindu97/mindbridge-ai.git
cd mindbridge-ai

# 2. Environment
cp .env.example .env      # then add your API keys

# 3. Start the database
docker compose up -d
docker compose ps         # 'postgres' should be running

# 4. Python environment
python3 -m venv .venv
source .venv/bin/activate # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 5. Run the API
uvicorn app.main:app --reload
```

Then open:
- http://127.0.0.1:8000/health — health check
- http://127.0.0.1:8000/docs — interactive API documentation

### Try the classifier

```bash
curl -X POST http://127.0.0.1:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"text": "I will never get a job, I always fail at everything."}'
```

```json
{
  "distortion": "overgeneralization",
  "confidence": 0.87,
  "evidence": "always fail at everything"
}
```

---

## Data model

| Table | Fields | Purpose |
|---|---|---|
| `users` | id, email*, first_name*, last_name, created_at | Account records |
| `conversations` | id, user_id* -> users, created_at | Groups messages into a session |
| `messages` | id, conversation_id* -> conversations, role*, content*, created_at | Individual turns (`user` / `assistant`) |
| `classifications` | id, message_id* -> messages, distortion_type*, confidence*, evidence, model_used*, created_at | Distortion analysis of a message |

*\* = not null*


---

## Project structure

```
mindbridge-ai/
|-- app/
|   |-- main.py          # FastAPI app + routes
|   |-- models.py        # SQLAlchemy models
|   |-- schemas.py       # Pydantic schemas (output contracts)
|   |-- llm.py           # LLM integration (Claude + OpenAI)
|-- architecture-decisions/   # ADRs
|-- docker-compose.yml   # Postgres + pgvector
|-- requirements.txt
|-- .env.example
|-- README.md
```

---

## Architecture decisions

Design decisions are recorded as ADRs in [`architecture-decisions/`](./architecture-decisions), written when each decision is made. Only genuinely debatable decisions get one.

| ADR | Decision | Phase |
|---|---|---|
| [001](./architecture-decisions/ADR-001-Why-FastAPI.md) | Why FastAPI | 1 (done) |
| [002](./architecture-decisions/ADR-002-Why-Postgres.md) | Why PostgreSQL | 1 (done) |
| [003](./architecture-decisions/ADR-003-Why-pgvector.md) | Why pgvector | 1 (done) |
| [004](./architecture-decisions/ADR-004-Structured-Output.md) | Structured output via tool-calling | 1 (done) |
| 005 | Hybrid RAG | 2 |
| 006 | LangGraph (and what stays out) | 3 |
| 007 | Confidence routing | 3 |
| 008 | Redis (why deferred) | 4 |
| 009 | Next.js | 6 |

---

## Roadmap

| Phase | Focus |
|---|---|
| 1 | Foundation — API, database, structured output, **first deploy** |
| 2 | Core pipeline — ETL, hybrid RAG, BERT, **MCP tool** (start applying) |
| 3 | AI engineering — memory, orchestration, confidence routing |
| 4 | Responsible AI — guardrails, crisis detection, cost controls |
| 5 | Production ops — CI/CD, testing, eval framework, observability |
| 6 | Frontend — Next.js + TypeScript |
| 7 | Package — docs, demo video, portfolio |

---

## Licence

MIT
