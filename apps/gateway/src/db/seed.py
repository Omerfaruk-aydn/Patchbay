"""Seed data for initial models and provider routes."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from patchbay_gateway.db.models import Organization, Project, LLMModel, ProviderRoute, VirtualKey, RoutingPolicy


async def seed_default_organization(db: AsyncSession) -> tuple[str, str]:
    """Create default org + project, return (org_id, project_id)."""
    result = await db.execute(select(Organization).limit(1))
    if result.scalar_one_or_none():
        org = result.scalar_one()
        proj_result = await db.execute(select(Project).where(Project.organization_id == org.id).limit(1))
        proj = proj_result.scalar_one()
        return str(org.id), str(proj.id)

    org = Organization(name="Default", slug="default")
    db.add(org)
    await db.flush()

    project = Project(organization_id=org.id, name="Default Project", slug="default")
    db.add(project)
    await db.flush()

    return str(org.id), str(project.id)


async def seed_models_and_routes(db: AsyncSession, project_id: str) -> None:
    """Seed LLM models and provider routes."""
    existing = await db.execute(select(LLMModel).limit(1))
    if existing.scalar_one_or_none():
        return

    models_data = [
        {
            "canonical_name": "gpt-4o",
            "family": "openai",
            "capabilities": {"vision": True, "tool_use": True, "context_window": 128000, "max_output_tokens": 16384, "supports_streaming": True},
            "routes": [
                {"provider_key": "openai", "provider_model_id": "gpt-4o", "input_cost": 250, "output_cost": 1000},
            ],
        },
        {
            "canonical_name": "gpt-4o-mini",
            "family": "openai",
            "capabilities": {"vision": True, "tool_use": True, "context_window": 128000, "max_output_tokens": 16384, "supports_streaming": True},
            "routes": [
                {"provider_key": "openai", "provider_model_id": "gpt-4o-mini", "input_cost": 15, "output_cost": 60},
            ],
        },
        {
            "canonical_name": "claude-opus-4-7",
            "family": "claude",
            "capabilities": {"vision": True, "tool_use": True, "context_window": 200000, "max_output_tokens": 64000, "supports_streaming": True, "extended_thinking": True},
            "routes": [
                {"provider_key": "anthropic", "provider_model_id": "claude-opus-4-20250514", "input_cost": 1500, "output_cost": 7500},
                {"provider_key": "aws_bedrock", "provider_model_id": "anthropic.claude-opus-4-20250514-v1:0", "region": "us-east-1", "input_cost": 1500, "output_cost": 7500},
            ],
        },
        {
            "canonical_name": "claude-sonnet-4",
            "family": "claude",
            "capabilities": {"vision": True, "tool_use": True, "context_window": 200000, "max_output_tokens": 64000, "supports_streaming": True},
            "routes": [
                {"provider_key": "anthropic", "provider_model_id": "claude-sonnet-4-20250514", "input_cost": 300, "output_cost": 1500},
            ],
        },
        {
            "canonical_name": "claude-haiku",
            "family": "claude",
            "capabilities": {"vision": True, "tool_use": True, "context_window": 200000, "max_output_tokens": 8192, "supports_streaming": True},
            "routes": [
                {"provider_key": "anthropic", "provider_model_id": "claude-3-5-haiku-20241022", "input_cost": 80, "output_cost": 400},
            ],
        },
        {
            "canonical_name": "gemini-2.5-pro",
            "family": "gemini",
            "capabilities": {"vision": True, "tool_use": True, "context_window": 1000000, "max_output_tokens": 65536, "supports_streaming": True},
            "routes": [
                {"provider_key": "google", "provider_model_id": "gemini-2.5-pro-preview-06-05", "input_cost": 125, "output_cost": 1000},
            ],
        },
        {
            "canonical_name": "gemini-2.5-flash",
            "family": "gemini",
            "capabilities": {"vision": True, "tool_use": True, "context_window": 1000000, "max_output_tokens": 65536, "supports_streaming": True},
            "routes": [
                {"provider_key": "google", "provider_model_id": "gemini-2.5-flash-preview-05-20", "input_cost": 15, "output_cost": 60},
            ],
        },
        {
            "canonical_name": "deepseek-coder",
            "family": "deepseek",
            "capabilities": {"tool_use": True, "context_window": 128000, "max_output_tokens": 8192, "supports_streaming": True},
            "routes": [
                {"provider_key": "deepseek", "provider_model_id": "deepseek-coder", "input_cost": 14, "output_cost": 28},
            ],
        },
        {
            "canonical_name": "deepseek-reasoner",
            "family": "deepseek",
            "capabilities": {"context_window": 64000, "max_output_tokens": 8192, "supports_streaming": True},
            "routes": [
                {"provider_key": "deepseek", "provider_model_id": "deepseek-reasoner", "input_cost": 55, "output_cost": 219},
            ],
        },
        {
            "canonical_name": "llama-4-maverick",
            "family": "meta",
            "capabilities": {"vision": True, "tool_use": True, "context_window": 1000000, "supports_streaming": True},
            "routes": [
                {"provider_key": "openrouter", "provider_model_id": "meta-llama/llama-4-maverick", "input_cost": 20, "output_cost": 60},
            ],
        },
        {
            "canonical_name": "mistral-large",
            "family": "mistral",
            "capabilities": {"tool_use": True, "context_window": 128000, "max_output_tokens": 32768, "supports_streaming": True},
            "routes": [
                {"provider_key": "openrouter", "provider_model_id": "mistralai/mistral-large", "input_cost": 200, "output_cost": 600},
            ],
        },
    ]

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
                auth_credential_ref=f"{route_data['provider_key']}_credential",
                region=route_data.get("region"),
                pricing_input_per_million_cents=route_data["input_cost"],
                pricing_output_per_million_cents=route_data["output_cost"],
            )
            db.add(route)

    await db.flush()
    await db.commit()


async def seed_routing_policy(db: AsyncSession, project_id: str) -> None:
    """Seed default routing policy."""
    result = await db.execute(select(RoutingPolicy).where(RoutingPolicy.project_id == project_id))
    if result.scalar_one_or_none():
        return

    policy = RoutingPolicy(
        project_id=project_id,
        name="Default Cost-Optimized",
        strategy="cost_optimized",
        config={"fallback_order": []},
        is_default=True,
    )
    db.add(policy)
    await db.flush()
    await db.commit()


async def run_seed(db: AsyncSession) -> None:
    """Run all seed operations."""
    org_id, project_id = await seed_default_organization(db)
    await seed_models_and_routes(db, project_id)
    await seed_routing_policy(db, project_id)
