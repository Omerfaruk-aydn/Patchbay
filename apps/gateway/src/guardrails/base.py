from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from patchbay_gateway.db.models import GuardrailViolation


@dataclass
class GuardrailCheckResult:
    action: str  # "pass" | "block" | "redact" | "flag"
    rule: str
    detail: dict = field(default_factory=dict)


class GuardrailCheck(ABC):
    name: str

    @abstractmethod
    async def evaluate(self, text: str) -> GuardrailCheckResult:
        ...

    def apply_redaction(self, text: str, result: GuardrailCheckResult) -> str:
        return text


class GuardrailPipeline:
    """Input/output guardrail pipeline."""

    stages: list[GuardrailCheck] = []

    async def run_input_checks(
        self, text: str, enabled_rules: list[str] | None = None
    ) -> list[GuardrailCheckResult]:
        results: list[GuardrailCheckResult] = []
        for check in self.stages:
            if enabled_rules and check.name not in enabled_rules:
                continue
            result = await check.evaluate(text)
            results.append(result)
            if result.action == "block":
                break
        return results
