"""Routing strategies — pluggable algorithms for provider selection.

Each strategy implements the RoutingStrategy ABC:
  base.py        — Abstract interface
  cost_based.py  — Lowest effective cost (price × fallback rate)
  latency_based.py — Lowest p95 latency from Redis metrics
  semantic.py    — Task-category-based model selection
  learned.py     — Phase 2 placeholder (multi-armed bandit)
"""
