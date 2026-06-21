from __future__ import annotations

import re

from patchbay_gateway.guardrails.base import GuardrailCheck, GuardrailCheckResult

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")
CREDIT_CARD_REGEX = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")


class PIIRedactionCheck(GuardrailCheck):
    """Detects and redacts PII (email, phone, credit card) from text."""

    name = "pii"

    async def evaluate(self, text: str) -> GuardrailCheckResult:
        found = []
        if EMAIL_REGEX.search(text):
            found.append("email")
        if PHONE_REGEX.search(text):
            found.append("phone")
        if CREDIT_CARD_REGEX.search(text):
            found.append("credit_card")

        if found:
            return GuardrailCheckResult(
                action="redact",
                rule=self.name,
                detail={"found_types": found},
            )
        return GuardrailCheckResult(action="pass", rule=self.name)

    def apply_redaction(self, text: str, result: GuardrailCheckResult) -> str:
        redacted = EMAIL_REGEX.sub("[REDACTED:EMAIL]", text)
        redacted = PHONE_REGEX.sub("[REDACTED:PHONE]", redacted)
        redacted = CREDIT_CARD_REGEX.sub("[REDACTED:CREDIT_CARD]", redacted)
        return redacted
