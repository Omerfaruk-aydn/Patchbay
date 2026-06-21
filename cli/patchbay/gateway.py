"""Gateway - Patchbay gateway management functions.

Handles:
  - Health checks and status reporting
  - Model catalog management
  - API key management
  - Routing strategy display
  - MCP server management
"""

from __future__ import annotations

import socket
from typing import Any

import httpx

from patchbay.config import get_config


# ═══════════════════════════════════════════════════════════════
# HEALTH CHECKS
# ═══════════════════════════════════════════════════════════════

def check_gateway(url: str | None = None) -> dict[str, Any]:
    """Check gateway health.

    Returns:
        Dict with 'status', 'latency_ms', 'checks' keys
    """
    cfg = get_config()
    gw_url = url or cfg.get("gateway_url", "http://localhost:8000")
    try:
        r = httpx.get(f"{gw_url}/health", timeout=5)
        r.raise_for_status()
        data = r.json()
        return {
            "status": "ok",
            "latency_ms": data.get("latency_ms", 0),
            "checks": data.get("checks", {}),
            "version": data.get("version", "?"),
            "service": data.get("service", "?"),
        }
    except httpx.ConnectError:
        return {"status": "down", "error": f"Cannot connect to {gw_url}"}
    except httpx.TimeoutException:
        return {"status": "timeout", "error": "Gateway health check timed out"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_dashboard(url: str | None = None) -> dict[str, Any]:
    """Check dashboard availability."""
    cfg = get_config()
    dash_url = url or cfg.get("dashboard_url", "http://localhost:3000")
    try:
        r = httpx.get(dash_url, timeout=5)
        return {"status": "ok", "status_code": r.status_code}
    except httpx.ConnectError:
        return {"status": "down", "error": f"Cannot connect to {dash_url}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_blender(host: str | None = None, port: int | None = None) -> dict[str, Any]:
    """Check Blender addon socket connectivity."""
    cfg = get_config()
    bh = host or cfg.get("blender_host", "localhost")
    bp = port or cfg.get("blender_port", 9876)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((bh, bp))
        s.close()
        return {"status": "ok", "host": bh, "port": bp}
    except socket.timeout:
        return {"status": "timeout", "error": f"Blender not responding at {bh}:{bp}"}
    except ConnectionRefusedError:
        return {"status": "down", "error": f"Blender addon not running at {bh}:{bp}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_mcp(host: str | None = None, port: int | None = None) -> dict[str, Any]:
    """Check MCP server connectivity."""
    cfg = get_config()
    mh = host or cfg.get("mcp_host", "localhost")
    mp = port or cfg.get("mcp_port", 8456)
    try:
        r = httpx.get(f"http://{mh}:{mp}/health", timeout=3)
        r.raise_for_status()
        return {"status": "ok", "data": r.json()}
    except Exception as e:
        return {"status": "down", "error": str(e)}


def get_full_status() -> list[tuple[str, str, str]]:
    """Get status of all services.

    Returns:
        List of (name, color, detail) tuples for table display
    """
    items = []

    # Gateway
    gw = check_gateway()
    if gw["status"] == "ok":
        items.append(("Gateway", "green", f"OK ({gw.get('latency_ms', 0):.0f}ms) v{gw.get('version', '?')}"))
        db = gw.get("checks", {}).get("database", "?")
        items.append(("Database", "green" if db == "ok" else "red", db))
    else:
        items.append(("Gateway", "red", gw.get("error", "DOWN")))

    # Dashboard
    dash = check_dashboard()
    items.append(("Dashboard", "green" if dash["status"] == "ok" else "red",
                  "OK" if dash["status"] == "ok" else dash.get("error", "DOWN")))

    # Blender
    blender = check_blender()
    items.append(("Blender MCP", "green" if blender["status"] == "ok" else "red",
                  f"{blender.get('host', '?')}:{blender.get('port', '?')}" if blender["status"] == "ok"
                  else blender.get("error", "DOWN")))

    # Models count
    try:
        cfg = get_config()
        r = httpx.get(f"{cfg.get('gateway_url', 'http://localhost:8000')}/v1/models", timeout=5)
        data = r.json()
        model_count = len(data.get("data", []))
        items.append(("Models", "green", f"{model_count} registered"))
    except Exception:
        items.append(("Models", "red", "Cannot fetch"))

    # MCP servers
    try:
        cfg = get_config()
        r = httpx.get(
            f"{cfg.get('gateway_url', 'http://localhost:8000')}/v1/mcp/servers",
            params={"project_id": "de5f0bac-805f-4e98-a964-5d7bc4a426d2"},
            timeout=5,
        )
        data = r.json()
        mcp_count = len(data.get("data", []))
        items.append(("MCP Servers", "green", f"{mcp_count} connected"))
    except Exception:
        items.append(("MCP Servers", "dim", "N/A"))

    return items


# ═══════════════════════════════════════════════════════════════
# MODEL MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def list_models() -> list[dict]:
    """Fetch all registered LLM models from the gateway."""
    cfg = get_config()
    gw_url = cfg.get("gateway_url", "http://localhost:8000")
    try:
        r = httpx.get(f"{gw_url}/v1/models", timeout=10)
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception:
        return []


def get_model_info(model_name: str) -> dict | None:
    """Get detailed info for a specific model."""
    models = list_models()
    for m in models:
        if m.get("id") == model_name:
            return m
    return None


# ═══════════════════════════════════════════════════════════════
# MCP SERVER MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def list_mcp_servers() -> list[dict]:
    """List connected MCP servers."""
    cfg = get_config()
    gw_url = cfg.get("gateway_url", "http://localhost:8000")
    try:
        r = httpx.get(
            f"{gw_url}/v1/mcp/servers",
            params={"project_id": "de5f0bac-805f-4e98-a964-5d7bc4a426d2"},
            timeout=5,
        )
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
# BLENDER MCP TOOLS
# ═══════════════════════════════════════════════════════════════

def blender_call(tool_name: str, arguments: dict | None = None) -> dict:
    """Call a Blender MCP tool via the SSE bridge."""
    cfg = get_config()
    mh = cfg.get("mcp_host", "localhost")
    mp = cfg.get("mcp_port", 8456)
    try:
        r = httpx.post(
            f"http://{mh}:{mp}/tools/call",
            json={"name": tool_name, "arguments": arguments or {}},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except httpx.ConnectError:
        return {"error": f"Blender MCP server not running at {mh}:{mp}"}
    except httpx.TimeoutException:
        return {"error": "Blender MCP timeout - Blender may not be responding"}
    except Exception as e:
        return {"error": str(e)}


def blender_get_scene() -> dict:
    """Get Blender scene info."""
    result = blender_call("get_scene_info")
    if "error" in result:
        return result
    try:
        import json
        content = result.get("content", [])
        if isinstance(content, list) and content:
            return json.loads(content[0].get("text", "{}"))
    except Exception:
        pass
    return {"error": "Failed to parse scene info"}


def blender_exec(code: str) -> dict:
    """Execute Python code in Blender."""
    result = blender_call("execute_code", {"code": code})
    if "error" in result:
        return result
    try:
        import json
        content = result.get("content", [])
        if isinstance(content, list) and content:
            return json.loads(content[0].get("text", "{}"))
    except Exception:
        pass
    return {"error": "Failed to parse execution result"}


# ═══════════════════════════════════════════════════════════════
# ROUTING STRATEGIES
# ═══════════════════════════════════════════════════════════════

ROUTING_STRATEGIES = [
    {
        "name": "cost_optimized",
        "description": "Route to the cheapest provider for each model",
        "default": True,
    },
    {
        "name": "latency_optimized",
        "description": "Route to the fastest provider based on response time",
        "default": False,
    },
    {
        "name": "quality_first",
        "description": "Route to the highest quality provider regardless of cost",
        "default": False,
    },
    {
        "name": "round_robin",
        "description": "Distribute requests evenly across available providers",
        "default": False,
    },
    {
        "name": "semantic",
        "description": "Route based on task type (code, creative, analysis, etc.)",
        "default": False,
    },
    {
        "name": "learned",
        "description": "ML-based routing using historical performance data",
        "default": False,
    },
]
