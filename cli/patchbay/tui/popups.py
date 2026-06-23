"""Popups - Modal dialogs for Patchbay CLI.

Implements: model picker, session picker, command palette, help overlay,
transcript overlay, file tree browser, markdown preview.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text

from patchbay.config import get_config, set_config_value
from patchbay.session import list_sessions, load_session
from patchbay.providers import fetch_models_cached


console = Console(force_terminal=True, color_system="truecolor")


def show_model_picker(provider: str, current_model: str, theme: Any) -> str | None:
    """Show model picker. Returns selected model id or None."""
    console.print(f"\n[{theme.rich_accent}]Fetching models from {provider}...[/]")
    models = fetch_models_cached(provider)
    if not models:
        console.print(f"[{theme.rich_muted}]No models fetched.[/]")
        return None

    table = Table(
        title=f"[bold {theme.rich_accent}]Models ({len(models)})[/]",
        border_style=theme.border, show_header=True, header_style=f"bold {theme.rich_accent}",
    )
    table.add_column("#", style=theme.rich_cyan, width=4)
    table.add_column("Model", style=theme.rich_text)
    table.add_column("Name", style=theme.rich_muted)
    table.add_column("Current", justify="center")

    for i, m in enumerate(models[:60], 1):
        cur = f"[{theme.rich_success}]*[/]" if m["id"] == current_model else ""
        table.add_row(str(i), m["id"], m.get("name", ""), cur)

    console.print(table)
    console.print(f"[{theme.rich_muted}]Enter number or model name (Esc to cancel):[/]")

    try:
        choice = console.input(f"[{theme.rich_cyan}]>[/] ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not choice:
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(models):
        return models[int(choice) - 1]["id"]
    return choice


def show_session_picker(current_session_id: str, theme: Any) -> str | None:
    """Show session picker. Returns session id, '__new__', or None."""
    sessions = list_sessions()
    if not sessions:
        console.print(f"[{theme.rich_muted}]No sessions. Creating new.[/]")
        return "__new__"

    table = Table(
        title=f"[bold {theme.rich_accent}]Sessions ({len(sessions)})[/]",
        border_style=theme.border, show_header=True, header_style=f"bold {theme.rich_accent}",
    )
    table.add_column("#", style=theme.rich_cyan, width=4)
    table.add_column("ID", style=theme.rich_accent)
    table.add_column("Updated", style=theme.rich_muted)
    table.add_column("Messages", justify="right", style=theme.rich_text)
    table.add_column("Model", style=theme.rich_muted)

    for i, s in enumerate(sessions[:20], 1):
        cur = f" [{theme.rich_success}]*[/]" if s["id"] == current_session_id else ""
        meta = s.get("metadata", {})
        model = meta.get("model", "?")
        table.add_row(
            str(i), s["id"] + cur,
            s.get("updated_at", "")[:16],
            str(s.get("count", 0)),
            model,
        )

    console.print(table)
    console.print(f"[{theme.rich_muted}]Enter number, 'n' for new, or session id (Esc to cancel):[/]")

    try:
        choice = console.input(f"[{theme.rich_cyan}]>[/] ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not choice or choice == "n":
        return "__new__"
    if choice.isdigit() and 1 <= int(choice) <= len(sessions):
        return sessions[int(choice) - 1]["id"]
    return choice


def show_command_palette(theme: Any) -> str | None:
    """Show command palette. Returns command id or None."""
    commands = [
        ("clear", "Clear conversation", "/clear"),
        ("status", "Gateway status", "/status"),
        ("models", "List models", "/models"),
        ("sessions", "List sessions", "/sessions"),
        ("save", "Save session", "/save"),
        ("config", "Show config", "/config"),
        ("help", "Help", "/help"),
        ("quit", "Quit", "/quit"),
        ("new_session", "New session", ""),
        ("switch_model", "Switch model", "Ctrl+P"),
        ("switch_session", "Switch session", "Ctrl+S"),
        ("theme", "Switch theme", "/theme"),
        ("export", "Export session", "/export"),
        ("compact", "Compact context", "/compact"),
        ("init", "Generate AGENTS.md", "/init"),
        ("undo", "Undo last change", "/undo"),
        ("diff", "Show changes", "/diff"),
        ("cost", "Show cost", "/cost"),
        ("blender", "Blender info", "/blender"),
    ]

    table = Table(
        title=f"[bold {theme.rich_accent}]Commands[/]",
        border_style=theme.border, show_header=True, header_style=f"bold {theme.rich_accent}",
    )
    table.add_column("#", style=theme.rich_cyan, width=4)
    table.add_column("Command", style=theme.rich_text)
    table.add_column("Shortcut", style=theme.rich_muted)

    for i, (cid, label, shortcut) in enumerate(commands, 1):
        table.add_row(str(i), label, shortcut)

    console.print(table)
    console.print(f"[{theme.rich_muted}]Enter number or command name (Esc to cancel):[/]")

    try:
        choice = console.input(f"[{theme.rich_cyan}]>[/] ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not choice:
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(commands):
        return commands[int(choice) - 1][0]
    return choice


def show_help(theme: Any) -> None:
    """Show help overlay."""
    console.print()
    console.print(f"[bold {theme.rich_accent}]Patchbay AI - Help[/]")
    console.print()

    sections = [
        ("Keyboard Shortcuts", [
            ("Ctrl+D", "Quick exit"),
            ("Ctrl+L", "Clear screen"),
            ("Ctrl+R", "Search history"),
            ("Ctrl+E", "Open in $EDITOR"),
            ("Ctrl+W", "Delete word backward"),
            ("Ctrl+U", "Delete line backward"),
            ("Ctrl+K", "Delete line forward"),
            ("Ctrl+A", "Beginning of line"),
            ("Ctrl+E", "End of line"),
            ("Ctrl+F/B", "Forward/Backward char"),
            ("Tab", "Switch Plan/Build mode"),
            ("Shift+Enter", "Multi-line input"),
            ("Esc", "Cancel input"),
        ]),
        ("Features", [
            ("@file", "Add file to context"),
            ("!cmd", "Run bash directly"),
            ("Ctrl+P", "Model picker"),
            ("Ctrl+S", "Session picker"),
            ("Ctrl+N", "New session"),
            ("Ctrl+K", "Command palette"),
            ("Ctrl+H", "Help"),
            ("Ctrl+T", "Transcript overlay"),
            ("Ctrl+B", "File tree browser"),
            ("Ctrl+M", "Markdown preview"),
            ("Ctrl+J/K", "Navigate messages"),
        ]),
        ("Slash Commands", [
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
            ("/undoall", "Undo all changes"),
            ("/diff", "List file changes"),
            ("/cost", "Show token cost"),
            ("/export [md|json]", "Export session"),
            ("/compact", "Compact context"),
            ("/init", "Generate AGENTS.md"),
            ("/blender", "Blender scene info"),
            ("/quit", "Exit"),
        ]),
    ]

    for title, items in sections:
        console.print(f"  [bold {theme.rich_accent}]{title}[/]")
        for key, desc in items:
            console.print(f"    [{theme.rich_cyan}]{key:16s}[/] [{theme.rich_muted}]{desc}[/]")
        console.print()


def show_transcript(messages: list[dict], theme: Any) -> None:
    """Show transcript overlay."""
    console.print()
    console.print(f"[bold {theme.rich_accent}]Transcript ({len(messages)} messages)[/]")
    console.print(f"[{theme.rich_muted}]{'─' * 60}[/]")

    for m in messages:
        role = m.get("role", "unknown")
        content = m.get("content", "")
        if role == "system":
            continue
        if role == "tool":
            continue
        if role == "user":
            console.print(f"\n[{theme.rich_accent}]You:[/]")
            console.print(content[:500] if content else "[no content]")
        elif role == "assistant" and content:
            console.print(f"\n[{theme.rich_success}]AI:[/]")
            console.print(content[:500] if content else "[no content]")

    console.print(f"\n[{theme.rich_muted}]{'─' * 60}[/]")


def show_file_tree(path: str = ".", theme: Any = None, max_depth: int = 3) -> None:
    """Show file tree browser."""
    p = Path(path).resolve()
    if not p.exists():
        console.print(f"[red]Path not found: {path}[/]")
        return

    tree = Tree(f"[bold {theme.rich_accent if theme else 'blue'}]{p.name}[/]")
    _add_tree_nodes(tree, p, max_depth, 0)
    console.print(tree)


def _add_tree_nodes(tree: Any, path: Path, max_depth: int, current_depth: int) -> None:
    if current_depth >= max_depth:
        return
    try:
        items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
        for item in items[:50]:
            if item.name.startswith(".") or item.name in ("node_modules", "__pycache__", ".venv", "venv"):
                continue
            if item.is_dir():
                branch = tree.add(f"[blue]{item.name}/[/]")
                _add_tree_nodes(branch, item, max_depth, current_depth + 1)
            else:
                size = ""
                try:
                    s = item.stat().st_size
                    if s > 1_000_000:
                        size = f" ({s / 1_000_000:.1f}MB)"
                    elif s > 1_000:
                        size = f" ({s / 1_000:.1f}KB)"
                except Exception:
                    pass
                tree.add(f"{item.name}[dim]{size}[/]")
    except PermissionError:
        pass


def show_markdown_preview(text: str, theme: Any) -> None:
    """Show markdown preview."""
    console.print()
    console.print(f"[bold {theme.rich_accent}]Markdown Preview[/]")
    console.print(f"[{theme.rich_muted}]{'─' * 60}[/]")
    try:
        console.print(Markdown(text))
    except Exception:
        console.print(text)
    console.print(f"[{theme.rich_muted}]{'─' * 60}[/]")
