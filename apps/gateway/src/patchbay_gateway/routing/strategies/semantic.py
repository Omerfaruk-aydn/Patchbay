"""Semantic routing strategy — selects model based on task category.

Instead of optimizing for cost or latency, this strategy matches the
request's intent to a task category and selects the best model for
that specific task.

Categories and preferred models:
  - code_generation → DeepSeek Coder, Claude Opus
  - creative_writing → Claude Opus, GPT-4o
  - reasoning_math → Claude Opus, GPT-4o
  - simple_classification → GPT-4o-mini, Claude Haiku
  - translation → GPT-4o, Claude Sonnet

This is similar to OpenRouter's "auto" selection but is EXPLAINABLE —
the response includes which category was matched and why.
"""

from __future__ import annotations

import logging
from typing import Any

from patchbay_gateway.routing.strategies.base import RoutingStrategy
from patchbay_gateway.routing.strategies.cost_based import CostBasedStrategy

logger = logging.getLogger(__name__)

SEMANTIC_CATEGORIES: dict[str, dict[str, Any]] = {
    "code_generation": {
        "preferred_models": ["deepseek-coder", "claude-opus-4-7", "gpt-4o"],
        "keywords": ["code", "function", "class", "debug", "refactor", "implement", "write a", "bug", "api", "endpoint", "algorithm"],
        "description": "Code writing, debugging, refactoring",
    },
    "creative_writing": {
        "preferred_models": ["claude-opus-4-7", "gpt-4o", "claude-sonnet-4"],
        "keywords": ["write", "story", "poem", "creative", "narrative", "essay", "blog", "content"],
        "description": "Creative text, stories, marketing copy",
    },
    "reasoning_math": {
        "preferred_models": ["claude-opus-4-7", "gpt-4o", "deepseek-reasoner"],
        "keywords": ["calculate", "prove", "analyze", "reason", "logic", "math", "equation", "proof"],
        "description": "Logic, math, analysis",
    },
    "simple_classification": {
        "preferred_models": ["gpt-4o-mini", "claude-haiku", "gemini-2.5-flash"],
        "keywords": ["classify", "categorize", "label", "extract", "summarize", "yes or no"],
        "description": "Simple tasks, classification, extraction",
    },
    "translation": {
        "preferred_models": ["gpt-4o", "claude-sonnet-4", "gemini-2.5-pro"],
        "keywords": ["translate", "çeviri", "traduire", "übersetzen", "language"],
        "description": "Multi-language translation",
    },
}


class SemanticRoutingStrategy(RoutingStrategy):
    """Routes based on task category rather than just cost/latency.

    Uses keyword matching (MVP) or embedding similarity (Phase 2)
    to determine the task category, then selects the preferred model
    for that category.

    The response includes routing metadata:
      - matched_category: Which category was detected
      - similarity_score: Confidence in the match
    """

    async def select(
        self,
        candidates: list[Any],
        request_context: dict[str, Any],
    ) -> Any:
        messages = request_context.get("messages", [])
        last_message = ""
        for m in reversed(messages):
            content = m.get("content", "")
            if isinstance(content, str) and content:
                last_message = content
                break

        category, score = self._categorize(last_message)
        preferred = SEMANTIC_CATEGORIES.get(category, {}).get("preferred_models", [])

        for model_name in preferred:
            match = next(
                (c for c in candidates if c.is_healthy and model_name in c.provider_model_id),
                None,
            )
            if match:
                logger.info(
                    "semantic_strategy_selected",
                    extra={
                        "category": category,
                        "score": score,
                        "provider": match.provider_key,
                        "model": match.provider_model_id,
                    },
                )
                return match

        # Fallback to cost-based if no semantic match
        logger.debug("semantic_strategy_fallback_to_cost")
        fallback = CostBasedStrategy()
        return await fallback.select(candidates, request_context)

    def _categorize(self, text: str) -> tuple[str, float]:
        """Categorize text using keyword matching.

        Returns:
            Tuple of (category_name, confidence_score).
        """
        text_lower = text.lower()
        best_category = "reasoning_math"
        best_score = 0.0

        for category, config in SEMANTIC_CATEGORIES.items():
            keywords = config.get("keywords", [])
            matches = sum(1 for kw in keywords if kw in text_lower)
            score = matches / max(len(keywords), 1)
            if score > best_score:
                best_score = score
                best_category = category

        if best_score == 0:
            return "reasoning_math", 0.5

        return best_category, min(best_score * 2, 1.0)
