from __future__ import annotations

import re

from patchbay_gateway.guardrails.base import GuardrailCheck, GuardrailCheckResult

JAILBREAK_PATTERNS = [
    re.compile(r"ignore (all )?(previous|prior|earlier) instructions", re.IGNORECASE),
    re.compile(r"you are now (?:DAN|in developer mode)", re.IGNORECASE),
    re.compile(r"pretend (?:you are|to be) (?:an? )?(?:evil|unrestricted)", re.IGNORECASE),
    re.compile(r"bypass (?:all )?(?:safety|content|security) filters", re.IGNORECASE),
    re.compile(r"act as if (?:you have|there are) no (?:rules|restrictions)", re.IGNORECASE),
]


class JailbreakDetectionCheck(GuardrailCheck):
    """Detects common jailbreak patterns using regex heuristics."""

    name = "jailbreak"

    async def evaluate(self, text: str) -> GuardrailCheckResult:
        for pattern in JAILBREAK_PATTERNS:
            if pattern.search(text):
                return GuardrailCheckResult(
                    action="flag",
                    rule=self.name,
                    detail={"pattern": pattern.pattern},
                )
        return GuardrailCheckResult(action="pass", rule=self.name)
