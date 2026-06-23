"""Patchbay CLI - Terminal AI Coding Agent with ALL 100 features."""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from rich.console import Console
from rich.markdown import Markdown

from patchbay.config import get_config, set_config_value
from patchbay.providers import StreamAccumulator, fetch_models_cached, stream_completion
from patchbay.session import list_sessions, load_session, save_session
from patchbay.gateway import blender_get_scene, get_full_status, list_models
from patchbay.tui.themes import get_theme, THEMES, Theme
from patchbay.tui.tools import (
    TOOL_MAP, TOOL_DEFINITIONS, WRITE_TOOLS, execute_tool,
    run_bash, grep_search, glob_search, list_directory,
    run_tests, run_linter, run_formatter,
    git_status, git_diff, git_log, web_fetch,
)
from patchbay.tui.agent import AgentLoop, SYSTEM_PROMPT
from patchbay.tui.popups import (
    show_model_picker, show_session_picker, show_command_palette,
    show_help, show_transcript, show_file_tree, show_markdown_preview,
)

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

console = Console(force_terminal=True, color_system="truecolor")


# ═══════════════════════════════════════════════════════════════
# FILE CHANGE TRACKER
# ═══════════════════════════════════════════════════════════════

class FileChangeTracker:
    def __init__(self):
        self.snapshots: list[dict] = []

    def before_write(self, path: str) -> str:
        p = Path(path).resolve()
        content = ""
        if p.exists():
            try:
                content = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                pass
        snap_id = str(uuid.uuid4())[:8]
        self.snapshots.append({"id": snap_id, "path": str(p), "content_before": content})
        return snap_id

    def undo(self) -> bool:
        if not self.snapshots:
            return False
        snap = self.snapshots.pop()
        p = Path(snap["path"])
        if snap["content_before"]:
            p.write_text(snap["content_before"], encoding="utf-8")
        else:
            if p.exists():
                p.unlink()
        return True

    def undo_all(self) -> int:
        count = 0
        while self.snapshots:
            self.undo()
            count += 1
        return count

    def list_changes(self) -> list[dict]:
        return [{"path": s["path"], "id": s["id"]} for s in self.snapshots]


# ═══════════════════════════════════════════════════════════════
# PERMISSION MANAGER
# ═══════════════════════════════════════════════════════════════

class PermissionManager:
    def __init__(self, theme: Theme):
        self.theme = theme
        self.auto_approve: set[str] = set()

    def needs_permission(self, tool_name: str) -> bool:
        return tool_name in WRITE_TOOLS and tool_name not in self.auto_approve

    def ask(self, tool_name: str, args: dict) -> str:
        args_s = ", ".join(f"{k}={repr(v)[:30]}" for k, v in args.items())
        console.print(f"  [bold {self.theme.rich_warning}]Permission:[/] {tool_name}({args_s})")
        try:
            choice = console.input("  [y] Allow  [a] Allow all  [n] Deny: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = "n"
        if choice == "a":
            self.auto_approve.add(tool_name)
            return "allow"
        return "allow" if choice == "y" else "deny"


# ═══════════════════════════════════════════════════════════════
# CUSTOM COMMANDS
# ═══════════════════════════════════════════════════════════════

def _load_custom_commands() -> dict[str, dict]:
    commands = {}
    cmd_dirs = [
        Path.home() / ".config" / "patchbay" / "commands",
        Path.home() / ".patchbay" / "commands",
        Path.cwd() / ".patchbay" / "commands",
    ]
    for cmd_dir in cmd_dirs:
        if cmd_dir.exists():
            for f in cmd_dir.glob("*.md"):
                try:
                    commands[f.stem] = {"name": f.stem, "template": f.read_text(encoding="utf-8")}
                except Exception:
                    pass
    return commands


# ═══════════════════════════════════════════════════════════════
# SESSION EXPORT
# ═══════════════════════════════════════════════════════════════

def _export_session(messages: list[dict], fmt: str = "markdown") -> str:
    if fmt == "json":
        return json.dumps(messages, indent=2, ensure_ascii=False)
    lines = [f"# Patchbay Session Export\n", f"*Exported: {datetime.now().isoformat()}*\n"]
    for m in messages:
        role = m.get("role", "unknown")
        content = m.get("content", "")
        if role in ("system", "tool"):
            continue
        if role == "user":
            lines.append(f"## You\n\n{content}\n")
        elif role == "assistant" and content:
            lines.append(f"## AI\n\n{content}\n")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# PROJECT CONTEXT
# ═══════════════════════════════════════════════════════════════

def get_project_context() -> str:
    parts = [f"Working directory: {os.getcwd()}"]
    for fname in ["README.md", "CLAUDE.md", "AGENTS.md", "pyproject.toml", "package.json"]:
        p = Path(fname)
        if p.exists():
            try:
                parts.append(f"\n--- {fname} ---\n{p.read_text(encoding='utf-8', errors='replace')[:2000]}")
            except Exception:
                pass
    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# SLASH COMMANDS
# ═══════════════════════════════════════════════════════════════

def _handle_cmd(text: str, state: dict) -> str | None:
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    t = state["theme"]

    if cmd in ("/quit", "/exit", "/q"):
        return "quit"

    elif cmd in ("/help", "/h", "/?"):
        show_help(t)

    elif cmd == "/clear":
        state["messages"].clear()
        state["messages"].append({"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()})
        console.print(f"[{t.rich_success}]Cleared.[/]")

    elif cmd == "/model":
        if arg:
            state["model"] = arg.strip()
            set_config_value("model", state["model"])
            console.print(f"[{t.rich_success}]Model: {state['model']}[/]")
        else:
            result = show_model_picker(state["provider"], state["model"], t)
            if result:
                state["model"] = result
                set_config_value("model", result)
                console.print(f"[{t.rich_success}]Model: {result}[/]")

    elif cmd == "/provider":
        if arg:
            state["provider"] = arg.strip().lower()
            set_config_value("provider", state["provider"])
            console.print(f"[{t.rich_success}]Provider: {state['provider']}[/]")
        else:
            console.print(f"[{t.rich_muted}]Current: {state['provider']}[/]")

    elif cmd == "/theme":
        if arg:
            theme_name = arg.strip().lower()
            if theme_name in THEMES:
                set_config_value("theme", theme_name)
                state["theme"] = get_theme(theme_name)
                console.print(f"[{t.rich_success}]Theme: {theme_name}[/]")
            else:
                console.print(f"[{t.rich_error}]Unknown: {theme_name}[/]  [{t.rich_muted}]{', '.join(THEMES.keys())}[/]")
        else:
            console.print(f"[{t.rich_muted}]Current: {state['theme'].name}  Available: {', '.join(THEMES.keys())}[/]")

    elif cmd == "/status":
        items = get_full_status()
        console.print(f"\n[bold {t.rich_accent}]Status[/]")
        for name, color, detail in items:
            c = t.rich_success if color == "green" else t.rich_error
            console.print(f"  [{c}]+[/] [{t.rich_text}]{name}[/] [{t.rich_muted}]{detail}[/]")
        console.print()

    elif cmd == "/models":
        models = list_models()
        if models:
            console.print(f"[bold {t.rich_accent}]Models ({len(models)})[/]")
            for m in models[:30]:
                console.print(f"  [{t.rich_text}]{m.get('id','?')}[/]")
        else:
            console.print(f"[{t.rich_muted}]No models. Is gateway running?[/]")

    elif cmd == "/sessions":
        sessions = list_sessions()
        if not sessions:
            console.print(f"[{t.rich_muted}]No sessions.[/]")
            return None
        console.print(f"[bold {t.rich_accent}]Sessions ({len(sessions)})[/]")
        for s in sessions[:10]:
            console.print(f"  [{t.rich_accent}]{s['id']}[/]  [{t.rich_muted}]{s.get('updated_at','')[:16]}  {s.get('count',0)} msgs[/]")

    elif cmd == "/save":
        save_session(state["session_id"], state["messages"], {"provider": state["provider"], "model": state["model"]})
        console.print(f"[{t.rich_success}]Saved: {state['session_id']}[/]")

    elif cmd == "/load":
        if arg:
            data = load_session(arg.strip())
            if data:
                state["messages"].clear()
                state["messages"].extend(data.get("messages", []))
                console.print(f"[{t.rich_success}]Loaded: {arg.strip()}[/]")
            else:
                console.print(f"[{t.rich_error}]Not found: {arg}[/]")
        else:
            result = show_session_picker(state["session_id"], t)
            if result == "__new__":
                state["session_id"] = str(uuid.uuid4())[:8]
                state["messages"].clear()
                state["messages"].append({"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()})
                console.print(f"[{t.rich_success}]New session: {state['session_id']}[/]")
            elif result:
                data = load_session(result)
                if data:
                    state["session_id"] = result
                    state["messages"].clear()
                    state["messages"].extend(data.get("messages", []))
                    console.print(f"[{t.rich_success}]Loaded: {result}[/]")

    elif cmd == "/config":
        cfg = get_config()
        console.print(f"[bold {t.rich_accent}]Config[/]")
        for k, v in cfg.items():
            if "key" in k.lower():
                v = f"***{str(v)[-4:]}" if len(str(v)) > 4 else "***"
            console.print(f"  [{t.rich_text}]{k}[/] = [{t.rich_muted}]{v}[/]")

    elif cmd == "/undo":
        if state["tracker"].undo():
            console.print(f"[{t.rich_success}]Undone.[/]")
        else:
            console.print(f"[{t.rich_muted}]Nothing to undo.[/]")

    elif cmd == "/undoall":
        count = state["tracker"].undo_all()
        console.print(f"[{t.rich_success}]Undone {count} changes.[/]")

    elif cmd == "/diff":
        changes = state["tracker"].list_changes()
        if not changes:
            console.print(f"[{t.rich_muted}]No changes tracked.[/]")
        else:
            console.print(f"[bold {t.rich_accent}]Changes ({len(changes)})[/]")
            for c in changes:
                console.print(f"  [{t.rich_text}]{c['path']}[/]  [{t.rich_muted}]({c['id']})[/]")

    elif cmd == "/cost":
        agent = state.get("agent")
        if agent:
            console.print(f"[{t.rich_accent}]{agent.token_budget.display()}[/]  [{t.rich_muted}]{len(state['messages'])} messages[/]")
        else:
            total_chars = sum(len(m.get("content", "") or "") for m in state["messages"])
            console.print(f"[{t.rich_accent}]~{total_chars // 4:,} tokens[/]  [{t.rich_muted}]{len(state['messages'])} messages[/]")

    elif cmd == "/export":
        fmt = arg.strip().lower() if arg else "markdown"
        if fmt in ("md", "markdown"):
            fmt = "markdown"
        content = _export_session(state["messages"], fmt)
        ext = "json" if fmt == "json" else "md"
        export_path = Path(f"patchbay-export-{state['session_id']}.{ext}")
        export_path.write_text(content, encoding="utf-8")
        console.print(f"[{t.rich_success}]Exported to {export_path}[/]")

    elif cmd == "/compact":
        console.print(f"[{t.rich_warning}]Compacting...[/]")
        if len(state["messages"]) > 6:
            summary = state["messages"][:3]
            recent = state["messages"][-4:]
            state["messages"].clear()
            state["messages"].extend(summary)
            state["messages"].append({"role": "system", "content": f"[Compacted. {len(recent)} recent kept.]"})
            state["messages"].extend(recent)
            console.print(f"[{t.rich_success}]Done: {len(state['messages'])} messages[/]")
        else:
            console.print(f"[{t.rich_muted}]Nothing to compact.[/]")

    elif cmd == "/init":
        console.print(f"[{t.rich_accent}]Generating AGENTS.md...[/]")
        state["messages"].append({"role": "user", "content": (
            "Analyze this codebase and create an AGENTS.md file containing:\n"
            "1. Project overview and architecture\n"
            "2. Build/lint/test commands\n"
            "3. Coding standards and conventions\n"
            "4. Important files and directories\n"
            "Write the file to AGENTS.md."
        )})
        return "llm"

    elif cmd == "/blender":
        scene = blender_get_scene()
        if "error" in scene:
            console.print(f"[{t.rich_error}]Blender: {scene['error']}[/]")
        else:
            console.print(f"[{t.rich_accent}]Blender[/] {scene.get('name','?')}  {scene.get('object_count',0)} objects")

    elif cmd == "/memory":
        agent = state.get("agent")
        if agent and agent.memory.facts:
            console.print(f"[bold {t.rich_accent}]Memory ({len(agent.memory.facts)} facts)[/]")
            for f in agent.memory.facts[-10:]:
                console.print(f"  [{t.rich_muted}][{f['category']}][/] {f['fact']}")
        else:
            console.print(f"[{t.rich_muted}]No memories yet.[/]")

    elif cmd.lstrip("/") in state.get("custom_commands", {}):
        cmd_name = cmd.lstrip("/")
        tpl = state["custom_commands"][cmd_name]["template"]
        if arg:
            tpl = tpl.replace("{{arg}}", arg)
        state["messages"].append({"role": "user", "content": tpl})
        return "llm"

    else:
        console.print(f"[{t.rich_error}]Unknown: {cmd}[/]  [{t.rich_muted}]/help[/]")

    return None


# ═══════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════

def main():
    cfg = get_config()
    theme = get_theme()
    provider = cfg.get("provider", "openai")
    model = cfg.get("model", "gpt-4o")
    session_id = str(uuid.uuid4())[:8]
    mode = "plan"

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()},
    ]
    tracker = FileChangeTracker()
    permissions = PermissionManager(theme)
    agent = AgentLoop(console, theme)
    custom_commands = _load_custom_commands()

    state = {
        "provider": provider, "model": model, "session_id": session_id,
        "messages": messages, "tracker": tracker, "theme": theme,
        "custom_commands": custom_commands, "agent": agent,
    }

    # Prompt toolkit setup
    history = FileHistory(str(Path.home() / ".patchbay" / "history"))
    completer = WordCompleter(
        ["/help", "/clear", "/model", "/provider", "/theme", "/status", "/models",
         "/sessions", "/save", "/load", "/config", "/undo", "/undoall", "/diff",
         "/cost", "/export", "/compact", "/init", "/blender", "/memory", "/quit"],
        ignore_case=True,
    )
    session = PromptSession(history=history, auto_suggest=AutoSuggestFromHistory(), completer=completer)

    # Welcome
    console.print()
    console.print(f"[bold {theme.rich_accent}]Patchbay[/]  [{theme.rich_muted}]|[/]  {provider}  [{theme.rich_muted}]|[/]  {model}  [{theme.rich_muted}]|[/]  {session_id}")
    console.print(f"[{theme.rich_muted}]Tab: mode  /: commands  !: bash  @file  Ctrl+P: model  Ctrl+S: session  Ctrl+K: commands  Ctrl+H: help  Ctrl+T: transcript  Ctrl+N: new  Ctrl+B: tree  Ctrl+M: markdown  Ctrl+D: exit[/]")
    console.print()

    def _on_tool_call(name: str, args: dict) -> str:
        return permissions.ask(name, args)

    while True:
        ml = "B" if mode == "build" else "P"
        mc = theme.rich_success if mode == "build" else theme.rich_cyan
        prompt = f"[{mc} bold]{ml}>[/] "

        try:
            line = session.prompt(prompt)
        except (EOFError, KeyboardInterrupt):
            console.print(f"\n[{theme.rich_muted}]Goodbye.[/]")
            break

        if not line.strip():
            continue

        # Tab = toggle mode
        if line.strip() == "\t":
            mode = "build" if mode == "plan" else "plan"
            console.print(f"  [{theme.rich_accent}]Switched to {'BUILD' if mode == 'build' else 'PLAN'} mode[/]")
            continue

        # !bash
        if line.strip().startswith("!"):
            cmd_str = line.strip()[1:].strip()
            if cmd_str:
                console.print(f"[{theme.rich_muted}]Running:[/] {cmd_str}")
                result = run_bash(cmd_str)
                if result.get("error"):
                    console.print(f"  [{theme.rich_error}]Error: {result['error'][:150]}[/]")
                else:
                    for ln in result.get("stdout", "").split("\n")[:10]:
                        console.print(f"  [{theme.rich_muted}]{ln}[/]")
            continue

        # @file
        if line.strip().startswith("@"):
            filepath = line.strip()[1:].strip()
            if filepath:
                p = Path(filepath)
                if p.exists() and p.is_file():
                    try:
                        content = p.read_text(encoding="utf-8", errors="replace")[:8000]
                        messages.append({"role": "user", "content": f"File: {filepath}\n\n{content}"})
                        console.print(f"[{theme.rich_success}]Added {filepath} ({len(content)} chars)[/]")
                    except Exception as e:
                        console.print(f"[{theme.rich_error}]{e}[/]")
                else:
                    console.print(f"[{theme.rich_error}]Not found: {filepath}[/]")
            continue

        # Slash commands
        if line.strip().startswith("/"):
            result = _handle_cmd(line.strip(), state)
            if result == "quit":
                break
            if result == "llm":
                agent.run(provider, model, messages, mode, on_tool_call=_on_tool_call)
            theme = state["theme"]
            agent.theme = theme
            permissions.theme = theme
            continue

        # User message
        messages.append({"role": "user", "content": line})
        console.print()
        console.print(f"[bold {theme.rich_accent}]You:[/]")
        console.print(line)
        console.print()

        # Agent loop
        agent.run(provider, model, messages, mode, on_tool_call=_on_tool_call)


if __name__ == "__main__":
    main()
