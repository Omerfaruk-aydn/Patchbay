"""Patchbay TUI - Full-screen terminal UI matching Codex/MiMoCode patterns.

Design principles (from Codex CLI source analysis):
- User messages: subtle background highlight, no border
- AI messages: plain text with role label
- Tool calls: inline exec cells with command + output
- Status bar at bottom: model, provider, context info
- No heavy panels or borders on messages
- Cyan accent color, Tokyo Night palette
- Approval dialog for tool execution
"""

from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Input, RichLog, Static

from patchbay.config import get_config, set_config_value
from patchbay.providers import StreamAccumulator, fetch_models_cached, stream_completion
from patchbay.session import list_sessions, load_session, save_session
from patchbay.tools import TOOLS_SPEC, execute_tool
from patchbay.gateway import blender_get_scene, get_full_status, list_models

SYSTEM_PROMPT = """You are Patchbay AI, an expert software engineering assistant embedded in a CLI tool.

You help with writing, reading, editing, and debugging code. You understand codebases and can run shell commands.

Tools: read_file, write_file, edit_file, run_bash, search_files, search_content, list_directory.
Rules: prefer edit_file over write_file, verify changes, be concise, never commit secrets."""


def get_project_context() -> str:
    parts = [f"Working directory: {os.getcwd()}"]
    for fname in ["README.md", "CLAUDE.md", "pyproject.toml", "package.json"]:
        p = __import__("pathlib").Path(fname)
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
# MESSAGE WIDGETS (Codex-style: no borders, subtle highlights)
# ═══════════════════════════════════════════════════════════════

class UserMessage(Static):
    """User message with subtle background highlight (like Codex)."""
    DEFAULT_CSS = """
    UserMessage {
        height: auto;
        padding: 0 1;
        background: #282d45;
    }
    """

    def __init__(self, content: str) -> None:
        text = f"[bold #7aa2f7]  You[/]\n{content}"
        super().__init__(text)


class AssistantMessage(Static):
    """AI response message — plain text, no highlight."""
    DEFAULT_CSS = """
    AssistantMessage {
        height: auto;
        padding: 0 1;
    }
    """

    def __init__(self, content: str) -> None:
        text = f"[bold #9ece6a]  AI[/]\n{content}"
        super().__init__(text)


class SystemMessage(Static):
    """System/info message — dimmed."""
    DEFAULT_CSS = """
    SystemMessage {
        height: auto;
        padding: 0 1;
    }
    """

    def __init__(self, content: str) -> None:
        super().__init__(f"[#565f89]  {content}[/]")


class ErrorMessage(Static):
    """Error message — red."""
    DEFAULT_CSS = """
    ErrorMessage {
        height: auto;
        padding: 0 1;
    }
    """

    def __init__(self, content: str) -> None:
        super().__init__(f"[bold #f7768e]  Error[/]\n[#f7768e]{content}[/]")


class ExecCell(Static):
    """Tool execution cell — like Codex's exec_cell.

    Shows command name + args on first line, result on subsequent lines.
    Uses subtle left border accent for visual grouping.
    """
    DEFAULT_CSS = """
    ExecCell {
        height: auto;
        padding: 0 1 0 3;
    }
    """

    def __init__(self, name: str, args: dict, result: dict | None = None) -> None:
        args_s = ", ".join(f"{k}={repr(v)[:40]}" for k, v in args.items())
        lines = [f"[#e0af68]  >[/] [bold #c0caf5]{name}[/][#565f89]({args_s})[/]"]
        if result:
            if result.get("error"):
                lines.append(f"  [#f7768e]x[/] {result['error'][:150]}")
            else:
                r = _fmt_result(name, result)
                for line in r.split("\n")[:6]:
                    lines.append(f"  [#565f89]{line}[/]")
        super().__init__("\n".join(lines))


# ═══════════════════════════════════════════════════════════════
# STATUS BAR (like Codex: model + dir + context)
# ═══════════════════════════════════════════════════════════════

class StatusBar(Static):
    """Bottom status bar — model, provider, session, keybindings."""
    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: #1f2335;
        color: #565f89;
        padding: 0 1;
    }
    """

    def __init__(self, provider: str, model: str, session_id: str) -> None:
        text = (
            f" [#7aa2f7 bold]patchbay[/]"
            f" [#3b4261]|[/]"
            f" [#9ece6a]{provider}[/]"
            f" [#3b4261]|[/]"
            f" [#c0caf5]{model}[/]"
            f" [#3b4261]|[/]"
            f" [#565f89]{session_id}[/]"
            f" [#3b4261]|[/]"
            f" [#3b4261]Ctrl+K[/] [#565f89]cmd[/]"
            f" [#3b4261]|[/]"
            f" [#3b4261]Ctrl+S[/] [#565f89]session[/]"
            f" [#3b4261]|[/]"
            f" [#3b4261]Ctrl+O[/] [#565f89]model[/]"
            f" [#3b4261]|[/]"
            f" [#3b4261]Ctrl+?[/] [#565f89]help[/]"
        )
        super().__init__(text)

    def update_info(self, provider: str, model: str, session_id: str) -> None:
        self.__init__(provider, model, session_id)


# ═══════════════════════════════════════════════════════════════
# STREAM BAR (like Codex: shows what's being generated)
# ═══════════════════════════════════════════════════════════════

class StreamBar(Static):
    """Shows streaming text preview above input."""
    DEFAULT_CSS = """
    StreamBar {
        dock: bottom;
        height: auto;
        max-height: 6;
        background: #1a1b26;
        color: #7dcfff;
        padding: 0 1;
        display: none;
    }
    """

    def show_text(self, text: str) -> None:
        if text:
            preview = text[-120:].replace("\n", " ")
            self.update(f"  {preview}[_]")
            self.display = True
        else:
            self.display = False


# ═══════════════════════════════════════════════════════════════
# DIALOGS (overlay style, like Codex approval dialogs)
# ═══════════════════════════════════════════════════════════════

class QuitScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    QuitScreen {
        align: center middle;
    }
    #quit-box {
        width: 44;
        height: auto;
        background: #1f2335;
        border: thick #f7768e;
        padding: 1 2;
    }
    """
    BINDINGS = [("y", "quit", "Quit"), ("n", "cancel", "Cancel"), ("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="quit-box"):
            yield Static("[bold #f7768e]  Quit Patchbay?[/]")
            yield Static("[#565f89]  Unsaved changes will be lost.[/]")
            yield Static("")
            yield Static("  [#9ece6a]y[/] Quit   [#565f89]n[/] Cancel")

    def action_quit(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class HelpScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-box {
        width: 60;
        height: auto;
        max-height: 32;
        background: #1f2335;
        border: thick #7aa2f7;
        padding: 1 2;
        overflow-y: auto;
    }
    """
    BINDINGS = [("escape", "close", "Close"), ("ctrl+?", "close", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-box"):
            yield Static("[bold #7aa2f7]  Patchbay AI[/]\n")
            yield Static("[bold #c0caf5]Keyboard[/]")
            for k, d in [
                ("Ctrl+C", "Quit"), ("Ctrl+K", "Command palette"),
                ("Ctrl+S", "Switch session"), ("Ctrl+O", "Switch model"),
                ("Ctrl+L", "Logs"), ("Ctrl+?", "Help"), ("Ctrl+X", "Cancel"), ("Enter", "Send"),
            ]:
                yield Static(f"  [#7dcfff]{k:12s}[/] [#565f89]{d}[/]")
            yield Static("")
            yield Static("[bold #c0caf5]Commands[/]")
            for c, d in [
                ("/help", "This help"), ("/clear", "Clear chat"), ("/model", "Switch model"),
                ("/provider", "Switch provider"), ("/status", "Gateway status"),
                ("/models", "List models"), ("/sessions", "List sessions"),
                ("/save", "Save session"), ("/config", "Show config"), ("/quit", "Exit"),
            ]:
                yield Static(f"  [#c0caf5]{c:14s}[/] [#565f89]{d}[/]")
            yield Static("\n  [#3b4261]Esc to close[/]")

    def action_close(self) -> None:
        self.dismiss(False)


class SessionScreen(ModalScreen[str | None]):
    DEFAULT_CSS = """
    SessionScreen {
        align: center middle;
    }
    #sess-box {
        width: 56;
        height: auto;
        max-height: 28;
        background: #1f2335;
        border: thick #7aa2f7;
        padding: 1 2;
        overflow-y: auto;
    }
    """
    BINDINGS = [("escape", "cancel", "Cancel"), ("n", "new", "New")]

    def __init__(self, sessions: list[dict], **kw: Any) -> None:
        super().__init__(**kw)
        self.sessions = sessions
        self.sel = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="sess-box"):
            yield Static(f"[bold #7aa2f7]  Sessions[/] [#565f89]({len(self.sessions)})[/]\n")
            if not self.sessions:
                yield Static("[#565f89]  No sessions. Press n for new.[/]")
            for s in self.sessions:
                yield Static(
                    f"  [#7aa2f7]{s['id']}[/]"
                    f"  [#565f89]{s.get('updated_at','')[:16]}[/]"
                    f"  [#565f89]{s.get('count',0)} msgs[/]"
                )
            yield Static("\n  [#3b4261]Enter select[/] [#3b4261]n[/] new [#3b4261]Esc[/] cancel")

    def on_key(self, event: Any) -> None:
        if event.key == "enter" and self.sessions:
            self.dismiss(self.sessions[self.sel]["id"])
            event.stop()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_new(self) -> None:
        self.dismiss("__new__")


class ModelScreen(ModalScreen[str | None]):
    DEFAULT_CSS = """
    ModelScreen {
        align: center middle;
    }
    #model-box {
        width: 64;
        height: auto;
        max-height: 32;
        background: #1f2335;
        border: thick #7aa2f7;
        padding: 1 2;
        overflow-y: auto;
    }
    #model-box Input {
        background: #2a2e42;
        color: #c0caf5;
        border: none;
        margin-bottom: 1;
    }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, models: list[dict], current: str = "", **kw: Any) -> None:
        super().__init__(**kw)
        self.all_models = models
        self.current = current
        self.filtered = list(models[:60])
        self.sel = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="model-box"):
            yield Input(placeholder="Search...", id="msearch")
            yield Static(f"[bold #7aa2f7]  Models[/] [#565f89]({len(self.all_models)})[/]\n")
            for m in self.filtered:
                cur = " [#9ece6a]*[/]" if m["id"] == self.current else ""
                yield Static(f"  [#c0caf5]{m['id']}[/]  [#565f89]{m.get('name','')}[/]{cur}")
            yield Static("\n  [#3b4261]Enter select[/] [#3b4261]Esc[/] cancel")

    @on(Input.Changed, "#msearch")
    def search_changed(self, ev: Input.Changed) -> None:
        q = ev.value.lower()
        self.filtered = [m for m in self.all_models if q in m["id"].lower() or q in m.get("name", "").lower()][:60]
        self.sel = 0

    def on_key(self, event: Any) -> None:
        if event.key == "enter" and self.filtered:
            self.dismiss(self.filtered[self.sel]["id"])
            event.stop()

    def action_cancel(self) -> None:
        self.dismiss(None)


class CmdPalette(ModalScreen[str | None]):
    DEFAULT_CSS = """
    CmdPalette {
        align: center middle;
    }
    #cmd-box {
        width: 52;
        height: auto;
        max-height: 28;
        background: #1f2335;
        border: thick #7aa2f7;
        padding: 1 2;
        overflow-y: auto;
    }
    #cmd-box Input {
        background: #2a2e42;
        color: #c0caf5;
        border: none;
        margin-bottom: 1;
    }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    CMDS = [
        ("clear", "Clear conversation", "/clear"),
        ("status", "Gateway status", "/status"),
        ("models", "List models", "/models"),
        ("sessions", "List sessions", "/sessions"),
        ("save", "Save session", "/save"),
        ("config", "Show config", "/config"),
        ("help", "Help", "/help"),
        ("quit", "Quit", "/quit"),
        ("new_session", "New session", ""),
        ("switch_model", "Switch model", "Ctrl+O"),
        ("switch_session", "Switch session", "Ctrl+S"),
    ]

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        self.filtered = list(self.CMDS)
        self.sel = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="cmd-box"):
            yield Input(placeholder="Search...", id="csearch")
            yield Static("[bold #7aa2f7]  Commands[/]\n")
            for cid, label, shortcut in self.filtered:
                sc = f"  [#565f89]{shortcut}[/]" if shortcut else ""
                yield Static(f"  [#c0caf5]{label}[/]{sc}")
            yield Static("\n  [#3b4261]Enter run[/] [#3b4261]Esc[/] cancel")

    @on(Input.Changed, "#csearch")
    def search_changed(self, ev: Input.Changed) -> None:
        q = ev.value.lower()
        self.filtered = [(i, l, s) for i, l, s in self.CMDS if q in l.lower()][:30]
        self.sel = 0

    def on_key(self, event: Any) -> None:
        if event.key == "enter" and self.filtered:
            self.dismiss(self.filtered[self.sel][0])
            event.stop()

    def action_cancel(self) -> None:
        self.dismiss(None)


class ApprovalScreen(ModalScreen[str]):
    """Tool approval dialog — like Codex's approval screen."""
    DEFAULT_CSS = """
    ApprovalScreen {
        align: center middle;
    }
    #approval-box {
        width: 56;
        height: auto;
        background: #1f2335;
        border: thick #e0af68;
        padding: 1 2;
    }
    """
    BINDINGS = [("y", "allow", "Allow"), ("a", "allow_all", "All"), ("n", "deny", "Deny"), ("escape", "deny", "Deny")]

    def __init__(self, tool_name: str, tool_args: dict, **kw: Any) -> None:
        super().__init__(**kw)
        self.tn = tool_name
        self.ta = tool_args

    def compose(self) -> ComposeResult:
        args = ", ".join(f"{k}={repr(v)[:30]}" for k, v in self.ta.items())
        with Vertical(id="approval-box"):
            yield Static("[bold #e0af68]  Approval Required[/]\n")
            yield Static(f"  [#c0caf5]{self.tn}[/][#565f89]({args})[/]\n")
            yield Static("  [#9ece6a]y[/] Allow   [#7dcfff]a[/] Allow all   [#f7768e]n[/] Deny")

    def action_allow(self) -> None:
        self.dismiss("allow")

    def action_allow_all(self) -> None:
        self.dismiss("allow_all")

    def action_deny(self) -> None:
        self.dismiss("deny")


class LogScreen(Screen):
    DEFAULT_CSS = """
    LogScreen {
        background: #1a1b26;
    }
    #log-box {
        height: 1fr;
        background: #1a1b26;
    }
    """
    BINDINGS = [("escape", "back", "Back"), ("q", "back", "Back"), ("ctrl+l", "back", "Back")]

    def __init__(self, logs: list[str], **kw: Any) -> None:
        super().__init__(**kw)
        self.logs = logs

    def compose(self) -> ComposeResult:
        yield RichLog(id="log-box", highlight=True, markup=True)

    def on_mount(self) -> None:
        log = self.query_one("#log-box", RichLog)
        for line in self.logs:
            log.write(line)
        if not self.logs:
            log.write("[#565f89]No logs yet.[/]")

    def action_back(self) -> None:
        self.app.pop_screen()


# ═══════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════

class PatchbayApp(App):
    """Patchbay AI — Codex/MiMoCode-style TUI."""

    TITLE = "Patchbay AI"
    DEFAULT_CSS = """
    Screen {
        background: #1a1b26;
    }
    #main {
        height: 1fr;
    }
    #chat {
        height: 1fr;
        overflow-y: auto;
        padding: 0 0;
    }
    #input-area {
        dock: bottom;
        height: auto;
        min-height: 3;
        max-height: 12;
        background: #1a1b26;
        padding: 0 0;
    }
    #input-area Input {
        background: #1f2335;
        color: #c0caf5;
        border: none;
        padding: 0 1;
    }
    #input-area Input:focus {
        background: #24283b;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=False),
        Binding("ctrl+?", "help", "Help", show=False),
        Binding("ctrl+k", "palette", "Cmds", show=False),
        Binding("ctrl+s", "session", "Session", show=False),
        Binding("ctrl+o", "model", "Model", show=False),
        Binding("ctrl+l", "logs", "Logs", show=False),
        Binding("ctrl+x", "cancel_gen", "Cancel", show=False),
    ]

    def __init__(self, **kw: Any) -> None:
        super().__init__(**kw)
        cfg = get_config()
        self.provider = cfg.get("provider", "openai")
        self.model = cfg.get("model", "gpt-4o")
        self.session_id = str(uuid.uuid4())[:8]
        self.messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()},
        ]
        self.logs: list[str] = []
        self.is_generating = False
        self.auto_approve = False

    def compose(self) -> ComposeResult:
        yield Vertical(
            ScrollableContainer(id="chat"),
            StreamBar(id="stream-bar"),
            Input(placeholder="Message Patchbay...  / for commands", id="input-area"),
            StatusBar(self.provider, self.model, self.session_id),
            id="main",
        )

    def on_mount(self) -> None:
        self._sys("Welcome to Patchbay AI  |  Universal LLM Gateway")
        self._sys(f"{self.provider} | {self.model} | {self.session_id}")
        self.query_one("#input-area", Input).focus()

    # ── Message helpers ──

    def _user(self, text: str) -> None:
        chat = self.query_one("#chat")
        chat.mount(UserMessage(text))
        chat.scroll_end(animate=False)

    def _ai(self, text: str) -> None:
        chat = self.query_one("#chat")
        chat.mount(AssistantMessage(text))
        chat.scroll_end(animate=False)

    def _sys(self, text: str) -> None:
        chat = self.query_one("#chat")
        chat.mount(SystemMessage(text))
        chat.scroll_end(animate=False)

    def _err(self, text: str) -> None:
        chat = self.query_one("#chat")
        chat.mount(ErrorMessage(text))
        chat.scroll_end(animate=False)

    def _exec(self, name: str, args: dict, result: dict | None = None) -> None:
        chat = self.query_one("#chat")
        chat.mount(ExecCell(name, args, result))
        chat.scroll_end(animate=False)

    def _stream(self, text: str) -> None:
        self.query_one("#stream-bar", StreamBar).show_text(text)

    def _refresh_status(self) -> None:
        old = self.query_one(StatusBar)
        old.remove()
        self.mount(StatusBar(self.provider, self.model, self.session_id), after=self.query_one("#input-area"))

    # ── Input ──

    @on(Input.Submitted, "#input-area")
    def on_submit(self, ev: Input.Submitted) -> None:
        text = ev.value.strip()
        ev.input.value = ""
        if not text:
            return
        if text.startswith("/"):
            self._cmd(text)
            return
        self.messages.append({"role": "user", "content": text})
        self._user(text)
        self._llm()

    # ── Slash commands ──

    def _cmd(self, text: str) -> None:
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd in ("/quit", "/exit", "/q"):
            self.action_quit()
        elif cmd in ("/help", "/h", "/?"):
            self.push_screen(HelpScreen())
        elif cmd == "/clear":
            self.messages = [self.messages[0]]
            self.query_one("#chat").remove_children()
            self._sys("Cleared.")
        elif cmd == "/status":
            items = get_full_status()
            lines = ["[bold #7aa2f7]Status[/]\n"]
            for name, color, detail in items:
                c = "#9ece6a" if color == "green" else "#f7768e"
                lines.append(f"  [{c}]+[/] [#c0caf5]{name}[/] [#565f89]{detail}[/]")
            self._sys("\n".join(lines))
        elif cmd == "/models":
            models = list_models()
            if models:
                lines = [f"[bold #7aa2f7]Models ({len(models)})[/]\n"]
                for m in models[:30]:
                    lines.append(f"  [#c0caf5]{m.get('id','?')}[/]")
                self._sys("\n".join(lines))
            else:
                self._sys("[#565f89]No models. Is gateway running?[/]")
        elif cmd == "/sessions":
            sessions = list_sessions()
            if not sessions:
                self._sys("[#565f89]No sessions.[/]")
                return
            lines = [f"[bold #7aa2f7]Sessions ({len(sessions)})[/]\n"]
            for s in sessions[:10]:
                lines.append(f"  [#7aa2f7]{s['id']}[/]  [#565f89]{s.get('updated_at','')[:16]}  {s.get('count',0)} msgs[/]")
            self._sys("\n".join(lines))
        elif cmd == "/save":
            save_session(self.session_id, self.messages, {"provider": self.provider, "model": self.model})
            self._sys(f"[#9ece6a]Saved: {self.session_id}[/]")
        elif cmd == "/config":
            cfg = get_config()
            lines = ["[bold #7aa2f7]Config[/]\n"]
            for k, v in cfg.items():
                if "key" in k.lower():
                    v = f"***{str(v)[-4:]}" if len(str(v)) > 4 else "***"
                lines.append(f"  [#c0caf5]{k}[/] = [#565f89]{v}[/]")
            self._sys("\n".join(lines))
        elif cmd == "/model":
            if arg:
                self.model = arg.strip()
                set_config_value("model", self.model)
                self._sys(f"[#9ece6a]Model: {self.model}[/]")
                self._refresh_status()
            else:
                self.action_model()
        elif cmd == "/provider":
            if arg:
                self.provider = arg.strip().lower()
                set_config_value("provider", self.provider)
                self._sys(f"[#9ece6a]Provider: {self.provider}[/]")
                self._refresh_status()
            else:
                self._sys(f"[#565f89]Current: {self.provider}. Use /provider <name>[/]")
        elif cmd == "/blender":
            scene = blender_get_scene()
            if "error" in scene:
                self._err(f"Blender: {scene['error']}")
            else:
                self._sys(f"[#7aa2f7]Blender[/] {scene.get('name','?')}  {scene.get('object_count',0)} objects")
        else:
            self._err(f"Unknown: {cmd}  /help")

    # ── LLM streaming ──

    @work(exclusive=True, group="llm", thread=True)
    def _llm(self) -> None:
        self.is_generating = True
        acc = StreamAccumulator()
        full = ""
        try:
            for chunk in stream_completion(self.provider, self.model, self.messages, tools=TOOLS_SPEC):
                text = acc.process_chunk(chunk)
                if text:
                    full += text
                    self._stream(full)
                if acc.error:
                    self._err(acc.error)
                    break
        except Exception as e:
            self._err(str(e))
        finally:
            self._stream("")
            self.is_generating = False

        if acc.error:
            return

        resp = acc.finalize()
        self.messages.append(resp)

        tool_calls = resp.get("tool_calls", [])
        if tool_calls:
            self._tools(tool_calls)
        else:
            if full:
                self._ai(full)

    # ── Tool execution ──

    def _tools(self, tool_calls: list[dict]) -> None:
        for tc in tool_calls:
            func = tc.get("function", {})
            name = func.get("name", "")
            try:
                args = json.loads(func.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}

            if not self.auto_approve:
                perm = self._ask_approval(name, args)
                if perm == "deny":
                    self.messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                    self.messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": "Denied by user"})
                    self._exec(name, args, {"error": "Denied"})
                    continue
                elif perm == "allow_all":
                    self.auto_approve = True

            result = execute_tool(name, args)
            self._exec(name, args, result)

            result_text = _fmt_result(name, result)
            clean = re.sub(r'\[/?[a-zA-Z_][^\]]*\]', '', result_text)
            if len(clean) > 8000:
                clean = clean[:8000] + "\n... truncated"

            self.messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
            self.messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": clean})

        self._llm()

    def _ask_approval(self, name: str, args: dict) -> str:
        import concurrent.futures
        future: concurrent.futures.Future[str] = concurrent.futures.Future()

        def _do() -> None:
            self.push_screen(ApprovalScreen(name, args), callback=lambda r: future.set_result(r or "deny"))

        self.call_from_thread(_do)
        try:
            return future.result(timeout=120)
        except Exception:
            return "deny"

    # ── Actions ──

    def action_quit(self) -> None:
        def _on_result(result: bool) -> None:
            if result:
                save_session(self.session_id, self.messages, {"provider": self.provider, "model": self.model})
                self.exit()

        self.push_screen(QuitScreen(), callback=_on_result)

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_palette(self) -> None:
        def _on_result(cid: str | None) -> None:
            if cid:
                self._run_cmd(cid)
        self.push_screen(CmdPalette(), callback=_on_result)

    def _run_cmd(self, cid: str) -> None:
        if cid == "clear":
            self._cmd("/clear")
        elif cid == "status":
            self._cmd("/status")
        elif cid == "models":
            self._cmd("/models")
        elif cid == "sessions":
            self._cmd("/sessions")
        elif cid == "save":
            self._cmd("/save")
        elif cid == "config":
            self._cmd("/config")
        elif cid == "help":
            self.push_screen(HelpScreen())
        elif cid == "quit":
            self.action_quit()
        elif cid == "new_session":
            self._cmd("/clear")
            self.session_id = str(uuid.uuid4())[:8]
            self._refresh_status()
        elif cid == "switch_model":
            self.action_model()
        elif cid == "switch_session":
            self.action_session()

    def action_session(self) -> None:
        sessions = list_sessions()

        def _on_result(sid: str | None) -> None:
            if sid == "__new__":
                self.session_id = str(uuid.uuid4())[:8]
                self.messages = [self.messages[0]]
                self.query_one("#chat").remove_children()
                self._sys(f"[#9ece6a]New: {self.session_id}[/]")
                self._refresh_status()
            elif sid:
                data = load_session(sid)
                if data:
                    self.session_id = sid
                    self.messages = data.get("messages", [])
                    self.query_one("#chat").remove_children()
                    for m in self.messages:
                        if m.get("role") in ("user", "assistant") and m.get("content"):
                            if m["role"] == "user":
                                self._user(m["content"])
                            else:
                                self._ai(m["content"])
                    self._sys(f"[#9ece6a]Loaded: {sid}[/]")
                    self._refresh_status()

        self.push_screen(SessionScreen(sessions), callback=_on_result)

    def action_model(self) -> None:
        @work(thread=True)
        def _fetch() -> None:
            models = fetch_models_cached(self.provider)
            if not models:
                self._sys("[#565f89]No models fetched.[/]")
                return

            def _on_result(mid: str | None) -> None:
                if mid:
                    self.model = mid
                    set_config_value("model", self.model)
                    self._sys(f"[#9ece6a]Model: {self.model}[/]")
                    self._refresh_status()

            self.call_from_thread(lambda: self.push_screen(ModelScreen(models, self.model), callback=_on_result))

        _fetch()

    def action_logs(self) -> None:
        self.push_screen(LogScreen(self.logs))

    def action_cancel_gen(self) -> None:
        if self.is_generating:
            self._sys("[#e0af68]Cancelled.[/]")
            self._stream("")
            self.is_generating = False


if __name__ == "__main__":
    PatchbayApp().run()
