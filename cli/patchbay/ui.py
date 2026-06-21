"""UI - Terminal rendering, themes, and visual components.

Provides the complete visual language for the Patchbay CLI:
  - Tokyo Night color palette
  - Panel builders for status, tools, errors
  - Markdown rendering with syntax highlighting
  - Spinner and progress indicators
  - ASCII art banner
"""

from __future__ import annotations

import sys
from typing import Any

from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from rich import box
from rich.style import Style
from rich.columns import Columns
from rich.padding import Padding
from rich.rule import Rule
from rich.align import Align
from rich.spinner import Spinner
from rich.live import Live
from rich.layout import Layout

# ═══════════════════════════════════════════════════════════════
# TOKYO NIGHT PALETTE
# ═══════════════════════════════════════════════════════════════

class Theme:
    """Tokyo Night color palette and style definitions."""

    # Backgrounds
    BG_BASE = "#1a1b26"
    BG_ELEVATED_1 = "#1f2335"
    BG_ELEVATED_2 = "#24283b"
    BG_ELEVATED_3 = "#2a2e42"

    # Borders
    BORDER_SUBTLE = "#2f3549"
    BORDER_STRONG = "#3b4261"

    # Text
    TEXT_PRIMARY = "#c0caf5"
    TEXT_SECONDARY = "#9aa5ce"
    TEXT_MUTED = "#565f89"

    # Accents
    ACCENT_BLUE = "#7aa2f7"
    ACCENT_CYAN = "#7dcfff"
    ACCENT_GREEN = "#9ece6a"
    ACCENT_YELLOW = "#e0af68"
    ACCENT_ORANGE = "#ff9e64"
    ACCENT_RED = "#f7768e"
    ACCENT_MAGENTA = "#bb9af7"
    ACCENT_TEAL = "#73daca"

    # Glass effects
    GLASS_BG = "rgba(36, 40, 59, 0.65)"
    GLASS_BORDER = "rgba(122, 162, 247, 0.12)"

    # Shadows
    SHADOW_GLOW_BLUE = "0 0 24px rgba(122, 162, 247, 0.25)"

    # Rich styles
    STYLE_USER = Style(color="cyan", bold=True)
    STYLE_ASSISTANT = Style(color="green", bold=True)
    STYLE_TOOL = Style(color="yellow", italic=True)
    STYLE_ERROR = Style(color="red", bold=True)
    STYLE_SUCCESS = Style(color="green", bold=True)
    STYLE_WARNING = Style(color="yellow", bold=True)
    STYLE_INFO = Style(color="blue")
    STYLE_DIM = Style(dim=True)
    STYLE_SYSTEM = Style(color="magenta", italic=True)

    # Box styles
    BOX_ROUNDED = box.ROUNDED
    BOX_HEAVY = box.HEAVY
    BOX_DOUBLE = box.DOUBLE
    BOX_SIMPLE = box.SIMPLE
    BOX_MINIMAL = box.SIMPLE_HEAD


# ═══════════════════════════════════════════════════════════════
# CONSOLE INSTANCES
# ═══════════════════════════════════════════════════════════════

def make_console() -> Console:
    """Create a properly configured console instance."""
    return Console(
        force_terminal=True,
        highlight=True,
        color_system="truecolor",
    )


console = make_console()
err_console = Console(stderr=True, force_terminal=True)


# ═══════════════════════════════════════════════════════════════
# ASCII ART & BANNERS
# ═══════════════════════════════════════════════════════════════

BANNER_ART = r"""
[bold {blue}]  ____            _                 ____  __  _____ ____
 |  _ \  ___  ___| | _____   _____| __ )/ / |_   _|  _ \
 | | | |/ _ \/ __| |/ / _ \ / / _ \  _ \ / /   | | | | |
 | |_| |  __/\__ \   < (_) | (_)  __/ |_) / /    | | |_| |
 |____/ \___||___/_|\_\___/ \___/\___/____/      |_| |____/[/bold {blue}]
[dim]  v0.2.0  ·  Universal LLM Gateway & AI Coding Assistant[/dim]
"""


def render_banner():
    """Render the startup banner with color."""
    from patchbay.config import get_config
    cfg = get_config()
    provider = cfg.get("provider", "openai")
    model = cfg.get("model", "gpt-4o")
    gw_url = cfg.get("gateway_url", "http://localhost:8000")

    banner = BANNER_ART.format(blue=Theme.ACCENT_BLUE, cyan=Theme.ACCENT_CYAN)
    console.print(banner)
    console.print(
        f"  [dim]Provider:[/dim] [cyan]{provider}[/cyan]"
        f"  [dim]|[/dim]  [dim]Model:[/dim] [cyan]{model}[/cyan]"
        f"  [dim]|[/dim]  [dim]Gateway:[/dim] [cyan]{gw_url}[/cyan]"
    )
    console.print(
        f"  [dim]Type[/dim] [white]/help[/white] [dim]for commands  ·  [/dim]"
        f"[dim]Ctrl+C[/dim] [dim]to interrupt  ·  [/dim]"
        f"[dim]/quit[/dim] [dim]to exit[/dim]"
    )
    console.print()


# ═══════════════════════════════════════════════════════════════
# PANEL BUILDERS
# ═══════════════════════════════════════════════════════════════

def panel_status(title: str, content: str, border: str = Theme.ACCENT_BLUE) -> Panel:
    """Create a status panel."""
    return Panel(
        content,
        title=f"[bold]{title}[/bold]",
        border_style=border,
        box=Theme.BOX_ROUNDED,
        padding=(0, 2),
    )


def panel_error(title: str, message: str) -> Panel:
    """Create an error panel."""
    return Panel(
        f"[red]{message}[/red]",
        title=f"[bold red]{title}[/bold red]",
        border_style=Theme.ACCENT_RED,
        box=Theme.BOX_ROUNDED,
        padding=(0, 2),
    )


def panel_success(title: str, message: str) -> Panel:
    """Create a success panel."""
    return Panel(
        f"[green]{message}[/green]",
        title=f"[bold green]{title}[/bold green]",
        border_style=Theme.ACCENT_GREEN,
        box=Theme.BOX_ROUNDED,
        padding=(0, 2),
    )


def panel_info(title: str, content: str) -> Panel:
    """Create an info panel."""
    return Panel(
        content,
        title=f"[bold cyan]{title}[/bold cyan]",
        border_style=Theme.ACCENT_CYAN,
        box=Theme.BOX_ROUNDED,
        padding=(0, 2),
    )


def panel_tool_call(name: str, args: dict) -> Panel:
    """Create a tool call indicator panel."""
    args_str = ", ".join(f"{k}={repr(v)[:60]}" for k, v in args.items())
    content = f"[yellow]{name}[/yellow]([dim]{args_str}[/dim])"
    return Panel(
        content,
        title="[bold yellow]Tool Call[/bold yellow]",
        border_style=Theme.ACCENT_YELLOW,
        box=Theme.BOX_SIMPLE,
        padding=(0, 1),
    )


def panel_tool_result(name: str, result: dict) -> Panel:
    """Create a tool result panel."""
    if result.get("error"):
        content = f"[red]{result['error']}[/red]"
        border = Theme.ACCENT_RED
        title = f"[red]Error: {name}[/red]"
    else:
        content = format_result_content(name, result)
        border = Theme.ACCENT_GREEN
        title = f"[green]{name}[/green]"

    return Panel(
        content,
        title=title,
        border_style=border,
        box=Theme.BOX_SIMPLE,
        padding=(0, 1),
    )


# ═══════════════════════════════════════════════════════════════
# TABLE BUILDERS
# ═══════════════════════════════════════════════════════════════

def table_models(models: list[dict]) -> Table:
    """Create a models table."""
    t = Table(
        box=Theme.BOX_ROUNDED,
        border_style=Theme.ACCENT_CYAN,
        title="[bold cyan]LLM Models[/bold cyan]",
        title_style="bold cyan",
        show_lines=False,
        pad_edge=True,
        expand=False,
    )
    t.add_column("Model", style="bold", min_width=20)
    t.add_column("Family", style=Theme.ACCENT_MAGENTA, min_width=10)
    t.add_column("Context", justify="right", min_width=12)
    t.add_column("Max Output", justify="right", min_width=12)
    t.add_column("Vision", justify="center", min_width=6)
    t.add_column("Tools", justify="center", min_width=6)
    t.add_column("Streaming", justify="center", min_width=8)

    for m in models:
        pb = m.get("patchbay", {})
        ctx = pb.get("context_window")
        out = pb.get("max_output_tokens")
        t.add_row(
            m.get("id", "?"),
            pb.get("family", "?"),
            f"{ctx:,}" if ctx else "-",
            f"{out:,}" if out else "-",
            "[green]Y[/green]" if pb.get("supports_vision") else "[dim]N[/dim]",
            "[green]Y[/green]" if pb.get("supports_tools") else "[dim]N[/dim]",
            "[green]Y[/green]" if pb.get("supports_streaming") else "[dim]N[/dim]",
        )
    return t


def table_status(items: list[tuple[str, str, str]]) -> Table:
    """Create a status table. items = [(name, color, detail), ...]"""
    t = Table(
        box=Theme.BOX_ROUNDED,
        border_style=Theme.ACCENT_BLUE,
        title="[bold blue]System Status[/bold blue]",
        title_style="bold blue",
        show_lines=False,
        pad_edge=True,
    )
    t.add_column("Service", style="bold", min_width=15)
    t.add_column("Status", justify="center", min_width=8)
    t.add_column("Details", style="dim", min_width=30)

    for name, color, detail in items:
        icon = "[green]+[/green]" if color == "green" else "[red]-[/red]"
        t.add_row(name, icon, detail)
    return t


def table_sessions(sessions: list[dict]) -> Table:
    """Create a sessions table."""
    t = Table(
        box=Theme.BOX_SIMPLE,
        border_style=Theme.ACCENT_MAGENTA,
        title="[bold magenta]Saved Sessions[/bold magenta]",
        show_lines=False,
    )
    t.add_column("ID", style="bold cyan", min_width=10)
    t.add_column("Updated", style="dim", min_width=20)
    t.add_column("Messages", justify="right", min_width=8)

    for s in sessions:
        t.add_row(s["id"], s["updated"][:19], str(s["count"]))
    return t


def table_config(config: dict) -> Table:
    """Create a config display table."""
    t = Table(
        box=Theme.BOX_SIMPLE,
        border_style=Theme.ACCENT_YELLOW,
        title="[bold yellow]Configuration[/bold yellow]",
        show_lines=False,
    )
    t.add_column("Key", style="bold", min_width=25)
    t.add_column("Value", min_width=40)

    for k, v in config.items():
        if "key" in k.lower() or "secret" in k.lower() or "token" in k.lower():
            val = f"[dim]***[/dim]{str(v)[-4:]}" if len(str(v)) > 4 else "[dim]***[/dim]"
        else:
            val = str(v)
        t.add_row(k, val)
    return t


# ═══════════════════════════════════════════════════════════════
# TREE BUILDERS
# ═══════════════════════════════════════════════════════════════

def tree_objects(objects: list[dict]) -> Tree:
    """Create a Blender objects tree."""
    tree = Tree("[bold]Blender Scene[/bold]", guide_style=Theme.ACCENT_BLUE)
    groups: dict[str, Tree] = {}
    for obj in objects:
        t = obj.get("type", "UNKNOWN")
        if t not in groups:
            groups[t] = tree.add(f"[magenta]{t}[/magenta]")
        loc = obj.get("location", [0, 0, 0])
        groups[t].add(
            f"[cyan]{obj['name']}[/cyan]  "
            f"[dim]({loc[0]:.1f}, {loc[1]:.1f}, {loc[2]:.1f})[/dim]"
        )
    return tree


def tree_directory(entries: list[dict], path: str = ".") -> Tree:
    """Create a directory tree."""
    tree = Tree(f"[bold]{path}[/bold]", guide_style=Theme.ACCENT_BLUE)
    for e in entries:
        if e["type"] == "dir":
            tree.add(f"[blue]{e['name']}/[/blue]")
        else:
            size = e.get("size", 0)
            if size > 1_000_000:
                size_str = f"{size / 1_000_000:.1f}MB"
            elif size > 1_000:
                size_str = f"{size / 1_000:.1f}KB"
            else:
                size_str = f"{size}B"
            tree.add(f"[dim]{e['name']}[/dim]  [dim]{size_str}[/dim]")
    return tree


# ═══════════════════════════════════════════════════════════════
# HELP TEXT
# ═══════════════════════════════════════════════════════════════

HELP_TEXT = f"""
[bold cyan]Commands:[/bold cyan]
  [white]/help[/white]            Show this help
  [white]/model[/white] [dim]<name>[/dim]     Switch model (e.g. /model gpt-4o)
  [white]/provider[/white] [dim]<name>[/dim]  Switch provider (openai, anthropic, deepseek, openrouter, patchbay)
  [white]/clear[/white]           Clear conversation history
  [white]/history[/white]         Show conversation history
  [white]/save[/white]            Save conversation to disk
  [white]/load[/white] [dim]<id>[/dim]        Load a saved conversation
  [white]/sessions[/white]        List saved sessions
  [white]/config[/white]          Show configuration
  [white]/config[/white] [dim]<k> <v>[/dim]   Set a config value
  [white]/status[/white]          Show gateway status
  [white]/models[/white]          List available models
  [white]/blender[/white]         Show Blender scene
  [white]/quit[/white]            Exit

[bold cyan]Tips:[/bold cyan]
  - Describe what you want and I'll use tools to help
  - I can [white]read[/white], [white]write[/white], and [white]edit[/white] files
  - I can [white]run bash[/white] commands
  - I can [white]search[/white] codebases
  - Streaming responses appear in real-time
  - Tool calls are shown with yellow indicators
  - Use [white]Ctrl+C[/white] to interrupt a long response
"""


# ═══════════════════════════════════════════════════════════════
# FORMAT HELPERS
# ═══════════════════════════════════════════════════════════════

def format_result_content(name: str, result: dict) -> str:
    """Format tool result for display in a panel."""
    if name == "read_file":
        content = result.get("content", "")
        total = result.get("total_lines", 0)
        offset = result.get("offset", 0)
        return f"[dim]{total} total lines, showing {offset}-{offset + len(content.splitlines())}[/dim]\n{content}"

    if name == "run_bash":
        parts = []
        if result.get("stdout"):
            parts.append(result["stdout"])
        if result.get("stderr"):
            parts.append(f"[yellow]STDERR:[/yellow]\n{result['stderr']}")
        rc = result.get("returncode", "?")
        status = "[green]OK[/green]" if rc == 0 else f"[red]Exit {rc}[/red]"
        parts.append(f"\n[dim]Status: {status}[/dim]")
        return "\n".join(parts) if parts else f"[dim]Exit code: {rc}[/dim]"

    if name == "search_files":
        files = result.get("files", [])
        total = result.get("total", 0)
        if not files:
            return "[dim]No files found[/dim]"
        return f"[dim]{total} files found:[/dim]\n" + "\n".join(files[:20])

    if name == "search_content":
        matches = result.get("matches", [])
        if not matches:
            return "[dim]No matches found[/dim]"
        lines = []
        for m in matches[:20]:
            lines.append(f"[cyan]{m['file']}:{m['line']}[/cyan]  {m['content']}")
        return "\n".join(lines)

    if name == "list_directory":
        entries = result.get("entries", [])
        if not entries:
            return "[dim]Empty directory[/dim]"
        lines = []
        for e in entries[:30]:
            if e["type"] == "dir":
                lines.append(f"  [blue]{e['name']}/[/blue]")
            else:
                lines.append(f"  {e['name']}")
        return "\n".join(lines)

    if name == "write_file" or name == "edit_file":
        return f"[green]{result.get('path', '?')}[/green]"

    import json
    return json.dumps(result, indent=2)


def render_markdown(text: str) -> Markdown:
    """Render markdown text safely."""
    return Markdown(text)
