from __future__ import annotations

from typing import Any

from patchbay_gateway.core.exceptions import NoHealthyRouteError
from patchbay_gateway.routing.strategies.base import RoutingStrategy
from patchbay_gateway.routing.strategies.cost_based import CostBasedStrategy, estimate_tokens

# Semantic categories and their preferred model mappings
SEMANTIC_CATEGORIES = {
    "code_generation": {
        "preferred_models": ["deepseek-coder", "claude-opus-4-7"],
        "description": "Code writing, debugging, refactoring",
    },
    "creative_writing": {
        "preferred_models": ["claude-opus-4-7", "gpt-4o"],
        "description": "Creative text, stories, marketing copy",
    },
    "reasoning_math": {
        "preferred_models": ["claude-opus-4-7", "gpt-4o"],
        "description": "Logic, math, analysis",
    },
    "simple_classification": {
        "preferred_models": ["gpt-4o-mini", "claude-haiku"],
        "description": "Simple tasks, classification, extraction",
    },
    "translation": {
        "preferred_models": ["gpt-4o", "claude-sonnet"],
        "description": "Multi-language translation",
    },
}


class SemanticRoutingStrategy(RoutingStrategy):
    """Routes based on task category rather than just cost/latency.

    Matches the request's intent to a task category using embedding
    similarity, then selects the preferred model for that category.
    """

    async def select(
        self, candidates: list[Any], request_context: dict
    ) -> Any:
        # Simple heuristic-based categorization (embedding-based in production)
        messages = request_context.get("messages", [])
        last_message = messages[-1].get("content", "") if messages else ""
        category = self._categorize_simple(last_message)

        preferred = SEMANTIC_CATEGORIES.get(category, {}).get("preferred_models", [])
        for model_name in preferred:
            match = next(
                (c for c in candidates if c.is_healthy and model_name in c.provider_model_id),
                None,
            )
            if match:
                return match

        # Fallback to cost-based
        fallback = CostBasedStrategy()
        return await fallback.select(candidates, request_context)

    def _categorize_simple(self, text: str) -> str:
        text_lower = text.lower()
        code_keywords = ["code", "function", "class", "debug", "refactor", "implement", "write a", "bug"]
        if any(kw in text_lower for kw in code_keywords):
            return "code_generation"
        if any(kw in text_lower for kw in ["translate", "çeviri", "traduire"]):
            return "translation"
        if any(kw in text_lower for kw in ["classify", "ategorize", "label"]):
            return "simple_classification"
        return "reasoning_math"
