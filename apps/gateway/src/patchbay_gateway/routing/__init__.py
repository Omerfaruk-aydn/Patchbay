"""Routing engine — selects optimal provider route for each request.

Modules:
  engine.py      — Main routing pipeline (resolve → filter → select)
  circuit_breaker.py — Redis-backed three-state circuit breaker
  fallback_chain.py  — Automatic fallback with transient error detection
  strategies/    — Pluggable routing strategies (cost, latency, semantic)
"""
