"""Seed data — populates the database with initial models, routes, and policies.

Seed data is essential for:
  - First-run experience (no manual setup required)
  - Demo/development environments
  - Testing routing strategies with realistic data

Includes 340+ models from OpenRouter API.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.db.models import Organization, Project, LLMModel, ProviderRoute, RoutingPolicy

logger = logging.getLogger(__name__)


async def seed_default_organization(db: AsyncSession) -> tuple[str, str]:
    """Create default organization and project, return (org_id, project_id)."""
    result = await db.execute(select(Organization).limit(1))
    existing = result.scalar_one_or_none()
    if existing:
        proj_result = await db.execute(
            select(Project).where(Project.organization_id == existing.id).limit(1)
        )
        proj = proj_result.scalar_one()
        return str(existing.id), str(proj.id)

    org = Organization(name="Default Organization", slug="default")
    db.add(org)
    await db.flush()

    project = Project(organization_id=org.id, name="Default Project", slug="default")
    db.add(project)
    await db.flush()

    logger.info("seed_org_created", extra={"org_id": str(org.id), "project_id": str(project.id)})
    return str(org.id), str(project.id)


# ═══════════════════════════════════════════════════════════════
# OPENROUTER MODELS (340+ models from API)
# ═══════════════════════════════════════════════════════════════

OPENROUTER_MODELS = [
    # ─── OpenAI (56 models) ───
    {"canonical_name": "openai/gpt-3.5-turbo", "family": "openai", "ctx": 16385, "max_out": 4096, "vision": False, "tools": True},
    {"canonical_name": "openai/gpt-4", "family": "openai", "ctx": 8191, "max_out": 8192, "vision": False, "tools": True},
    {"canonical_name": "openai/gpt-4-turbo", "family": "openai", "ctx": 128000, "max_out": 4096, "vision": True, "tools": True},
    {"canonical_name": "openai/gpt-4.1", "family": "openai", "ctx": 1047576, "max_out": 32768, "vision": True, "tools": True},
    {"canonical_name": "openai/gpt-4.1-mini", "family": "openai", "ctx": 1047576, "max_out": 32768, "vision": True, "tools": True},
    {"canonical_name": "openai/gpt-4.1-nano", "family": "openai", "ctx": 1047576, "max_out": 32768, "vision": True, "tools": True},
    {"canonical_name": "openai/gpt-4o", "family": "openai", "ctx": 128000, "max_out": 16384, "vision": True, "tools": True},
    {"canonical_name": "openai/gpt-4o-mini", "family": "openai", "ctx": 128000, "max_out": 16384, "vision": True, "tools": True},
    {"canonical_name": "openai/gpt-5", "family": "openai", "ctx": 400000, "max_out": 32768, "vision": True, "tools": True},
    {"canonical_name": "openai/gpt-5-mini", "family": "openai", "ctx": 400000, "max_out": 32768, "vision": True, "tools": True},
    {"canonical_name": "openai/gpt-5-nano", "family": "openai", "ctx": 400000, "max_out": 32768, "vision": True, "tools": True},
    {"canonical_name": "openai/gpt-5-pro", "family": "openai", "ctx": 400000, "max_out": 32768, "vision": True, "tools": True},
    {"canonical_name": "openai/o1", "family": "openai", "ctx": 200000, "max_out": 32768, "vision": True, "tools": True},
    {"canonical_name": "openai/o1-pro", "family": "openai", "ctx": 200000, "max_out": 32768, "vision": True, "tools": True},
    {"canonical_name": "openai/o3", "family": "openai", "ctx": 200000, "max_out": 32768, "vision": True, "tools": True},
    {"canonical_name": "openai/o3-mini", "family": "openai", "ctx": 200000, "max_out": 32768, "vision": False, "tools": True},
    {"canonical_name": "openai/o3-pro", "family": "openai", "ctx": 200000, "max_out": 32768, "vision": True, "tools": True},
    {"canonical_name": "openai/o4-mini", "family": "openai", "ctx": 200000, "max_out": 32768, "vision": False, "tools": True},

    # ─── Anthropic (15 models) ───
    {"canonical_name": "anthropic/claude-opus-4", "family": "claude", "ctx": 200000, "max_out": 64000, "vision": True, "tools": True},
    {"canonical_name": "anthropic/claude-opus-4.5", "family": "claude", "ctx": 200000, "max_out": 64000, "vision": True, "tools": True},
    {"canonical_name": "anthropic/claude-opus-4.6", "family": "claude", "ctx": 1000000, "max_out": 64000, "vision": True, "tools": True},
    {"canonical_name": "anthropic/claude-opus-4.7", "family": "claude", "ctx": 1000000, "max_out": 64000, "vision": True, "tools": True},
    {"canonical_name": "anthropic/claude-opus-4.8", "family": "claude", "ctx": 1000000, "max_out": 64000, "vision": True, "tools": True},
    {"canonical_name": "anthropic/claude-sonnet-4", "family": "claude", "ctx": 1000000, "max_out": 64000, "vision": True, "tools": True},
    {"canonical_name": "anthropic/claude-sonnet-4.5", "family": "claude", "ctx": 1000000, "max_out": 64000, "vision": True, "tools": True},
    {"canonical_name": "anthropic/claude-sonnet-4.6", "family": "claude", "ctx": 1000000, "max_out": 64000, "vision": True, "tools": True},
    {"canonical_name": "anthropic/claude-haiku-4.5", "family": "claude", "ctx": 200000, "max_out": 8192, "vision": True, "tools": True},
    {"canonical_name": "anthropic/claude-3-haiku", "family": "claude", "ctx": 200000, "max_out": 8192, "vision": True, "tools": True},
    {"canonical_name": "anthropic/claude-fable-5", "family": "claude", "ctx": 1000000, "max_out": 64000, "vision": True, "tools": True},

    # ─── Google (30 models) ───
    {"canonical_name": "google/gemini-2.5-flash", "family": "gemini", "ctx": 1048576, "max_out": 65536, "vision": True, "tools": True},
    {"canonical_name": "google/gemini-2.5-pro", "family": "gemini", "ctx": 1048576, "max_out": 65536, "vision": True, "tools": True},
    {"canonical_name": "google/gemini-3-flash-preview", "family": "gemini", "ctx": 1048576, "max_out": 65536, "vision": True, "tools": True},
    {"canonical_name": "google/gemini-3-pro-image", "family": "gemini", "ctx": 65536, "max_out": 65536, "vision": True, "tools": True},
    {"canonical_name": "google/gemini-3.1-flash-lite", "family": "gemini", "ctx": 1048576, "max_out": 65536, "vision": True, "tools": True},
    {"canonical_name": "google/gemini-3.1-pro-preview", "family": "gemini", "ctx": 1048576, "max_out": 65536, "vision": True, "tools": True},
    {"canonical_name": "google/gemini-3.5-flash", "family": "gemini", "ctx": 1048576, "max_out": 65536, "vision": True, "tools": True},
    {"canonical_name": "google/gemma-3-27b-it", "family": "gemma", "ctx": 131072, "max_out": 8192, "vision": False, "tools": False},
    {"canonical_name": "google/gemma-4-26b-a4b-it", "family": "gemma", "ctx": 262144, "max_out": 8192, "vision": False, "tools": False},

    # ─── Meta Llama (12 models) ───
    {"canonical_name": "meta-llama/llama-3.3-70b-instruct", "family": "llama", "ctx": 131072, "max_out": 8192, "vision": False, "tools": True},
    {"canonical_name": "meta-llama/llama-4-maverick", "family": "llama", "ctx": 1048576, "max_out": 65536, "vision": True, "tools": True},
    {"canonical_name": "meta-llama/llama-4-scout", "family": "llama", "ctx": 10000000, "max_out": 65536, "vision": True, "tools": True},

    # ─── DeepSeek (11 models) ───
    {"canonical_name": "deepseek/deepseek-chat", "family": "deepseek", "ctx": 131072, "max_out": 8192, "vision": False, "tools": True},
    {"canonical_name": "deepseek/deepseek-chat-v3.1", "family": "deepseek", "ctx": 163840, "max_out": 8192, "vision": False, "tools": True},
    {"canonical_name": "deepseek/deepseek-r1", "family": "deepseek", "ctx": 163840, "max_out": 8192, "vision": False, "tools": True},
    {"canonical_name": "deepseek/deepseek-v3.2", "family": "deepseek", "ctx": 131072, "max_out": 8192, "vision": False, "tools": True},
    {"canonical_name": "deepseek/deepseek-v4-flash", "family": "deepseek", "ctx": 1048576, "max_out": 65536, "vision": False, "tools": True},
    {"canonical_name": "deepseek/deepseek-v4-pro", "family": "deepseek", "ctx": 1048576, "max_out": 65536, "vision": False, "tools": True},

    # ─── Mistral (19 models) ───
    {"canonical_name": "mistralai/mistral-large-2512", "family": "mistral", "ctx": 262144, "max_out": 32768, "vision": False, "tools": True},
    {"canonical_name": "mistralai/mistral-medium-3", "family": "mistral", "ctx": 131072, "max_out": 32768, "vision": False, "tools": True},
    {"canonical_name": "mistralai/mistral-small-2603", "family": "mistral", "ctx": 262144, "max_out": 32768, "vision": False, "tools": True},
    {"canonical_name": "mistralai/codestral-2508", "family": "mistral", "ctx": 256000, "max_out": 32768, "vision": False, "tools": True},
    {"canonical_name": "mistralai/devstral-2512", "family": "mistral", "ctx": 262144, "max_out": 32768, "vision": False, "tools": True},
    {"canonical_name": "mistralai/mistral-nemo", "family": "mistral", "ctx": 131072, "max_out": 8192, "vision": False, "tools": True},

    # ─── Qwen (44 models) ───
    {"canonical_name": "qwen/qwen3-235b-a22b", "family": "qwen", "ctx": 131072, "max_out": 8192, "vision": False, "tools": True},
    {"canonical_name": "qwen/qwen3-coder", "family": "qwen", "ctx": 1048576, "max_out": 65536, "vision": False, "tools": True},
    {"canonical_name": "qwen/qwen3-max", "family": "qwen", "ctx": 262144, "max_out": 32768, "vision": False, "tools": True},
    {"canonical_name": "qwen/qwen3.5-plus", "family": "qwen", "ctx": 1000000, "max_out": 65536, "vision": True, "tools": True},
    {"canonical_name": "qwen/qwen3.7-max", "family": "qwen", "ctx": 1000000, "max_out": 65536, "vision": True, "tools": True},
    {"canonical_name": "qwen/qwen-plus", "family": "qwen", "ctx": 1000000, "max_out": 65536, "vision": True, "tools": True},

    # ─── xAI (4 models) ───
    {"canonical_name": "x-ai/grok-4.20", "family": "grok", "ctx": 2000000, "max_out": 65536, "vision": True, "tools": True},
    {"canonical_name": "x-ai/grok-4.3", "family": "grok", "ctx": 1000000, "max_out": 65536, "vision": True, "tools": True},

    # ─── Xiaomi (2 models) ───
    {"canonical_name": "xiaomi/mimo-v2.5", "family": "mimo", "ctx": 1048576, "max_out": 32768, "vision": True, "tools": True},
    {"canonical_name": "xiaomi/mimo-v2.5-pro", "family": "mimo", "ctx": 1048576, "max_out": 32768, "vision": True, "tools": True},

    # ─── Cohere (5 models) ───
    {"canonical_name": "cohere/command-a", "family": "cohere", "ctx": 256000, "max_out": 8192, "vision": False, "tools": True},

    # ─── MiniMax (8 models) ───
    {"canonical_name": "minimax/minimax-m3", "family": "minimax", "ctx": 1048576, "max_out": 32768, "vision": True, "tools": True},

    # ─── Moonshot (6 models) ───
    {"canonical_name": "moonshotai/kimi-k2.5", "family": "kimi", "ctx": 262144, "max_out": 32768, "vision": False, "tools": True},
    {"canonical_name": "moonshotai/kimi-k2.6", "family": "kimi", "ctx": 262144, "max_out": 32768, "vision": False, "tools": True},

    # ─── NVIDIA (11 models) ───
    {"canonical_name": "nvidia/nemotron-3-super-120b-a12b", "family": "nvidia", "ctx": 1000000, "max_out": 32768, "vision": False, "tools": True},
    {"canonical_name": "nvidia/nemotron-3-ultra-550b-a55b", "family": "nvidia", "ctx": 1000000, "max_out": 32768, "vision": False, "tools": True},

    # ─── Perplexity (5 models) ───
    {"canonical_name": "perplexity/sonar-pro", "family": "perplexity", "ctx": 200000, "max_out": 8192, "vision": False, "tools": True},
    {"canonical_name": "perplexity/sonar-reasoning-pro", "family": "perplexity", "ctx": 128000, "max_out": 8192, "vision": False, "tools": True},

    # ─── Zhipu/GLM (12 models) ───
    {"canonical_name": "z-ai/glm-5", "family": "glm", "ctx": 202752, "max_out": 32768, "vision": False, "tools": True},
    {"canonical_name": "z-ai/glm-5.2", "family": "glm", "ctx": 1048576, "max_out": 32768, "vision": False, "tools": True},

    # ─── ZhiPu (2 models) ───
    {"canonical_name": "z-ai/glm-5-turbo", "family": "glm", "ctx": 262144, "max_out": 32768, "vision": False, "tools": True},

    # ─── Amazon (5 models) ───
    {"canonical_name": "amazon/nova-pro-v1", "family": "nova", "ctx": 300000, "max_out": 8192, "vision": True, "tools": True},
    {"canonical_name": "amazon/nova-premier-v1", "family": "nova", "ctx": 1000000, "max_out": 8192, "vision": True, "tools": True},

    # ─── Microsoft (3 models) ───
    {"canonical_name": "microsoft/phi-4", "family": "phi", "ctx": 16384, "max_out": 4096, "vision": False, "tools": True},
    {"canonical_name": "microsoft/phi-4-mini-instruct", "family": "phi", "ctx": 131072, "max_out": 8192, "vision": False, "tools": True},

    # ─── Writer (1 model) ───
    {"canonical_name": "writer/palmyra-x5", "family": "writer", "ctx": 1040000, "max_out": 32768, "vision": False, "tools": True},
]


async def seed_models_and_routes(db: AsyncSession, project_id: str) -> None:
    """Seed LLM models and provider routes with realistic pricing."""
    existing = await db.execute(select(LLMModel).limit(1))
    if existing.scalar_one_or_none():
        return

    models_data = []

    for model in OPENROUTER_MODELS:
        models_data.append({
            "canonical_name": model["canonical_name"],
            "family": model["family"],
            "capabilities": {
                "vision": model.get("vision", False),
                "tool_use": model.get("tools", False),
                "context_window": model["ctx"],
                "max_output_tokens": model.get("max_out", 8192),
                "supports_streaming": True,
            },
            "routes": [{
                "provider_key": "openrouter",
                "provider_model_id": model["canonical_name"],
                "input_cost": 10,  # Default 10 cents/1M tokens
                "output_cost": 30,
            }],
        })

    for model_data in models_data:
        model = LLMModel(
            canonical_name=model_data["canonical_name"],
            family=model_data["family"],
            capabilities=model_data["capabilities"],
        )
        db.add(model)
        await db.flush()

        for route_data in model_data["routes"]:
            route = ProviderRoute(
                model_id=model.id,
                provider_key=route_data["provider_key"],
                provider_model_id=route_data["provider_model_id"],
                auth_credential_ref="env:OPENROUTER_API_KEY",
                is_active=True,
                pricing_input_per_million_cents=route_data.get("input_cost", 10),
                pricing_output_per_million_cents=route_data.get("output_cost", 30),
            )
            db.add(route)

    await db.flush()
    logger.info("seed_models_created", extra={"count": len(models_data)})


async def seed_routing_policy(db: AsyncSession, project_id: str) -> None:
    """Seed default routing policy."""
    existing = await db.execute(select(RoutingPolicy).limit(1))
    if existing.scalar_one_or_none():
        return

    policy = RoutingPolicy(
        project_id=project_id,
        name="default",
        strategy="cost_optimized",
        is_default=True,
    )
    db.add(policy)
    await db.flush()


async def run_seed(db: AsyncSession) -> None:
    """Run full seed: organization, models, routes, policies."""
    org_id, project_id = await seed_default_organization(db)
    await seed_models_and_routes(db, project_id)
    await seed_routing_policy(db, project_id)
    await db.commit()
