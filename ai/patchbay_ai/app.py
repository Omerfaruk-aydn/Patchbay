"""App - Main REPL application for Patchbay AI."""

from __future__ import annotations

import os
import sys
import json
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich import box

from patchbay_ai.provider import chat_completion, get_config, save_config, get_api_key
from patchbay_ai.tools import TOOLS, execute_tool
from patchbay_ai.session import save_session, load_session, list_sessions, delete_session

console = Console()
error_console = Console(stderr=True)

# ─── ANSI Colors ───
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
WHITE = "\033[37m"
BG_DARK = "\033[40m"
GRAY = "\033[90m"

DEFAULT_MODEL = "gpt-4o"
DEFAULT_PROVIDER = "openai"
MAX_TOOL_ROUNDS = 10

SYSTEM_PROMPT = """You are Patchbay AI, an expert software engineering assistant. You help users with coding tasks, debugging, refactoring, and understanding codebases.

You have access to the following tools:
- read_file: Read file contents
- write_file: Write/create files
- edit_file: Make precise edits to files
- run_bash: Execute shell commands
- search_files: Find files by pattern
- search_content: Search file contents with regex
- list_directory: List directory contents

When making edits, prefer using edit_file with exact string replacements over rewriting entire files.
Always verify your changes work by running relevant tests or linting commands.
Be concise and direct. Focus on the task at hand."""


def get_project_context() -> str:
    """Gather project context from the current directory."""
    context_parts = []

    cwd = os.getcwd()
    context_parts.append(f"Working directory: {cwd}")

    # Check for key files
    key_files = ["README.md", "CLAUDE.md", "AGENTS.md", "pyproject.toml", "package.json", "Cargo.toml"]
    for f in key_files:
        p = Path(f)
        if p.exists():
            try:
                content = p.read_text(encoding="utf-8")[:2000]
                context_parts.append(f"\n--- {f} ---\n{content}")
            except Exception:
                pass

    # List top-level structure
    try:
        entries = []
        for item in sorted(Path(".").iterdir()):
            if item.name.startswith(".") or item.name == "node_modules":
                continue
            kind = "d" if item.is_dir() else "f"
            entries.append(f"  {'[' if kind == 'd' else ' '}{kind}{']' if kind == 'd' else ' '} {item.name}")
        if entries:
            context_parts.append("\n--- Project Structure ---\n" + "\n".join(entries[:30]))
    except Exception:
        pass

    return "\n".join(context_parts)


def print_banner():
    """Print the startup banner."""
    banner = f"""{CYAN}{BOLD}
   ____            _                 ____  __  _____ ____ 
  |  _ \  ___  ___| | _____   _____| __ )/ / |_   _|  _ \\
  | | | |/ _ \\/ __| |/ / _ \\ / / _ \  _ \ / /   | | | | |
  | |_| |  __/\\__ \\   < (_) | (_)  __/ |_) / /    | | |_| |
  |____/ \___||___/_|\_\\___/ \___/\___/____/      |_| |____/
{RESET}{DIM}  Interactive AI Coding Assistant  v0.1.0{RESET}
"""
    console.print(banner)


def print_help():
    """Print help text."""
    help_text = f"""
{BOLD}{CYAN}Commands:{RESET}
  {WHITE}/help{RESET}     Show this help
  {WHITE}/model{RESET}    Switch model (e.g. /model gpt-4o)
  {WHITE}/provider{RESET} Switch provider (openai, anthropic, deepseek, openrouter, patchbay)
  {WHITE}/clear{RESET}    Clear conversation history
  {WHITE}/history{RESET}  Show conversation history
  {WHITE}/save{RESET}     Save conversation to disk
  {WHITE}/load{RESET}     Load a saved conversation
  {WHITE}/sessions{RESET} List saved sessions
  {WHITE}/config{RESET}   Show/set configuration
  {WHITE}/quit{RESET}     Exit
  {WHITE}/exit{RESET}     Exit

{BOLD}{CYAN}Tips:{RESET}
  - Describe what you want to do and I'll help
  - I can read, write, and edit files
  - I can run bash commands
  - I can search codebases
  - Use {WHITE}@filename{RESET} to mention a file
"""
    console.print(help_text)


def handle_command(line: str, messages: list[dict], provider: str, model: str) -> tuple[str, str, bool]:
    """Handle slash commands. Returns (provider, model, should_continue)."""
    parts = line.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "/help" or cmd == "/h":
        print_help()

    elif cmd == "/quit" or cmd == "/exit" or cmd == "/q":
        console.print(f"\n{DIM}Goodbye!{RESET}")
        raise SystemExit(0)

    elif cmd == "/clear":
        messages.clear()
        console.print(f"{GREEN}Conversation cleared.{RESET}")

    elif cmd == "/model":
        if arg:
            model = arg.strip()
            console.print(f"{GREEN}Model set to: {model}{RESET}")
        else:
            console.print(f"{YELLOW}Current model: {model}{RESET}")
            console.print(f"{DIM}Usage: /model <model-name>{RESET}")

    elif cmd == "/provider":
        if arg:
            provider = arg.strip().lower()
            console.print(f"{GREEN}Provider set to: {provider}{RESET}")
        else:
            console.print(f"{YELLOW}Current provider: {provider}{RESET}")
            console.print(f"{DIM}Options: openai, anthropic, deepseek, openrouter, patchbay{RESET}")

    elif cmd == "/history":
        if not messages:
            console.print(f"{DIM}No messages yet.{RESET}")
        else:
            for m in messages:
                role = m["role"]
                if role == "system":
                    continue
                color = GREEN if role == "assistant" else CYAN
                prefix = "You" if role == "user" else "AI"
                content = m["content"] if isinstance(m["content"], str) else json.dumps(m["content"])[:200]
                console.print(f"\n{BOLD}{color}{prefix}:{RESET} {content[:300]}")

    elif cmd == "/save":
        sid = str(uuid.uuid4())[:8]
        save_session(sid, messages)
        console.print(f"{GREEN}Session saved: {sid}{RESET}")

    elif cmd == "/sessions":
        sessions = list_sessions()
        if not sessions:
            console.print(f"{DIM}No saved sessions.{RESET}")
        else:
            for s in sessions[:10]:
                console.print(f"  {CYAN}{s['id']}{RESET}  {s['updated_at'][:19]}  {s['message_count']} messages")

    elif cmd == "/load":
        if arg:
            data = load_session(arg.strip())
            if data:
                messages.clear()
                messages.extend(data.get("messages", []))
                console.print(f"{GREEN}Loaded session {arg} ({len(messages)} messages){RESET}")
            else:
                console.print(f"{RED}Session not found: {arg}{RESET}")
        else:
            console.print(f"{DIM}Usage: /load <session-id>{RESET}")

    elif cmd == "/config":
        config = get_config()
        if arg:
            parts = arg.split(maxsplit=1)
            if len(parts) == 2:
                config[parts[0]] = parts[1]
                save_config(config)
                console.print(f"{GREEN}Set {parts[0]} = {parts[1]}{RESET}")
            else:
                console.print(f"{RED}Usage: /config <key> <value>{RESET}")
        else:
            table = Table(box=box.SIMPLE, border_style="cyan")
            table.add_column("Key", style="bold")
            table.add_column("Value")
            for k, v in config.items():
                val = v if "key" not in k.lower() else "***" + str(v)[-4:] if len(str(v)) > 4 else "***"
                table.add_row(k, str(val))
            console.print(table)

    else:
        console.print(f"{RED}Unknown command: {cmd}{RESET}  (type /help for help)")

    return provider, model, True


def format_tool_result(name: str, result: dict) -> str:
    """Format tool result for display."""
    if result.get("error"):
        return f"[Tool Error] {name}: {result['error']}"

    if name == "read_file":
        return result.get("content", "")
    elif name == "run_bash":
        parts = []
        if result.get("stdout"):
            parts.append(result["stdout"])
        if result.get("stderr"):
            parts.append(f"STDERR: {result['stderr']}")
        return "\n".join(parts) if parts else f"Exit code: {result.get('returncode', '?')}"
    elif name == "search_files":
        files = result.get("files", [])
        return "\n".join(files) if files else "No files found"
    elif name == "search_content":
        matches = result.get("matches", [])
        if not matches:
            return "No matches found"
        lines = [f"{m['file']}:{m['line']}: {m['content']}" for m in matches]
        return "\n".join(lines)
    elif name == "list_directory":
        entries = result.get("entries", [])
        return "\n".join(f"{'[d]' if e['type'] == 'dir' else '   '} {e['name']}" for e in entries)
    else:
        return json.dumps(result, indent=2)


def render_markdown_safe(text: str) -> None:
    """Render markdown text with Rich."""
    try:
        md = Markdown(text)
        console.print(md)
    except Exception:
        console.print(text)


def process_streaming_response(
    provider: str,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
) -> dict[str, Any]:
    """Process a streaming response, handling tool calls. Returns final assistant message."""
    all_content = ""
    tool_calls = []
    tool_call_accum: dict[int, dict] = {}
    usage = {}

    try:
        for chunk in chat_completion(provider, model, messages, tools=tools, stream=True):
            # OpenAI format
            if "choices" in chunk:
                choice = chunk["choices"][0]
                delta = choice.get("delta", {})

                # Content
                if delta.get("content"):
                    content = delta["content"]
                    all_content += content
                    console.print(content, end="", highlight=False)

                # Tool calls
                if delta.get("tool_calls"):
                    for tc in delta["tool_calls"]:
                        idx = tc.get("index", 0)
                        if idx not in tool_call_accum:
                            tool_call_accum[idx] = {
                                "id": tc.get("id", ""),
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        if tc.get("id"):
                            tool_call_accum[idx]["id"] = tc["id"]
                        func = tc.get("function", {})
                        if func.get("name"):
                            tool_call_accum[idx]["function"]["name"] = func["name"]
                        if func.get("arguments"):
                            tool_call_accum[idx]["function"]["arguments"] += func["arguments"]

                if chunk.get("usage"):
                    usage = chunk["usage"]

            # Anthropic format
            elif "type" in chunk:
                event_type = chunk["type"]

                if event_type == "content_block_delta":
                    delta = chunk.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        all_content += text
                        console.print(text, end="", highlight=False)
                    elif delta.get("type") == "input_json_delta":
                        # Accumulate tool args
                        if tool_call_accum:
                            last_idx = max(tool_call_accum.keys())
                            tool_call_accum[last_idx]["function"]["arguments"] += delta.get("partial_json", "")

                elif event_type == "content_block_start":
                    block = chunk.get("content_block", {})
                    if block.get("type") == "tool_use":
                        idx = len(tool_call_accum)
                        tool_call_accum[idx] = {
                            "id": block.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": block.get("name", ""),
                                "arguments": "",
                            },
                        }

                elif event_type == "message_delta":
                    usage = chunk.get("usage", usage)

    except KeyboardInterrupt:
        console.print(f"\n{YELLOW}[Interrupted]{RESET}")
    except Exception as e:
        console.print(f"\n{RED}[Error: {e}]{RESET}")

    console.print()  # newline after streaming

    # Build tool calls list
    tool_calls = []
    for idx in sorted(tool_call_accum.keys()):
        tc = tool_call_accum[idx]
        try:
            args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
        except json.JSONDecodeError:
            args = {}
        tool_calls.append({
            "id": tc["id"],
            "type": "function",
            "function": {
                "name": tc["function"]["name"],
                "arguments": json.dumps(args),
            },
        })

    return {
        "role": "assistant",
        "content": all_content if all_content else None,
        "tool_calls": tool_calls if tool_calls else None,
        "usage": usage,
    }


def execute_tool_calls(tool_calls: list[dict], messages: list[dict]) -> None:
    """Execute tool calls and append results to messages."""
    for tc in tool_calls:
        func = tc.get("function", {})
        name = func.get("name", "")
        try:
            args = json.loads(func.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {}

        console.print(f"\n{GRAY}  > {name}({', '.join(f'{k}={repr(v)[:50]}' for k, v in args.items())}){RESET}")

        result = execute_tool(name, args)

        result_text = format_tool_result(name, result)

        # Truncate long results
        if len(result_text) > 3000:
            result_text = result_text[:3000] + f"\n... ({len(result_text) - 3000} chars truncated)"

        # Add tool call and result to messages
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [tc],
        })
        messages.append({
            "role": "tool",
            "tool_call_id": tc.get("id", ""),
            "content": result_text,
        })


def main():
    """Main entry point for the Patchbay AI REPL."""
    import argparse

    parser = argparse.ArgumentParser(description="Patchbay AI - Interactive coding assistant")
    parser.add_argument("--provider", "-p", default=None, help="LLM provider")
    parser.add_argument("--model", "-m", default=None, help="Model name")
    parser.add_argument("--prompt", "-c", default=None, help="Single prompt (non-interactive)")
    parser.add_argument("--session", "-s", default=None, help="Load a saved session")
    args = parser.parse_args()

    # Determine provider and model
    config = get_config()
    provider = args.provider or config.get("provider", DEFAULT_PROVIDER)
    model = args.model or config.get("model", DEFAULT_MODEL)

    # Init messages
    messages: list[dict] = []

    # Load session if specified
    if args.session:
        data = load_session(args.session)
        if data:
            messages.extend(data.get("messages", []))
            console.print(f"{GREEN}Loaded session {args.session}{RESET}")

    # Single prompt mode
    if args.prompt:
        messages.append({"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()})
        messages.append({"role": "user", "content": args.prompt})
        resp = process_streaming_response(provider, model, messages, tools=TOOLS)
        if resp.get("tool_calls"):
            execute_tool_calls(resp["tool_calls"], messages)
        return

    # Interactive REPL
    print_banner()
    console.print(f"{DIM}  Provider: {provider}  |  Model: {model}  |  Type /help for commands{RESET}\n")

    # Project context
    project_ctx = get_project_context()
    messages.append({"role": "system", "content": SYSTEM_PROMPT + "\n\n" + project_ctx})

    session_id = str(uuid.uuid4())[:8]

    while True:
        try:
            # Prompt
            try:
                line = console.input(f"{BOLD}{CYAN}>{RESET} ")
            except EOFError:
                console.print(f"\n{DIM}Goodbye!{RESET}")
                break

            if not line.strip():
                continue

            # Handle commands
            if line.strip().startswith("/"):
                provider, model, _ = handle_command(line, messages, provider, model)
                continue

            # Add user message
            messages.append({"role": "user", "content": line})

            # Tool loop
            for round_num in range(MAX_TOOL_ROUNDS):
                resp = process_streaming_response(provider, model, messages, tools=TOOLS)

                # Add assistant message to history
                messages.append(resp)

                # Execute tool calls if any
                if resp.get("tool_calls"):
                    execute_tool_calls(resp["tool_calls"], messages)
                    # Continue loop for another LLM turn after tool execution
                else:
                    # No tool calls - done
                    break

            # Auto-save periodically
            if len(messages) % 20 == 0:
                save_session(session_id, messages)

        except SystemExit:
            break
        except KeyboardInterrupt:
            console.print(f"\n{YELLOW}[Interrupted - type /quit to exit]{RESET}")
        except Exception as e:
            console.print(f"\n{RED}[Error: {e}]{RESET}")

    # Save final session
    save_session(session_id, messages)


if __name__ == "__main__":
    main()
