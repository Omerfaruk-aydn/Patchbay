"""Patchbay CLI - Terminal AI Coding Agent.

Based on terminal-ai-agent-prompt.md spec:
- Plan/Build mode toggle (Tab)
- File change tracking + /undo
- Permission system
- Config hierarchy (CLI flags > env > project > user > defaults)
- Theme system (Tokyo Night, Dark, Light, Dracula, Catppuccin, Gruvbox, Nord)
- Custom commands from markdown files
- Session export (markdown, JSON)
- /compact for context management
- Non-interactive mode (-p flag)
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.text import Text

from patchbay.config import get_config, set_config_value
from patchbay.providers import StreamAccumulator, fetch_models_cached, stream_completion
from patchbay.session import list_sessions, load_session, save_session
from patchbay.tools import TOOLS_SPEC, execute_tool
from patchbay.gateway import blender_get_scene, get_full_status, list_models

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

console = Console(force_terminal=True, color_system="truecolor")

# ═══════════════════════════════════════════════════════════════
# THEMES (spec section 6.3)
# ═══════════════════════════════════════════════════════════════

THEMES = {
    "tokyo-night": {
        "bg": "#1a1b26", "surface": "#1f2335", "border": "#3b4261",
        "text": "#c0caf5", "muted": "#565f89",
        "accent": "#7aa2f7", "success": "#9ece6a", "warning": "#e0af68", "error": "#f7768e",
        "cyan": "#7dcfff", "magenta": "#bb9af7", "orange": "#ff9e64",
    },
    "dark": {
        "bg": "#0D1117", "surface": "#161B22", "border": "#30363D",
        "text": "#E6EDF3", "muted": "#8B949E",
        "accent": "#58A6FF", "success": "#3FB950", "warning": "#D29922", "error": "#F85149",
        "cyan": "#79C0FF", "magenta": "#D2A8FF", "orange": "#FFA657",
    },
    "dracula": {
        "bg": "#282A36", "surface": "#44475A", "border": "#6272A4",
        "text": "#F8F8F2", "muted": "#6272A4",
        "accent": "#BD93F9", "success": "#50FA7B", "warning": "#F1FA8C", "error": "#FF5555",
        "cyan": "#8BE9FD", "magenta": "#FF79C6", "orange": "#FFB86C",
    },
    "catppuccin": {
        "bg": "#1E1E2E", "surface": "#313244", "border": "#585B70",
        "text": "#CDD6F4", "muted": "#6C7086",
        "accent": "#89B4FA", "success": "#A6E3A1", "warning": "#F9E2AF", "error": "#F38BA8",
        "cyan": "#94E2D5", "magenta": "#F5C2E7", "orange": "#FAB387",
    },
    "gruvbox": {
        "bg": "#282828", "surface": "#3C3836", "border": "#504945",
        "text": "#EBDBB2", "muted": "#928374",
        "accent": "#83A598", "success": "#B8BB26", "warning": "#FABD2F", "error": "#FB4934",
        "cyan": "#8EC07C", "magenta": "#D3869B", "orange": "#FE8019",
    },
    "nord": {
        "bg": "#2E3440", "surface": "#3B4252", "border": "#434C5E",
        "text": "#ECEFF4", "muted": "#616E88",
        "accent": "#88C0D0", "success": "#A3BE8C", "warning": "#EBCB8B", "error": "#BF616A",
        "cyan": "#8FBCBB", "magenta": "#B48EAD", "orange": "#D08770",
    },
    "light": {
        "bg": "#FFFFFF", "surface": "#F6F8FA", "border": "#D0D7DE",
        "text": "#1F2328", "muted": "#656D76",
        "accent": "#0969DA", "success": "#1A7F37", "warning": "#9A6700", "error": "#CF222E",
        "cyan": "#0550AE", "magenta": "#8250DF", "orange": "#BC4C00",
    },
}

def _t(key: str) -> str:
    """Get current theme color."""
    cfg = get_config()
    theme_name = cfg.get("theme", "tokyo-night")
    theme = THEMES.get(theme_name, THEMES["tokyo-night"])
    return theme.get(key, "#c0caf5")

# ═══════════════════════════════════════════════════════════════
# FILE CHANGE TRACKER (spec section 14)
# ═══════════════════════════════════════════════════════════════

class FileChangeTracker:
    def __init__(self, session_id: str):
        self.session_id = session_id
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
# PERMISSION SYSTEM (spec section 4.3)
# ═══════════════════════════════════════════════════════════════

WRITE_TOOLS = {"write_file", "edit_file", "run_bash", "delete_file"}

class PermissionManager:
    def __init__(self):
        self.auto_approve: set[str] = set()

    def needs_permission(self, tool_name: str) -> bool:
        if tool_name in self.auto_approve:
            return False
        return tool_name in WRITE_TOOLS

    def ask_permission(self, tool_name: str, args: dict) -> str:
        args_s = ", ".join(f"{k}={repr(v)[:30]}" for k, v in args.items())
        console.print(f"  [bold {_t('warning')}]Permission required:[/] {tool_name}({args_s})")
        try:
            choice = console.input("  [y] Allow  [a] Allow all  [n] Deny: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = "n"
        if choice == "a":
            self.auto_approve.add(tool_name)
            return "allow"
        return "allow" if choice == "y" else "deny"

# ═══════════════════════════════════════════════════════════════
# CUSTOM COMMANDS (spec section 10)
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
                    content = f.read_text(encoding="utf-8")
                    name = f.stem
                    commands[name] = {"name": name, "template": content, "source": str(f)}
                except Exception:
                    pass
    return commands

# ═══════════════════════════════════════════════════════════════
# SESSION EXPORT (spec section 9.2)
# ═══════════════════════════════════════════════════════════════

def _export_session(messages: list[dict], fmt: str = "markdown") -> str:
    if fmt == "json":
        return json.dumps(messages, indent=2, ensure_ascii=False)
    lines = [f"# Patchbay Session Export\n", f"*Exported: {datetime.now().isoformat()}*\n"]
    for m in messages:
        role = m.get("role", "unknown")
        content = m.get("content", "")
        if role == "system":
            continue
        if role == "tool":
            continue
        if role == "user":
            lines.append(f"## You\n\n{content}\n")
        elif role == "assistant" and content:
            lines.append(f"## AI\n\n{content}\n")
    return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════

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
# HEADER / STATUS BAR
# ═══════════════════════════════════════════════════════════════

def _print_header(provider: str, model: str, session_id: str, mode: str):
    console.print()
    ac = _t('accent')
    console.print(
        f"[bold {ac}]Patchbay[/]"
        f"  [#565f89]|[/]  {provider}"
        f"  [#565f89]|[/]  {model}"
        f"  [#565f89]|[/]  {session_id}"
    )

def _print_status_bar(mode: str, file_changes: int = 0):
    mc = _t('success') if mode == "build" else _t('cyan')
    ml = "BUILD" if mode == "build" else "PLAN"
    ch = f"  [#565f89]|[/]  {file_changes} changes" if file_changes > 0 else ""
    console.print(
        f"[#1f2335]  [{mc} bold]{ml}[/]  "
        f"[#565f89]Tab: switch mode  /: commands  !: bash[/]{ch}[/]"
    )

def _print_input_prompt(mode: str):
    mc = _t('success') if mode == "build" else _t('cyan')
    ch = "B" if mode == "build" else "P"
    try:
        return console.input(f"[{mc} bold]{ch}>[/] ")
    except (EOFError, KeyboardInterrupt):
        return "/quit"


# ═══════════════════════════════════════════════════════════════
# REPL
# ═══════════════════════════════════════════════════════════════

def main():
    cfg = get_config()
    provider = cfg.get("provider", "openai")
    model = cfg.get("model", "gpt-4o")
    session_id = str(uuid.uuid4())[:8]
    mode = "plan"  # Plan/Build mode
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()},
    ]
    tracker = FileChangeTracker(session_id)
    permissions = PermissionManager()
    custom_commands = _load_custom_commands()

    # Welcome
    _print_header(provider, model, session_id, mode)
    _print_status_bar(mode)
    console.print()

    while True:
        try:
            line = _print_input_prompt(mode)
        except SystemExit:
            break

        if not line.strip():
            continue

        # Tab = toggle mode
        if line.strip() == "\t":
            mode = "build" if mode == "plan" else "plan"
            console.print(f"  [{_t('accent')}]Switched to {'BUILD' if mode == 'build' else 'PLAN'} mode[/]")
            _print_status_bar(mode, len(tracker.snapshots))
            continue

        # ! prefix = bash shortcut
        if line.strip().startswith("!"):
            cmd_str = line.strip()[1:].strip()
            if cmd_str:
                messages.append({"role": "user", "content": f"Run: {cmd_str}"})
                console.print(f"[{_t('muted')}]Running:[/] {cmd_str}")
                result = execute_tool("run_bash", {"command": cmd_str})
                if result.get("error"):
                    console.print(f"  [{_t('error')}]Error: {result['error'][:150]}[/]")
                else:
                    out = result.get("stdout", "")
                    for ln in out.split("\n")[:10]:
                        console.print(f"  [#565f89]{ln}[/]")
                messages.append({"role": "tool", "tool_call_id": str(uuid.uuid4())[:8], "content": json.dumps(result)})
            continue

        # Slash commands
        if line.strip().startswith("/"):
            result = _cmd(line.strip(), messages, provider, model, session_id, cfg,
                         mode, tracker, permissions, custom_commands)
            if result == "quit":
                break
            if result and result.startswith("mode:"):
                mode = result.split(":")[1]
            cfg = get_config()
            provider = cfg.get("provider", provider)
            model = cfg.get("model", model)
            _print_status_bar(mode, len(tracker.snapshots))
            continue

        # User message
        messages.append({"role": "user", "content": line})
        console.print()
        console.print(f"[bold {_t('accent')}]You:[/]")
        console.print(line)
        console.print()

        # LLM response
        _llm(provider, model, messages, mode, permissions, tracker)


def _llm(provider: str, model: str, messages: list[dict], mode: str,
          permissions: PermissionManager, tracker: FileChangeTracker):
    acc = StreamAccumulator()
    full = ""

    console.print(f"[bold {_t('success')}]AI:[/]")

    # Filter tools based on mode
    tools = TOOLS_SPEC if mode == "build" else [
        t for t in TOOLS_SPEC
        if t["function"]["name"] in ("read_file", "search_files", "search_content", "list_directory")
    ]

    try:
        for chunk in stream_completion(provider, model, messages, tools=tools):
            text = acc.process_chunk(chunk)
            if text:
                full += text
                console.print(text, end="", highlight=False)
            if acc.error:
                console.print(f"\n[{_t('error')}]Error: {acc.error}[/]")
                break
    except KeyboardInterrupt:
        console.print(f"\n[{_t('warning')}]Interrupted.[/]")
    except Exception as e:
        console.print(f"\n[{_t('error')}]Error: {e}[/]")

    console.print()

    if acc.error:
        return

    resp = acc.finalize()
    messages.append(resp)

    tool_calls = resp.get("tool_calls", [])
    if tool_calls:
        _tools(tool_calls, messages, provider, model, mode, permissions, tracker)


def _tools(tool_calls: list[dict], messages: list[dict], provider: str, model: str,
            mode: str, permissions: PermissionManager, tracker: FileChangeTracker):
    for tc in tool_calls:
        func = tc.get("function", {})
        name = func.get("name", "")
        try:
            args = json.loads(func.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {}

        # Permission check
        if permissions.needs_permission(name):
            perm = permissions.ask_permission(name, args)
            if perm == "deny":
                console.print(f"  [{_t('error')}]Denied[/]")
                messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": "Denied by user"})
                continue

        # File change tracking for write tools
        snap_id = None
        if name in ("write_file", "edit_file") and args.get("path"):
            snap_id = tracker.before_write(args["path"])

        # Show tool call
        args_s = ", ".join(f"{k}={repr(v)[:40]}" for k, v in args.items())
        console.print()
        console.print(f"[{_t('accent')}] >[/] [bold]{name}[/][#565f89]({args_s})[/]")

        # Execute
        result = execute_tool(name, args)

        # Show result
        if result.get("error"):
            console.print(f"  [{_t('error')}]x[/] {result['error'][:150]}")
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
    _llm(provider, model, messages, mode, permissions, tracker)


def _cmd(text: str, messages: list[dict], provider: str, model: str, session_id: str,
          cfg: dict, mode: str, tracker: FileChangeTracker, permissions: PermissionManager,
          custom_commands: dict) -> str | None:
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd in ("/quit", "/exit", "/q"):
        console.print(f"[{_t('muted')}]Goodbye.[/]")
        return "quit"

    elif cmd in ("/help", "/h", "/?"):
        console.print()
        console.print(f"[bold {_t('accent')}]Commands[/]")
        cmds = [
            ("/help", "This help"),
            ("/clear", "Clear conversation"),
            ("/model [name]", "Switch model"),
            ("/provider [name]", "Switch provider"),
            ("/theme [name]", "Switch theme"),
            ("/status", "Gateway status"),
            ("/models", "List models"),
            ("/sessions", "List sessions"),
            ("/save", "Save session"),
            ("/load [id]", "Load session"),
            ("/config", "Show config"),
            ("/undo", "Undo last file change"),
            ("/undoall", "Undo all file changes"),
            ("/diff", "List file changes"),
            ("/cost", "Show session cost"),
            ("/export [md|json]", "Export session"),
            ("/compact", "Summarize context"),
            ("/init", "Generate AGENTS.md"),
            ("/mcp", "MCP server management"),
            ("/blender", "Blender scene info"),
            ("/quit", "Exit"),
        ]
        for c, d in cmds:
            console.print(f"  [#7aa2f7]{c:22s}[/] [#565f89]{d}[/]")
        console.print()
        console.print(f"[bold {_t('accent')}]Keyboard[/]")
        console.print(f"  [#7dcfff]Tab[/]         Switch Plan/Build mode")
        console.print(f"  [#7dcfff]![/]<command>  Run bash directly")
        console.print(f"  [#7dcfff]Ctrl+C[/]      Interrupt")
        console.print()

    elif cmd == "/clear":
        messages.clear()
        messages.append({"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()})
        console.print(f"[{_t('success')}]Cleared.[/]")

    elif cmd == "/model":
        if arg:
            model = arg.strip()
            set_config_value("model", model)
            console.print(f"[{_t('success')}]Model: {model}[/]")
        else:
            console.print(f"[#565f89]Current: {model}[/]")
            console.print("[#565f89]Usage: /model <name>[/]")

    elif cmd == "/provider":
        if arg:
            provider = arg.strip().lower()
            set_config_value("provider", provider)
            console.print(f"[{_t('success')}]Provider: {provider}[/]")
        else:
            console.print(f"[#565f89]Current: {provider}[/]")

    elif cmd == "/theme":
        if arg:
            theme = arg.strip().lower()
            if theme in THEMES:
                set_config_value("theme", theme)
                console.print(f"[{_t('success')}]Theme: {theme}[/]")
            else:
                console.print(f"[{_t('error')}]Unknown theme: {theme}[/]")
                console.print(f"[#565f89]Available: {', '.join(THEMES.keys())}[/]")
        else:
            cfg2 = get_config()
            current = cfg2.get("theme", "tokyo-night")
            console.print(f"[#565f89]Current: {current}[/]")
            console.print(f"[#565f89]Available: {', '.join(THEMES.keys())}[/]")

    elif cmd == "/status":
        items = get_full_status()
        console.print()
        console.print(f"[bold {_t('accent')}]Status[/]")
        for name, color, detail in items:
            c = _t('success') if color == "green" else _t('error')
            console.print(f"  [#9ece6a]+[/] [#c0caf5]{name}[/] [#565f89]{detail}[/]")
        console.print()

    elif cmd == "/models":
        models = list_models()
        if models:
            console.print(f"[bold {_t('accent')}]Models ({len(models)})[/]")
            for m in models[:30]:
                console.print(f"  [#c0caf5]{m.get('id','?')}[/]")
        else:
            console.print("[#565f89]No models. Is gateway running?[/]")

    elif cmd == "/sessions":
        sessions = list_sessions()
        if not sessions:
            console.print("[#565f89]No sessions.[/]")
            return
        console.print(f"[bold {_t('accent')}]Sessions ({len(sessions)})[/]")
        for s in sessions[:10]:
            console.print(f"  [#7aa2f7]{s['id']}[/]  [#565f89]{s.get('updated_at','')[:16]}  {s.get('count',0)} msgs[/]")

    elif cmd == "/save":
        save_session(session_id, messages, {"provider": provider, "model": model})
        console.print(f"[{_t('success')}]Saved: {session_id}[/]")

    elif cmd == "/load":
        if not arg:
            console.print("[#565f89]Usage: /load <session-id>[/]")
            return
        data = load_session(arg.strip())
        if data:
            messages.clear()
            messages.extend(data.get("messages", []))
            console.print(f"[{_t('success')}]Loaded: {arg.strip()} ({len(messages)} messages)[/]")
        else:
            console.print(f"[{_t('error')}]Session not found: {arg}[/]")

    elif cmd == "/config":
        cfg2 = get_config()
        console.print(f"[bold {_t('accent')}]Config[/]")
        for k, v in cfg2.items():
            if "key" in k.lower():
                v = f"***{str(v)[-4:]}" if len(str(v)) > 4 else "***"
            console.print(f"  [#c0caf5]{k}[/] = [#565f89]{v}[/]")

    elif cmd == "/undo":
        if tracker.undo():
            console.print(f"[{_t('success')}]Undone.[/]")
        else:
            console.print("[#565f89]Nothing to undo.[/]")

    elif cmd == "/undoall":
        count = tracker.undo_all()
        console.print(f"[{_t('success')}]Undone {count} changes.[/]")

    elif cmd == "/diff":
        changes = tracker.list_changes()
        if not changes:
            console.print("[#565f89]No changes tracked.[/]")
        else:
            console.print(f"[bold {_t('accent')}]Changes ({len(changes)})[/]")
            for c in changes:
                console.print(f"  [#c0caf5]{c['path']}[/]  [#565f89]({c['id']})[/]")

    elif cmd == "/cost":
        # Approximate token count from messages
        total_chars = sum(len(m.get("content", "") or "") for m in messages)
        approx_tokens = total_chars // 4
        console.print(f"[{_t('accent')}]~{approx_tokens:,} tokens[/]  [#565f89]{len(messages)} messages[/]")

    elif cmd == "/export":
        fmt = arg.strip().lower() if arg else "markdown"
        if fmt not in ("markdown", "json", "md"):
            fmt = "markdown"
        if fmt == "md":
            fmt = "markdown"
        content = _export_session(messages, fmt)
        ext = "json" if fmt == "json" else "md"
        export_path = Path(f"patchbay-export-{session_id}.{ext}")
        export_path.write_text(content, encoding="utf-8")
        console.print(f"[{_t('success')}]Exported to {export_path}[/]")

    elif cmd == "/compact":
        console.print(f"[{_t('warning')}]Compacting context...[/]")
        # Simple compaction: summarize older messages
        if len(messages) > 6:
            summary_msgs = messages[:3]  # Keep system + first exchange
            recent = messages[-4:]  # Keep last 2 exchanges
            summary_content = f"[Context compacted. Previous {len(messages)-4} messages summarized.]"
            messages.clear()
            messages.extend(summary_msgs)
            messages.append({"role": "system", "content": summary_content})
            messages.extend(recent)
            console.print(f"[{_t('success')}]Compacted: {len(messages)} messages remaining[/]")
        else:
            console.print("[#565f89]Nothing to compact.[/]")

    elif cmd == "/init":
        console.print(f"[{_t('accent')}]Generating AGENTS.md...[/]")
        # Ask AI to generate it
        messages.append({"role": "user", "content": (
            "Analyze this codebase and create an AGENTS.md file containing:\n"
            "1. Project overview and architecture\n"
            "2. Build/lint/test commands\n"
            "3. Coding standards and conventions\n"
            "4. Important files and directories\n"
            "Write the file to AGENTS.md in the current directory."
        )})
        _llm(provider, model, messages, mode, permissions, tracker)

    elif cmd == "/blender":
        scene = blender_get_scene()
        if "error" in scene:
            console.print(f"[{_t('error')}]Blender: {scene['error']}[/]")
        else:
            console.print(f"[{_t('accent')}]Blender[/] {scene.get('name','?')}  {scene.get('object_count',0)} objects")

    elif cmd == "/mcp":
        console.print("[#565f89]MCP management coming soon.[/]")

    # Custom commands
    elif cmd.lstrip("/") in custom_commands:
        cmd_name = cmd.lstrip("/")
        tpl = custom_commands[cmd_name]["template"]
        if arg:
            tpl = tpl.replace("{{arg}}", arg)
        messages.append({"role": "user", "content": tpl})
        console.print(f"[{_t('accent')}]Running custom command: {cmd_name}[/]")
        _llm(provider, model, messages, mode, permissions, tracker)

    else:
        console.print(f"[{_t('error')}]Unknown: {cmd}[/]  [#565f89]/help[/]")

    return None


if __name__ == "__main__":
    main()
