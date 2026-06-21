# ADR-002: Provider Adapter Pattern with Plugin Registry

## Status
Accepted

## Context
We need to support 10+ LLM providers, each with different:
- Authentication mechanisms (API key, OAuth, IAM SigV4)
- Request/response schemas
- Streaming formats

Adding a new provider should not require changes to the routing engine or API layer.

## Decision
Use an abstract `ProviderAdapter` base class with an auto-discovery registry.

## Consequences

### Positive
- Adding a new provider = creating one file (Open/Closed Principle)
- Registry auto-discovers adapters at import time
- Each adapter is independently testable
- Routing engine and API layer never know provider-specific details

### Negative
- Some providers share similar patterns (OpenAI-compatible), leading to code duplication
- Adapter implementations vary in completeness (some have streaming, some don't)

### Mitigation
- Create a base `OpenAICompatibleAdapter` for providers that use the same API shape
- Mark incomplete implementations clearly (e.g., "streaming not yet implemented")
