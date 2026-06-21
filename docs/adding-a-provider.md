# Adding a New Provider Adapter

This guide walks through adding a new LLM provider to Patchbay.

## Prerequisites
- The provider must expose a REST API (or have a Python SDK)
- You have API credentials for the provider

## Steps

### 1. Create the adapter file

Create `apps/gateway/src/providers/{provider_name}_adapter.py`:

```python
from patchbay_gateway.providers.base import ProviderAdapter
from patchbay_gateway.providers.schemas import NormalizedRequest, NormalizedResponse
from patchbay_gateway.providers.registry import ProviderRegistry

@ProviderRegistry.register
class MyProviderAdapter(ProviderAdapter):
    provider_key = "my_provider"

    def normalize_request(self, req: dict) -> NormalizedRequest:
        # Convert OpenAI-format to provider format
        ...

    def normalize_response(self, response) -> NormalizedResponse:
        # Convert provider response to unified format
        ...

    async def send(self, route, request: NormalizedRequest) -> NormalizedResponse:
        # Make API call
        ...

    async def stream(self, route, request: NormalizedRequest):
        # Implement streaming (optional for MVP)
        ...

    async def health_check(self, route) -> bool:
        # Lightweight health check
        ...

    def count_tokens(self, text: str, model: str) -> int:
        # Token counting for cost estimation
        ...
```

### 2. Add seed data

Create a migration that adds entries to `models` and `provider_routes`:

```sql
INSERT INTO models (canonical_name, family, capabilities) VALUES
  ('my-model', 'my_provider', '{"tool_use": true}');

INSERT INTO provider_routes (model_id, provider_key, provider_model_id, auth_credential_ref, pricing_input_per_million_cents, pricing_output_per_million_cents) VALUES
  ((SELECT id FROM models WHERE canonical_name = 'my-model'), 'my_provider', 'model-id-in-api', 'credential-ref', 10.0, 30.0);
```

### 3. Add tests

Create `apps/gateway/tests/unit/test_{provider_name}_adapter.py` with:
- `normalize_request` tests
- `normalize_response` tests
- Mock `send` tests

### 4. Update docs

Add the provider to the README and this guide.

## Checklist
- [ ] Adapter implements all `ProviderAdapter` methods
- [ ] Unit tests pass with `pytest`
- [ ] `mypy --strict` passes
- [ ] Seed migration adds model + route
- [ ] Health check returns correct status
