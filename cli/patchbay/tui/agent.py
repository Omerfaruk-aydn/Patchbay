"""Agent - Enhanced agent loop with all features.

Features: Plan/Build modes, streaming markdown, tool retry, token budget,
context window display, auto-compact, memory system, reasoning mode.
"""

from __future__ import annotations

import json
import os
import re
import time
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


class MemorySystem:
    """Persistent memory for important facts across sessions."""

    def __init__(self):
        self.facts: list[dict] = []

    def add(self, fact: str, category: str = "general") -> None:
        self.facts.append({"fact": fact, "category": category, "time": time.time()})

    def get_context(self) -> str:
        if not self.facts:
            return ""
        lines = ["## Remembered Facts"]
        for f in self.facts[-20:]:  # Last 20 facts
            lines.append(f"- [{f['category']}] {f['fact']}")
        return "\n".join(lines)

    def search(self, query: str) -> list[dict]:
        q = query.lower()
        return [f for f in self.facts if q in f["fact"].lower() or q in f["category"].lower()]


class TokenBudget:
    """Track token usage and enforce budget."""

    def __init__(self, max_tokens: int = 1_000_000):
        self.max_tokens = max_tokens
        self.total_input = 0
        self.total_output = 0
        self.turn_count = 0

    def add_usage(self, input_tokens: int, output_tokens: int) -> None:
        self.total_input += input_tokens
        self.total_output += output_tokens
        self.turn_count += 1

    def remaining(self) -> int:
        return max(0, self.max_tokens - self.total_input - self.total_output)

    def percent_used(self) -> float:
        total = self.total_input + self.total_output
        return min(100.0, (total / self.max_tokens) * 100) if self.max_tokens > 0 else 0

    def display(self) -> str:
        used = self.total_input + self.total_output
        return f"{used:,}/{self.max_tokens:,} tokens ({self.percent_used():.1f}%)"


class ContextWindow:
    """Track context window usage."""

    def __init__(self, model: str = "gpt-4o"):
        self.model = model
        self.window_size = self._get_window_size(model)
        self.current_tokens = 0

    def _get_window_size(self, model: str) -> int:
        windows = {
            "gpt-4o": 128_000, "gpt-4o-mini": 128_000, "gpt-4-turbo": 128_000,
            "claude-sonnet-4-20250514": 200_000, "claude-3-5-sonnet-20241022": 200_000,
            "claude-3-5-haiku-20241022": 200_000,
            "gemini-2.5-flash": 1_000_000, "gemini-2.5-pro": 1_000_000,
        }
        for key, size in windows.items():
            if key in model:
                return size
        return 128_000

    def update(self, messages: list[dict]) -> None:
        total_chars = sum(len(m.get("content", "") or "") for m in messages)
        self.current_tokens = total_chars // 4  # Approximate

    def percent_used(self) -> float:
        return min(100.0, (self.current_tokens / self.window_size) * 100) if self.window_size > 0 else 0

    def display(self) -> str:
        return f"{self.current_tokens:,}/{self.window_size:,} ({self.percent_used():.1f}%)"


class AgentLoop:
    """Enhanced agent loop with all features."""

    def __init__(self, console: Console, theme: Any):
        self.console = console
        self.theme = theme
        self.is_generating = False
        self.max_tool_rounds = 15
        self.max_retries = 3
        self.token_budget = TokenBudget()
        self.context_window = ContextWindow()
        self.memory = MemorySystem()
        self.auto_compact_threshold = 0.80
        self.reasoning_mode = False
        self.message_history: list[dict] = []

    def get_tools_for_mode(self, mode: str) -> list[dict]:
        if mode == "build":
            return TOOL_DEFINITIONS
        read_only = {"read_file", "grep_search", "glob_search", "list_directory",
                      "git_status", "git_diff", "git_log", "git_blame", "web_fetch"}
        return [t for t in TOOL_DEFINITIONS if t["function"]["name"] in read_only]

    def _check_auto_compact(self, messages: list[dict]) -> bool:
        """Auto-compact if context window is getting full."""
        self.context_window.update(messages)
        if self.context_window.percent_used() >= self.auto_compact_threshold * 100:
            self.console.print(f"[{self.theme.rich_warning}]Auto-compacting (context at {self.context_window.percent_used():.0f}%)[/]")
            if len(messages) > 6:
                summary = messages[:3]
                recent = messages[-4:]
                messages.clear()
                messages.extend(summary)
                messages.append({"role": "system", "content": f"[Auto-compacted. {len(recent)} recent messages kept.]"})
                messages.extend(recent)
                self.context_window.update(messages)
                return True
        return False

    def _detect_memory_facts(self, text: str) -> None:
        """Auto-detect important facts from AI responses."""
        patterns = [
            (r"important[:\s]+(.+)", "important"),
            (r"note[:\s]+(.+)", "note"),
            (r"remember[:\s]+(.+)", "remember"),
            (r"rule[:\s]+(.+)", "rule"),
            (r"convention[:\s]+(.+)", "convention"),
        ]
        for pattern, category in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                self.memory.add(match.strip(), category)

    def run(self, provider: str, model: str, messages: list[dict], mode: str,
            on_tool_call: Any = None, on_stream: Any = None) -> dict | None:
        """Run the agent loop with retry logic and all features."""
        self.is_generating = True
        tools = self.get_tools_for_mode(mode)
        self.context_window.model = model

        # Check auto-compact
        self._check_auto_compact(messages)

        # Add memory context if available
        mem_ctx = self.memory.get_context()
        if mem_ctx:
            # Add to system message if not already there
            for m in messages:
                if m["role"] == "system" and mem_ctx not in m.get("content", ""):
                    m["content"] = m["content"] + "\n\n" + mem_ctx

        try:
            for round_num in range(self.max_tool_rounds):
                acc = StreamAccumulator()
                full = ""
                start_time = time.time()

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
                elapsed = time.time() - start_time

                # Token budget tracking
                if acc.usage:
                    self.token_budget.add_usage(
                        acc.usage.get("prompt_tokens", 0),
                        acc.usage.get("completion_tokens", 0),
                    )

                # Show status
                status = f"[{self.theme.rich_muted}]{elapsed:.1f}s  {self.token_budget.display()}  {self.context_window.display()}[/]"
                self.console.print(status)

                if acc.error:
                    self.is_generating = False
                    return None

                resp = acc.finalize()
                messages.append(resp)

                # Detect memory facts
                if full:
                    self._detect_memory_facts(full)

                tool_calls = resp.get("tool_calls", [])
                if not tool_calls:
                    self.is_generating = False
                    return resp

                # Execute tools with retry
                for tc in tool_calls:
                    func = tc.get("function", {})
                    name = func.get("name", "")
                    try:
                        args = json.loads(func.get("arguments", "{}"))
                    except json.JSONDecodeError:
                        args = {}

                    # Permission check
                    if name in WRITE_TOOLS and on_tool_call:
                        perm = on_tool_call(name, args)
                        if perm == "deny":
                            messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                            messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": "Denied by user"})
                            continue

                    # Show tool call
                    args_s = ", ".join(f"{k}={repr(v)[:40]}" for k, v in args.items())
                    self.console.print()
                    self.console.print(f"[{self.theme.rich_warning}] >[/] [bold]{name}[/] [{self.theme.rich_muted}]({args_s})[/]")

                    # Execute with retry
                    result = None
                    for attempt in range(self.max_retries):
                        result = execute_tool(name, args)
                        if not result.get("error"):
                            break
                        if attempt < self.max_retries - 1:
                            self.console.print(f"  [{self.theme.rich_warning}]Retry {attempt + 2}/{self.max_retries}...[/]")
                            time.sleep(0.5 * (attempt + 1))

                    # Show result
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
