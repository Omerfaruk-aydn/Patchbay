"""Agent - Agent loop with Plan/Build modes, streaming, tool execution."""

from __future__ import annotations

import json
import re
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from patchbay.providers import StreamAccumulator, stream_completion
from patchbay.tui.tools import TOOL_DEFINITIONS, WRITE_TOOLS, execute_tool


SYSTEM_PROMPT = """You are Patchbay AI, an expert software engineering assistant embedded in a CLI tool.

You help with writing, reading, editing, and debugging code. You understand codebases and can run shell commands.

Tools: read_file, write_file, edit_file, patch_file, delete_file, rename_file, copy_file, create_directory, grep_search, glob_search, list_directory, run_bash, run_tests, run_linter, run_formatter, git_status, git_diff, git_log, git_blame, web_fetch.
Rules: prefer edit_file over write_file, verify changes, be concise, never commit secrets."""


class AgentLoop:
    """Handles the LLM interaction loop with tool execution."""

    def __init__(self, console: Console, theme: Any):
        self.console = console
        self.theme = theme
        self.is_generating = False
        self.max_tool_rounds = 15

    def get_tools_for_mode(self, mode: str) -> list[dict]:
        if mode == "build":
            return TOOL_DEFINITIONS
        # Plan mode: read-only tools
        read_only = {"read_file", "grep_search", "glob_search", "list_directory", "git_status", "git_diff", "git_log", "git_blame", "web_fetch"}
        return [t for t in TOOL_DEFINITIONS if t["function"]["name"] in read_only]

    def run(self, provider: str, model: str, messages: list[dict], mode: str,
            on_tool_call: Any = None, on_tool_result: Any = None,
            on_stream: Any = None) -> dict | None:
        """Run the agent loop. Returns the final assistant message."""
        self.is_generating = True
        tools = self.get_tools_for_mode(mode)

        try:
            for round_num in range(self.max_tool_rounds):
                acc = StreamAccumulator()
                full = ""

                # Show streaming indicator
                self.console.print(f"[bold {self.theme.rich_success}]AI:[/]")

                try:
                    for chunk in stream_completion(provider, model, messages, tools=tools):
                        text = acc.process_chunk(chunk)
                        if text:
                            full += text
                            if on_stream:
                                on_stream(full)
                            else:
                                self.console.print(text, end="", highlight=False)
                        if acc.error:
                            self.console.print(f"\n[{self.theme.rich_error}]Error: {acc.error}[/]")
                            self.is_generating = False
                            return None
                except KeyboardInterrupt:
                    self.console.print(f"\n[{self.theme.rich_warning}]Interrupted.[/]")
                    self.is_generating = False
                    return None
                except Exception as e:
                    self.console.print(f"\n[{self.theme.rich_error}]Error: {e}[/]")
                    self.is_generating = False
                    return None

                self.console.print()

                if acc.error:
                    self.is_generating = False
                    return None

                resp = acc.finalize()
                messages.append(resp)

                tool_calls = resp.get("tool_calls", [])
                if not tool_calls:
                    self.is_generating = False
                    return resp

                # Execute tools
                for tc in tool_calls:
                    func = tc.get("function", {})
                    name = func.get("name", "")
                    try:
                        args = json.loads(func.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        args = {}

                    # Permission check
                    if name in WRITE_TOOLS:
                        if on_tool_call:
                            perm = on_tool_call(name, args)
                            if perm == "deny":
                                messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                                messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": "Denied by user"})
                                continue

                    # Show tool call
                    args_s = ", ".join(f"{k}={repr(v)[:40]}" for k, v in args.items())
                    self.console.print()
                    self.console.print(f"[{self.theme.rich_warning}] >[/] [bold]{name}[/] [{self.theme.rich_muted}]({args_s})[/]")

                    # Execute
                    result = execute_tool(name, args)

                    # Show result
                    if on_tool_result:
                        on_tool_result(name, args, result)
                    else:
                        if result.get("error"):
                            self.console.print(f"  [{self.theme.rich_error}]x[/] {result['error'][:150]}")
                        else:
                            r = self._format_result(name, result)
                            for line in r.split("\n")[:6]:
                                self.console.print(f"  [{self.theme.rich_muted}]{line}[/]")

                    # Format for LLM
                    result_text = self._format_result(name, result)
                    clean = re.sub(r'\[/?[a-zA-Z_][^\]]*\]', '', result_text)
                    if len(clean) > 8000:
                        clean = clean[:8000] + "\n... truncated"

                    messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                    messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": clean})

            self.is_generating = False
            return None

        finally:
            self.is_generating = False

    def _format_result(self, name: str, result: dict) -> str:
        if name == "read_file":
            return result.get("content", "")[:400]
        if name == "run_bash":
            out = result.get("stdout", "")[:200]
            err = result.get("stderr", "")[:100]
            rc = result.get("returncode", "?")
            return f"{out}\n{err}\nexit:{rc}" if out or err else f"exit:{rc}"
        if name in ("grep_search", "search_content"):
            matches = result.get("matches", [])
            return "\n".join(f"{m['file']}:{m['line']} {m['content'][:80]}" for m in matches[:10]) or "no matches"
        if name in ("glob_search", "search_files"):
            files = result.get("files", [])
            return f"{result.get('total',0)} files\n" + "\n".join(files[:10])
        if name in ("git_status", "git_diff", "git_log", "git_blame"):
            return result.get("stdout", "")[:400] or result.get("error", "no output")
        if name in ("write_file", "edit_file", "patch_file"):
            return result.get("path", "?")
        if name == "list_directory":
            entries = result.get("entries", [])
            return "\n".join(f"{'[dir]' if e['type'] == 'dir' else '    '} {e['name']}" for e in entries[:20])
        if name == "web_fetch":
            return result.get("content", "")[:400] or result.get("error", "no content")
        return json.dumps(result, indent=2)[:300]
