"""Tests for MCP schema translation between provider formats."""

from __future__ import annotations

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from patchbay_gateway.mcp_orchestration.schema_translator import MCPSchemaTranslator


class TestMCPSchemaTranslator:
    """Tests for MCP ↔ provider format translation."""

    def setup_method(self):
        self.translator = MCPSchemaTranslator()
        self.mcp_tool = {
            "name": "create_object",
            "description": "Create a 3D object in Blender",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Object name"},
                    "location": {"type": "object", "properties": {"x": {"type": "number"}}},
                },
                "required": ["name"],
            },
        }

    def test_to_openai_format(self):
        result = self.translator.to_openai_format(self.mcp_tool)
        assert result["type"] == "function"
        assert result["function"]["name"] == "create_object"
        assert result["function"]["description"] == "Create a 3D object in Blender"
        assert result["function"]["parameters"]["type"] == "object"
        assert "name" in result["function"]["parameters"]["properties"]

    def test_to_anthropic_format(self):
        result = self.translator.to_anthropic_format(self.mcp_tool)
        assert result["name"] == "create_object"
        assert result["description"] == "Create a 3D object in Blender"
        assert "input_schema" in result
        assert result["input_schema"]["type"] == "object"

    def test_to_gemini_format(self):
        result = self.translator.to_gemini_format(self.mcp_tool)
        assert "function_declarations" in result
        assert len(result["function_declarations"]) == 1
        assert result["function_declarations"][0]["name"] == "create_object"
        assert "parameters" in result["function_declarations"][0]

    def test_translate_tools_for_openai(self):
        tools = [self.mcp_tool]
        result = self.translator.translate_tools_for_provider("openai", tools)
        assert len(result) == 1
        assert result[0]["type"] == "function"

    def test_translate_tools_for_anthropic(self):
        tools = [self.mcp_tool]
        result = self.translator.translate_tools_for_provider("anthropic", tools)
        assert len(result) == 1
        assert "input_schema" in result[0]

    def test_translate_tools_for_google(self):
        tools = [self.mcp_tool]
        result = self.translator.translate_tools_for_provider("google", tools)
        assert len(result) == 1
        assert "function_declarations" in result[0]

    def test_parse_tool_invocation_openai(self):
        raw = {"id": "call_123", "function": {"name": "create_object", "arguments": '{"name": "cube"}'}}
        tc = self.translator.parse_tool_invocation("openai", raw)
        assert tc.id == "call_123"
        assert tc.name == "create_object"
        assert tc.arguments == {"name": "cube"}

    def test_parse_tool_invocation_anthropic(self):
        raw = {"id": "toolu_123", "name": "create_object", "input": {"name": "cube"}}
        tc = self.translator.parse_tool_invocation("anthropic", raw)
        assert tc.name == "create_object"
        assert tc.arguments == {"name": "cube"}

    def test_parse_tool_invocation_deepseek(self):
        raw = {"id": "call_456", "function": {"name": "rotate", "arguments": {"angle": 45}}}
        tc = self.translator.parse_tool_invocation("deepseek", raw)
        assert tc.name == "rotate"
        assert tc.arguments == {"angle": 45}

    def test_empty_tools(self):
        result = self.translator.translate_tools_for_provider("openai", [])
        assert result == []

    def test_handles_missing_fields(self):
        incomplete_tool = {"name": "test"}
        result = self.translator.to_openai_format(incomplete_tool)
        assert result["function"]["name"] == "test"
        assert result["function"]["description"] == ""
        assert result["function"]["parameters"] == {}
