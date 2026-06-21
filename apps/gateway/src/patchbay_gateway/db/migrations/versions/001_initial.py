"""Initial migration — all Patchbay tables.

Revision ID: 001_initial
Revises:
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.String(255), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("settings", sa.JSON(), server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "slug"),
    )

    op.create_table(
        "virtual_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("key_hash", sa.String(255), unique=True, nullable=False),
        sa.Column("key_prefix", sa.String(255), nullable=False),
        sa.Column("scopes", postgresql.ARRAY(sa.Text()), server_default=sa.text("'{}'")),
        sa.Column("rate_limit_rpm", sa.Integer(), nullable=True),
        sa.Column("budget_usd_cents", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_virtual_keys_project", "virtual_keys", ["project_id"])

    op.create_table(
        "models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("canonical_name", sa.String(255), unique=True, nullable=False),
        sa.Column("family", sa.String(100), nullable=False),
        sa.Column("capabilities", sa.JSON(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
    )

    op.create_table(
        "provider_routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("models.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_key", sa.String(100), nullable=False),
        sa.Column("provider_model_id", sa.String(255), nullable=False),
        sa.Column("auth_credential_ref", sa.Text(), nullable=False),
        sa.Column("region", sa.String(100), nullable=True),
        sa.Column("pricing_input_per_million_cents", sa.Numeric(10, 4), nullable=False),
        sa.Column("pricing_output_per_million_cents", sa.Numeric(10, 4), nullable=False),
        sa.Column("priority", sa.Integer(), server_default=sa.text("100")),
        sa.Column("avg_latency_ms", sa.Integer(), nullable=True),
        sa.Column("is_healthy", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_provider_routes_model", "provider_routes", ["model_id"])

    op.create_table(
        "routing_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("strategy", sa.String(50), nullable=False),
        sa.Column("config", sa.JSON(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("virtual_key_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("virtual_keys.id"), nullable=False),
        sa.Column("model_requested", sa.String(255), nullable=False),
        sa.Column("provider_route_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("provider_routes.id"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("fallback_chain", sa.JSON(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd_cents", sa.Numeric(10, 4), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("trace_id", sa.String(255), nullable=True),
        sa.Column("request_body_ref", sa.Text(), nullable=True),
        sa.Column("response_body_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_requests_key_time", "requests", ["virtual_key_id", sa.text("created_at DESC")])
    op.create_index("idx_requests_status", "requests", ["status"])

    op.create_table(
        "mcp_servers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("transport", sa.String(50), nullable=False),
        sa.Column("connection_uri", sa.Text(), nullable=False),
        sa.Column("auth_credential_ref", sa.Text(), nullable=True),
        sa.Column("discovered_via", sa.String(50), server_default=sa.text("'manual'")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "mcp_tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("mcp_server_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mcp_servers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_name", sa.String(255), nullable=False),
        sa.Column("input_schema", sa.JSON(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("mcp_server_id", "tool_name"),
    )

    op.create_table(
        "tool_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mcp_tool_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("mcp_tools.id"), nullable=False),
        sa.Column("status", sa.String(50), server_default=sa.text("'pending'")),
        sa.Column("input_payload", sa.JSON(), nullable=False),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_tool_calls_request", "tool_calls", ["request_id"])
    op.create_index("idx_tool_calls_status", "tool_calls", ["status"], postgresql_where=sa.text("status IN ('pending','running')"))

    op.create_table(
        "guardrail_violations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("detail", sa.JSON(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("target", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "semantic_cache_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prompt_embedding", sa.Text(), nullable=False),
        sa.Column("prompt_text_hash", sa.String(255), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=False),
        sa.Column("similarity_threshold", sa.Numeric(3, 2), server_default=sa.text("0.95")),
        sa.Column("hit_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("semantic_cache_entries")
    op.drop_table("audit_log")
    op.drop_table("guardrail_violations")
    op.drop_table("tool_calls")
    op.drop_table("mcp_tools")
    op.drop_table("mcp_servers")
    op.drop_table("requests")
    op.drop_table("routing_policies")
    op.drop_table("provider_routes")
    op.drop_index("idx_provider_routes_model")
    op.drop_table("models")
    op.drop_index("idx_virtual_keys_project")
    op.drop_table("virtual_keys")
    op.drop_table("projects")
    op.drop_table("organizations")
    op.execute("DROP EXTENSION IF EXISTS vector")
