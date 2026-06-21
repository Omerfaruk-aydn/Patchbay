# ADR-001: PostgreSQL + pgvector for Primary Database

## Status
Accepted

## Context
We need a primary database that supports:
- Relational integrity (organizations → projects → keys hierarchy)
- JSONB for flexible metadata
- Vector search for semantic caching
- High concurrency for gateway workloads

## Decision
Use PostgreSQL 16+ with the pgvector extension as the sole database.

## Consequences

### Positive
- Single database reduces operational complexity
- pgvector provides cosine similarity search without a separate vector DB
- JSONB columns offer flexibility without schema changes
- Rich ecosystem of tools (Alembic, SQLAlchemy async, pgAdmin)

### Negative
- pgvector may not scale as well as purpose-built vector DBs (Qdrant, Pinecone) at billions of vectors
- Semantic cache query performance depends on ivfflat index tuning

### Mitigation
- For MVP, pgvector is sufficient (semantic cache is per-project, not global)
- If scale becomes an issue, the vector search component can be swapped to a dedicated DB without changing the API surface
