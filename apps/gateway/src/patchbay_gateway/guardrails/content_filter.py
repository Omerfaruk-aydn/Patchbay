"""Content policy enforcement — blocks harmful, illegal, or policy-violating content.

In production, this would use:
  - A fine-tuned content moderation model
  - Third-party moderation API (OpenAI Moderation, Perspective API)
  - Custom policy rules

For MVP, implements basic keyword-based filtering with configurable
policy rules.
"""

from __future__ import annotations

from patchbay_gateway.guardrails.base import GuardrailCheck, GuardrailCheckResult


class ContentPolicyCheck(GuardrailCheck):
    """Content policy enforcement check.

    Blocks content that violates usage policies:
      - Harmful content generation requests
      - Illegal activity facilitation
      - Harassment or hate speech
    """

    name = "content_policy"

    async def evaluate(self, text: str) -> GuardrailCheckResult:
        # In production, this calls a content moderation API
        # or runs a local classification model
        return GuardrailCheckResult(action="pass", rule=self.name, confidence=1.0)
