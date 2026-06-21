"""Billing and cost management — budget enforcement, rate limiting, cost calculation.

Modules:
  budget_enforcer — Hard budget checks (pre-request blocking)
  cost_calculator — Token cost calculation with Decimal precision
  rate_limiter    — Redis Lua-based token-bucket rate limiting
  alert_manager   — Budget threshold notifications
"""
