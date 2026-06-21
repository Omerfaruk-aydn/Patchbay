"""Patchbay CLI -- Universal LLM Gateway Control Plane."""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree
from rich.columns import Columns
from rich import box
from rich.markdown import Markdown
from rich.live import Live
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax

console = Console(force_terminal=True)
error_console = Console(stderr=True, force_terminal=True)

CONFIG_DIR = Path.home() / ".patchbay"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def ensure_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(
            "gateway_url: http://localhost:8000\n"
            "dashboard_url: http://localhost:3000\n"
            "blender_host: localhost\n"
            "blender_port: 9876\n"
            "mcp_host: localhost\n"
            "mcp_port: 8456\n"
            "theme: tokyo-night\n"
        )


def load_config() -> dict:
    ensure_config()
    import yaml
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def save_config(config: dict):
    import yaml
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def api_url(cfg: dict, path: str = "") -> str:
    return f"{cfg['gateway_url']}/v1{path}"


def api_get(cfg: dict, path: str = "", timeout: int = 10):
    import httpx
    try:
        r = httpx.get(api_url(cfg, path), timeout=timeout)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        console.print("[red]Gateway baglantisi kurulamadi[/red]")
        console.print(f"[dim]{cfg['gateway_url']}[/dim]")
        raise SystemExit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]HTTP {e.response.status_code}: {e.response.text[:200]}[/red]")
        raise SystemExit(1)


def api_post(cfg: dict, path: str = "", json: dict | None = None, timeout: int = 10):
    import httpx
    try:
        r = httpx.post(api_url(cfg, path), json=json, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        console.print("[red]Gateway baglantisi kurulamadi[/red]")
        raise SystemExit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]HTTP {e.response.status_code}: {e.response.text[:200]}[/red]")
        raise SystemExit(1)


BANNER = r"""
[bold blue]
  ____            _           ____ _               _
 |  _ \  ___  ___| | _____   / ___| |__   ___  ___| | __
 | | | |/ _ \/ __| |/ / _ \ | |   | '_ \ / _ \/ __| |/ /
 | |_| |  __/\__ \   <  __/ | |___| | | |  __/ (__|   <
 |____/ \___||___/_|\_\___|  \____|_| |_|\___|\___|_|\_\

[/bold blue]
[dim]Universal LLM Gateway & Orchestration Platform  v0.1.0[/dim]
"""


# ══════════════════════════════════════════════════════════════
# MAIN CLI GROUP
# ══════════════════════════════════════════════════════════════

@click.group()
@click.version_option("0.1.0", prog_name="patchbay")
def cli():
    """Patchbay — Universal LLM Gateway CLI

    Manage providers, API keys, models, MCP servers, Blender integration,
    and routing rules from the command line.
    """
    pass


# ══════════════════════════════════════════════════════════════
# STATUS
# ══════════════════════════════════════════════════════════════

@cli.command()
def status():
    """Show gateway status, services, and connection health."""
    console.print(BANNER)
    cfg = load_config()

    # Gateway health
    try:
        import httpx
        r = httpx.get(f"{cfg['gateway_url']}/health", timeout=3)
        health = r.json()
        gw_status = "[green][+][/green]"
        gw_latency = f"{health.get('latency_ms', 0):.0f}ms"
        db_status = health.get("checks", {}).get("database", "unknown")
    except Exception:
        gw_status = "[red][-][/red]"
        gw_latency = "N/A"
        db_status = "N/A"

    # Dashboard
    try:
        import httpx
        r = httpx.get(cfg["dashboard_url"], timeout=3)
        dash_status = "[green][+][/green]" if r.status_code == 200 else f"[yellow][!] HTTP {r.status_code}[/yellow]"
    except Exception:
        dash_status = "[red][-][/red]"

    # Blender
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((cfg["blender_host"], cfg["blender_port"]))
        s.close()
        blender_status = "[green][+][/green]"
    except Exception:
        blender_status = "[-] DISCONNECTED"

    # Models count
    try:
        models_data = api_get(cfg, "/models")
        model_count = len(models_data.get("data", []))
    except SystemExit:
        model_count = "?"

    # MCP servers
    try:
        projects = api_get(cfg, "/mcp/servers?project_id=de5f0bac-805f-4e98-a964-5d7bc4a426d2")
        mcp_count = len(projects.get("data", []))
    except SystemExit:
        mcp_count = "?"

    # Build status table
    table = Table(box=box.ROUNDED, border_style="blue", title="System Status", title_style="bold blue")
    table.add_column("Service", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")

    table.add_row("Gateway", gw_status, f"{cfg['gateway_url']}  ({gw_latency})")
    table.add_row("Database", f"[green][+] {db_status}[/green]" if db_status == "ok" else f"[red][-] {db_status}[/red]", "PostgreSQL 16 + pgvector")
    table.add_row("Dashboard", dash_status, cfg["dashboard_url"])
    table.add_row("Blender MCP", blender_status, f"{cfg['blender_host']}:{cfg['blender_port']}")
    table.add_row("Models", f"[cyan]{model_count}[/cyan]", "Registered in catalog")
    table.add_row("MCP Servers", f"[cyan]{mcp_count}[/cyan]", "Connected servers")

    console.print(table)
    console.print()


# ══════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════

@cli.group()
def models():
    """Manage LLM models in the catalog."""
    pass


@models.command("list")
def models_list():
    """List all registered LLM models."""
    cfg = load_config()
    data = api_get(cfg, "/models")
    table = Table(box=box.ROUNDED, border_style="cyan", title="LLM Models", title_style="bold cyan")
    table.add_column("Model", style="bold")
    table.add_column("Family", style="magenta")
    table.add_column("Context", justify="right")
    table.add_column("Max Output", justify="right")
    table.add_column("Vision", justify="center")
    table.add_column("Tools", justify="center")
    table.add_column("Streaming", justify="center")

    for m in data.get("data", []):
        pb = m.get("patchbay", {})
        table.add_row(
            m["id"],
            pb.get("family", "?"),
            f"{pb.get('context_window', 0):,}" if pb.get("context_window") else "-",
            f"{pb.get('max_output_tokens', 0):,}" if pb.get("max_output_tokens") else "-",
            "Yes" if pb.get("supports_vision") else "No",
            "Yes" if pb.get("supports_tools") else "No",
            "Yes" if pb.get("supports_streaming") else "No",
        )
    console.print(table)


@models.command("info")
@click.argument("model_name")
def models_info(model_name: str):
    """Show detailed info for a specific model."""
    cfg = load_config()
    data = api_get(cfg, "/models")
    for m in data.get("data", []):
        if m["id"] == model_name:
            panel = Panel(
                Syntax(str(m, indent=2), "json", theme="monokai", line_numbers=True),
                title=f"[bold]{model_name}[/bold]",
                border_style="cyan",
            )
            console.print(panel)
            return
    console.print(f"[red]Model '{model_name}' not found[/red]")


# ══════════════════════════════════════════════════════════════
# API KEYS
# ══════════════════════════════════════════════════════════════

@cli.group()
def keys():
    """Manage provider API keys."""
    pass


@keys.command("list")
def keys_list():
    """List configured API keys (masked)."""
    cfg = load_config()
    try:
        data = api_get(cfg, "/keys")
    except SystemExit:
        console.print("[yellow]Keys endpoint not available yet[/yellow]")
        return
    table = Table(box=box.ROUNDED, border_style="green", title="API Keys", title_style="bold green")
    table.add_column("Name", style="bold")
    table.add_column("Provider")
    table.add_column("Key (masked)")
    table.add_column("Created")
    for k in data.get("data", []):
        table.add_row(
            k.get("name", "?"),
            k.get("provider", "?"),
            k.get("key_preview", "****"),
            k.get("created_at", "?")[:10],
        )
    console.print(table)


@keys.command("add")
@click.option("--provider", "-p", prompt="Provider", help="Provider name (openai, anthropic, google, etc.)")
@click.option("--name", "-n", prompt="Key name", help="A friendly name for this key")
@click.option("--key", "-k", prompt="API Key", hide_input=True, help="The API key value")
def keys_add(provider: str, name: str, key: str):
    """Add a new provider API key."""
    cfg = load_config()
    try:
        data = api_post(cfg, "/keys", json={"provider": provider, "name": name, "key": key})
        console.print(f"[green]✓ API key '{name}' added for {provider}[/green]")
        console.print(f"  ID: [dim]{data.get('id', '?')}[/dim]")
    except SystemExit:
        console.print("[yellow]Keys endpoint not available yet. Saving locally.[/yellow]")
        keys_file = CONFIG_DIR / "keys.yaml"
        import yaml
        existing = {}
        if keys_file.exists():
            with open(keys_file) as f:
                existing = yaml.safe_load(f) or {}
        existing[name] = {"provider": provider, "key": key}
        with open(keys_file, "w") as f:
            yaml.dump(existing, f, default_flow_style=False)
        console.print(f"[green]✓ Saved locally to {keys_file}[/green]")


@keys.command("delete")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def keys_delete(name: str, yes: bool):
    """Delete an API key by name."""
    if not yes:
        if not Confirm.ask(f"Delete key [bold]{name}[/bold]?"):
            console.print("Cancelled.")
            return
    keys_file = CONFIG_DIR / "keys.yaml"
    import yaml
    if keys_file.exists():
        with open(keys_file) as f:
            existing = yaml.safe_load(f) or {}
        if name in existing:
            del existing[name]
            with open(keys_file, "w") as f:
                yaml.dump(existing, f, default_flow_style=False)
            console.print(f"[green]✓ Deleted key '{name}'[/green]")
        else:
            console.print(f"[red]Key '{name}' not found[/red]")
    else:
        console.print("[red]No keys file found[/red]")


# ══════════════════════════════════════════════════════════════
# MCP SERVERS
# ══════════════════════════════════════════════════════════════

@cli.group()
def mcp():
    """Manage MCP (Model Context Protocol) servers."""
    pass


@mcp.command("list")
def mcp_list():
    """List connected MCP servers."""
    cfg = load_config()
    try:
        data = api_get(cfg, "/mcp/servers?project_id=de5f0bac-805f-4e98-a964-5d7bc4a426d2")
    except SystemExit:
        console.print("[yellow]Could not fetch MCP servers[/yellow]")
        return

    table = Table(box=box.ROUNDED, border_style="magenta", title="MCP Servers", title_style="bold magenta")
    table.add_column("Name", style="bold")
    table.add_column("Transport")
    table.add_column("Connection URI")
    table.add_column("Status")

    for s in data.get("data", []):
        table.add_row(
            s["name"],
            s["transport"],
            s["connection_uri"],
            "[green]Active[/green]" if s.get("is_active") else "[red]Inactive[/red]",
        )
    console.print(table)


@mcp.command("tools")
def mcp_tools():
    """List all available MCP tools."""
    cfg = load_config()
    try:
        data = api_get(cfg, "/mcp/servers?project_id=de5f0bac-805f-4e98-a964-5d7bc4a426d2")
    except SystemExit:
        return

    for server in data.get("data", []):
        console.print(Panel(
            f"[bold]{server['name']}[/bold]  ({server['transport']})\n"
            f"[dim]{server['connection_uri']}[/dim]",
            border_style="magenta",
        ))


@mcp.command("add")
@click.option("--name", "-n", prompt="Server name", help="Friendly name")
@click.option("--transport", "-t", prompt="Transport (stdio/sse/streamable_http)", help="Transport type")
@click.option("--uri", "-u", prompt="Connection URI", help="Server connection URI")
def mcp_add(name: str, transport: str, uri: str):
    """Register a new MCP server."""
    cfg = load_config()
    data = api_post(cfg, "/mcp/servers", json={
        "project_id": "de5f0bac-805f-4e98-a964-5d7bc4a426d2",
        "name": name,
        "transport": transport,
        "connection_uri": uri,
    })
    console.print(f"[green]✓ MCP server '{name}' registered (ID: {data.get('id', '?')})[/green]")


# ══════════════════════════════════════════════════════════════
# BLENDER
# ══════════════════════════════════════════════════════════════

@cli.group()
def blender():
    """Control Blender via MCP — scene management, code execution, and more."""
    pass


def blender_call(tool_name: str, arguments: dict | None = None) -> dict:
    """Call a Blender MCP tool via the SSE bridge."""
    cfg = load_config()
    import httpx
    try:
        r = httpx.post(
            f"http://{cfg['mcp_host']}:{cfg['mcp_port']}/tools/call",
            json={"name": tool_name, "arguments": arguments or {}},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        console.print("[red]Blender MCP server baglantisi kurulamadi[/red]")
        console.print(f"[dim]http://{cfg['mcp_host']}:{cfg['mcp_port']}[/dim]")
        console.print("[yellow]Blender'i baslatin ve MCP addon'unu etkinlestirin.[/yellow]")
        raise SystemExit(1)
    except httpx.TimeoutException:
        console.print("[red]Blender MCP timeout — Blender yanit vermiyor[/red]")
        raise SystemExit(1)


def extract_text(result: dict) -> str:
    """Extract text content from MCP tool call result."""
    content = result.get("content", [])
    if isinstance(content, list) and content:
        return content[0].get("text", str(result))
    return str(result)


@blender.command("info")
def blender_info():
    """Show Blender scene information."""
    result = blender_call("get_scene_info")
    text = extract_text(result)

    import json
    try:
        scene = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        console.print(text)
        return

    console.print(Panel(
        f"[bold blue]Scene:[/bold blue] {scene.get('name', '?')}\n"
        f"[bold cyan]Objects:[/bold cyan] {scene.get('object_count', 0)}\n"
        f"[bold green]Materials:[/bold green] {scene.get('materials_count', 0)}",
        title="Blender Scene",
        border_style="blue",
    ))

    objects = scene.get("objects", [])
    if objects:
        table = Table(box=box.SIMPLE_HEAVY, border_style="blue")
        table.add_column("Name", style="bold")
        table.add_column("Type", style="magenta")
        table.add_column("Location", style="dim")

        for obj in objects:
            loc = obj.get("location", [0, 0, 0])
            table.add_row(
                obj["name"],
                obj["type"],
                f"({loc[0]:.2f}, {loc[1]:.2f}, {loc[2]:.2f})",
            )
        console.print(table)


@blender.command("objects")
def blender_objects():
    """List all objects in the Blender scene."""
    result = blender_call("get_scene_info")
    text = extract_text(result)

    import json
    try:
        scene = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        console.print(text)
        return

    objects = scene.get("objects", [])
    if not objects:
        console.print("[yellow]No objects in scene[/yellow]")
        return

    tree = Tree(f"[bold]Scene: {scene.get('name', '?')}[/bold]")
    type_groups: dict[str, Tree] = {}
    for obj in objects:
        t = obj["type"]
        if t not in type_groups:
            type_groups[t] = tree.add(f"[magenta]{t}[/magenta]")
        loc = obj.get("location", [0, 0, 0])
        type_groups[t].add(f"[cyan]{obj['name']}[/cyan]  [dim]({loc[0]:.1f}, {loc[1]:.1f}, {loc[2]:.1f})[/dim]")

    console.print(tree)


@blender.command("exec")
@click.argument("code")
def blender_exec(code: str):
    """Execute Python code in Blender's context.

    Example: patchbay blender exec "bpy.ops.mesh.primitive_cube_add(location=(0,0,2))"
    """
    result = blender_call("execute_code", {"code": code})
    text = extract_text(result)

    import json
    try:
        data = json.loads(text)
        if data.get("executed"):
            console.print("[green]✓ Code executed successfully[/green]")
        elif data.get("status") == "error":
            console.print(f"[red]✗ Error: {data.get('message', 'Unknown')}[/red]")
        else:
            console.print(text)
    except (json.JSONDecodeError, TypeError):
        console.print(text)


@blender.command("screenshot")
def blender_screenshot():
    """Capture a screenshot of the Blender 3D viewport."""
    result = blender_call("get_viewport_screenshot")
    text = extract_text(result)

    import json
    try:
        data = json.loads(text)
        if data.get("type") == "image":
            import base64
            img_data = base64.b64decode(data["data"])
            screenshot_path = Path.cwd() / "blender_screenshot.png"
            screenshot_path.write_bytes(img_data)
            console.print(f"[green]✓ Screenshot saved to {screenshot_path}[/green]")
        else:
            console.print(text)
    except (json.JSONDecodeError, TypeError, KeyError):
        console.print(text)


@blender.command("create")
@click.argument("primitive", type=click.Choice([
    "cube", "sphere", "cylinder", "cone", "torus", "plane", "monkey",
]))
@click.option("--location", "-l", default="0,0,0", help="X,Y,Z location")
@click.option("--name", "-n", default="", help="Object name")
@click.option("--scale", "-s", default="1,1,1", help="X,Y,Z scale")
def blender_create(primitive: str, location: str, name: str, scale: str):
    """Create a primitive object in Blender.

    Primitives: cube, sphere, cylinder, cone, torus, plane, monkey
    """
    loc = [float(x.strip()) for x in location.split(",")]
    scl = [float(x.strip()) for x in scale.split(",")]

    op_map = {
        "cube": "bpy.ops.mesh.primitive_cube_add",
        "sphere": "bpy.ops.mesh.primitive_uv_sphere_add",
        "cylinder": "bpy.ops.mesh.primitive_cylinder_add",
        "cone": "bpy.ops.mesh.primitive_cone_add",
        "torus": "bpy.ops.mesh.primitive_torus_add",
        "plane": "bpy.ops.mesh.primitive_plane_add",
        "monkey": "bpy.ops.mesh.primitive_monkey_add",
    }

    code = f"{op_map[primitive]}(location=({loc[0]}, {loc[1]}, {loc[2]}), scale=({scl[0]}, {scl[1]}, {scl[2]}))"
    if name:
        code += f'\nbpy.context.active_object.name = "{name}"'

    result = blender_call("execute_code", {"code": code})
    text = extract_text(result)

    import json
    try:
        data = json.loads(text)
        if data.get("executed"):
            obj_name = name or primitive.capitalize()
            console.print(f"[green]✓ Created {primitive} '{obj_name}' at ({loc[0]}, {loc[1]}, {loc[2]})[/green]")
        else:
            console.print(f"[red]✗ {data.get('message', 'Unknown error')}[/red]")
    except (json.JSONDecodeError, TypeError):
        console.print(text)


@blender.command("delete")
@click.argument("object_name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def blender_delete(object_name: str, yes: bool):
    """Delete an object from the Blender scene."""
    if not yes:
        if not Confirm.ask(f"Delete object [bold]{object_name}[/bold]?"):
            console.print("Cancelled.")
            return

    code = (
        f'obj = bpy.data.objects.get("{object_name}")\n'
        "if obj:\n"
        "    bpy.data.objects.remove(obj, do_unlink=True)\n"
        '    print(f"Deleted {obj.name}")\n'
        "else:\n"
        f'    print("Object \'{object_name}\' not found")'
    )

    result = blender_call("execute_code", {"code": code})
    text = extract_text(result)
    console.print(f"[green]{text.strip()}[/green]")


@blender.command("material")
@click.argument("object_name")
@click.option("--color", "-c", prompt="Color (hex or name)", help="Material color")
def blender_material(object_name: str, color: str):
    """Assign a material with color to a Blender object."""
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
        try:
            parts = [float(x.strip()) for x in color.split(",")]
            rgba = tuple(parts[:4]) if len(parts) >= 4 else (*parts[:3], 1)
        except ValueError:
            console.print(f"[red]Invalid color: {color}[/red]")
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
        f'    print(f"Material applied to {obj.name}")\n'
        "else:\n"
        f'    print("Object not found")'
    )

    result = blender_call("execute_code", {"code": code})
    text = extract_text(result)
    console.print(f"[green]{text.strip()}[/green]")


# ══════════════════════════════════════════════════════════════
# CHAT (Interactive LLM Chat)
# ══════════════════════════════════════════════════════════════

@cli.command()
@click.option("--model", "-m", default="gpt-4o", help="Model to chat with")
@click.option("--system", "-s", default="", help="System prompt")
def chat(model: str, system: str):
    """Start an interactive chat session with an LLM model.

    Type your messages and get responses. Use /quit or /exit to stop.
    """
    cfg = load_config()
    console.print(Panel(
        f"[bold]Interactive Chat[/bold]\n"
        f"Model: [cyan]{model}[/cyan]\n"
        f"Type [dim]/quit[/dim] to exit, [dim]/history[/dim] to show history",
        title="Patchbay Chat",
        border_style="cyan",
    ))

    messages = []
    if system:
        messages.append({"role": "system", "content": system})

    while True:
        try:
            user_input = Prompt.ask("\n[bold blue]You[/bold blue]")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Chat ended.[/dim]")
            break

        if user_input.strip() in ("/quit", "/exit", "/q"):
            console.print("[dim]Chat ended.[/dim]")
            break

        if user_input.strip() == "/history":
            for msg in messages:
                role = msg["role"]
                if role == "system":
                    continue
                color = "green" if role == "assistant" else "blue"
                console.print(f"[bold {color}]{role.title()}:[/bold {color}] {msg['content'][:200]}")
            continue

        if not user_input.strip():
            continue

        messages.append({"role": "user", "content": user_input})

        # Build request for the gateway's chat endpoint
        try:
            import httpx
            with httpx.stream(
                "POST",
                api_url(cfg, "/chat"),
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True,
                },
                timeout=60,
            ) as r:
                r.raise_for_status()
                console.print("\n[bold green]Assistant:[/bold green] ", end="")
                full_response = ""
                for line in r.iter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        import json
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                console.print(content, end="")
                                full_response += content
                        except json.JSONDecodeError:
                            continue
                console.print()
                messages.append({"role": "assistant", "content": full_response})
        except httpx.HTTPStatusError:
            # If streaming not available, try non-streaming
            try:
                data = api_post(cfg, "/chat", json={
                    "model": model,
                    "messages": messages,
                })
                response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                console.print(f"\n[bold green]Assistant:[/bold green] {response}")
                messages.append({"role": "assistant", "content": response})
            except SystemExit:
                console.print("[red]Could not reach the chat endpoint[/red]")
        except httpx.ConnectError:
            console.print("[red]Gateway baglantisi kurulamadi[/red]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


# ══════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════

@cli.group()
def config():
    """Manage CLI configuration."""
    pass


@config.command("show")
def config_show():
    """Show current configuration."""
    cfg = load_config()
    table = Table(box=box.ROUNDED, border_style="yellow", title="Configuration", title_style="bold yellow")
    table.add_column("Setting", style="bold")
    table.add_column("Value")
    for key, value in cfg.items():
        table.add_row(key, str(value))
    console.print(table)
    console.print(f"\n[dim]Config file: {CONFIG_FILE}[/dim]")


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a configuration value.

    Example: patchbay config set gateway_url http://localhost:8000
    """
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
    console.print(f"[green]✓ Set {key} = {value}[/green]")


@config.command("init")
def config_init():
    """Initialize configuration with interactive prompts."""
    console.print(Panel("[bold]Patchbay CLI Setup[/bold]", border_style="yellow"))
    cfg = load_config()

    cfg["gateway_url"] = Prompt.ask("Gateway URL", default=cfg.get("gateway_url", "http://localhost:8000"))
    cfg["dashboard_url"] = Prompt.ask("Dashboard URL", default=cfg.get("dashboard_url", "http://localhost:3000"))
    cfg["blender_host"] = Prompt.ask("Blender host", default=cfg.get("blender_host", "localhost"))
    cfg["blender_port"] = int(Prompt.ask("Blender MCP port", default=str(cfg.get("blender_port", 8456))))

    save_config(cfg)
    console.print("[green]✓ Configuration saved![/green]")


# ══════════════════════════════════════════════════════════════
# ROUTING
# ══════════════════════════════════════════════════════════════

@cli.group()
def routing():
    """Manage routing policies and strategies."""
    pass


@routing.command("list")
def routing_list():
    """List routing strategies."""
    strategies = Table(box=box.ROUNDED, border_style="cyan", title="Routing Strategies", title_style="bold cyan")
    strategies.add_column("Strategy", style="bold")
    strategies.add_column("Description")
    strategies.add_column("Default", justify="center")

    strategies.add_row("cost_optimized", "Route to cheapest provider for each model", "✓")
    strategies.add_row("latency_optimized", "Route to fastest provider based on response time", "")
    strategies.add_row("quality_first", "Route to highest quality provider regardless of cost", "")
    strategies.add_row("round_robin", "Distribute requests evenly across providers", "")
    strategies.add_row("semantic", "Route based on task type (code, creative, analysis)", "")
    strategies.add_row("learned", "ML-based routing using historical performance data", "")

    console.print(strategies)


# ══════════════════════════════════════════════════════════════
# QUICK COMMANDS
# ══════════════════════════════════════════════════════════════

@cli.command("open")
def open_dashboard():
    """Open the dashboard in the default browser."""
    cfg = load_config()
    import webbrowser
    webbrowser.open(cfg["dashboard_url"])
    console.print(f"[green]Opening {cfg['dashboard_url']} in browser...[/green]")


@cli.command("health")
def health():
    """Quick health check of all services."""
    cfg = load_config()

    items = []
    # Gateway
    try:
        import httpx
        r = httpx.get(f"{cfg['gateway_url']}/health", timeout=3)
        items.append(("Gateway", "green", "OK"))
    except Exception:
        items.append(("Gateway", "red", "DOWN"))

    # Dashboard
    try:
        import httpx
        r = httpx.get(cfg["dashboard_url"], timeout=3)
        items.append(("Dashboard", "green", "OK"))
    except Exception:
        items.append(("Dashboard", "red", "DOWN"))

    # Blender
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((cfg["blender_host"], cfg["blender_port"]))
        s.close()
        items.append(("Blender MCP", "green", "OK"))
    except Exception:
        items.append(("Blender MCP", "red", "DOWN"))

    for name, color, status in items:
        icon = "+" if color == "green" else "-"
        console.print(f"  [{color}][{icon}][/{color}] {name}: [{color}]{status}[/{color}]")
    all_ok = all(s == "OK" for _, _, s in items)
    if all_ok:
        console.print("[green bold]All services healthy![/green bold]")
    else:
        console.print("[yellow]Some services are down.[/yellow]")


@cli.command("dashboard")
def dashboard_cmd():
    """Open the web dashboard."""
    open_dashboard.callback()


if __name__ == "__main__":
    cli()
