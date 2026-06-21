"""Provider adapters — one file per LLM provider.

Auto-discovered at startup via ProviderRegistry.discover().
Adding a new provider = creating one new file with @ProviderRegistry.register.

Supported providers:
  openai, anthropic, google, deepseek, openrouter,
  aws_bedrock, azure_openai, vertex_ai, local
"""
