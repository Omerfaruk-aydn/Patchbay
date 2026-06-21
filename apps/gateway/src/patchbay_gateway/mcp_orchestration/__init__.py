"""MCP (Model Context Protocol) orchestration layer.

Modules:
  registry.py          — MCP server connection and tool synchronization
  client_pool.py       — Persistent connection pool with idle cleanup
  schema_translator.py — MCP ↔ provider tool schema translation (6 formats)
  task_manager.py      — Async tool call lifecycle (pending→running→completed/failed)
"""
