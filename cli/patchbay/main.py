"""Patchbay CLI - One CLI to rule them all.

Default (no args): Interactive AI coding assistant (like Claude Code)
With subcommands: Gateway management, Blender, models, keys, etc.
"""

from __future__ import annotations

import io
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from patchbay.tools import TOOLS_SPEC, execute_tool
from patchbay.provider import get_config, save_config, get_api_key, stream_completion
from patchbay.session import save as save_session, load as load_session, list_all

# Force UTF-8 on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

console = Console(force_terminal=True)

SYSTEM_PROMPT = """You are Patchbay AI, an expert software engineering assistant. You help with coding, debugging, refactoring, and understanding codebases.

You have tools to read/write/edit files, run shell commands, and search code. Use them when needed.
Be concise and direct. Prefer edit_file over rewriting entire files."""


def get_project_context() -> str:
    parts = [f"Working directory: {os.getcwd()}"]
    for f in ["README.md", "CLAUDE.md", "AGENTS.md", "pyproject.toml", "package.json"]:
        p = Path(f)
        if p.exists():
            try:
                parts.append(f"\n--- {f} ---\n{p.read_text('utf-8', 'replace')[:2000]}")
            except Exception:
                pass
    try:
        entries = sorted(Path(".").iterdir())
        lines = []
        for item in entries:
            if item.name.startswith(".") or item.name in ("node_modules", "__pycache__"):
                continue
            kind = "d" if item.is_dir() else "f"
            lines.append(f"  {'[' + kind + ']' if kind == 'd' else '   '} {item.name}")
        if lines:
            parts.append("\n--- Structure ---\n" + "\n".join(lines[:30]))
    except Exception:
        pass
    return "\n".join(parts)


def format_tool_result(name: str, result: dict) -> str:
    if result.get("error"):
        return f"[Error] {result['error']}"
    if name == "read_file":
        return result.get("content", "")
    if name == "run_bash":
        parts = []
        if result.get("stdout"):
            parts.append(result["stdout"])
        if result.get("stderr"):
            parts.append(f"STDERR:\n{result['stderr']}")
        return "\n".join(parts) if parts else f"exit {result.get('returncode', '?')}"
    if name == "search_files":
        return "\n".join(result.get("files", [])) or "No files"
    if name == "search_content":
        return "\n".join(f"{m['file']}:{m['line']}: {m['content']}" for m in result.get("matches", [])) or "No matches"
    if name == "list_directory":
        return "\n".join(f"{'[d] ' if e['type'] == 'dir' else '    '}{e['name']}" for e in result.get("entries", []))
    return json.dumps(result, indent=2)


def run_repl(provider: str, model: str):
    """Interactive AI coding assistant REPL."""
    from rich.markdown import Markdown

    banner = f"""[bold cyan]   ____            _                 ____  __  _____ ____ 
  |  _ \\  ___  ___| | _____   _____| __ )/ / |_   _|  _ \\
  | | | |/ _ \\/ __| |/ / _ \\ / / _ \\  _ \\ / /   | | | | |
  | |_| |  __/\\__ \\   < (_) | (_)  __/ |_) / /    | | |_| |
  |____/ \\___||___/_|\\_\\___/ \\___/\\___/____/      |_| |____/[/bold cyan]
[dim]  Interactive AI Coding Assistant  v0.1.0[/dim]
"""
    console.print(banner)
    console.print(f"[dim]  Provider: {provider}  |  Model: {model}  |  /help for commands[/dim]\n")

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()},
    ]
    session_id = str(uuid.uuid4())[:8]
    tool_rounds = 10

    while True:
        try:
            line = console.input("[bold cyan]>[/bold cyan] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if not line.strip():
            continue

        # Commands
        if line.startswith("/"):
            cmd = line.split()[0].lower()
            arg = line[len(cmd):].strip()
            if cmd in ("/quit", "/exit", "/q"):
                console.print("[dim]Goodbye![/dim]")
                break
            elif cmd == "/help":
                console.print("""
[bold]Commands:[/bold]
  /help         Show this help
  /model NAME   Switch model (e.g. /model gpt-4o)
  /provider NAME Switch provider (openai, anthropic, deepseek, openrouter)
  /clear        Clear conversation
  /history      Show history
  /save         Save session
  /load ID      Load session
  /sessions     List sessions
  /config       Show/set config
  /quit         Exit
""")
            elif cmd == "/model":
                if arg:
                    model = arg
                    console.print(f"[green]Model: {model}[/green]")
                else:
                    console.print(f"[yellow]Current: {model}[/yellow]")
            elif cmd == "/provider":
                if arg:
                    provider = arg
                    console.print(f"[green]Provider: {provider}[/green]")
                else:
                    console.print(f"[yellow]Current: {provider}[/yellow]")
            elif cmd == "/clear":
                messages.clear()
                messages.append({"role": "system", "content": SYSTEM_PROMPT + "\n\n" + get_project_context()})
                console.print("[green]Cleared[/green]")
            elif cmd == "/history":
                for m in messages:
                    if m["role"] == "system":
                        continue
                    c = "green" if m["role"] == "assistant" else "cyan"
                    text = m.get("content", "") or ""
                    console.print(f"\n[bold {c}]{'You' if m['role'] == 'user' else 'AI'}:[/bold {c}] {text[:300]}")
            elif cmd == "/save":
                sid = arg or str(uuid.uuid4())[:8]
                save_session(sid, messages)
                console.print(f"[green]Saved: {sid}[/green]")
            elif cmd == "/load":
                if arg:
                    data = load_session(arg)
                    if data:
                        messages.clear()
                        messages.extend(data["messages"])
                        console.print(f"[green]Loaded {arg} ({len(messages)} msgs)[/green]")
                    else:
                        console.print(f"[red]Not found: {arg}[/red]")
            elif cmd == "/sessions":
                for s in list_all()[:10]:
                    console.print(f"  [cyan]{s['id']}[/cyan]  {s['updated'][:19]}  {s['count']} msgs")
            elif cmd == "/config":
                config = get_config()
                if arg:
                    parts = arg.split(maxsplit=1)
                    if len(parts) == 2:
                        config[parts[0]] = parts[1]
                        save_config(config)
                        console.print(f"[green]Set {parts[0]}[/green]")
                else:
                    t = Table(box=box.SIMPLE, border_style="cyan")
                    t.add_column("Key", style="bold")
                    t.add_column("Value")
                    for k, v in config.items():
                        val = v if "key" not in k.lower() else f"***{str(v)[-4:]}" if len(str(v)) > 4 else "***"
                        t.add_row(k, str(val))
                    console.print(t)
            else:
                console.print(f"[red]Unknown: {cmd}[/red]")
            continue

        messages.append({"role": "user", "content": line})

        # Tool loop
        for _ in range(tool_rounds):
            tool_calls_list = []
            content_parts = []

            try:
                for chunk in stream_completion(provider, model, messages, tools=TOOLS_SPEC):
                    # OpenAI
                    if "choices" in chunk:
                        delta = chunk["choices"][0].get("delta", {})
                        if delta.get("content"):
                            console.print(delta["content"], end="", highlight=False)
                            content_parts.append(delta["content"])
                        if delta.get("tool_calls"):
                            for tc in delta["tool_calls"]:
                                idx = tc.get("index", 0)
                                while len(tool_calls_list) <= idx:
                                    tool_calls_list.append({"id": "", "type": "function",
                                        "function": {"name": "", "arguments": ""}})
                                entry = tool_calls_list[idx]
                                if tc.get("id"):
                                    entry["id"] = tc["id"]
                                if tc.get("function", {}).get("name"):
                                    entry["function"]["name"] = tc["function"]["name"]
                                if tc.get("function", {}).get("arguments"):
                                    entry["function"]["arguments"] += tc["function"]["arguments"]

                    # Anthropic
                    elif "type" in chunk:
                        et = chunk["type"]
                        if et == "content_block_delta":
                            d = chunk.get("delta", {})
                            if d.get("type") == "text_delta":
                                console.print(d.get("text", ""), end="", highlight=False)
                                content_parts.append(d.get("text", ""))
                            elif d.get("type") == "input_json_delta" and tool_calls_list:
                                tool_calls_list[-1]["function"]["arguments"] += d.get("partial_json", "")
                        elif et == "content_block_start":
                            b = chunk.get("content_block", {})
                            if b.get("type") == "tool_use":
                                tool_calls_list.append({"id": b.get("id", ""), "type": "function",
                                    "function": {"name": b.get("name", ""), "arguments": ""}})

            except KeyboardInterrupt:
                console.print("\n[yellow][Interrupted][/yellow]")
                break
            except Exception as e:
                console.print(f"\n[red][Error: {e}][/red]")
                break

            console.print()

            # Build assistant message
            assistant_msg = {"role": "assistant", "content": "".join(content_parts) if content_parts else None}

            if tool_calls_list:
                # Clean up tool calls
                clean_tcs = []
                for tc in tool_calls_list:
                    if tc["function"]["name"]:
                        try:
                            args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                        except json.JSONDecodeError:
                            args = {}
                        clean_tcs.append({
                            "id": tc["id"], "type": "function",
                            "function": {"name": tc["function"]["name"], "arguments": json.dumps(args)},
                        })
                assistant_msg["tool_calls"] = clean_tcs

            messages.append(assistant_msg)

            # Execute tools
            if tool_calls_list:
                for tc in tool_calls_list:
                    name = tc["function"]["name"]
                    if not name:
                        continue
                    try:
                        args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                    except json.JSONDecodeError:
                        args = {}
                    console.print(f"[dim]  > {name}({', '.join(f'{k}={repr(v)[:40]}' for k, v in args.items())})[/dim]")
                    result = execute_tool(name, args)
                    result_text = format_tool_result(name, result)
                    if len(result_text) > 4000:
                        result_text = result_text[:4000] + f"\n... ({len(result_text) - 4000} truncated)"
                    messages.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": result_text})
            else:
                break  # No tools, done

        if len(messages) % 20 == 0:
            save_session(session_id, messages)

    save_session(session_id, messages)


# ─── Click CLI ───

@click.group(invoke_without_command=True)
@click.option("--provider", "-p", default=None, help="LLM provider")
@click.option("--model", "-m", default=None, help="Model name")
@click.pass_context
def cli(ctx, provider, model):
    """Patchbay - Universal LLM Gateway & AI Coding Assistant

    Run without arguments to start the interactive AI assistant.
    Use subcommands to manage the gateway, models, Blender, etc.
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
        run_repl(p, m)


@cli.command()
def status():
    """Show gateway status."""
    cfg = get_config()
    gw_url = cfg.get("gateway_url", "http://localhost:8000")

    import httpx
    items = []
    # Gateway
    try:
        r = httpx.get(f"{gw_url}/health", timeout=3)
        h = r.json()
        items.append(("Gateway", "green", f"OK ({h.get('latency_ms',0):.0f}ms)"))
        db = h.get("checks", {}).get("database", "?")
        items.append(("Database", "green" if db == "ok" else "red", db))
    except Exception:
        items.append(("Gateway", "red", "DOWN"))

    # Dashboard
    try:
        r = httpx.get(cfg.get("dashboard_url", "http://localhost:3000"), timeout=3)
        items.append(("Dashboard", "green", "OK"))
    except Exception:
        items.append(("Dashboard", "red", "DOWN"))

    # Blender
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((cfg.get("blender_host", "localhost"), cfg.get("blender_port", 9876)))
        s.close()
        items.append(("Blender MCP", "green", "OK"))
    except Exception:
        items.append(("Blender MCP", "red", "DOWN"))

    t = Table(box=box.ROUNDED, border_style="cyan", title="System Status", title_style="bold cyan")
    t.add_column("Service", style="bold")
    t.add_column("Status")
    t.add_column("Details", style="dim")
    for name, color, detail in items:
        t.add_row(name, f"[{color}]+[/{color}]" if color == "green" else f"[red]-[/red]", detail)
    console.print(t)


@cli.command("models")
def models_cmd():
    """List available LLM models."""
    cfg = get_config()
    gw_url = cfg.get("gateway_url", "http://localhost:8000")
    try:
        import httpx
        data = httpx.get(f"{gw_url}/v1/models", timeout=5).json()
    except Exception as e:
        console.print(f"[red]Could not fetch models: {e}[/red]")
        return

    t = Table(box=box.ROUNDED, border_style="cyan", title="Models", title_style="bold cyan")
    t.add_column("Model", style="bold")
    t.add_column("Family")
    t.add_column("Context", justify="right")
    t.add_column("Vision", justify="center")
    t.add_column("Tools", justify="center")
    for m in data.get("data", []):
        pb = m.get("patchbay", {})
        t.add_row(m["id"], pb.get("family", "?"),
                  f"{pb.get('context_window',0):,}" if pb.get("context_window") else "-",
                  "Y" if pb.get("supports_vision") else "N",
                  "Y" if pb.get("supports_tools") else "N")
    console.print(t)


@cli.command()
def health():
    """Quick health check."""
    cfg = get_config()
    gw_url = cfg.get("gateway_url", "http://localhost:8000")
    for name, check_fn in [
        ("Gateway", lambda: __import__("httpx").get(f"{gw_url}/health", timeout=3).status_code == 200),
        ("Dashboard", lambda: __import__("httpx").get(cfg.get("dashboard_url", "http://localhost:3000"), timeout=3).ok),
        ("Blender", lambda: (lambda s: (s.connect((cfg.get("blender_host", "localhost"), cfg.get("blender_port", 9876))), s.close()))(socket.socket())),
    ]:
        try:
            ok = check_fn()
            console.print(f"  [{'green' if ok else 'red'}]+[/{'green' if ok else 'red'}] {name}")
        except Exception:
            console.print(f"  [red]-[/red] {name}")


@cli.group()
def blender():
    """Blender integration via MCP."""
    pass


@blender.command("info")
def blender_info():
    """Show Blender scene."""
    cfg = get_config()
    import httpx
    try:
        r = httpx.post(f"http://{cfg.get('mcp_host','localhost')}:{cfg.get('mcp_port',8456)}/tools/call",
                       json={"name": "get_scene_info", "arguments": {}}, timeout=20)
        text = r.json()["content"][0]["text"]
        scene = json.loads(text)
    except Exception as e:
        console.print(f"[red]Blender MCP error: {e}[/red]")
        return

    console.print(Panel(f"[bold]Scene:[/bold] {scene.get('name','?')}\n"
                        f"[bold]Objects:[/bold] {scene.get('object_count',0)}\n"
                        f"[bold]Materials:[/bold] {scene.get('materials_count',0)}",
                        title="Blender", border_style="blue"))

    t = Table(box=box.SIMPLE_HEAVY, border_style="blue")
    t.add_column("Name", style="bold")
    t.add_column("Type", style="magenta")
    t.add_column("Location", style="dim")
    for obj in scene.get("objects", []):
        loc = obj.get("location", [0, 0, 0])
        t.add_row(obj["name"], obj["type"], f"({loc[0]:.1f}, {loc[1]:.1f}, {loc[2]:.1f})")
    console.print(t)


@blender.command("exec")
@click.argument("code")
def blender_exec(code):
    """Execute Python code in Blender."""
    cfg = get_config()
    import httpx
    try:
        r = httpx.post(f"http://{cfg.get('mcp_host','localhost')}:{cfg.get('mcp_port',8456)}/tools/call",
                       json={"name": "execute_code", "arguments": {"code": code}}, timeout=20)
        result = json.loads(r.json()["content"][0]["text"])
        if result.get("executed"):
            console.print("[green]Done[/green]")
        else:
            console.print(f"[red]{result.get('message', 'Error')}[/red]")
    except Exception as e:
        console.print(f"[red]{e}[/red]")


@blender.command("create")
@click.argument("primitive", type=click.Choice(["cube", "sphere", "cylinder", "cone", "torus", "plane", "monkey"]))
@click.option("--name", "-n", default="")
@click.option("--location", "-l", default="0,0,0")
def blender_create(primitive, name, location):
    """Create a primitive in Blender."""
    loc = [float(x.strip()) for x in location.split(",")]
    ops = {"cube": "primitive_cube_add", "sphere": "primitive_uv_sphere_add",
           "cylinder": "primitive_cylinder_add", "cone": "primitive_cone_add",
           "torus": "primitive_torus_add", "plane": "primitive_plane_add", "monkey": "primitive_monkey_add"}
    code = f"bpy.ops.mesh.{ops[primitive]}(location=({loc[0]},{loc[1]},{loc[2]}))"
    if name:
        code += f'\nbpy.context.active_object.name = "{name}"'
    cfg = get_config()
    import httpx
    try:
        r = httpx.post(f"http://{cfg.get('mcp_host','localhost')}:{cfg.get('mcp_port',8456)}/tools/call",
                       json={"name": "execute_code", "arguments": {"code": code}}, timeout=20)
        result = json.loads(r.json()["content"][0]["text"])
        if result.get("executed"):
            console.print(f"[green]Created {primitive} at ({loc[0]},{loc[1]},{loc[2]})[/green]")
        else:
            console.print(f"[red]{result.get('message', 'Error')}[/red]")
    except Exception as e:
        console.print(f"[red]{e}[/red]")


@blender.command("objects")
def blender_objects():
    """List Blender objects."""
    cfg = get_config()
    import httpx
    try:
        r = httpx.post(f"http://{cfg.get('mcp_host','localhost')}:{cfg.get('mcp_port',8456)}/tools/call",
                       json={"name": "get_scene_info", "arguments": {}}, timeout=20)
        scene = json.loads(r.json()["content"][0]["text"])
    except Exception as e:
        console.print(f"[red]{e}[/red]")
        return
    for obj in scene.get("objects", []):
        loc = obj.get("location", [0,0,0])
        console.print(f"  [cyan]{obj['name']}[/cyan]  [dim]{obj['type']} ({loc[0]:.1f},{loc[1]:.1f},{loc[2]:.1f})[/dim]")


@cli.group()
def keys():
    """Manage API keys."""
    pass


@keys.command("list")
def keys_list():
    """List configured keys."""
    cfg = get_config()
    t = Table(box=box.SIMPLE, border_style="green", title="API Keys", title_style="bold green")
    t.add_column("Key", style="bold")
    t.add_column("Value")
    for k, v in cfg.items():
        if "key" in k.lower():
            val = f"***{str(v)[-4:]}" if len(str(v)) > 4 else "***"
            t.add_row(k, val)
    console.print(t)


@keys.command("set")
@click.argument("key")
@click.argument("value")
def keys_set(key, value):
    """Set a config value (e.g. patchbay keys set openai_api_key sk-xxx)."""
    cfg = get_config()
    cfg[key] = value
    save_config(cfg)
    console.print(f"[green]Set {key}[/green]")


@cli.group()
def config():
    """Configuration management."""
    pass


@config.command("show")
def config_show():
    """Show all config."""
    cfg = get_config()
    t = Table(box=box.SIMPLE, border_style="yellow", title="Config", title_style="bold yellow")
    t.add_column("Key", style="bold")
    t.add_column("Value")
    for k, v in cfg.items():
        val = v if "key" not in k.lower() else f"***{str(v)[-4:]}" if len(str(v)) > 4 else "***"
        t.add_row(k, str(val))
    console.print(t)


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key, value):
    """Set a config value."""
    cfg = get_config()
    cfg[key] = value
    save_config(cfg)
    console.print(f"[green]Set {key} = {value}[/green]")


@cli.command("open")
def open_dashboard():
    """Open dashboard in browser."""
    import webbrowser
    cfg = get_config()
    url = cfg.get("dashboard_url", "http://localhost:3000")
    webbrowser.open(url)
    console.print(f"[green]Opening {url}[/green]")


@cli.group()
def routing():
    """Routing strategies."""
    pass


@routing.command("list")
def routing_list():
    """List routing strategies."""
    t = Table(box=box.ROUNDED, border_style="cyan", title="Routing", title_style="bold cyan")
    t.add_column("Strategy", style="bold")
    t.add_column("Description")
    t.add_row("cost_optimized", "Cheapest provider for each model")
    t.add_row("latency_optimized", "Fastest provider by response time")
    t.add_row("quality_first", "Highest quality regardless of cost")
    t.add_row("round_robin", "Distribute evenly across providers")
    t.add_row("semantic", "Route by task type (code, creative, analysis)")
    t.add_row("learned", "ML-based using historical performance")
    console.print(t)


if __name__ == "__main__":
    cli()
