# ADR-003 — Why pgvector


## Problem
Phase 2 introduces retrieval: a curated knowledge base of therapeutic reframing techniques must be chunked, embedded, and searched by semantic similarity so that generated reframes are grounded in retrieved material rather than invented by the model.

That requires storing high-dimensional vectors and running nearest-neighbour search over them. Phase 2 also requires *hybrid* retrieval — keyword search combined with vector search — and later phases add long-term memory records that are themselves retrieved by similarity.

The decision is where those vectors live: inside the existing PostgreSQL database, or in a separate purpose-built vector store.

## Options considered
**Pinecone** — fully managed, purpose-built, scales to very large collections with minimal operational work. External service, per-usage cost, network hop, and another vendor dependency.

**Qdrant** — open source, self-hostable or managed, strong filtering and payload support, excellent performance. Means running and deploying a second stateful service.

**Weaviate** — open source with built-in vectorisation modules and hybrid search. Feature-rich, but heavier to operate for this scale.

**Chroma** — very simple developer experience, ideal for prototypes. Less suited to a system intended to demonstrate a production deployment path.

**FAISS** — a library, not a database. Fast, but provides no persistence, no filtering, and no concurrent access model; all of that becomes application code.

**pgvector** — a PostgreSQL extension adding a `vector` column type with similarity search operators and indexing (IVFFlat, HNSW).


## Why
1. **No second data store to run.** Postgres is already a dependency (ADR-002). Adding pgvector adds an extension, not a service — one container, one connection string, one backup, one thing to deploy to AWS. At this scale, an additional stateful service is real operational cost for no functional gain.
2. **Vectors can be filtered and joined relationally.** Retrieval is rarely pure similarity. Queries like *"the most similar technique chunks, restricted to those relevant to this distortion type"* combine a vector operator with an ordinary `WHERE` clause and a join — a single SQL statement, transactionally consistent. With an external store, the same query becomes two round trips plus application-side merging, and the filter metadata must be duplicated into the vector store and kept in sync.
3. **Hybrid retrieval lives in one engine.** Phase 2 requires BM25-style keyword search alongside vector search. Postgres provides full-text search natively, so both retrieval arms run against the same database and can be combined in one query before reranking. Splitting them across two systems would make fusion harder and add a network hop per request.
4. **Consistency for free.** Chunks and their embeddings are written in the same transaction. There is no window in which a document exists but its vector does not, which is a genuine class of bug when a separate vector store is written asynchronously.
5. **Volume does not justify more.** The knowledge base is on the order of thousands of chunks, not millions. pgvector with an HNSW index is comfortably fast at that size; a dedicated vector database would be solving a scale problem this project does not have.
6. **Consistent with the project's principle on technology.** Introduce a component when it solves a problem that exists — the same reasoning applied to deferring Redis to Phase 4.

## Trade-offs
- **Lower ceiling than dedicated stores.** Beyond roughly tens of millions of vectors, purpose-built engines outperform pgvector on latency and index build time.
- **Index tuning is manual.** HNSW parameters (`m`, `ef_construction`, `ef_search`) and IVFFlat list counts must be chosen and tested; managed services tune this automatically.
- **Shared resource contention.** Vector search competes with transactional queries for the same CPU and memory. At high load, this would argue for separation.
- **Fewer specialised features.** No built-in reranking, sparse-dense fusion, or multi-tenancy primitives — these are implemented in application code here.
- **Index rebuild cost.** Changing embedding models means re-embedding and rebuilding the index, which is easier to orchestrate in some managed offerings.

## When I'd choose something else
- **Qdrant or Pinecone** — once the collection reaches millions of vectors, or when vector search latency becomes the system bottleneck and needs to scale independently of the transactional database.
- **Pinecone specifically** — when there is no appetite to operate stateful infrastructure at all and per-query cost is acceptable.
- **Chroma** — for a throwaway prototype or notebook experiment where persistence and deployment are irrelevant.
- **FAISS** — for offline batch similarity work, such as deduplicating a corpus or clustering embeddings during analysis, where no serving layer is needed.
- **A separate store regardless of scale** — if retrieval had to be shared across several independent services that should not couple to this application's database.
