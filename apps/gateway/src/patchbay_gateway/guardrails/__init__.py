"""Guardrails — input/output safety checks for the LLM pipeline.

Modules:
  base.py              — Pipeline orchestration with sequential check execution
  pii_redaction.py     — PII detection (email, phone, credit card, SSN) and redaction
  jailbreak_detector.py — Jailbreak pattern detection (8 known patterns)
  content_filter.py    — Content policy enforcement
"""
