"""Patchbay TUI - Full-screen terminal UI inspired by OpenCode.

A complete rewrite of the Patchbay CLI as a modern full-screen TUI
with chat, status bar, overlay dialogs, and keyboard-driven navigation.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
)

from patchbay.config import (
    get_config,
    save_config,
    set_config_value,
    validate_provider,
)
from patchbay.providers import StreamAccumulator, fetch_models_cached, stream_completion
from patchbay.session import (
    list_sessions,
    load_session,
    save_session,
)
from patchbay.tools import TOOLS_SPEC, execute_tool
from patchbay.gateway import (
    blender_get_scene,
    get_full_status,
    list_models,
)


# ═══════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are Patchbay AI, an expert software engineering assistant embedded in a CLI tool.

You help with writing, reading, editing, and debugging code. You understand codebases and can run shell commands.

Tools: read_file, write_file, edit_file, run_bash, search_files, search_content, list_directory.
Rules: prefer edit_file over write_file, verify changes, be concise, never commit secrets."""

PROVIDERS_INFO = [
    {"id": "openrouter", "name": "OpenRouter", "desc": "100+ models", "key_name": "OPENROUTER_API_KEY"},
    {"id": "openai", "name": "OpenAI", "desc": "GPT-4o, o3, o4", "key_name": "OPENAI_API_KEY"},
    {"id": "anthropic", "name": "Anthropic", "desc": "Claude 4", "key_name": "ANTHROPIC_API_KEY"},
    {"id": "deepseek", "name": "DeepSeek", "desc": "Chat & R1", "key_name": "DEEPSEEK_API_KEY"},
    {"id": "google", "name": "Google", "desc": "Gemini 2.5", "key_name": "GOOGLE_API_KEY"},
]


# ═══════════════════════════════════════════════════════════════
# PROJECT CONTEXT
# ═══════════════════════════════════════════════════════════════

def get_project_context() -> str:
    parts = [f"Working directory: {os.getcwd()}"]
    for fname in ["README.md", "CLAUDE.md", "pyproject.toml", "package.json"]:
        p = Path(fname)
        if p.exists():
            try:
                content = p.read_text(encoding="utf-8", errors="replace")[:2000]
                parts.append(f"\n--- {fname} ---\n{content}")
            except Exception:
                pass
    try:
        entries = []
        for item in sorted(Path(".").iterdir()):
            if item.name.startswith(".") or item.name in ("node_modules", "__pycache__", ".venv"):
                continue
            kind = "d" if item.is_dir() else "f"
            entries.append(f"  {'[' + kind + ']' if kind == 'd' else '   '} {item.name}")
        if entries:
            parts.append("\n--- Structure ---\n" + "\n".join(entries[:30]))
    except Exception:
        pass
    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# CUSTOM WIDGETS
# ═══════════════════════════════════════════════════════════════

class StatusBar(Static):
    """Bottom status bar showing provider, model, and keybindings."""

    def compose(self) -> ComposeResult:
        cfg = get_config()
        provider = cfg.get("provider", "openai")
        model = cfg.get("model", "gpt-4o")
        gw = cfg.get("gateway_url", "localhost:8000")
        yield Label(
            f" [bold cyan]patchbay[/bold cyan] "
            f"[dim]|[/dim] [green]{provider}[/green] "
            f"[dim]|[/dim] [cyan]{model}[/cyan] "
            f"[dim]|[/dim] [dim]{gw}[/dim]",
            classes="status-left",
        )
        yield Label(
            " [dim]Ctrl+K cmd  Ctrl+S session  Ctrl+O model  Ctrl+? help  Ctrl+C quit[/dim] ",
            classes="status-right",
        )

    def update_status(self) -> None:
        cfg = get_config()
        provider = cfg.get("provider", "openai")
        model = cfg.get("model", "gpt-4o")
        gw = cfg.get("gateway_url", "localhost:8000")
        self.query_one(".status-left", Label).update(
            f" [bold cyan]patchbay[/bold cyan] "
            f"[dim]|[/dim] [green]{provider}[/green] "
            f"[dim]|[/dim] [cyan]{model}[/cyan] "
            f"[dim]|[/dim] [dim]{gw}[/dim]"
        )


class StreamingIndicator(Static):
    """Shows streaming status."""

    def on_mount(self) -> None:
        self.visible = False

    def show_streaming(self, model: str = "") -> None:
        self.update(f" [accent]Generating...[/accent] [dim]{model}[/dim]")
        self.visible = True

    def hide_streaming(self) -> None:
        self.visible = False


class ChatMessage(Static):
    """A single chat message widget."""

    def __init__(self, role: str, content: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.role = role
        self.message_content = content

    def compose(self) -> ComposeResult:
        if self.role == "user":
            yield Label("[bold blue]You[/bold blue]", classes="message-label")
        elif self.role == "assistant":
            yield Label("[bold green]AI[/bold green]", classes="message-label")
        elif self.role == "system":
            yield Label("[dim]sys[/dim]", classes="message-label")
        else:
            yield Label("[bold yellow]tool[/bold yellow]", classes="message-label")

        yield Static(self.message_content, classes="message-content")


class ToolCallWidget(Static):
    """Displays a tool call and its result."""

    def __init__(self, name: str, args: dict, result: dict | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tool_name = name
        self.tool_args = args
        self.tool_result = result

    def compose(self) -> ComposeResult:
        args_str = ", ".join(f"{k}={repr(v)[:50]}" for k, v in self.tool_args.items())
        yield Static(
            f"[yellow]>[/yellow] [bold]{self.tool_name}[/bold]([dim]{args_str}[/dim])",
            classes="tool-call",
        )
        if self.tool_result:
            if self.tool_result.get("error"):
                yield Static(
                    f"[red]Error: {self.tool_result['error'][:200]}[/red]",
                    classes="tool-result tool-result-error",
                )
            else:
                result_text = _format_tool_result(self.tool_name, self.tool_result)
                if len(result_text) > 500:
                    result_text = result_text[:500] + "..."
                yield Static(result_text, classes="tool-result")


def _format_tool_result(name: str, result: dict) -> str:
    if name == "read_file":
        content = result.get("content", "")
        total = result.get("total_lines", 0)
        return f"[dim]{total} lines[/dim]\n{content[:400]}"
    if name == "run_bash":
        parts = []
        if result.get("stdout"):
            parts.append(result["stdout"][:300])
        if result.get("stderr"):
            parts.append(f"[yellow]{result['stderr'][:200]}[/yellow]")
        rc = result.get("returncode", "?")
        status = "[green]OK[/green]" if rc == 0 else f"[red]Exit {rc}[/red]"
        parts.append(f"[dim]{status}[/dim]")
        return "\n".join(parts) if parts else f"[dim]Exit: {rc}[/dim]"
    if name == "search_files":
        files = result.get("files", [])
        return f"[dim]{result.get('total', 0)} files[/dim]\n" + "\n".join(files[:15])
    if name == "search_content":
        matches = result.get("matches", [])
        if not matches:
            return "[dim]No matches[/dim]"
        lines = [f"[cyan]{m['file']}:{m['line']}[/cyan] {m['content'][:80]}" for m in matches[:15]]
        return "\n".join(lines)
    if name in ("write_file", "edit_file"):
        return f"[green]{result.get('path', '?')}[/green]"
    import json as _json
    return _json.dumps(result, indent=2)[:400]


# ═══════════════════════════════════════════════════════════════
# DIALOG SCREENS
# ═══════════════════════════════════════════════════════════════

class QuitDialog(ModalScreen[bool]):
    """Quit confirmation dialog."""

    CSS = """
    QuitDialog {
        align: center middle;
    }
    #quit-box {
        width: 40;
        height: 7;
        background: $background-light;
        border: thick $error;
        padding: 1 2;
        content-align: center middle;
        height: auto;
    }
    #quit-box Static {
        width: 100%;
        text-align: center;
    }
    .quit-buttons {
        margin-top: 1;
        width: 100%;
        height: 3;
        content-align: center middle;
    }
    """

    BINDINGS = [
        Binding("y", "quit", "Quit"),
        Binding("n", "cancel", "Cancel"),
        Binding("escape", "cancel", "Cancel"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="quit-box"):
            yield Static("[bold red]Quit Patchbay?[/bold red]")
            yield Static("[dim]Unsaved changes will be lost.[/dim]")
            with Horizontal(classes="quit-buttons"):
                yield Static("[bold green]y[/bold green] Quit    [dim]n[/dim] Cancel")

    def action_quit(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class HelpDialog(ModalScreen[bool]):
    """Help overlay showing keybindings and commands."""

    CSS = """
    HelpDialog {
        align: center middle;
    }
    #help-box {
        width: 70;
        max-height: 80%;
        background: $background-light;
        border: thick $border-focus;
        padding: 1 2;
    }
    #help-box Static {
        width: 100%;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("ctrl+?", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-box"):
            yield Static("[bold cyan]Patchbay AI - Help[/bold cyan]\n")
            yield Static("[bold]Keyboard Shortcuts[/bold]")
            yield Static("  [accent]Ctrl+C[/accent]       Quit")
            yield Static("  [accent]Ctrl+K[/accent]       Command palette")
            yield Static("  [accent]Ctrl+S[/accent]       Switch session")
            yield Static("  [accent]Ctrl+O[/accent]       Switch model")
            yield Static("  [accent]Ctrl+L[/accent]       View logs")
            yield Static("  [accent]Ctrl+?[/accent]       Toggle help")
            yield Static("  [accent]Ctrl+X[/accent]       Cancel generation")
            yield Static("  [accent]Escape[/accent]       Close dialog")
            yield Static("  [accent]Enter[/accent]        Send message")
            yield Static("")
            yield Static("[bold]Slash Commands[/bold]")
            yield Static("  [white]/help[/white]            Show this help")
            yield Static("  [white]/clear[/white]           Clear conversation")
            yield Static("  [white]/model[/white] [dim]<name>[/dim]     Switch model")
            yield Static("  [white]/provider[/white] [dim]<name>[/dim]  Switch provider")
            yield Static("  [white]/status[/white]          Show gateway status")
            yield Static("  [white]/models[/white]          List available models")
            yield Static("  [white]/sessions[/white]        List saved sessions")
            yield Static("  [white]/save[/white]            Save session")
            yield Static("  [white]/config[/white]          Show config")
            yield Static("  [white]/quit[/white]            Exit")
            yield Static("")
            yield Static("[bold]Tools[/bold]")
            yield Static("  I can [dim]read[/dim], [dim]write[/dim], [dim]edit[/dim] files, [dim]run bash[/dim], [dim]search[/dim] code")
            yield Static("  Tool calls appear as yellow indicators below messages")
            yield Static("")
            yield Static("[dim]Press Escape or Ctrl+? to close[/dim]")

    def action_close(self) -> None:
        self.dismiss(False)


class SessionDialog(ModalScreen[str | None]):
    """Session switcher dialog."""

    CSS = """
    SessionDialog {
        align: center middle;
    }
    #session-box {
        width: 50;
        max-height: 70%;
        background: $background-light;
        border: thick $border-focus;
        padding: 1 0;
    }
    #session-box Static {
        width: 100%;
        padding: 0 2;
    }
    #session-list {
        height: 1fr;
        overflow-y: auto;
    }
    .session-item {
        height: 3;
        padding: 0 1;
    }
    .session-item-selected {
        background: $primary 15%;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("n", "new_session", "New"),
    ]

    def __init__(self, sessions: list[dict], current_id: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.sessions = sessions
        self.current_id = current_id
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="session-box"):
            yield Static("[bold cyan]Sessions[/bold cyan]")
            if not self.sessions:
                yield Static("[dim]No saved sessions. Press 'n' for new session.[/dim]")
            with Vertical(id="session-list"):
                for i, s in enumerate(self.sessions):
                    is_current = s["id"] == self.current_id
                    marker = " [green]*[/green]" if is_current else ""
                    label = f"  {s['id']}  [dim]{s.get('updated_at', '')[:16]}[/dim]  [dim]{s.get('count', 0)} msgs[/dim]{marker}"
                    yield Static(label, classes="session-item" + (" session-item-selected" if i == self.selected_index else ""))

    def on_key(self, event: Any) -> None:
        if event.key == "up" and self.selected_index > 0:
            self.selected_index -= 1
            self._refresh_list()
            event.stop()
        elif event.key == "down" and self.selected_index < len(self.sessions) - 1:
            self.selected_index += 1
            self._refresh_list()
            event.stop()
        elif event.key == "enter":
            if self.sessions:
                self.dismiss(self.sessions[self.selected_index]["id"])
            event.stop()
        elif event.key == "n":
            self.dismiss("__new__")
            event.stop()

    def _refresh_list(self) -> None:
        items = self.query(".session-item")
        for i, item in enumerate(items):
            if i == self.selected_index:
                item.add_class("session-item-selected")
            else:
                item.remove_class("session-item-selected")

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_new_session(self) -> None:
        self.dismiss("__new__")


class ModelDialog(ModalScreen[str | None]):
    """Model picker dialog with search."""

    CSS = """
    ModelDialog {
        align: center middle;
    }
    #model-box {
        width: 60;
        max-height: 80%;
        background: $background-light;
        border: thick $border-focus;
        padding: 1 0;
    }
    #model-box Input {
        background: $surface;
        color: $text;
        border: none;
        padding: 0 2;
        margin: 0 0 1 0;
    }
    #model-box Static {
        width: 100%;
        padding: 0 2;
    }
    #model-list {
        height: 1fr;
        overflow-y: auto;
    }
    .model-item {
        height: 1;
        padding: 0 1;
    }
    .model-item-selected {
        background: $primary 15%;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, models: list[dict], current_model: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.all_models = models
        self.current_model = current_model
        self.filtered_models = list(models)
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="model-box"):
            yield Input(placeholder="Search models...", id="model-search")
            yield Static(f"[bold cyan]Models[/bold cyan] [dim]({len(self.all_models)} total)[/dim]")
            with Vertical(id="model-list"):
                for i, m in enumerate(self.filtered_models[:50]):
                    name = m.get("name", m["id"])
                    marker = " [green]*[/green]" if m["id"] == self.current_model else ""
                    yield Static(
                        f"  {m['id']}  [dim]{name}[/dim]{marker}",
                        classes="model-item" + (" model-item-selected" if i == self.selected_index else ""),
                    )
            yield Static("[dim]Type to search  Enter to select  Esc to cancel[/dim]")

    @on(Input.Changed, "#model-search")
    def on_search_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        self.filtered_models = [
            m for m in self.all_models
            if query in m["id"].lower() or query in m.get("name", "").lower()
        ]
        self.selected_index = 0
        self._refresh_list()

    def on_key(self, event: Any) -> None:
        if event.key == "up" and self.selected_index > 0:
            self.selected_index -= 1
            self._refresh_list()
            event.stop()
        elif event.key == "down" and self.selected_index < len(self.filtered_models) - 1:
            self.selected_index += 1
            self._refresh_list()
            event.stop()
        elif event.key == "enter":
            if self.filtered_models:
                self.dismiss(self.filtered_models[self.selected_index]["id"])
            event.stop()

    def _refresh_list(self) -> None:
        model_list = self.query_one("#model-list")
        model_list.remove_children()
        for i, m in enumerate(self.filtered_models[:50]):
            name = m.get("name", m["id"])
            marker = " [green]*[/green]" if m["id"] == self.current_model else ""
            label = Static(
                f"  {m['id']}  [dim]{name}[/dim]{marker}",
                classes="model-item" + (" model-item-selected" if i == self.selected_index else ""),
            )
            model_list.mount(label)

    def action_cancel(self) -> None:
        self.dismiss(None)


class CommandPalette(ModalScreen[str | None]):
    """Command palette (Ctrl+K) for quick actions."""

    CSS = """
    CommandPalette {
        align: center middle;
    }
    #cmd-box {
        width: 50;
        max-height: 70%;
        background: $background-light;
        border: thick $border-focus;
        padding: 1 0;
    }
    #cmd-box Input {
        background: $surface;
        color: $text;
        border: none;
        padding: 0 2;
        margin: 0 0 1 0;
    }
    #cmd-box Static {
        width: 100%;
        padding: 0 2;
    }
    #cmd-list {
        height: 1fr;
        overflow-y: auto;
    }
    .cmd-item {
        height: 1;
        padding: 0 1;
    }
    .cmd-item-selected {
        background: $primary 15%;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    COMMANDS = [
        {"id": "clear", "label": "Clear conversation", "shortcut": "/clear"},
        {"id": "status", "label": "Show gateway status", "shortcut": "/status"},
        {"id": "models", "label": "List available models", "shortcut": "/models"},
        {"id": "sessions", "label": "List saved sessions", "shortcut": "/sessions"},
        {"id": "save", "label": "Save current session", "shortcut": "/save"},
        {"id": "config", "label": "Show configuration", "shortcut": "/config"},
        {"id": "help", "label": "Show help", "shortcut": "/help"},
        {"id": "quit", "label": "Quit Patchbay", "shortcut": "/quit"},
        {"id": "new_session", "label": "New session", "shortcut": ""},
        {"id": "switch_model", "label": "Switch model...", "shortcut": "Ctrl+O"},
        {"id": "switch_session", "label": "Switch session...", "shortcut": "Ctrl+S"},
        {"id": "open_dashboard", "label": "Open dashboard", "shortcut": ""},
        {"id": "blender_info", "label": "Blender scene info", "shortcut": ""},
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.filtered = list(self.COMMANDS)
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="cmd-box"):
            yield Input(placeholder="Search commands...", id="cmd-search")
            yield Static("[bold cyan]Commands[/bold cyan]")
            with Vertical(id="cmd-list"):
                for i, cmd in enumerate(self.filtered):
                    shortcut = f"  [dim]{cmd['shortcut']}[/dim]" if cmd["shortcut"] else ""
                    yield Static(
                        f"  {cmd['label']}{shortcut}",
                        classes="cmd-item" + (" cmd-item-selected" if i == self.selected_index else ""),
                    )
            yield Static("[dim]Enter to run  Esc to cancel[/dim]")

    @on(Input.Changed, "#cmd-search")
    def on_search_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        self.filtered = [c for c in self.COMMANDS if query in c["label"].lower()]
        self.selected_index = 0
        self._refresh_list()

    def on_key(self, event: Any) -> None:
        if event.key == "up" and self.selected_index > 0:
            self.selected_index -= 1
            self._refresh_list()
            event.stop()
        elif event.key == "down" and self.selected_index < len(self.filtered) - 1:
            self.selected_index += 1
            self._refresh_list()
            event.stop()
        elif event.key == "enter":
            if self.filtered:
                self.dismiss(self.filtered[self.selected_index]["id"])
            event.stop()

    def _refresh_list(self) -> None:
        cmd_list = self.query_one("#cmd-list")
        cmd_list.remove_children()
        for i, cmd in enumerate(self.filtered):
            shortcut = f"  [dim]{cmd['shortcut']}[/dim]" if cmd["shortcut"] else ""
            label = Static(
                f"  {cmd['label']}{shortcut}",
                classes="cmd-item" + (" cmd-item-selected" if i == self.selected_index else ""),
            )
            cmd_list.mount(label)

    def action_cancel(self) -> None:
        self.dismiss(None)


class PermissionDialog(ModalScreen[str]):
    """Tool permission dialog - ask user before executing tools."""

    CSS = """
    PermissionDialog {
        align: center middle;
    }
    #perm-box {
        width: 50;
        background: $background-light;
        border: thick $warning;
        padding: 1 2;
        height: auto;
    }
    #perm-box Static {
        width: 100%;
    }
    .perm-buttons {
        margin-top: 1;
        width: 100%;
        height: 3;
        content-align: center middle;
    }
    """

    BINDINGS = [
        Binding("y", "allow", "Allow"),
        Binding("a", "allow_session", "Allow All"),
        Binding("n", "deny", "Deny"),
        Binding("escape", "deny", "Deny"),
    ]

    def __init__(self, tool_name: str, tool_args: dict, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.tool_name = tool_name
        self.tool_args = tool_args

    def compose(self) -> ComposeResult:
        args_str = ", ".join(f"{k}={repr(v)[:40]}" for k, v in self.tool_args.items())
        with Vertical(id="perm-box"):
            yield Static(f"[bold yellow]Tool Permission Required[/bold yellow]")
            yield Static(f"\n[bold]{self.tool_name}[/bold]([dim]{args_str}[/dim])")
            yield Static("\n[dim]Allow this tool call?[/dim]")
            with Horizontal(classes="perm-buttons"):
                yield Static("[bold green]y[/bold green] Allow  [bold cyan]a[/bold cyan] Allow all  [bold red]n[/bold red] Deny")

    def action_allow(self) -> None:
        self.dismiss("allow")

    def action_allow_session(self) -> None:
        self.dismiss("allow_session")

    def action_deny(self) -> None:
        self.dismiss("deny")


# ═══════════════════════════════════════════════════════════════
# LOG SCREEN
# ═══════════════════════════════════════════════════════════════

class LogScreen(Screen):
    """Log viewer screen."""

    CSS = """
    LogScreen {
        background: $background;
    }
    #log-view {
        height: 1fr;
        background: $background;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("q", "back", "Back"),
        Binding("ctrl+l", "back", "Back"),
    ]

    def __init__(self, logs: list[str], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.logs = logs

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="log-view", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        log_view = self.query_one("#log-view", RichLog)
        for line in self.logs:
            log_view.write(line)
        if not self.logs:
            log_view.write("[dim]No logs yet.[/dim]")

    def action_back(self) -> None:
        self.app.pop_screen()


# ═══════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════

class PatchbayApp(App):
    """Patchbay AI - Full-screen TUI for the Universal LLM Gateway."""

    TITLE = "Patchbay AI"
    SUB_TITLE = "Universal LLM Gateway"
    CSS_PATH = "tokyo-night.tcss"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("ctrl+?", "toggle_help", "Help", show=True),
        Binding("ctrl+k", "command_palette", "Commands", show=True),
        Binding("ctrl+s", "switch_session", "Session", show=True),
        Binding("ctrl+o", "switch_model", "Model", show=True),
        Binding("ctrl+l", "show_logs", "Logs", show=True),
        Binding("ctrl+x", "cancel_generation", "Cancel", show=True),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        cfg = get_config()
        self.provider: str = cfg.get("provider", "openai")
        self.model: str = cfg.get("model", "gpt-4o")
        self.session_id: str = str(uuid.uuid4())[:8]
        self.messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()},
        ]
        self.logs: list[str] = []
        self.is_generating: bool = False
        self.auto_approve_tools: bool = False
        self.pending_tool_calls: list[dict] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Header(show_clock=True)
            yield ScrollableContainer(id="chat-container")
            yield StreamingIndicator(id="streaming-indicator")
            with Container(id="input-area"):
                yield Input(placeholder="Message Patchbay... (Ctrl+S to send, / for commands)", id="user-input")
            yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        """Show welcome message on startup."""
        cfg = get_config()
        self.provider = cfg.get("provider", "openai")
        self.model = cfg.get("model", "gpt-4o")

        chat = self.query_one("#chat-container")
        chat.mount(ChatMessage("system", "[bold]Welcome to Patchbay AI[/bold]\n[dim]Universal LLM Gateway & AI Coding Assistant[/dim]\n\nType a message or press [bold]Ctrl+K[/bold] for commands."))
        chat.mount(ChatMessage("system", f"[dim]Provider: {self.provider} | Model: {self.model} | Session: {self.session_id}[/dim]"))

        self.query_one("#user-input", Input).focus()

    # ── Input Handling ──

    @on(Input.Submitted, "#user-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return

        event.input.value = ""

        if text.startswith("/"):
            self._handle_slash_command(text)
            return

        self._send_user_message(text)

    def _send_user_message(self, text: str) -> None:
        """Add user message and trigger LLM response."""
        self.messages.append({"role": "user", "content": text})
        self._add_chat_message("user", text)
        self._trigger_llm_response()

    def _add_chat_message(self, role: str, content: str) -> None:
        """Mount a chat message widget."""
        chat = self.query_one("#chat-container")
        chat.mount(ChatMessage(role, content))
        chat.scroll_end(animate=False)

    def _add_tool_call(self, name: str, args: dict, result: dict | None = None) -> None:
        """Mount a tool call widget."""
        chat = self.query_one("#chat-container")
        chat.mount(ToolCallWidget(name, args, result))
        chat.scroll_end(animate=False)

    # ── Slash Commands ──

    def _handle_slash_command(self, text: str) -> None:
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("/quit", "/exit", "/q"):
            self.action_quit()
        elif cmd in ("/help", "/h", "/?"):
            self.push_screen(HelpDialog())
        elif cmd == "/clear":
            self.messages.clear()
            self.messages.append({"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()})
            chat = self.query_one("#chat-container")
            chat.remove_children()
            self._add_chat_message("system", "[green]Conversation cleared.[/green]")
        elif cmd == "/status":
            self._show_status()
        elif cmd == "/models":
            self._show_models()
        elif cmd == "/sessions":
            self._show_sessions()
        elif cmd == "/save":
            save_session(self.session_id, self.messages, {"provider": self.provider, "model": self.model})
            self._add_chat_message("system", f"[green]Session saved: {self.session_id}[/green]")
        elif cmd == "/config":
            self._show_config()
        elif cmd == "/model":
            if arg:
                self.model = arg.strip()
                set_config_value("model", self.model)
                self._add_chat_message("system", f"[green]Model: {self.model}[/green]")
                self.query_one("#status-bar", StatusBar).update_status()
            else:
                self.action_switch_model()
        elif cmd == "/provider":
            if arg:
                self.provider = arg.strip().lower()
                set_config_value("provider", self.provider)
                self._add_chat_message("system", f"[green]Provider: {self.provider}[/green]")
                self.query_one("#status-bar", StatusBar).update_status()
            else:
                self._add_chat_message("system", f"[dim]Current: {self.provider}. Use /provider <name> to switch.[/dim]")
        elif cmd == "/blender":
            self._show_blender()
        else:
            self._add_chat_message("system", f"[red]Unknown command: {cmd}[/red] (type /help)")

    def _show_status(self) -> None:
        items = get_full_status()
        lines = ["[bold]System Status[/bold]\n"]
        for name, color, detail in items:
            icon = f"[green]+[/green]" if color == "green" else "[red]-[/red]"
            lines.append(f"  {icon} [bold]{name}[/bold]: {detail}")
        self._add_chat_message("system", "\n".join(lines))

    def _show_models(self) -> None:
        models = list_models()
        if models:
            lines = [f"[bold]Gateway Models ({len(models)})[/bold]\n"]
            for m in models[:30]:
                lines.append(f"  [cyan]{m.get('id', '?')}[/cyan]")
            self._add_chat_message("system", "\n".join(lines))
        else:
            self._add_chat_message("system", "[dim]Could not fetch models. Is the gateway running?[/dim]")

    def _show_sessions(self) -> None:
        sessions = list_sessions()
        if not sessions:
            self._add_chat_message("system", "[dim]No saved sessions.[/dim]")
            return
        lines = [f"[bold]Saved Sessions ({len(sessions)})[/bold]\n"]
        for s in sessions[:10]:
            lines.append(f"  [cyan]{s['id']}[/cyan]  [dim]{s.get('updated_at', '')[:16]}[/dim]  [dim]{s.get('count', 0)} msgs[/dim]")
        self._add_chat_message("system", "\n".join(lines))

    def _show_config(self) -> None:
        cfg = get_config()
        lines = ["[bold]Configuration[/bold]\n"]
        for k, v in cfg.items():
            if "key" in k.lower() or "secret" in k.lower():
                val = f"***{str(v)[-4:]}" if len(str(v)) > 4 else "***"
            else:
                val = str(v)
            lines.append(f"  [bold]{k}[/bold] = {val}")
        self._add_chat_message("system", "\n".join(lines))

    def _show_blender(self) -> None:
        scene = blender_get_scene()
        if "error" in scene:
            self._add_chat_message("system", f"[red]Blender: {scene['error']}[/red]")
            return
        self._add_chat_message("system", f"[bold]Blender Scene[/bold]\n  Name: {scene.get('name', '?')}\n  Objects: {scene.get('object_count', 0)}")

    # ── LLM Response ──

    @work(exclusive=True, group="llm", thread=True)
    def _trigger_llm_response(self) -> None:
        """Stream LLM response in background."""
        self.is_generating = True
        indicator = self.query_one("#streaming-indicator", StreamingIndicator)
        indicator.show_streaming(self.model)

        accumulator = StreamAccumulator()
        full_text = ""

        try:
            for chunk in stream_completion(self.provider, self.model, self.messages, tools=TOOLS_SPEC):
                text = accumulator.process_chunk(chunk)
                if text:
                    full_text += text
                    # Update the last assistant message or create new one
                    self._update_streaming_message(full_text)

                if accumulator.error:
                    self._add_chat_message("system", f"[red]Error: {accumulator.error}[/red]")
                    break

        except Exception as e:
            self._add_chat_message("system", f"[red]Stream error: {e}[/red]")
        finally:
            indicator.hide_streaming()
            self.is_generating = False

        if accumulator.error:
            return

        # Build final message
        resp = accumulator.finalize()
        self.messages.append(resp)

        # Handle tool calls
        tool_calls = resp.get("tool_calls", [])
        if tool_calls:
            self._handle_tool_calls(tool_calls)

    def _update_streaming_message(self, text: str) -> None:
        """Update or create streaming message display."""
        chat = self.query_one("#chat-container")
        # Remove old streaming message if exists
        existing = chat.query(".streaming-msg")
        if existing:
            existing[0].remove()
        # Mount updated
        chat.mount(ChatMessage("assistant", text, classes="streaming-msg"))
        chat.scroll_end(animate=False)

    # ── Tool Execution ──

    def _handle_tool_calls(self, tool_calls: list[dict]) -> None:
        """Execute tool calls with permission dialogs."""
        for tc in tool_calls:
            func = tc.get("function", {})
            name = func.get("name", "")
            try:
                args = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}

            # Check permission
            if not self.auto_approve_tools:
                result = self._request_tool_permission(name, args)
                if result == "deny":
                    self.messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tc],
                    })
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "content": "Tool call denied by user.",
                    })
                    self._add_tool_call(name, args, {"error": "Denied by user"})
                    continue
                elif result == "allow_session":
                    self.auto_approve_tools = True

            # Execute
            exec_result = execute_tool(name, args)
            self._add_tool_call(name, args, exec_result)

            # Format for LLM
            result_text = _format_tool_result(name, exec_result)
            clean_text = re.sub(r'\[/?[a-zA-Z_][^\]]*\]', '', result_text)
            if len(clean_text) > 8000:
                clean_text = clean_text[:8000] + "\n... (truncated)"

            self.messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [tc],
            })
            self.messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": clean_text,
            })

        # Continue LLM after tools
        self._trigger_llm_response()

    def _request_tool_permission(self, name: str, args: dict) -> str:
        """Show permission dialog and wait for response."""
        result = self.push_screen_wait(PermissionDialog(name, args))
        return result or "deny"

    # ── Actions (keybindings) ──

    def action_quit(self) -> None:
        result = self.push_screen_wait(QuitDialog())
        if result:
            save_session(self.session_id, self.messages, {"provider": self.provider, "model": self.model})
            self.exit()

    def action_toggle_help(self) -> None:
        self.push_screen(HelpDialog())

    def action_command_palette(self) -> None:
        result = self.push_screen_wait(CommandPalette())
        if result:
            self._handle_command_result(result)

    def action_switch_session(self) -> None:
        sessions = list_sessions()
        result = self.push_screen_wait(SessionDialog(sessions, self.session_id))
        if result == "__new__":
            self.session_id = str(uuid.uuid4())[:8]
            self.messages.clear()
            self.messages.append({"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()})
            chat = self.query_one("#chat-container")
            chat.remove_children()
            self._add_chat_message("system", f"[green]New session: {self.session_id}[/green]")
        elif result:
            data = load_session(result)
            if data:
                self.session_id = result
                self.messages.clear()
                self.messages.extend(data.get("messages", []))
                chat = self.query_one("#chat-container")
                chat.remove_children()
                # Replay messages
                for m in self.messages:
                    if m["role"] in ("user", "assistant") and m.get("content"):
                        self._add_chat_message(m["role"], m["content"])
                self._add_chat_message("system", f"[green]Loaded session {result} ({len(self.messages)} messages)[/green]")
        self.query_one("#status-bar", StatusBar).update_status()

    def action_switch_model(self) -> None:
        self._show_model_picker()

    @work(exclusive=True, group="model_picker", thread=True)
    def _show_model_picker(self) -> None:
        """Fetch models and show picker."""
        self._add_chat_message("system", "[dim]Fetching models...[/dim]")
        models = fetch_models_cached(self.provider)
        if not models:
            self._add_chat_message("system", f"[dim]No models fetched for {self.provider}. Using config.[/dim]")
            return

        result = self.push_screen_wait(ModelDialog(models, self.model))
        if result:
            self.model = result
            set_config_value("model", self.model)
            self._add_chat_message("system", f"[green]Model: {self.model}[/green]")
            self.query_one("#status-bar", StatusBar).update_status()

    def action_show_logs(self) -> None:
        self.push_screen(LogScreen(self.logs))

    def action_cancel_generation(self) -> None:
        if self.is_generating:
            self._add_chat_message("system", "[yellow]Generation cancelled.[/yellow]")
            # The work decorator will handle cancellation
            self.query_one("#streaming-indicator", StreamingIndicator).hide_streaming()
            self.is_generating = False

    def _handle_command_result(self, command_id: str) -> None:
        """Execute a command from the palette."""
        if command_id == "clear":
            self._handle_slash_command("/clear")
        elif command_id == "status":
            self._show_status()
        elif command_id == "models":
            self._show_models()
        elif command_id == "sessions":
            self._show_sessions()
        elif command_id == "save":
            self._handle_slash_command("/save")
        elif command_id == "config":
            self._show_config()
        elif command_id == "help":
            self.push_screen(HelpDialog())
        elif command_id == "quit":
            self.action_quit()
        elif command_id == "new_session":
            self.session_id = str(uuid.uuid4())[:8]
            self.messages.clear()
            self.messages.append({"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()})
            chat = self.query_one("#chat-container")
            chat.remove_children()
            self._add_chat_message("system", f"[green]New session: {self.session_id}[/green]")
        elif command_id == "switch_model":
            self.action_switch_model()
        elif command_id == "switch_session":
            self.action_switch_session()
        elif command_id == "open_dashboard":
            import webbrowser
            cfg = get_config()
            webbrowser.open(cfg.get("dashboard_url", "http://localhost:3000"))
            self._add_chat_message("system", "[green]Opening dashboard...[/green]")
        elif command_id == "blender_info":
            self._show_blender()



# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = PatchbayApp()
    app.run()
