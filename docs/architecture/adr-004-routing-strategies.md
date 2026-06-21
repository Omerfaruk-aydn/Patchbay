# ADR-004: Routing Strategies

## Status
Accepted

## Context
Different use cases require different routing strategies:
- Cost-sensitive workloads want the cheapest model
- Latency-sensitive workloads want the fastest route
- Task-specific workloads want the best model for the job

## Decision
Implement a strategy pattern with pluggable routing strategies:
1. **Cost-Based**: Lowest effective cost (price × fallback rate)
2. **Latency-Based**: Lowest p95 latency from Redis metrics
3. **Semantic**: Task category → preferred model mapping
4. **Learned** (Phase 2): Multi-armed bandit from historical data

## Consequences

### Positive
- Each strategy is independently testable
- Users can configure per-project routing policies
- New strategies can be added without changing the engine

### Negative
- Cost-based strategy needs fallback rate data (cold start problem)
- Semantic strategy needs embedding computation (adds latency)

### Mitigation
- Default to cost-based with a simple heuristic until enough data accumulates
- Semantic routing uses lightweight heuristics for MVP, embeddings in Phase 3
