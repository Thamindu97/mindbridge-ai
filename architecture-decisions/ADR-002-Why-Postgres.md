# ADR-002 — Why PostgreSQL


## Problem
The system needs durable storage for several kinds of data that are related to each other:

- Users, conversations, and messages — clearly relational, with strict parent/child relationships
- Classification results linked to specific messages, retained over time so the same message can be re-analysed by different models
- Later phases add: retrieved document chunks with embeddings, long-term memory records, human feedback, and evaluation runs

These are not independent datasets. Almost every meaningful query crosses them.

## Options considered
- **SQLite** — zero setup, great locally; weak concurrent writes, awkward to serve.
- **MySQL/MariaDB** — solid relational option; no first-class vector extension.
- **MongoDB** — flexible, but relationships and joins move into application code.
- **PostgreSQL** — strong constraints, transactions, full-text search, and the `pgvector` extension.


## Why
1. **The data is relational, so use a relational database.** Every table here has a mandatory parent: a message belongs to a conversation, a conversation belongs to a user, a classification belongs to a message. Foreign keys enforce that at the database level rather than hoping application code never breaks it.
2. **Constraints catch bugs early.** `NOT NULL` on `messages.role`, `messages.content`, and `classifications.confidence` means malformed records fail at write time rather than surfacing as confusing behaviour during evaluation weeks later. In a system whose whole thesis is "constrain the unreliable parts," letting the storage layer be unconstrained would be inconsistent.
3. **One database instead of several.** Postgres holds relational data *and*, via pgvector, embeddings — and later can hold evaluation results and feedback. That avoids running a separate vector store, keeping deployment and backups simple.
4. **Transactions matter for multi-step writes.** Saving a message, its classification, and its generated response should either all succeed or all fail. ACID transactions give that without application-level compensation logic.
5. **Full-text search is built in.** Phase 2 requires hybrid retrieval — BM25-style keyword search alongside vector similarity. Postgres provides `tsvector`/`ts_rank` natively, so both halves of hybrid search can live in the same query engine.
6. **It is the industry default.** It runs everywhere, deploys cleanly on AWS (RDS or a container), and is the most commonly listed database in the roles this project targets.

## Trade-offs
- More operational overhead than SQLite; needs a running service and credentials.
- Schema changes require migrations (Alembic).
- Scales up well but not trivially out; connection pooling must be configured under async load.

## When I'd choose something else
- **SQLite** — for a single-user local tool, a prototype with no deployment target, or an embedded application. Genuinely the right answer more often than people admit.
- **MongoDB** — if documents were truly schemaless and independent, with few cross-entity queries, for example raw ingestion of heterogeneous third-party payloads.
- **A dedicated vector database (Pinecone, Qdrant, Weaviate)** — if vector volume reached the tens of millions and retrieval latency became the system's bottleneck (see ADR-003).
- **A managed warehouse (BigQuery, Snowflake)** — for large-scale analytical workloads over historical evaluation data, which is an entirely different access pattern from transactional serving.
