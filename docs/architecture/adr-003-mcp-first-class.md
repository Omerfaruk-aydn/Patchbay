# ADR-003: MCP as First-Class Citizen

## Status
Accepted

## Context
Most LLM gateways treat MCP as an afterthought. We want to differentiate by making MCP tool orchestration a core feature, not an integration.

## Decision
MCP is a first-class concept alongside LLM routing:
1. Tool definitions are stored in the database (not just passed through)
2. Schema translation happens at the gateway level (MCP ↔ provider format)
3. Tool calls are tracked with a lifecycle state machine (pending → running → completed/failed)
4. Any MCP server works with any LLM provider transparently

## Consequences

### Positive
- Users connect MCP servers once, use them with any model
- Tool call history is queryable and auditable
- Enables the "Blender MCP + any LLM" demo scenario

### Negative
- Added complexity in the request pipeline (tool injection before provider send)
- Schema translation must handle edge cases across providers

### Mitigation
- Schema translator is well-tested with unit tests for each provider format
- Tool injection is a clean pipeline step, not interleaved with other logic
