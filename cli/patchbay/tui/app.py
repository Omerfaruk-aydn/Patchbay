"""Patchbay TUI - Full-screen terminal UI inspired by OpenCode.

Clean, minimal design like OpenCode/Crush:
- Chat messages with role labels
- Status bar at bottom
- Input area with border
- Overlay dialogs for help, sessions, models, commands
- Tokyo Night color palette hardcoded in DEFAULT_CSS
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
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.screen import ModalScreen, Screen
from textual.widgets import Input, Label, RichLog, Static

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
        s = f"exit:{rc}"
        return f"{out}\n{err}\n{s}" if out or err else s
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
# WIDGETS
# ═══════════════════════════════════════════════════════════════

class StatusLine(Static):
    """Bottom status line — like OpenCode's status bar."""
    DEFAULT_CSS = """
    StatusLine {
        dock: bottom;
        height: 1;
        background: #1f2335;
        color: #565f89;
        padding: 0 1;
    }
    """

    def __init__(self, provider: str, model: str, session_id: str) -> None:
        text = (
            f" [#7aa2f7]patchbay[/] "
            f"[#565f89]|[/] [#9ece6a]{provider}[/] "
            f"[#565f89]|[/] [#c0caf5]{model}[/] "
            f"[#565f89]|[/] [#565f89]{session_id}[/] "
            f"[#565f89]  Ctrl+K commands  Ctrl+S session  Ctrl+O model  Ctrl+? help  Ctrl+C quit[/]"
        )
        super().__init__(text)


class ChatMessage(Static):
    """Single chat message — clean like OpenCode."""
    DEFAULT_CSS = """
    ChatMessage {
        height: auto;
        margin: 0 0;
        padding: 0 0 0 0;
    }
    """

    def __init__(self, role: str, content: str) -> None:
        if role == "user":
            text = f"[bold #7aa2f7]  You[/]\n[#c0caf5]{content}[/]"
        elif role == "assistant":
            text = f"[bold #9ece6a]  AI[/]\n[#c0caf5]{content}[/]"
        elif role == "error":
            text = f"[bold #f7768e]  Error[/]\n[#f7768e]{content}[/]"
        else:
            text = f"[#565f89]  {content}[/]"
        super().__init__(text)


class ToolWidget(Static):
    """Tool call + result display."""
    DEFAULT_CSS = """
    ToolWidget {
        height: auto;
        margin: 0 0 0 0;
        padding: 0 0 0 4;
    }
    """

    def __init__(self, name: str, args: dict, result: dict | None = None) -> None:
        args_s = ", ".join(f"{k}={repr(v)[:40]}" for k, v in args.items())
        text = f"[#e0af68]  > {name}[/][#565f89]({args_s})[/]"
        if result:
            if result.get("error"):
                text += f"\n  [#f7768e]x {result['error'][:150]}[/]"
            else:
                r = _fmt_result(name, result)
                for line in r.split("\n")[:8]:
                    text += f"\n  [#565f89]{line}[/]"
        super().__init__(text)


# ═══════════════════════════════════════════════════════════════
# DIALOGS
# ═══════════════════════════════════════════════════════════════

class QuitScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    QuitScreen {
        align: center middle;
    }
    #quit-box {
        width: 44;
        height: 7;
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
            yield Static("[#9ece6a]  y[/] Quit   [#565f89]n[/] Cancel")

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
        width: 64;
        height: auto;
        max-height: 32;
        background: #1f2335;
        border: thick #7aa2f7;
        padding: 1 2;
    }
    """
    BINDINGS = [("escape", "close", "Close"), ("ctrl+?", "close", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-box", auto_scroll=True):
            yield Static("[bold #7aa2f7]  Patchbay AI[/]\n")
            yield Static("[bold #c0caf5]Keyboard[/]")
            yield Static("  [#7dcfff]Ctrl+C[/]       Quit")
            yield Static("  [#7dcfff]Ctrl+K[/]       Command palette")
            yield Static("  [#7dcfff]Ctrl+S[/]       Switch session")
            yield Static("  [#7dcfff]Ctrl+O[/]       Switch model")
            yield Static("  [#7dcfff]Ctrl+L[/]       Logs")
            yield Static("  [#7dcfff]Ctrl+?[/]       Help")
            yield Static("  [#7dcfff]Ctrl+X[/]       Cancel generation")
            yield Static("  [#7dcfff]Enter[/]        Send message\n")
            yield Static("[bold #c0caf5]Commands[/]")
            yield Static("  [#c0caf5]/help[/]         This help")
            yield Static("  [#c0caf5]/clear[/]        Clear chat")
            yield Static("  [#c0caf5]/model[/]        Switch model")
            yield Static("  [#c0caf5]/provider[/]     Switch provider")
            yield Static("  [#c0caf5]/status[/]       Gateway status")
            yield Static("  [#c0caf5]/models[/]       List models")
            yield Static("  [#c0caf5]/sessions[/]     List sessions")
            yield Static("  [#c0caf5]/save[/]         Save session")
            yield Static("  [#c0caf5]/config[/]       Show config")
            yield Static("  [#c0caf5]/quit[/]         Exit\n")
            yield Static("[#565f89]Esc to close[/]")

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
    }
    """
    BINDINGS = [("escape", "cancel", "Cancel"), ("n", "new", "New")]

    def __init__(self, sessions: list[dict], **kw: Any) -> None:
        super().__init__(**kw)
        self.sessions = sessions
        self.sel = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="sess-box", auto_scroll=True):
            yield Static(f"[bold #7aa2f7]  Sessions ({len(self.sessions)})[/]\n")
            if not self.sessions:
                yield Static("[#565f89]  No sessions. Press n for new.[/]")
            for i, s in enumerate(self.sessions):
                marker = " [#9ece6a]*[/]" if i == 0 else ""
                yield Static(
                    f"  [#7aa2f7]{s['id']}[/]  "
                    f"[#565f89]{s.get('updated_at','')[:16]}[/]  "
                    f"[#565f89]{s.get('count',0)} msgs[/]{marker}",
                    id=f"sess-{i}",
                )
            yield Static("\n[#565f89]Enter select  n new  Esc cancel[/]")

    def on_key(self, event: Any) -> None:
        if event.key == "enter" and self.sessions:
            self.dismiss(self.sessions[self.sel]["id"])
            event.stop()
        elif event.key == "n":
            self.dismiss("__new__")
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
        with Vertical(id="model-box", auto_scroll=True):
            yield Input(placeholder="Search...", id="msearch")
            yield Static(f"[bold #7aa2f7]  Models[/] [#565f89]({len(self.all_models)})[/]\n")
            for i, m in enumerate(self.filtered):
                cur = " [#9ece6a]*[/]" if m["id"] == self.current else ""
                yield Static(
                    f"  [#c0caf5]{m['id']}[/]  [#565f89]{m.get('name','')}[/]{cur}",
                    id=f"m-{i}",
                )
            yield Static("\n[#565f89]Enter select  Esc cancel[/]")

    @on(Input.Changed, "#msearch")
    def search_changed(self, ev: Input.Changed) -> None:
        q = ev.value.lower()
        self.filtered = [m for m in self.all_models if q in m["id"].lower() or q in m.get("name", "").lower()][:60]
        self.sel = 0
        self._refresh()

    def _refresh(self) -> None:
        box = self.query_one("#model-box")
        for w in box.query(".mitem"):
            w.remove()
        for i, m in enumerate(self.filtered):
            cur = " [#9ece6a]*[/]" if m["id"] == self.current else ""
            box.mount(
                Static(f"  [#c0caf5]{m['id']}[/]  [#565f89]{m.get('name','')}[/]{cur}", id=f"m-{i}", classes="mitem"),
                after=box.query("Static").last(),
            )

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
        with Vertical(id="cmd-box", auto_scroll=True):
            yield Input(placeholder="Search...", id="csearch")
            yield Static("[bold #7aa2f7]  Commands[/]\n")
            for i, (cid, label, shortcut) in enumerate(self.filtered):
                sc = f"  [#565f89]{shortcut}[/]" if shortcut else ""
                yield Static(f"  [#c0caf5]{label}[/]{sc}", id=f"c-{i}")
            yield Static("\n[#565f89]Enter run  Esc cancel[/]")

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


class PermScreen(ModalScreen[str]):
    DEFAULT_CSS = """
    PermScreen {
        align: center middle;
    }
    #perm-box {
        width: 52;
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
        with Vertical(id="perm-box"):
            yield Static(f"[bold #e0af68]  Tool Permission[/]\n")
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
    """Patchbay AI — full-screen TUI for the Universal LLM Gateway."""

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
        padding: 0 1;
    }
    #input-box {
        dock: bottom;
        height: auto;
        min-height: 3;
        max-height: 12;
        padding: 0 0;
        background: #1a1b26;
    }
    #input-box Input {
        background: #1f2335;
        color: #c0caf5;
        border: none;
        padding: 0 1;
    }
    #input-box Input:focus {
        background: #24283b;
    }
    #stream-bar {
        dock: bottom;
        height: 1;
        background: #1f2335;
        color: #7dcfff;
        padding: 0 1;
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
            Static("", id="stream-bar"),
            Input(placeholder="Message Patchbay...  / for commands", id="input-box"),
            StatusLine(self.provider, self.model, self.session_id),
            id="main",
        )

    def on_mount(self) -> None:
        self._msg("system", "Welcome to Patchbay AI  [#565f89]|[/] Universal LLM Gateway")
        self._msg("system", f"[#565f89]{self.provider} | {self.model} | {self.session_id}[/]")
        self.query_one("#input-box", Input).focus()

    # ── Helpers ──

    def _msg(self, role: str, text: str) -> None:
        chat = self.query_one("#chat")
        chat.mount(ChatMessage(role, text))
        chat.scroll_end(animate=False)

    def _tool_widget(self, name: str, args: dict, result: dict | None = None) -> None:
        chat = self.query_one("#chat")
        chat.mount(ToolWidget(name, args, result))
        chat.scroll_end(animate=False)

    def _stream_text(self, text: str) -> None:
        bar = self.query_one("#stream-bar", Static)
        if text:
            preview = text[-80:].replace("\n", " ")
            bar.update(f"  [#7dcfff]>[/] {preview}[_]")
            bar.visible = True
        else:
            bar.visible = False

    def _refresh_status(self) -> None:
        old = self.query_one(StatusLine)
        old.remove()
        self.mount(StatusLine(self.provider, self.model, self.session_id), after=self.query_one("#input-box"))

    # ── Input ──

    @on(Input.Submitted, "#input-box")
    def on_submit(self, ev: Input.Submitted) -> None:
        text = ev.value.strip()
        ev.input.value = ""
        if not text:
            return
        if text.startswith("/"):
            self._cmd(text)
            return
        self.messages.append({"role": "user", "content": text})
        self._msg("user", text)
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
            self._msg("system", "[#9ece6a]Cleared.[/]")
        elif cmd == "/status":
            items = get_full_status()
            lines = ["[bold #7aa2f7]Status[/]\n"]
            for name, color, detail in items:
                c = "#9ece6a" if color == "green" else "#f7768e"
                lines.append(f"  [{c}]+[/] [#c0caf5]{name}[/] [#565f89]{detail}[/]")
            self._msg("system", "\n".join(lines))
        elif cmd == "/models":
            models = list_models()
            if models:
                lines = [f"[bold #7aa2f7]Models ({len(models)})[/]\n"]
                for m in models[:30]:
                    lines.append(f"  [#c0caf5]{m.get('id','?')}[/]")
                self._msg("system", "\n".join(lines))
            else:
                self._msg("system", "[#565f89]No models. Is gateway running?[/]")
        elif cmd == "/sessions":
            sessions = list_sessions()
            if not sessions:
                self._msg("system", "[#565f89]No sessions.[/]")
                return
            lines = [f"[bold #7aa2f7]Sessions ({len(sessions)})[/]\n"]
            for s in sessions[:10]:
                lines.append(f"  [#7aa2f7]{s['id']}[/]  [#565f89]{s.get('updated_at','')[:16]}  {s.get('count',0)} msgs[/]")
            self._msg("system", "\n".join(lines))
        elif cmd == "/save":
            save_session(self.session_id, self.messages, {"provider": self.provider, "model": self.model})
            self._msg("system", f"[#9ece6a]Saved: {self.session_id}[/]")
        elif cmd == "/config":
            cfg = get_config()
            lines = ["[bold #7aa2f7]Config[/]\n"]
            for k, v in cfg.items():
                if "key" in k.lower():
                    v = f"***{str(v)[-4:]}" if len(str(v)) > 4 else "***"
                lines.append(f"  [#c0caf5]{k}[/] = [#565f89]{v}[/]")
            self._msg("system", "\n".join(lines))
        elif cmd == "/model":
            if arg:
                self.model = arg.strip()
                set_config_value("model", self.model)
                self._msg("system", f"[#9ece6a]Model: {self.model}[/]")
                self._refresh_status()
            else:
                self.action_model()
        elif cmd == "/provider":
            if arg:
                self.provider = arg.strip().lower()
                set_config_value("provider", self.provider)
                self._msg("system", f"[#9ece6a]Provider: {self.provider}[/]")
                self._refresh_status()
            else:
                self._msg("system", f"[#565f89]Current: {self.provider}. Use /provider <name>[/]")
        elif cmd == "/blender":
            scene = blender_get_scene()
            if "error" in scene:
                self._msg("system", f"[#f7768e]Blender: {scene['error']}[/]")
            else:
                self._msg("system", f"[#7aa2f7]Blender[/] {scene.get('name','?')}  {scene.get('object_count',0)} objects")
        else:
            self._msg("system", f"[#f7768e]Unknown: {cmd}[/]  [#565f89]/help[/]")

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
                    self._stream_text(full)
                if acc.error:
                    self._msg("error", acc.error)
                    break
        except Exception as e:
            self._msg("error", str(e))
        finally:
            self._stream_text("")
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
                self._msg("assistant", full)

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
                perm = self.push_screen_wait_sync(PermScreen(name, args))
                if perm == "deny":
                    self.messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                    self.messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": "Denied by user"})
                    self._tool_widget(name, args, {"error": "Denied"})
                    continue
                elif perm == "allow_all":
                    self.auto_approve = True

            result = execute_tool(name, args)
            self._tool_widget(name, args, result)

            result_text = _fmt_result(name, result)
            clean = re.sub(r'\[/?[a-zA-Z_][^\]]*\]', '', result_text)
            if len(clean) > 8000:
                clean = clean[:8000] + "\n... truncated"

            self.messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
            self.messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": clean})

        self._llm()

    def push_screen_wait_sync(self, screen: Any) -> Any:
        """Synchronous wrapper for push_screen_wait from a thread."""
        import concurrent.futures
        future: concurrent.futures.Future[Any] = concurrent.futures.Future()

        def _do() -> None:
            self.push_screen(screen, callback=lambda r: future.set_result(r))

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
                self._run_cmd_id(cid)
        self.push_screen(CmdPalette(), callback=_on_result)

    def _run_cmd_id(self, cid: str) -> None:
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
                self._msg("system", f"[#9ece6a]New: {self.session_id}[/]")
                self._refresh_status()
            elif sid:
                data = load_session(sid)
                if data:
                    self.session_id = sid
                    self.messages = data.get("messages", [])
                    self.query_one("#chat").remove_children()
                    for m in self.messages:
                        if m.get("role") in ("user", "assistant") and m.get("content"):
                            self._msg(m["role"], m["content"])
                    self._msg("system", f"[#9ece6a]Loaded: {sid}[/]")
                    self._refresh_status()

        self.push_screen(SessionScreen(sessions), callback=_on_result)

    def action_model(self) -> None:
        @work(thread=True)
        def _fetch() -> None:
            models = fetch_models_cached(self.provider)
            if not models:
                self._msg("system", "[#565f89]No models fetched.[/]")
                return

            def _on_result(mid: str | None) -> None:
                if mid:
                    self.model = mid
                    set_config_value("model", self.model)
                    self._msg("system", f"[#9ece6a]Model: {self.model}[/]")
                    self._refresh_status()

            self.call_from_thread(lambda: self.push_screen(ModelScreen(models, self.model), callback=_on_result))

        _fetch()

    def action_logs(self) -> None:
        self.push_screen(LogScreen(self.logs))

    def action_cancel_gen(self) -> None:
        if self.is_generating:
            self._msg("system", "[#e0af68]Cancelled.[/]")
            self._stream_text("")
            self.is_generating = False


if __name__ == "__main__":
    PatchbayApp().run()
