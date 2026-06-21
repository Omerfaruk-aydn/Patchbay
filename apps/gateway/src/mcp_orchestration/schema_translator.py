from __future__ import annotations

from typing import Any

from patchbay_gateway.providers.schemas import ToolCall


class MCPSchemaTranslator:
    """Translates MCP tool schemas to/from provider-specific formats.

    MCP format (source, always the same):
      {"name": "...", "description": "...", "inputSchema": {JSON Schema}}

    Target formats:
      - OpenAI:    {"type": "function", "function": {"name", "description", "parameters"}}
      - Anthropic: {"name", "description", "input_schema"}
      - Gemini:    {"functionDeclarations": [{"name", "description", "parameters"}]}
    """

    def to_openai_format(self, mcp_tool: dict) -> dict:
        return {
            "type": "function",
            "function": {
                "name": mcp_tool["name"],
                "description": mcp_tool.get("description", ""),
                "parameters": mcp_tool.get("inputSchema", {}),
            },
        }

    def to_anthropic_format(self, mcp_tool: dict) -> dict:
        return {
            "name": mcp_tool["name"],
            "description": mcp_tool.get("description", ""),
            "input_schema": mcp_tool.get("inputSchema", {}),
        }

    def to_gemini_format(self, mcp_tool: dict) -> dict:
        return {
            "function_declarations": [
                {
                    "name": mcp_tool["name"],
                    "description": mcp_tool.get("description", ""),
                    "parameters": mcp_tool.get("inputSchema", {}),
                }
            ]
        }

    def translate_tools_for_provider(
        self, provider_key: str, mcp_tools: list[dict]
    ) -> list[dict]:
        """Translate a list of MCP tools to the provider's format."""
        translators = {
            "openai": self.to_openai_format,
            "anthropic": self.to_anthropic_format,
            "google": self.to_gemini_format,
        }
        translator = translators.get(provider_key, self.to_openai_format)
        return [translator(t) for t in mcp_tools]

    def parse_tool_invocation(
        self, provider_key: str, raw_tool_call: dict
    ) -> ToolCall:
        """Parse a provider-specific tool call into a normalized ToolCall."""
        if provider_key in ("openai",):
            func = raw_tool_call.get("function", {})
            return ToolCall(
                id=raw_tool_call.get("id", ""),
                name=func.get("name", ""),
                arguments=func.get("arguments", {}),
            )
        elif provider_key == "anthropic":
            return ToolCall(
                id=raw_tool_call.get("id", ""),
                name=raw_tool_call.get("name", ""),
                arguments=raw_tool_call.get("input", {}),
            )
        elif provider_key == "google":
            fc = raw_tool_call.get("function_call", raw_tool_call)
            return ToolCall(
                id=fc.get("name", ""),
                name=fc.get("name", ""),
                arguments=fc.get("args", {}),
            )
        return ToolCall(
            id=raw_tool_call.get("id", ""),
            name=raw_tool_call.get("name", ""),
            arguments=raw_tool_call.get("arguments", {}),
        )
