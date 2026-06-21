from __future__ import annotations

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from patchbay_gateway.mcp_orchestration.schema_translator import MCPSchemaTranslator


class TestMCPSchemaTranslator:
    def setup_method(self):
        self.translator = MCPSchemaTranslator()
        self.mcp_tool = {
            "name": "create_object",
            "description": "Create a 3D object in Blender",
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
            },
        }

    def test_to_openai_format(self):
        result = self.translator.to_openai_format(self.mcp_tool)
        assert result["type"] == "function"
        assert result["function"]["name"] == "create_object"
        assert result["function"]["parameters"]["type"] == "object"

    def test_to_anthropic_format(self):
        result = self.translator.to_anthropic_format(self.mcp_tool)
        assert result["name"] == "create_object"
        assert "input_schema" in result

    def test_to_gemini_format(self):
        result = self.translator.to_gemini_format(self.mcp_tool)
        assert "function_declarations" in result
        assert result["function_declarations"][0]["name"] == "create_object"

    def test_translate_tools_for_provider(self):
        tools = [self.mcp_tool]
        openai_tools = self.translator.translate_tools_for_provider("openai", tools)
        assert len(openai_tools) == 1
        assert openai_tools[0]["type"] == "function"

    def test_parse_tool_invocation_openai(self):
        raw = {"id": "call_123", "function": {"name": "create_object", "arguments": {"name": "cube"}}}
        tc = self.translator.parse_tool_invocation("openai", raw)
        assert tc.id == "call_123"
        assert tc.name == "create_object"
        assert tc.arguments == {"name": "cube"}

    def test_parse_tool_invocation_anthropic(self):
        raw = {"id": "toolu_123", "name": "create_object", "input": {"name": "cube"}}
        tc = self.translator.parse_tool_invocation("anthropic", raw)
        assert tc.name == "create_object"
        assert tc.arguments == {"name": "cube"}
