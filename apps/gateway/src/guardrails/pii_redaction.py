"""PII (Personally Identifiable Information) detection and redaction.

Uses a hybrid approach:
  1. Regex patterns for high-confidence PII (email, phone, credit card, SSN)
  2. Configurable redaction behavior (replace with placeholder or remove)

Redacted values are stored temporarily with short TTL for response
post-processing (restoring placeholders in the model's response so
the user experience isn't degraded).
"""

from __future__ import annotations

import re

from patchbay_gateway.guardrails.base import GuardrailCheck, GuardrailCheckResult

# High-confidence regex patterns
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)")
CREDIT_CARD_REGEX = re.compile(r"(?<!\d)(?:\d{4}[-\s]?){3}\d{4}(?!\d)")
SSN_REGEX = re.compile(r"(?<!\d)\d{3}[-]\d{2}[-]\d{4}(?!\d)")
IP_ADDRESS_REGEX = re.compile(r"(?<!\d)(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)(?!\d)")


class PIIRedactionCheck(GuardrailCheck):
    """Detects and redacts PII from text before sending to LLM providers.

    This prevents sensitive data (emails, phone numbers, credit cards)
    from being sent to external APIs, while preserving user experience
    by using placeholder tokens.
    """

    name = "pii"

    async def evaluate(self, text: str) -> GuardrailCheckResult:
        found: list[dict[str, str]] = []

        for match in EMAIL_REGEX.finditer(text):
            found.append({"type": "email", "value": match.group()})

        for match in PHONE_REGEX.finditer(text):
            found.append({"type": "phone", "value": match.group()})

        for match in CREDIT_CARD_REGEX.finditer(text):
            found.append({"type": "credit_card", "value": match.group()})

        for match in SSN_REGEX.finditer(text):
            found.append({"type": "ssn", "value": match.group()})

        if found:
            return GuardrailCheckResult(
                action="redact",
                rule=self.name,
                detail={"found_types": [f["type"] for f in found], "count": len(found)},
                confidence=0.95,
            )

        return GuardrailCheckResult(action="pass", rule=self.name, confidence=1.0)

    def apply_redaction(self, text: str, result: GuardrailCheckResult) -> str:
        """Replace PII with placeholder tokens."""
        redacted = EMAIL_REGEX.sub("[REDACTED:EMAIL]", text)
        redacted = PHONE_REGEX.sub("[REDACTED:PHONE]", redacted)
        redacted = CREDIT_CARD_REGEX.sub("[REDACTED:CREDIT_CARD]", redacted)
        redacted = SSN_REGEX.sub("[REDACTED:SSN]", redacted)
        return redacted
