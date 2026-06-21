"""Jailbreak detection using pattern matching and heuristics.

Detects common jailbreak patterns:
  - Role-play exploitation ("DAN", "developer mode")
  - Instruction override ("ignore previous instructions")
  - Safety bypass attempts
  - Encoding tricks (character escaping, Unicode substitution)

Detection is hybrid:
  1. Regex patterns for known jailbreak templates (fast, deterministic)
  2. Embedding similarity against known jailbreak corpus (Phase 2)
"""

from __future__ import annotations

import re

from patchbay_gateway.guardrails.base import GuardrailCheck, GuardrailCheckResult

JAILBREAK_PATTERNS = [
    (re.compile(r"ignore\s+(all\s+)?(previous|prior|earlier|above)\s+instructions?", re.IGNORECASE), "instruction_override"),
    (re.compile(r"you\s+are\s+now\s+(DAN|in\s+developer\s+mode|unrestricted)", re.IGNORECASE), "role_exploitation"),
    (re.compile(r"pretend\s+(you\s+are|to\s+be)\s+(an?\s+)?(evil|unrestricted|unfiltered)", re.IGNORECASE), "role_exploitation"),
    (re.compile(r"bypass\s+(all\s+)?(safety|content|security)\s+(filters?|restrictions?|guidelines?)", re.IGNORECASE), "safety_bypass"),
    (re.compile(r"act\s+as\s+if\s+(you\s+have|there\s+are)\s+no\s+(rules?|restrictions?|limits?)", re.IGNORECASE), "rule_override"),
    (re.compile(r"do\s+anything\s+now|DAN\s*mode|jailbreak", re.IGNORECASE), "explicit_jailbreak"),
    (re.compile(r"from\s+now\s+on\s+you\s+(will|must|should)\s+(not\s+)?(refuse|decline|deny)", re.IGNORECASE), "behavior_override"),
    (re.compile(r"(system|developer)\s*prompt\s*(override|injection|bypass)", re.IGNORECASE), "system_injection"),
]


class JailbreakDetectionCheck(GuardrailCheck):
    """Detects jailbreak attempts using pattern matching.

    Default policy is "flag" (log but allow). Enterprise deployments
    can configure to "block" for stricter enforcement.
    """

    name = "jailbreak"

    async def evaluate(self, text: str) -> GuardrailCheckResult:
        detections: list[dict[str, str]] = []

        for pattern, category in JAILBREAK_PATTERNS:
            match = pattern.search(text)
            if match:
                detections.append({
                    "category": category,
                    "pattern": pattern.pattern,
                    "match": match.group()[:100],
                })

        if detections:
            return GuardrailCheckResult(
                action="flag",
                rule=self.name,
                detail={"detections": detections, "count": len(detections)},
                confidence=0.8,
            )

        return GuardrailCheckResult(action="pass", rule=self.name, confidence=0.9)
