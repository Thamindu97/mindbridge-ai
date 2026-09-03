# ADR-001 — Why FastAPI


## Problem
MindBridge AI needs an HTTP layer between clients and the AI pipeline. 

User (browser/mobile app)
         ↕
    FastAPI 
         ↕
Claude/GPT APIs
         ↕
PostgreSQL database

FastAPI lets you define endpoints, URLs that do specific things when called.

Its specific demands:

- LLM outputs must be validated against a fixed schema before anything downstream trusts them
- Requests involve slow network calls to model providers, so concurrency matters
- The Python ecosystem is non-negotiable — the classifier is a fine-tuned PyTorch model, and the LLM/RAG tooling is Python-first
- The API needs to be documented for a portfolio audience without hand-writing docs

## Options considered
Feature	            FastAPI	             Flask	        Django
Speed	            ⚡ Very fast	        Medium	        Medium
Auto API docs	    ✅ Built in	        ❌ Manual	  ❌ Manual
Pydantic integration✅ Native	        ❌ Manual	  ❌ Manual
Async support	    ✅ Built in	        ❌ Limited	  ❌ Limited
Modern Python	    ✅ Yes	            Partial	        Partial


## Decision
**FastAPI.**

## Why
1. **Pydantic is the point.** The core design principle of this system is that LLM output must be forced into a validated shape rather than trusted as prose. FastAPI uses Pydantic natively, so the same models that constrain LLM tool-calling also define and validate the API contract. One schema definition, enforced in both places.
2. **Async fits the workload.** Nearly every request is I/O-bound — waiting on Anthropic, OpenAI, or Postgres. ASGI handles concurrent waiting without a thread per request, which matters more as retrieval, routing, and multi-model calls are added in later phases.
3. **Free, always-accurate documentation.** `/docs` is generated from the type hints, so it can't drift from the implementation. For a portfolio project where "API documentation" is a deliverable, this removes an entire maintenance task.
4. **Same language as the AI stack.** The BERT classifier, embedding pipeline, and orchestration libraries are all Python. Keeping the API in Python avoids a cross-service boundary in the hot path.

## Trade-offs
- **Smaller ecosystem than Flask or Django.** Fewer ready-made extensions; some things (admin interfaces, auth flows) must be built rather than installed.
- **No built-in ORM or migrations.** SQLAlchemy and Alembic are separate choices with their own learning curve — Django would have supplied both.
- **Async is easy to misuse.** A blocking call inside an async endpoint stalls the event loop. Model inference in particular must be handled deliberately rather than awaited naively.
- **Younger project.** Less accumulated production folklore than Flask or Django, though adoption is now broad.

## When I'd choose something else
- **Django** — if the product needed user management, an admin interface, and complex relational modelling out of the box, and the AI surface were a small part of a larger web application.
- **Flask** — for a genuinely small synchronous service where FastAPI's async model and validation layer would be unused overhead.
- **Node/Express** — if the team's expertise were JavaScript and the ML work lived behind a separate Python inference service anyway.
- **A managed serverless function** — for a single stateless endpoint with no database and no persistent state; the framework choice would then matter far less than cold-start behaviour.
