"""MCP schema translator — translates tool definitions between MCP and provider formats.

This is the core of the "one tool definition, works with every model" feature.

Translation directions:
  MCP → OpenAI:    {"name", "description", "inputSchema"} → {"type":"function", "function":{...}}
  MCP → Anthropic: {"name", "description", "inputSchema"} → {"name", "description", "input_schema"}
  MCP → Gemini:    {"name", "description", "inputSchema"} → {"functionDeclarations":[{...}]}

Reverse translation (provider tool call → MCP tool call):
  OpenAI tool_calls → ToolInvocation(id, name, arguments)
  Anthropic tool_use → ToolInvocation(id, name, arguments)
  Gemini function_call → ToolInvocation(id, name, arguments)
"""

from __future__ import annotations

from patchbay_gateway.providers.schemas import ToolCall


class MCPSchemaTranslator:
    """Translates MCP tool schemas to/from provider-specific formats."""

    def to_openai_format(self, mcp_tool: dict) -> dict:
        """Convert MCP tool to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": mcp_tool.get("name", ""),
                "description": mcp_tool.get("description", ""),
                "parameters": mcp_tool.get("inputSchema", mcp_tool.get("input_schema", {})),
            },
        }

    def to_anthropic_format(self, mcp_tool: dict) -> dict:
        """Convert MCP tool to Anthropic tool format."""
        return {
            "name": mcp_tool.get("name", ""),
            "description": mcp_tool.get("description", ""),
            "input_schema": mcp_tool.get("inputSchema", mcp_tool.get("input_schema", {})),
        }

    def to_gemini_format(self, mcp_tool: dict) -> dict:
        """Convert MCP tool to Gemini function declaration format."""
        return {
            "function_declarations": [
                {
                    "name": mcp_tool.get("name", ""),
                    "description": mcp_tool.get("description", ""),
                    "parameters": mcp_tool.get("inputSchema", mcp_tool.get("input_schema", {})),
                }
            ]
        }

    def translate_tools_for_provider(
        self,
        provider_key: str,
        mcp_tools: list[dict],
    ) -> list[dict]:
        """Translate a list of MCP tools to the provider's format."""
        translators = {
            "openai": self.to_openai_format,
            "anthropic": self.to_anthropic_format,
            "google": self.to_gemini_format,
            "deepseek": self.to_openai_format,
            "openrouter": self.to_openai_format,
            "azure_openai": self.to_openai_format,
            "local": self.to_openai_format,
        }
        translator = translators.get(provider_key, self.to_openai_format)
        return [translator(t) for t in mcp_tools]

    def parse_tool_invocation(
        self,
        provider_key: str,
        raw_tool_call: dict,
    ) -> ToolCall:
        """Parse a provider-specific tool call into a normalized ToolCall."""
        if provider_key in ("openai", "deepseek", "openrouter", "azure_openai", "local"):
            func = raw_tool_call.get("function", raw_tool_call)
            args = func.get("arguments", "{}")
            if isinstance(args, str):
                import json
                try:
                    args = json.loads(args)
                except (json.JSONDecodeError, TypeError):
                    args = {}
            return ToolCall(
                id=raw_tool_call.get("id", ""),
                name=func.get("name", ""),
                arguments=args,
            )
        elif provider_key == "anthropic":
            return ToolCall(
                id=raw_tool_call.get("id", ""),
                name=raw_tool_call.get("name", ""),
                arguments=raw_tool_call.get("input", {}),
            )
        elif provider_key in ("google", "vertex_ai"):
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
