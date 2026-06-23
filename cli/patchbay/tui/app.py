"""Patchbay CLI - MiMoCode/Codex-style REPL.

NOT a full-screen TUI. A simple line-based REPL like MiMoCode/Codex:
- User types a message
- AI responds with streaming text
- Tool calls shown inline
- Slash commands for config
- Clean, minimal output
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from patchbay.config import get_config, set_config_value
from patchbay.providers import StreamAccumulator, fetch_models_cached, stream_completion
from patchbay.session import list_sessions, load_session, save_session
from patchbay.tools import TOOLS_SPEC, execute_tool
from patchbay.gateway import blender_get_scene, get_full_status, list_models

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

console = Console(force_terminal=True, color_system="truecolor")

SYSTEM_PROMPT = """You are Patchbay AI, an expert software engineering assistant embedded in a CLI tool.

You help with writing, reading, editing, and debugging code. You understand codebases and can run shell commands.

Tools: read_file, write_file, edit_file, run_bash, search_files, search_content, list_directory.
Rules: prefer edit_file over write_file, verify changes, be concise, never commit secrets."""


def get_project_context() -> str:
    parts = [f"Working directory: {os.getcwd()}"]
    for fname in ["README.md", "CLAUDE.md", "pyproject.toml", "package.json"]:
        p = Path(fname)
        if p.exists():
            try:
                parts.append(f"\n--- {fname} ---\n{p.read_text(encoding='utf-8', errors='replace')[:2000]}")
            except Exception:
                pass
    return "\n".join(parts)


def _fmt_result(name: str, result: dict) -> str:
    if name == "read_file":
        return result.get("content", "")[:400]
    if name == "run_bash":
        out = result.get("stdout", "")[:200]
        err = result.get("stderr", "")[:100]
        rc = result.get("returncode", "?")
        return f"{out}\n{err}\nexit:{rc}" if out or err else f"exit:{rc}"
    if name == "search_files":
        files = result.get("files", [])
        return f"{result.get('total',0)} files\n" + "\n".join(files[:10])
    if name == "search_content":
        matches = result.get("matches", [])
        return "\n".join(f"{m['file']}:{m['line']} {m['content'][:80]}" for m in matches[:10]) or "no matches"
    if name in ("write_file", "edit_file"):
        return result.get("path", "?")
    return json.dumps(result, indent=2)[:300]


# ═══════════════════════════════════════════════════════════════
# REPL
# ═══════════════════════════════════════════════════════════════

def main():
    cfg = get_config()
    provider = cfg.get("provider", "openai")
    model = cfg.get("model", "gpt-4o")
    session_id = str(uuid.uuid4())[:8]
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()},
    ]

    # Welcome
    console.print()
    console.print("[bold #7aa2f7]Patchbay AI[/] [#565f89]|[/] Universal LLM Gateway")
    console.print(f"[#565f89]{provider} | {model} | {session_id}[/]")
    console.print(f"[#565f89]Type your message or / for commands. Ctrl+C to exit.[/]")
    console.print()

    while True:
        try:
            line = console.input("[bold #7aa2f7]>[/] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[#565f89]Goodbye.[/]")
            break

        if not line.strip():
            continue

        # Slash commands
        if line.strip().startswith("/"):
            _cmd(line.strip(), messages, provider, model, session_id, cfg)
            cfg = get_config()
            provider = cfg.get("provider", provider)
            model = cfg.get("model", model)
            continue

        # User message
        messages.append({"role": "user", "content": line})
        console.print()
        console.print(f"[bold #7aa2f7]You:[/]")
        console.print(line)
        console.print()

        # LLM response
        _llm(provider, model, messages)


def _llm(provider: str, model: str, messages: list[dict]):
    acc = StreamAccumulator()
    full = ""

    console.print(f"[bold #9ece6a]AI:[/]")

    try:
        for chunk in stream_completion(provider, model, messages, tools=TOOLS_SPEC):
            text = acc.process_chunk(chunk)
            if text:
                full += text
                console.print(text, end="", highlight=False)
            if acc.error:
                console.print(f"\n[red]Error: {acc.error}[/red]")
                break
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")

    console.print()

    if acc.error:
        return

    resp = acc.finalize()
    messages.append(resp)

    tool_calls = resp.get("tool_calls", [])
    if tool_calls:
        _tools(tool_calls, messages, provider, model)


def _tools(tool_calls: list[dict], messages: list[dict], provider: str, model: str):
    for tc in tool_calls:
        func = tc.get("function", {})
        name = func.get("name", "")
        try:
            args = json.loads(func.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {}

        # Show tool call
        args_s = ", ".join(f"{k}={repr(v)[:40]}" for k, v in args.items())
        console.print()
        console.print(f"[#e0af68]>[/] [bold]{name}[/][#565f89]({args_s})[/]")

        # Execute
        result = execute_tool(name, args)

        # Show result
        if result.get("error"):
            console.print(f"  [red]x[/] {result['error'][:150]}")
        else:
            r = _fmt_result(name, result)
            for line in r.split("\n")[:6]:
                console.print(f"  [#565f89]{line}[/]")

        # Format for LLM
        result_text = _fmt_result(name, result)
        clean = re.sub(r'\[/?[a-zA-Z_][^\]]*\]', '', result_text)
        if len(clean) > 8000:
            clean = clean[:8000] + "\n... truncated"

        messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
        messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": clean})

    # Continue after tools
    _llm(provider, model, messages)


def _cmd(text: str, messages: list[dict], provider: str, model: str, session_id: str, cfg: dict):
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd in ("/quit", "/exit", "/q"):
        console.print("[#565f89]Goodbye.[/]")
        raise SystemExit(0)

    elif cmd in ("/help", "/h", "/?"):
        console.print()
        console.print("[bold #7aa2f7]Commands[/]")
        console.print("  [#c0caf5]/help[/]          This help")
        console.print("  [#c0caf5]/clear[/]         Clear conversation")
        console.print("  [#c0caf5]/model[/] [dim]<name>[/dim]  Switch model")
        console.print("  [#c0caf5]/provider[/] [dim]<name>[/dim]  Switch provider")
        console.print("  [#c0caf5]/status[/]        Gateway status")
        console.print("  [#c0caf5]/models[/]        List models")
        console.print("  [#c0caf5]/sessions[/]      List sessions")
        console.print("  [#c0caf5]/save[/]          Save session")
        console.print("  [#c0caf5]/config[/]        Show config")
        console.print("  [#c0caf5]/quit[/]          Exit")
        console.print()

    elif cmd == "/clear":
        messages.clear()
        messages.append({"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()})
        console.print("[#9ece6a]Cleared.[/]")

    elif cmd == "/model":
        if arg:
            model = arg.strip()
            set_config_value("model", model)
            console.print(f"[#9ece6a]Model: {model}[/]")
        else:
            console.print(f"[#565f89]Current: {model}[/]")
            console.print("[#565f89]Usage: /model <name>[/]")

    elif cmd == "/provider":
        if arg:
            provider = arg.strip().lower()
            set_config_value("provider", provider)
            console.print(f"[#9ece6a]Provider: {provider}[/]")
        else:
            console.print(f"[#565f89]Current: {provider}[/]")
            console.print("[#565f89]Usage: /provider <name>[/]")

    elif cmd == "/status":
        items = get_full_status()
        console.print()
        console.print("[bold #7aa2f7]Status[/]")
        for name, color, detail in items:
            c = "#9ece6a" if color == "green" else "#f7768e"
            console.print(f"  [{c}]+[/] [#c0caf5]{name}[/] [#565f89]{detail}[/]")
        console.print()

    elif cmd == "/models":
        models = list_models()
        if models:
            console.print(f"[bold #7aa2f7]Models ({len(models)})[/]")
            for m in models[:30]:
                console.print(f"  [#c0caf5]{m.get('id','?')}[/]")
        else:
            console.print("[#565f89]No models. Is gateway running?[/]")

    elif cmd == "/sessions":
        sessions = list_sessions()
        if not sessions:
            console.print("[#565f89]No sessions.[/]")
            return
        console.print(f"[bold #7aa2f7]Sessions ({len(sessions)})[/]")
        for s in sessions[:10]:
            console.print(f"  [#7aa2f7]{s['id']}[/]  [#565f89]{s.get('updated_at','')[:16]}  {s.get('count',0)} msgs[/]")

    elif cmd == "/save":
        save_session(session_id, messages, {"provider": provider, "model": model})
        console.print(f"[#9ece6a]Saved: {session_id}[/]")

    elif cmd == "/config":
        cfg = get_config()
        console.print("[bold #7aa2f7]Config[/]")
        for k, v in cfg.items():
            if "key" in k.lower():
                v = f"***{str(v)[-4:]}" if len(str(v)) > 4 else "***"
            console.print(f"  [#c0caf5]{k}[/] = [#565f89]{v}[/]")

    elif cmd == "/blender":
        scene = blender_get_scene()
        if "error" in scene:
            console.print(f"[red]Blender: {scene['error']}[/red]")
        else:
            console.print(f"[#7aa2f7]Blender[/] {scene.get('name','?')}  {scene.get('object_count',0)} objects")

    else:
        console.print(f"[red]Unknown: {cmd}[/]  [#565f89]/help[/]")


if __name__ == "__main__":
    main()
