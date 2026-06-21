"""App - Main REPL engine and CLI entry point.

The heart of Patchbay CLI:
  - Interactive AI assistant REPL with streaming
  - Tool execution loop (max rounds with visual feedback)
  - Slash command handler
  - Project context auto-detection
  - Click CLI group for gateway management commands
"""

from __future__ import annotations

import io
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import click
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner

from patchbay.ui import (
    console, err_console, Theme,
    render_banner, HELP_TEXT,
    table_models, table_status, table_sessions, table_config,
    tree_objects,
    panel_status, panel_error, panel_success, panel_info, panel_tool_call, panel_tool_result,
    format_result_content, render_markdown,
)
from patchbay.config import (
    get_config, save_config, set_config_value,
    get_api_key, validate_provider, PROVIDER_KEY_MAP,
)
from patchbay.providers import stream_completion, StreamAccumulator
from patchbay.tools import TOOLS_SPEC, execute_tool
from patchbay.session import save_session, load_session, list_sessions, delete_session, update_session
from patchbay.gateway import (
    get_full_status, list_models, list_mcp_servers,
    blender_get_scene, blender_exec, blender_call,
    check_gateway, ROUTING_STRATEGIES,
)

# Force UTF-8 on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are Patchbay AI, an expert software engineering assistant embedded in a CLI tool.

You help users with:
- Writing, reading, editing, and debugging code
- Understanding and navigating codebases
- Running shell commands and interpreting output
- Creating files and project structures
- Fixing bugs and implementing features

You have access to these tools:
- read_file: Read file contents with line numbers
- write_file: Write/create files
- edit_file: Make precise edits (preferred over full rewrites)
- run_bash: Execute shell commands
- search_files: Find files by glob pattern
- search_content: Search code with regex
- list_directory: List directory contents

Rules:
1. Always prefer edit_file over write_file for partial changes
2. Verify changes by running tests or linting after edits
3. Be concise - no unnecessary explanations unless asked
4. Use search tools before reading large files
5. When fixing errors, find root cause first
6. Never commit secrets or API keys"""


def get_project_context() -> str:
    """Auto-detect project context from the current directory."""
    parts = [f"Working directory: {os.getcwd()}"]

    # Check for key project files
    key_files = [
        "README.md", "CLAUDE.md", "AGENTS.md", "CONTRIBUTING.md",
        "pyproject.toml", "package.json", "Cargo.toml", "go.mod",
        "Makefile", "Dockerfile", "docker-compose.yml",
        ".gitignore", ".env.example",
    ]
    for fname in key_files:
        p = Path(fname)
        if p.exists():
            try:
                content = p.read_text(encoding="utf-8", errors="replace")[:2000]
                parts.append(f"\n--- {fname} ---\n{content}")
            except Exception:
                pass

    # List top-level structure
    try:
        entries = []
        for item in sorted(Path(".").iterdir()):
            if item.name.startswith(".") or item.name in ("node_modules", "__pycache__", ".venv", "venv"):
                continue
            kind = "d" if item.is_dir() else "f"
            size = ""
            if item.is_file():
                try:
                    s = item.stat().st_size
                    if s > 1_000_000:
                        size = f" ({s / 1_000_000:.1f}MB)"
                    elif s > 1_000:
                        size = f" ({s / 1_000:.1f}KB)"
                except Exception:
                    pass
            entries.append(f"  {'[' + kind + ']' if kind == 'd' else '   '} {item.name}{size}")
        if entries:
            parts.append("\n--- Project Structure ---\n" + "\n".join(entries[:40]))
    except Exception:
        pass

    # Git info
    try:
        import subprocess
        r = subprocess.run("git branch --show-current", shell=True, capture_output=True, text=True, timeout=3)
        if r.returncode == 0 and r.stdout.strip():
            parts.append(f"\nGit branch: {r.stdout.strip()}")
    except Exception:
        pass

    return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════
# SLASH COMMANDS
# ═══════════════════════════════════════════════════════════════

def handle_slash_command(
    line: str,
    messages: list[dict],
    provider: str,
    model: str,
    session_id: str,
) -> tuple[str, str, str]:
    """Handle slash commands. Returns (provider, model, session_id)."""
    parts = line.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd in ("/quit", "/exit", "/q"):
        console.print("[dim]Goodbye![/dim]")
        raise SystemExit(0)

    elif cmd in ("/help", "/h", "/?"):
        console.print(HELP_TEXT)

    elif cmd == "/clear":
        messages.clear()
        messages.append({"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()})
        console.print("[green]Conversation cleared.[/green]")

    elif cmd == "/model":
        if arg:
            # Check if it's a number (from the list)
            provider_info = next((p for p in PROVIDERS_INFO if p["id"] == provider), None)
            if provider_info and arg.isdigit() and 1 <= int(arg) <= len(provider_info["models"]):
                model = provider_info["models"][int(arg) - 1]
            else:
                model = arg.strip()
            set_config_value("model", model)
            console.print(f"[green]Model: {model}[/green]")
        else:
            console.print(f"[yellow]Current model: {model}[/yellow]\n")
            provider_info = next((p for p in PROVIDERS_INFO if p["id"] == provider), None)
            if provider_info:
                console.print(f"[bold]Available models for {provider_info['name']}:[/bold]\n")
                for i, m in enumerate(provider_info["models"], 1):
                    marker = " [green](current)[/green]" if m == model else ""
                    console.print(f"  [cyan]{i:>2}[/cyan]  {m}{marker}")
                console.print(f"\n  [dim]Usage: /model <name> or /model <number>[/dim]")
            else:
                console.print("[dim]Usage: /model gpt-4o[/dim]")

    elif cmd == "/provider":
        if arg:
            provider = arg.strip().lower()
            set_config_value("provider", provider)
            console.print(f"[green]Provider: {provider}[/green]")
            # Show available models for the new provider
            provider_info = next((p for p in PROVIDERS_INFO if p["id"] == provider), None)
            if provider_info:
                console.print(f"\n[bold]Models for {provider_info['name']}:[/bold]")
                for i, m in enumerate(provider_info["models"], 1):
                    console.print(f"  [cyan]{i:>2}[/cyan]  {m}")
                console.print(f"\n  [dim]Type /model <name> or /model <number> to switch[/dim]")
        else:
            console.print(f"[yellow]Current provider: {provider}[/yellow]\n")
            for p in PROVIDERS_INFO:
                marker = " [green]*(current)[/green]" if p["id"] == provider else ""
                console.print(f"  {p['id']:12s}  {p['desc']}{marker}")
            console.print("\n  [dim]Usage: /provider openrouter[/dim]")

    elif cmd == "/history":
        if not messages or all(m["role"] == "system" for m in messages):
            console.print("[dim]No messages yet.[/dim]")
        else:
            console.print(Rule("History", style=Theme.ACCENT_BLUE))
            for m in messages:
                if m["role"] == "system":
                    continue
                if m["role"] == "tool":
                    continue
                color = "green" if m["role"] == "assistant" else "cyan"
                prefix = "You" if m["role"] == "user" else "AI"
                content = m.get("content", "")
                if content:
                    console.print(f"\n[bold {color}]{prefix}:[/bold {color}]")
                    console.print(content[:500])
                    if len(content) > 500:
                        console.print(f"[dim]... ({len(content) - 500} more chars)[/dim]")

    elif cmd == "/save":
        sid = arg.strip() if arg else str(uuid.uuid4())[:8]
        cfg = get_config()
        save_session(sid, messages, {"provider": provider, "model": model})
        console.print(f"[green]Session saved: {sid}[/green]")

    elif cmd == "/load":
        if not arg:
            console.print("[dim]Usage: /load <session-id>[/dim]")
            return provider, model, session_id
        data = load_session(arg.strip())
        if data:
            messages.clear()
            messages.extend(data.get("messages", []))
            new_id = data.get("id", arg.strip())
            console.print(f"[green]Loaded session {new_id} ({len(messages)} messages)[/green]")
            session_id = new_id
        else:
            console.print(f"[red]Session not found: {arg}[/red]")

    elif cmd == "/sessions":
        sessions = list_sessions()
        if not sessions:
            console.print("[dim]No saved sessions.[/dim]")
        else:
            console.print(table_sessions(sessions))

    elif cmd == "/delete":
        if arg and delete_session(arg.strip()):
            console.print(f"[green]Deleted session: {arg}[/green]")
        else:
            console.print(f"[red]Session not found: {arg}[/red]")

    elif cmd == "/config":
        cfg = get_config()
        if arg:
            kv = arg.split(maxsplit=1)
            if len(kv) == 2:
                set_config_value(kv[0], kv[1])
                console.print(f"[green]Set {kv[0]} = {kv[1]}[/green]")
            else:
                val = cfg.get(kv[0], "[dim]not set[/dim]")
                console.print(f"  {kv[0]} = {val}")
        else:
            console.print(table_config(cfg))

    elif cmd == "/status":
        _show_status()

    elif cmd == "/models":
        _show_models()

    elif cmd == "/blender":
        _show_blender()

    else:
        console.print(f"[red]Unknown command: {cmd}[/red]  (type /help)")

    return provider, model, session_id


def _show_status():
    """Display system status."""
    items = get_full_status()
    console.print(table_status(items))


def _show_models():
    """Display models table."""
    models = list_models()
    if models:
        console.print(table_models(models))
    else:
        console.print("[red]Could not fetch models. Is the gateway running?[/red]")


def _show_blender():
    """Display Blender scene info."""
    scene = blender_get_scene()
    if "error" in scene:
        console.print(f"[red]Blender error: {scene['error']}[/red]")
        return

    console.print(panel_info(
        "Blender Scene",
        f"[bold]Scene:[/bold] {scene.get('name', '?')}\n"
        f"[bold]Objects:[/bold] {scene.get('object_count', 0)}\n"
        f"[bold]Materials:[/bold] {scene.get('materials_count', 0)}",
    ))

    objects = scene.get("objects", [])
    if objects:
        console.print(tree_objects(objects))


# ═══════════════════════════════════════════════════════════════
# TOOL EXECUTION
# ═══════════════════════════════════════════════════════════════

def execute_and_display_tools(tool_calls: list[dict], messages: list[dict]) -> None:
    """Execute tool calls, display results, and append to messages."""
    for tc in tool_calls:
        func = tc.get("function", {})
        name = func.get("name", "")
        try:
            args = json.loads(func.get("arguments", "{}"))
        except json.JSONDecodeError:
            args = {}

        # Show tool call
        console.print()
        console.print(panel_tool_call(name, args))

        # Execute
        result = execute_tool(name, args)

        # Show result
        console.print(panel_tool_result(name, result))

        # Format for LLM
        result_text = format_result_content(name, result)

        # Strip Rich markup for LLM
        import re
        clean_text = re.sub(r'\[/?[a-zA-Z_][^\]]*\]', '', result_text)

        if len(clean_text) > 8000:
            clean_text = clean_text[:8000] + f"\n... ({len(clean_text) - 8000} chars truncated)"

        # Append to messages
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [tc],
        })
        messages.append({
            "role": "tool",
            "tool_call_id": tc.get("id", ""),
            "content": clean_text,
        })


# ═══════════════════════════════════════════════════════════════
# STREAMING RESPONSE HANDLER
# ═══════════════════════════════════════════════════════════════

def process_streaming_response(
    provider: str,
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
) -> dict:
    """Process a streaming LLM response.

    Displays content as it arrives, accumulates tool calls.
    Returns the complete assistant message.
    """
    accumulator = StreamAccumulator()

    try:
        for chunk in stream_completion(provider, model, messages, tools=tools):
            text = accumulator.process_chunk(chunk)
            if text:
                console.print(text, end="", highlight=False)

            if accumulator.error:
                console.print(f"\n[red][Error: {accumulator.error}][/red]")
                break

    except KeyboardInterrupt:
        console.print("\n[yellow][Interrupted][/yellow]")
    except Exception as e:
        console.print(f"\n[red][Stream error: {e}][/red]")

    console.print()  # Final newline

    return accumulator.finalize()


# ═══════════════════════════════════════════════════════════════
# MAIN REPL
# ═══════════════════════════════════════════════════════════════

def run_repl(provider: str, model: str):
    """Run the interactive AI coding assistant REPL."""
    render_banner()

    # Init messages
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()},
    ]

    session_id = str(uuid.uuid4())[:8]
    cfg = get_config()
    max_tool_rounds = cfg.get("max_tool_rounds", 15)
    auto_save_interval = cfg.get("auto_save_interval", 20)

    while True:
        try:
            # Prompt
            try:
                line = console.input("[bold cyan]>[/bold cyan] ")
            except EOFError:
                console.print("\n[dim]Goodbye![/dim]")
                break

            if not line.strip():
                continue

            # Slash commands
            if line.strip().startswith("/"):
                provider, model, session_id = handle_slash_command(
                    line, messages, provider, model, session_id
                )
                continue

            # User message
            messages.append({"role": "user", "content": line})

            # Tool execution loop
            for round_num in range(max_tool_rounds):
                resp = process_streaming_response(provider, model, messages, tools=TOOLS_SPEC)

                # Add to messages
                messages.append(resp)

                # Check for tool calls
                tool_calls = resp.get("tool_calls", [])
                if tool_calls:
                    execute_and_display_tools(tool_calls, messages)
                    # Continue loop for next LLM turn
                else:
                    break  # No tools, done

            # Auto-save
            cfg = get_config()
            if cfg.get("auto_save", True) and len(messages) % auto_save_interval == 0:
                update_session(session_id, messages)

        except SystemExit:
            break
        except KeyboardInterrupt:
            console.print(f"\n[yellow][Interrupted - type /quit to exit][/yellow]")
        except Exception as e:
            console.print(f"\n[red][Error: {e}][/red]")

    # Save on exit
    save_session(session_id, messages, {"provider": provider, "model": model})


# ═══════════════════════════════════════════════════════════════
# CLICK CLI GROUPS
# ═══════════════════════════════════════════════════════════════

@click.group(invoke_without_command=True)
@click.option("--provider", "-p", default=None, help="LLM provider (openai, anthropic, deepseek, openrouter, google)")
@click.option("--model", "-m", default=None, help="Model name (e.g. gpt-4o, claude-sonnet-4)")
@click.version_option("0.2.0", prog_name="patchbay")
@click.pass_context
def cli(ctx, provider, model):
    """Patchbay - Universal LLM Gateway & AI Coding Assistant

    Run without arguments to start the interactive AI assistant.
    Use subcommands to manage the gateway, models, Blender, and more.
    """
    ctx.ensure_object(dict)
    if provider:
        ctx.obj["provider"] = provider
    if model:
        ctx.obj["model"] = model

    if ctx.invoked_subcommand is None:
        cfg = get_config()
        p = provider or cfg.get("provider", "openai")
        m = model or cfg.get("model", "gpt-4o")

        # Auto-detect: if no API key for provider, show setup
        if not validate_provider(p):
            console.print(f"[yellow]No API key configured for {p}.[/yellow]\n")
            _run_setup()
            console.print()
            cfg = get_config()
            p = cfg.get("provider", p)
            m = cfg.get("model", m)

        run_repl(p, m)


# ─── Setup Wizard ───

PROVIDERS_INFO = [
    {"id": "openrouter", "name": "OpenRouter", "desc": "100+ models (GPT, Claude, Gemini, Llama, Mistral...)", "key_url": "https://openrouter.ai/keys", "key_name": "OPENROUTER_API_KEY", "models": [
        "openai/gpt-4o", "openai/gpt-4o-mini", "openai/gpt-4-turbo", "openai/o3-mini", "openai/o4-mini",
        "anthropic/claude-sonnet-4", "anthropic/claude-3.5-sonnet", "anthropic/claude-3.5-haiku", "anthropic/claude-3-opus",
        "google/gemini-2.5-flash", "google/gemini-2.5-pro", "google/gemini-2.0-flash",
        "meta-llama/llama-4-maverick", "meta-llama/llama-4-scout", "meta-llama/llama-3.3-70b",
        "deepseek/deepseek-chat", "deepseek/deepseek-r1",
        "mistralai/mistral-large", "mistralai/mistral-small",
        "qwen/qwen-2.5-72b", "qwen/qwen3-235b-a22b",
    ]},
    {"id": "openai", "name": "OpenAI", "desc": "GPT-4o, GPT-4o-mini, o3, o4-mini", "key_url": "https://platform.openai.com/api-keys", "key_name": "OPENAI_API_KEY", "models": [
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo",
        "o3-mini", "o4-mini", "o3", "o4-pro",
    ]},
    {"id": "anthropic", "name": "Anthropic", "desc": "Claude 4 Opus, Sonnet, Haiku", "key_url": "https://console.anthropic.com/keys", "key_name": "ANTHROPIC_API_KEY", "models": [
        "claude-opus-4-20250514", "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022",
    ]},
    {"id": "deepseek", "name": "DeepSeek", "desc": "DeepSeek Chat & R1 (very cheap)", "key_url": "https://platform.deepseek.com/api_keys", "key_name": "DEEPSEEK_API_KEY", "models": [
        "deepseek-chat", "deepseek-reasoner",
    ]},
    {"id": "google", "name": "Google Gemini", "desc": "Gemini 2.5 Pro & Flash", "key_url": "https://aistudio.google.com/apikey", "key_name": "GOOGLE_API_KEY", "models": [
        "gemini-2.5-flash", "gemini-2.5-pro",
        "gemini-2.0-flash", "gemini-1.5-pro",
    ]},
]


def _run_setup():
    """Interactive setup wizard for API key and provider selection."""
    from patchbay.config import set_config_value, get_config

    console.print(Panel(
        "[bold cyan]Patchbay Setup Wizard[/bold cyan]\n\n"
        "Choose a provider and enter your API key.\n"
        "You can change these later with [white]/config[/white] or [white]/model[/white].",
        title="[bold]Setup[/bold]",
        border_style="cyan",
    ))

    # Show providers
    console.print("\n[bold]Available providers:[/bold]\n")
    for i, p in enumerate(PROVIDERS_INFO, 1):
        key_status = "[green]+[/green]" if _has_key(p["key_name"]) else "[dim]-[/dim]"
        console.print(f"  [cyan]{i}[/cyan]  {key_status} {p['name']}  [dim]— {p['desc']}[/dim]")

    console.print()

    # Select provider
    while True:
        try:
            choice = console.input("  [cyan]Pick a provider (1-5) [/cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if choice.isdigit() and 1 <= int(choice) <= len(PROVIDERS_INFO):
            selected = PROVIDERS_INFO[int(choice) - 1]
            break
        else:
            console.print("  [red]Invalid choice. Enter 1-5.[/red]")

    console.print(f"\n  [green]Selected: {selected['name']}[/green]")

    # Get API key
    if _has_key(selected["key_name"]):
        console.print(f"  [dim]API key already configured.[/dim]")
    else:
        console.print(f"\n  [dim]Get your key at: {selected['key_url']}[/dim]\n")
        while True:
            try:
                api_key = console.input("  [cyan]Paste your API key [/cyan]").strip()
            except (EOFError, KeyboardInterrupt):
                return

            if not api_key:
                console.print("  [red]API key cannot be empty.[/red]")
                continue
            if len(api_key) < 10:
                console.print("  [red]API key looks too short. Try again.[/red]")
                continue
            break

        set_config_value(selected["key_name"], api_key)
        console.print(f"\n  [green]API key saved for {selected['name']}![/green]")

    # Set provider
    set_config_value("provider", selected["id"])

    # Select model
    console.print(f"\n[bold]Available models for {selected['name']}:[/bold]\n")
    for i, model in enumerate(selected["models"], 1):
        console.print(f"  [cyan]{i:>2}[/cyan]  {model}")
    console.print(f"       [dim]...or type any model name[/dim]")

    console.print()
    while True:
        try:
            choice = console.input(f"  [cyan]Pick a model (1-{len(selected['models'])} or type name) [/cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if not choice:
            continue

        if choice.isdigit() and 1 <= int(choice) <= len(selected["models"]):
            chosen_model = selected["models"][int(choice) - 1]
            break
        else:
            # Custom model name typed
            chosen_model = choice
            break

    set_config_value("model", chosen_model)
    console.print(f"\n  [green]Model set to: {chosen_model}[/green]")

    # Gateway URL
    cfg = get_config()
    gw_url = cfg.get("gateway_url", "http://localhost:8000")
    console.print(f"\n  [dim]Gateway URL: {gw_url}[/dim]")
    try:
        change_gw = console.input("  [cyan]Change gateway URL? (n): [/cyan]").strip().lower()
    except (EOFError, KeyboardInterrupt):
        change_gw = "n"

    if change_gw in ("y", "yes"):
        try:
            new_url = console.input("  [cyan]Gateway URL [/cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            new_url = ""
        if new_url:
            set_config_value("gateway_url", new_url)
            console.print(f"  [green]Gateway URL updated.[/green]")

    console.print(f"\n[bold green]Setup complete![/bold green] Starting Patchbay AI...\n")


def _has_key(env_key: str) -> bool:
    """Check if API key is available in config or env."""
    import os
    config = get_config()
    cfg_key = env_key.lower()
    return bool(config.get(cfg_key) or os.getenv(env_key))


# ─── Setup command ───

@cli.command()
def setup():
    """Interactive setup wizard - configure provider and API key."""
    _run_setup()
    # After setup, start REPL
    cfg = get_config()
    run_repl(cfg.get("provider", "openai"), cfg.get("model", "gpt-4o"))


# ─── Status ───

@cli.command()
def status():
    """Show system status - gateway, database, dashboard, Blender, models."""
    _show_status()


# ─── Health ───

@cli.command()
def health():
    """Quick health check of all services."""
    items = get_full_status()
    all_ok = all(color == "green" for _, color, _ in items)
    for name, color, detail in items:
        icon = "[green]+[/green]" if color == "green" else "[red]-[/red]"
        console.print(f"  {icon} {name}: {detail}")
    console.print()
    if all_ok:
        console.print("[green bold]All services healthy![/green bold]")
    else:
        console.print("[yellow]Some services need attention.[/yellow]")


# ─── Models ───

@cli.command("models")
def models_cmd():
    """List all registered LLM models in the catalog."""
    _show_models()


# ─── Keys ───

@cli.group()
def keys():
    """Manage provider API keys."""
    pass


@keys.command("list")
def keys_list():
    """List configured API keys (values are masked)."""
    cfg = get_config()
    console.print(table_config(cfg))


@keys.command("set")
@click.argument("provider_name")
@click.argument("api_key")
def keys_set(provider_name: str, api_key: str):
    """Set an API key for a provider.

    Example: patchbay keys set openai sk-xxxxxxxx
    """
    cfg_key, env_key = PROVIDER_KEY_MAP.get(
        provider_name, (f"{provider_name}_api_key", f"{provider_name.upper()}_API_KEY")
    )
    set_config_value(cfg_key, api_key)
    console.print(f"[green]API key set for {provider_name}[/green]")
    console.print(f"[dim]Config key: {cfg_key}  |  Env var: {env_key}[/dim]")


@keys.command("test")
@click.argument("provider_name")
def keys_test(provider_name: str):
    """Test if an API key is configured and valid."""
    if validate_provider(provider_name):
        console.print(f"[green]+ API key configured for {provider_name}[/green]")
    else:
        console.print(f"[red]- No API key for {provider_name}[/red]")
        cfg_key, env_key = PROVIDER_KEY_MAP.get(
            provider_name, (f"{provider_name}_api_key", f"{provider_name.upper()}_API_KEY")
        )
        console.print(f"[dim]Set via: patchbay keys set {provider_name} sk-xxx[/dim]")
        console.print(f"[dim]Or env:  {env_key}=sk-xxx[/dim]")


# ─── MCP ───

@cli.group()
def mcp():
    """Manage MCP (Model Context Protocol) servers."""
    pass


@mcp.command("list")
def mcp_list():
    """List connected MCP servers."""
    servers = list_mcp_servers()
    if not servers:
        console.print("[dim]No MCP servers connected.[/dim]")
        return
    for s in servers:
        status = "[green]active[/green]" if s.get("is_active") else "[red]inactive[/red]"
        console.print(f"  [cyan]{s['name']}[/cyan]  {s['transport']}  {s['connection_uri']}  {status}")


# ─── Blender ───

@cli.group()
def blender():
    """Control Blender via MCP integration."""
    pass


@blender.command("info")
def blender_info():
    """Show Blender scene information."""
    _show_blender()


@blender.command("objects")
def blender_objects():
    """List all objects in the Blender scene."""
    scene = blender_get_scene()
    if "error" in scene:
        console.print(f"[red]{scene['error']}[/red]")
        return
    objects = scene.get("objects", [])
    if not objects:
        console.print("[dim]No objects in scene.[/dim]")
        return
    console.print(tree_objects(objects))


@blender.command("exec")
@click.argument("code")
def blender_exec_cmd(code: str):
    """Execute Python code in Blender.

    Example: patchbay blender exec "bpy.ops.mesh.primitive_cube_add()"
    """
    result = blender_exec(code)
    if result.get("executed"):
        console.print("[green]Code executed successfully.[/green]")
    elif result.get("status") == "error":
        console.print(f"[red]Error: {result.get('message', 'Unknown')}[/red]")
    else:
        console.print(str(result))


@blender.command("create")
@click.argument("primitive", type=click.Choice([
    "cube", "sphere", "cylinder", "cone", "torus", "plane", "monkey",
]))
@click.option("--name", "-n", default="", help="Object name")
@click.option("--location", "-l", default="0,0,0", help="X,Y,Z location")
@click.option("--scale", "-s", default="1,1,1", help="X,Y,Z scale")
def blender_create(primitive: str, name: str, location: str, scale: str):
    """Create a primitive object in Blender."""
    loc = [float(x.strip()) for x in location.split(",")]
    scl = [float(x.strip()) for x in scale.split(",")]

    ops = {
        "cube": "primitive_cube_add", "sphere": "primitive_uv_sphere_add",
        "cylinder": "primitive_cylinder_add", "cone": "primitive_cone_add",
        "torus": "primitive_torus_add", "plane": "primitive_plane_add",
        "monkey": "primitive_monkey_add",
    }
    code = f"bpy.ops.mesh.{ops[primitive]}(location=({loc[0]},{loc[1]},{loc[2]}), scale=({scl[0]},{scl[1]},{scl[2]}))"
    if name:
        code += f'\nbpy.context.active_object.name = "{name}"'

    result = blender_exec(code)
    if result.get("executed"):
        obj_name = name or primitive.capitalize()
        console.print(f"[green]Created {primitive} '{obj_name}' at ({loc[0]},{loc[1]},{loc[2]})[/green]")
    else:
        console.print(f"[red]{result.get('message', 'Error')}[/red]")


@blender.command("delete")
@click.argument("object_name")
def blender_delete(object_name: str):
    """Delete an object from the Blender scene."""
    code = (
        f'obj = bpy.data.objects.get("{object_name}")\n'
        "if obj:\n"
        "    bpy.data.objects.remove(obj, do_unlink=True)\n"
        "    print(f'Deleted {obj.name}')\n"
        "else:\n"
        f"    print('Object not found: {object_name}')"
    )
    result = blender_exec(code)
    if result.get("executed"):
        console.print(f"[green]Deleted: {object_name}[/green]")
    else:
        console.print(f"[red]{result.get('message', 'Error')}[/red]")


@blender.command("material")
@click.argument("object_name")
@click.option("--color", "-c", required=True, help="Color (name or hex: red, #ff0000)")
def blender_material(object_name: str, color: str):
    """Apply a material with color to a Blender object."""
    color_map = {
        "red": (0.8, 0.1, 0.1, 1), "green": (0.1, 0.8, 0.1, 1),
        "blue": (0.1, 0.1, 0.8, 1), "yellow": (0.9, 0.9, 0.1, 1),
        "white": (0.9, 0.9, 0.9, 1), "black": (0.05, 0.05, 0.05, 1),
        "cyan": (0.1, 0.9, 0.9, 1), "magenta": (0.8, 0.1, 0.8, 1),
        "orange": (0.9, 0.5, 0.1, 1), "purple": (0.5, 0.1, 0.8, 1),
    }
    if color.startswith("#"):
        r_val = int(color[1:3], 16) / 255
        g_val = int(color[3:5], 16) / 255
        b_val = int(color[5:7], 16) / 255
        rgba = (r_val, g_val, b_val, 1)
    elif color in color_map:
        rgba = color_map[color]
    else:
        console.print(f"[red]Unknown color: {color}[/red]")
        return

    code = (
        f'obj = bpy.data.objects.get("{object_name}")\n'
        "if obj:\n"
        "    mat = bpy.data.materials.new(name='PatchbayMaterial')\n"
        "    mat.use_nodes = True\n"
        "    bsdf = mat.node_tree.nodes.get('Principled BSDF')\n"
        "    if bsdf:\n"
        f"        bsdf.inputs['Base Color'].default_value = {rgba}\n"
        "    obj.data.materials.clear()\n"
        "    obj.data.materials.append(mat)\n"
        f"    print(f'Material applied to {object_name}')\n"
        "else:\n"
        "    print('Object not found')"
    )
    result = blender_exec(code)
    if result.get("executed"):
        console.print(f"[green]Applied {color} material to {object_name}[/green]")
    else:
        console.print(f"[red]{result.get('message', 'Error')}[/red]")


# ─── Routing ───

@cli.group()
def routing():
    """Manage routing strategies."""
    pass


@routing.command("list")
def routing_list():
    """List available routing strategies."""
    from rich.table import Table
    from rich import box
    t = Table(box=box.ROUNDED, border_style=Theme.ACCENT_CYAN,
              title="[bold cyan]Routing Strategies[/bold cyan]")
    t.add_column("Strategy", style="bold", min_width=20)
    t.add_column("Description", min_width=50)
    t.add_column("Default", justify="center", min_width=8)
    for s in ROUTING_STRATEGIES:
        t.add_row(s["name"], s["description"], "[green]+[/green]" if s["default"] else "")
    console.print(t)


# ─── Config ───

@cli.group()
def config():
    """Configuration management."""
    pass


@config.command("show")
def config_show():
    """Show all configuration values."""
    cfg = get_config()
    console.print(table_config(cfg))
    console.print(f"\n[dim]Config file: {Path.home() / '.patchbay' / 'config.yaml'}[/dim]")


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a configuration value.

    Examples:
      patchbay config set provider openai
      patchbay config set model gpt-4o
      patchbay config set gateway_url http://localhost:8000
    """
    set_config_value(key, value)
    console.print(f"[green]Set {key} = {value}[/green]")


@config.command("reset")
def config_reset():
    """Reset configuration to defaults."""
    from patchbay.config import reset_config, DEFAULTS
    reset_config()
    console.print("[green]Configuration reset to defaults.[/green]")


# ─── Dashboard ───

@cli.command("open")
def open_dashboard():
    """Open the web dashboard in the default browser."""
    import webbrowser
    cfg = get_config()
    url = cfg.get("dashboard_url", "http://localhost:3000")
    webbrowser.open(url)
    console.print(f"[green]Opening {url}[/green]")


# ─── Chat (single prompt) ───

@cli.command("chat")
@click.argument("prompt")
@click.option("--provider", "-p", default=None)
@click.option("--model", "-m", default=None)
def chat_cmd(prompt: str, provider: str | None, model: str | None):
    """Send a single prompt and get a response (non-interactive)."""
    cfg = get_config()
    p = provider or cfg.get("provider", "openai")
    m = model or cfg.get("model", "gpt-4o")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()},
        {"role": "user", "content": prompt},
    ]

    resp = process_streaming_response(p, m, messages, tools=TOOLS_SPEC)
    messages.append(resp)

    # Handle tool calls
    tool_calls = resp.get("tool_calls", [])
    if tool_calls:
        execute_and_display_tools(tool_calls, messages)
        # One more LLM turn after tools
        resp = process_streaming_response(p, m, messages, tools=TOOLS_SPEC)


if __name__ == "__main__":
    cli()
