"""Tools - File operations, bash execution, code search for the AI assistant."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def read_file(path: str, offset: int = 0, limit: int = 200) -> dict[str, Any]:
    """Read a file's contents."""
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if not p.is_file():
        return {"error": f"Not a file: {path}"}

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        total = len(lines)
        sliced = lines[offset : offset + limit]
        return {
            "content": "\n".join(sliced),
            "total_lines": total,
            "offset": offset,
            "limit": limit,
            "path": str(p),
        }
    except Exception as e:
        return {"error": str(e)}


def write_file(path: str, content: str, append: bool = False) -> dict[str, Any]:
    """Write content to a file."""
    p = Path(path).resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(p, mode, encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "path": str(p), "bytes": len(content.encode())}
    except Exception as e:
        return {"error": str(e)}


def edit_file(path: str, old_string: str, new_string: str) -> dict[str, Any]:
    """Replace exact string in file."""
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}

    try:
        content = p.read_text(encoding="utf-8")
        if old_string not in content:
            return {"error": "old_string not found in file"}

        count = content.count(old_string)
        if count > 1:
            return {"error": f"Found {count} occurrences. Provide more context."}

        new_content = content.replace(old_string, new_string, 1)
        p.write_text(new_content, encoding="utf-8")
        return {"success": True, "path": str(p)}
    except Exception as e:
        return {"error": str(e)}


def run_bash(command: str, timeout: int = 30, cwd: str | None = None) -> dict[str, Any]:
    """Execute a bash/shell command."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or os.getcwd(),
            encoding="utf-8",
            errors="replace",
        )
        return {
            "stdout": result.stdout[-4000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
            "returncode": result.returncode,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}


def search_files(pattern: str, path: str = ".") -> dict[str, Any]:
    """Search for files matching a glob pattern."""
    p = Path(path).resolve()
    try:
        matches = sorted(str(f.relative_to(p)) for f in p.glob(pattern) if f.is_file())
        return {"files": matches[:100], "total": len(matches)}
    except Exception as e:
        return {"error": str(e)}


def search_content(pattern: str, path: str = ".", include: str = "*") -> dict[str, Any]:
    """Search file contents using grep-like matching."""
    import re

    p = Path(path).resolve()
    results = []
    try:
        regex = re.compile(pattern, re.IGNORECASE)
        for file_path in p.rglob(include):
            if file_path.is_file() and "node_modules" not in str(file_path) and ".git" not in str(file_path):
                try:
                    text = file_path.read_text(encoding="utf-8", errors="replace")
                    for i, line in enumerate(text.split("\n"), 1):
                        if regex.search(line):
                            results.append({
                                "file": str(file_path.relative_to(p)),
                                "line": i,
                                "content": line.strip()[:200],
                            })
                            if len(results) >= 50:
                                break
                except Exception:
                    continue
            if len(results) >= 50:
                break
    except re.error:
        return {"error": f"Invalid regex: {pattern}"}

    return {"matches": results, "total": len(results)}


def list_directory(path: str = ".") -> dict[str, Any]:
    """List directory contents."""
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"Directory not found: {path}"}
    if not p.is_dir():
        return {"error": f"Not a directory: {path}"}

    entries = []
    try:
        for item in sorted(p.iterdir()):
            kind = "dir" if item.is_dir() else "file"
            size = item.stat().st_size if item.is_file() else 0
            entries.append({"name": item.name, "type": kind, "size": size})
    except PermissionError:
        return {"error": "Permission denied"}

    return {"path": str(p), "entries": entries[:200]}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file's contents. Returns lines with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to read"},
                    "offset": {"type": "integer", "description": "Line number to start from (0-indexed)", "default": 0},
                    "limit": {"type": "integer", "description": "Max lines to read", "default": 200},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file. Creates parent directories if needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write to"},
                    "content": {"type": "string", "description": "Content to write"},
                    "append": {"type": "boolean", "description": "Append instead of overwrite", "default": False},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace an exact string in a file. The old_string must match exactly (including whitespace).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to edit"},
                    "old_string": {"type": "string", "description": "Exact string to find and replace"},
                    "new_string": {"type": "string", "description": "Replacement string"},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": "Execute a shell command and return stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Find files matching a glob pattern (e.g. **/*.py, src/**/*.ts).",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern"},
                    "path": {"type": "string", "description": "Directory to search in", "default": "."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_content",
            "description": "Search file contents using regex. Returns matching lines with file paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "path": {"type": "string", "description": "Directory to search in", "default": "."},
                    "include": {"type": "string", "description": "File glob to include (e.g. *.py)", "default": "*"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List contents of a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path", "default": "."},
                },
            },
        },
    },
]

TOOL_MAP = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "run_bash": run_bash,
    "search_files": search_files,
    "search_content": search_content,
    "list_directory": list_directory,
}


def execute_tool(name: str, arguments: dict) -> dict[str, Any]:
    """Execute a tool by name with given arguments."""
    func = TOOL_MAP.get(name)
    if not func:
        return {"error": f"Unknown tool: {name}"}
    return func(**arguments)
