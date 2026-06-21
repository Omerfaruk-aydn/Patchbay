"""Tools - File operations, bash execution, and code search.

Each tool is a function that takes keyword arguments and returns a dict.
Success returns {"result": ...}, failure returns {"error": "..."}.

Tool definitions are exported as TOOLS_SPEC for the LLM API.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════
# TOOL IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════

def read_file(path: str, offset: int = 0, limit: int = 200) -> dict[str, Any]:
    """Read a file's contents with line numbers.

    Args:
        path: Absolute or relative file path
        offset: Line number to start from (0-indexed)
        limit: Maximum number of lines to read

    Returns:
        Dict with 'content', 'total_lines', 'offset', 'path' keys
    """
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if not p.is_file():
        return {"error": f"Not a file: {path} ({'dir' if p.is_dir() else 'unknown'})"}
    if p.stat().st_size > 10_000_000:  # 10MB limit
        return {"error": f"File too large ({p.stat().st_size / 1_000_000:.1f}MB). Use offset/limit to read sections."}

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        total = len(lines)
        sliced = lines[offset : offset + limit]

        # Add line numbers
        numbered = []
        for i, line in enumerate(sliced, start=offset + 1):
            numbered.append(f"{i:>4} | {line}")

        return {
            "content": "\n".join(numbered),
            "raw_content": "\n".join(sliced),
            "total_lines": total,
            "offset": offset,
            "limit": limit,
            "path": str(p),
        }
    except PermissionError:
        return {"error": f"Permission denied: {path}"}
    except Exception as e:
        return {"error": f"Read error: {e}"}


def write_file(path: str, content: str, append: bool = False) -> dict[str, Any]:
    """Write content to a file. Creates parent directories if needed.

    Args:
        path: File path to write to
        content: Content to write
        append: If True, append instead of overwrite

    Returns:
        Dict with 'success', 'path', 'bytes_written' keys
    """
    p = Path(path).resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(p, mode, encoding="utf-8") as f:
            f.write(content)
        return {
            "success": True,
            "path": str(p),
            "bytes_written": len(content.encode("utf-8")),
            "append": append,
        }
    except PermissionError:
        return {"error": f"Permission denied: {path}"}
    except Exception as e:
        return {"error": f"Write error: {e}"}


def edit_file(path: str, old_string: str, new_string: str) -> dict[str, Any]:
    """Replace an exact string in a file. The old_string must match exactly.

    Args:
        path: File path to edit
        old_string: Exact string to find (including whitespace)
        new_string: Replacement string

    Returns:
        Dict with 'success', 'path' keys
    """
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}

    try:
        content = p.read_text(encoding="utf-8")

        if old_string not in content:
            # Try to help the user
            similar_lines = [
                line.strip()
                for line in content.split("\n")
                if any(word in line for word in old_string.split()[:3])
            ][:5]
            hint = ""
            if similar_lines:
                hint = f"\nSimilar lines found:\n" + "\n".join(f"  - {l}" for l in similar_lines)
            return {"error": f"old_string not found in {path}{hint}"}

        count = content.count(old_string)
        if count > 1:
            return {
                "error": f"Found {count} occurrences. Provide more surrounding context to make it unique.",
                "occurrences": count,
            }

        new_content = content.replace(old_string, new_string, 1)
        p.write_text(new_content, encoding="utf-8")
        return {"success": True, "path": str(p), "replacements": 1}
    except PermissionError:
        return {"error": f"Permission denied: {path}"}
    except Exception as e:
        return {"error": f"Edit error: {e}"}


def run_bash(command: str, timeout: int = 30, cwd: str | None = None) -> dict[str, Any]:
    """Execute a shell command and return stdout/stderr.

    Args:
        command: Shell command to execute
        timeout: Timeout in seconds (default 30)
        cwd: Working directory (default: current)

    Returns:
        Dict with 'stdout', 'stderr', 'returncode' keys
    """
    working_dir = cwd or os.getcwd()
    if not Path(working_dir).exists():
        return {"error": f"Working directory not found: {working_dir}"}

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir,
            encoding="utf-8",
            errors="replace",
        )
        return {
            "stdout": result.stdout[-8000:] if result.stdout else "",
            "stderr": result.stderr[-4000:] if result.stderr else "",
            "returncode": result.returncode,
            "success": result.returncode == 0,
            "command": command,
            "cwd": working_dir,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s: {command}"}
    except PermissionError:
        return {"error": f"Permission denied: {command}"}
    except Exception as e:
        return {"error": f"Execution error: {e}"}


def search_files(pattern: str, path: str = ".", ignore_dirs: str = "node_modules,.git,__pycache__,.venv,venv") -> dict[str, Any]:
    """Find files matching a glob pattern.

    Args:
        pattern: Glob pattern (e.g. **/*.py, src/**/*.ts)
        path: Directory to search in
        ignore_dirs: Comma-separated directories to ignore

    Returns:
        Dict with 'files', 'total' keys
    """
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"Directory not found: {path}"}

    ignore_set = set(ignore_dirs.split(","))

    try:
        matches = []
        for f in p.glob(pattern):
            if f.is_file():
                # Check if any parent is in ignore set
                rel = f.relative_to(p)
                parts = set(rel.parts)
                if not parts & ignore_set:
                    matches.append(str(rel))
                    if len(matches) >= 200:
                        break
        matches.sort()
        return {"files": matches, "total": len(matches)}
    except Exception as e:
        return {"error": f"Search error: {e}"}


def search_content(
    pattern: str,
    path: str = ".",
    include: str = "*",
    ignore_dirs: str = "node_modules,.git,__pycache__,.venv,venv",
    max_results: int = 50,
) -> dict[str, Any]:
    """Search file contents using regex.

    Args:
        pattern: Regex pattern to search for
        path: Directory to search in
        include: File glob to include (e.g. *.py, *.{ts,tsx})
        ignore_dirs: Comma-separated directories to ignore
        max_results: Maximum number of results

    Returns:
        Dict with 'matches', 'total' keys
    """
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"Directory not found: {path}"}

    ignore_set = set(ignore_dirs.split(","))

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return {"error": f"Invalid regex: {e}"}

    results = []
    try:
        for file_path in p.rglob(include):
            if not file_path.is_file():
                continue
            if len(results) >= max_results:
                break

            # Check ignore dirs
            rel = file_path.relative_to(p)
            if set(rel.parts) & ignore_set:
                continue

            # Skip binary files
            try:
                if file_path.stat().st_size > 1_000_000:
                    continue
            except Exception:
                continue

            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
                for line_num, line in enumerate(text.split("\n"), 1):
                    if regex.search(line):
                        results.append({
                            "file": str(rel),
                            "line": line_num,
                            "content": line.strip()[:300],
                        })
                        if len(results) >= max_results:
                            break
            except Exception:
                continue

    except Exception as e:
        return {"error": f"Search error: {e}"}

    return {"matches": results, "total": len(results)}


def list_directory(path: str = ".", show_hidden: bool = False) -> dict[str, Any]:
    """List contents of a directory.

    Args:
        path: Directory path
        show_hidden: Whether to show hidden files

    Returns:
        Dict with 'path', 'entries' keys
    """
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"Directory not found: {path}"}
    if not p.is_dir():
        return {"error": f"Not a directory: {path}"}

    entries = []
    try:
        for item in sorted(p.iterdir()):
            if not show_hidden and item.name.startswith("."):
                continue
            kind = "dir" if item.is_dir() else "file"
            size = 0
            if item.is_file():
                try:
                    size = item.stat().st_size
                except Exception:
                    pass
            entries.append({"name": item.name, "type": kind, "size": size})
    except PermissionError:
        return {"error": f"Permission denied: {path}"}
    except Exception as e:
        return {"error": f"List error: {e}"}

    return {"path": str(p), "entries": entries[:300]}


# ═══════════════════════════════════════════════════════════════
# TOOL REGISTRY
# ═══════════════════════════════════════════════════════════════

TOOL_MAP: dict[str, Any] = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "run_bash": run_bash,
    "search_files": search_files,
    "search_content": search_content,
    "list_directory": list_directory,
}


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute a tool by name with given arguments.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        Tool result dict
    """
    func = TOOL_MAP.get(name)
    if not func:
        return {"error": f"Unknown tool: {name}. Available: {', '.join(TOOL_MAP.keys())}"}
    try:
        return func(**arguments)
    except TypeError as e:
        return {"error": f"Invalid arguments for {name}: {e}"}
    except Exception as e:
        return {"error": f"Tool execution error: {e}"}


# ═══════════════════════════════════════════════════════════════
# LLM TOOL DEFINITIONS (OpenAI function calling format)
# ═══════════════════════════════════════════════════════════════

TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read a file's contents with line numbers. "
                "Use offset and limit for large files. "
                "Returns content with line numbers prefixed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to read (absolute or relative)",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Line number to start from (0-indexed). Default 0.",
                        "default": 0,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum lines to read. Default 200.",
                        "default": 200,
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write content to a file. Creates parent directories if needed. "
                "Use this for new files or complete rewrites. "
                "For partial edits, prefer edit_file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to write to",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write",
                    },
                    "append": {
                        "type": "boolean",
                        "description": "Append instead of overwrite. Default false.",
                        "default": False,
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Replace an exact string in a file. "
                "The old_string must match exactly (including whitespace and indentation). "
                "If multiple matches found, provides an error - use more context. "
                "Preferred over write_file for partial changes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to edit",
                    },
                    "old_string": {
                        "type": "string",
                        "description": "Exact string to find and replace (including whitespace)",
                    },
                    "new_string": {
                        "type": "string",
                        "description": "Replacement string",
                    },
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bash",
            "description": (
                "Execute a shell command and return stdout/stderr. "
                "Use for running tests, linting, git commands, build tools, etc. "
                "Default timeout is 30 seconds."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds. Default 30.",
                        "default": 30,
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": (
                "Find files matching a glob pattern. "
                "Examples: **/*.py, src/**/*.ts, **/test_*.py"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern to match files",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in. Default: current directory.",
                        "default": ".",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_content",
            "description": (
                "Search file contents using regex. "
                "Returns matching lines with file paths and line numbers. "
                "Useful for finding function definitions, variable usage, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regex pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in. Default: current directory.",
                        "default": ".",
                    },
                    "include": {
                        "type": "string",
                        "description": "File glob to include (e.g. *.py, *.{ts,tsx}). Default: *",
                        "default": "*",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List contents of a directory. Shows files and subdirectories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path. Default: current directory.",
                        "default": ".",
                    },
                },
            },
        },
    },
]
