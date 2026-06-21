"""Guardrail pipeline — orchestrates multiple safety checks on input/output.

Pipeline stages run sequentially. If any stage returns "block", the
pipeline stops and the request is rejected. "redact" stages modify the
input text before passing to the next stage.

Pipeline flow:
  input → PII Redaction → Jailbreak Detection → Content Filter → output

Each check is independently testable and configurable per project.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GuardrailCheckResult:
    """Result of a single guardrail check."""

    action: str  # "pass" | "block" | "redact" | "flag"
    rule: str
    detail: dict = field(default_factory=dict)
    confidence: float = 1.0


class GuardrailCheck(ABC):
    """Abstract base class for individual guardrail checks."""

    name: str

    @abstractmethod
    async def evaluate(self, text: str) -> GuardrailCheckResult:
        """Evaluate the text against this guardrail rule."""
        ...

    def apply_redaction(self, text: str, result: GuardrailCheckResult) -> str:
        """Apply redaction to the text (only for 'redact' actions)."""
        return text


class GuardrailPipeline:
    """Orchestrates multiple guardrail checks in sequence."""

    def __init__(self, stages: list[GuardrailCheck] | None = None) -> None:
        self.stages = stages or []

    async def run_input_checks(
        self,
        text: str,
        enabled_rules: list[str] | None = None,
    ) -> list[GuardrailCheckResult]:
        """Run all enabled guardrail checks on the input text.

        Args:
            text: The input text to check.
            enabled_rules: If provided, only run checks with these names.

        Returns:
            List of results from each check that ran.
        """
        results: list[GuardrailCheckResult] = []
        current_text = text

        for check in self.stages:
            if enabled_rules and check.name not in enabled_rules:
                continue

            try:
                result = await check.evaluate(current_text)
                results.append(result)

                if result.action == "block":
                    logger.warning(
                        "guardrail_blocked",
                        extra={"rule": check.name, "detail": result.detail},
                    )
                    break

                if result.action == "redact":
                    current_text = check.apply_redaction(current_text, result)

            except Exception as e:
                logger.error(
                    "guardrail_error",
                    extra={"rule": check.name, "error": str(e)},
                )
                continue

        return results
