"""Tools for the AI assistant - file ops, bash, search."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file's contents with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "offset": {"type": "integer", "default": 0},
                    "limit": {"type": "integer", "default": 200},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates parent dirs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "append": {"type": "boolean", "default": False},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace exact string in file (must match exactly).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Execute a shell command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer", "default": 30},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Find files by glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string", "default": "."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_content",
            "description": "Search file contents with regex.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string", "default": "."},
                    "include": {"type": "string", "default": "*"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List directory contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "default": "."},
                },
            },
        },
    },
]


def read_file(path: str, offset: int = 0, limit: int = 200) -> dict:
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if not p.is_file():
        return {"error": f"Not a file: {path}"}
    content = p.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")
    sliced = lines[offset : offset + limit]
    return {"content": "\n".join(sliced), "total_lines": len(lines), "offset": offset}


def write_file(path: str, content: str, append: bool = False) -> dict:
    p = Path(path).resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a" if append else "w", encoding="utf-8") as f:
        f.write(content)
    return {"success": True, "path": str(p)}


def edit_file(path: str, old_string: str, new_string: str) -> dict:
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"Not found: {path}"}
    content = p.read_text(encoding="utf-8")
    if old_string not in content:
        return {"error": "old_string not found"}
    if content.count(old_string) > 1:
        return {"error": f"{content.count(old_string)} matches - provide more context"}
    p.write_text(content.replace(old_string, new_string, 1), encoding="utf-8")
    return {"success": True}


def run_bash(command: str, timeout: int = 30, cwd: str | None = None) -> dict:
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True,
                           timeout=timeout, cwd=cwd or os.getcwd(),
                           encoding="utf-8", errors="replace")
        return {
            "stdout": r.stdout[-4000:] if r.stdout else "",
            "stderr": r.stderr[-2000:] if r.stderr else "",
            "returncode": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Timeout after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}


def search_files(pattern: str, path: str = ".") -> dict:
    p = Path(path).resolve()
    matches = sorted(str(f.relative_to(p)) for f in p.glob(pattern) if f.is_file())
    return {"files": matches[:100], "total": len(matches)}


def search_content(pattern: str, path: str = ".", include: str = "*") -> dict:
    import re
    p = Path(path).resolve()
    results = []
    regex = re.compile(pattern, re.IGNORECASE)
    for fp in p.rglob(include):
        if fp.is_file() and "node_modules" not in str(fp) and ".git" not in str(fp):
            try:
                for i, line in enumerate(fp.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
                    if regex.search(line):
                        results.append({"file": str(fp.relative_to(p)), "line": i, "content": line.strip()[:200]})
                        if len(results) >= 50:
                            break
            except Exception:
                continue
        if len(results) >= 50:
            break
    return {"matches": results}


def list_directory(path: str = ".") -> dict:
    p = Path(path).resolve()
    entries = []
    for item in sorted(p.iterdir()):
        entries.append({"name": item.name, "type": "dir" if item.is_dir() else "file"})
    return {"entries": entries[:200]}


TOOL_MAP = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "run_bash": run_bash,
    "search_files": search_files,
    "search_content": search_content,
    "list_directory": list_directory,
}


def execute_tool(name: str, arguments: dict) -> dict:
    func = TOOL_MAP.get(name)
    if not func:
        return {"error": f"Unknown tool: {name}"}
    return func(**arguments)
