"""Caching layer — exact-match and semantic caching for cost optimization.

Modules:
  exact_cache    — Redis SHA-256 hash-based exact-match cache
  semantic_cache — pgvector cosine similarity cache for near-duplicate prompts
"""
