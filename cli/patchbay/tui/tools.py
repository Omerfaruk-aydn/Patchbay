"""Tools - Enhanced tool system for Patchbay CLI.

All 20 tools from the spec:
- File: read_file, write_file, edit_file, patch_file, delete_file, rename_file, copy_file, create_directory
- Search: grep_search, glob_search, list_directory
- Execution: run_bash, run_tests, run_linter, run_formatter
- Git: git_status, git_diff, git_log, git_blame
- Web: web_fetch, web_search
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════
# FILE TOOLS
# ═══════════════════════════════════════════════════════════════

def read_file(path: str, offset: int = 0, limit: int = 200) -> dict:
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if not p.is_file():
        return {"error": f"Not a file: {path}"}
    if p.stat().st_size > 10_000_000:
        return {"error": f"File too large ({p.stat().st_size / 1_000_000:.1f}MB)"}
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        total = len(lines)
        sliced = lines[offset:offset + limit]
        numbered = [f"{i:>4} | {line}" for i, line in enumerate(sliced, start=offset + 1)]
        return {"content": "\n".join(numbered), "total_lines": total, "offset": offset, "path": str(p)}
    except Exception as e:
        return {"error": f"Read error: {e}"}


def write_file(path: str, content: str) -> dict:
    p = Path(path).resolve()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"success": True, "path": str(p), "bytes_written": len(content.encode("utf-8"))}
    except Exception as e:
        return {"error": f"Write error: {e}"}


def edit_file(path: str, old_string: str, new_string: str) -> dict:
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}
    try:
        content = p.read_text(encoding="utf-8")
        if old_string not in content:
            return {"error": f"old_string not found in {path}"}
        count = content.count(old_string)
        if count > 1:
            return {"error": f"Found {count} occurrences. Provide more context."}
        new_content = content.replace(old_string, new_string, 1)
        p.write_text(new_content, encoding="utf-8")
        return {"success": True, "path": str(p)}
    except Exception as e:
        return {"error": f"Edit error: {e}"}


def patch_file(path: str, diff: str) -> dict:
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}
    try:
        content = p.read_text(encoding="utf-8")
        lines = content.split("\n")
        new_lines = []
        i = 0
        for line in diff.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                new_lines.append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                i += 1
            elif line.startswith("@@"):
                continue
            else:
                if i < len(lines):
                    new_lines.append(lines[i])
                    i += 1
        p.write_text("\n".join(new_lines), encoding="utf-8")
        return {"success": True, "path": str(p)}
    except Exception as e:
        return {"error": f"Patch error: {e}"}


def delete_file(path: str) -> dict:
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}
    try:
        if p.is_dir():
            import shutil
            shutil.rmtree(p)
        else:
            p.unlink()
        return {"success": True, "path": str(p)}
    except Exception as e:
        return {"error": f"Delete error: {e}"}


def rename_file(old_path: str, new_path: str) -> dict:
    old = Path(old_path).resolve()
    new = Path(new_path).resolve()
    if not old.exists():
        return {"error": f"File not found: {old_path}"}
    try:
        new.parent.mkdir(parents=True, exist_ok=True)
        old.rename(new)
        return {"success": True, "from": str(old), "to": str(new)}
    except Exception as e:
        return {"error": f"Rename error: {e}"}


def copy_file(src: str, dst: str) -> dict:
    s = Path(src).resolve()
    d = Path(dst).resolve()
    if not s.exists():
        return {"error": f"File not found: {src}"}
    try:
        d.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        if s.is_dir():
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)
        return {"success": True, "from": str(s), "to": str(d)}
    except Exception as e:
        return {"error": f"Copy error: {e}"}


def create_directory(path: str) -> dict:
    p = Path(path).resolve()
    try:
        p.mkdir(parents=True, exist_ok=True)
        return {"success": True, "path": str(p)}
    except Exception as e:
        return {"error": f"Create dir error: {e}"}


# ═══════════════════════════════════════════════════════════════
# SEARCH TOOLS
# ═══════════════════════════════════════════════════════════════

def grep_search(pattern: str, path: str = ".", include: str = "*",
                case_sensitive: bool = False, max_results: int = 100) -> dict:
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"Directory not found: {path}"}
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return {"error": f"Invalid regex: {e}"}
    results = []
    for file_path in p.rglob(include):
        if not file_path.is_file():
            continue
        if len(results) >= max_results:
            break
        try:
            if file_path.stat().st_size > 1_000_000:
                continue
            text = file_path.read_text(encoding="utf-8", errors="replace")
            for line_num, line in enumerate(text.split("\n"), 1):
                if regex.search(line):
                    rel = file_path.relative_to(p)
                    results.append({"file": str(rel), "line": line_num, "content": line.strip()[:200]})
                    if len(results) >= max_results:
                        break
        except Exception:
            continue
    return {"matches": results, "total": len(results)}


def glob_search(pattern: str, path: str = ".", max_results: int = 200) -> dict:
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"Directory not found: {path}"}
    try:
        matches = []
        for f in p.glob(pattern):
            if f.is_file():
                matches.append(str(f.relative_to(p)))
                if len(matches) >= max_results:
                    break
        matches.sort()
        return {"files": matches, "total": len(matches)}
    except Exception as e:
        return {"error": f"Search error: {e}"}


def list_directory(path: str = ".", depth: int = 2, show_hidden: bool = False) -> dict:
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
            if len(entries) >= 300:
                break
    except PermissionError:
        return {"error": f"Permission denied: {path}"}
    return {"path": str(p), "entries": entries[:300]}


# ═══════════════════════════════════════════════════════════════
# EXECUTION TOOLS
# ═══════════════════════════════════════════════════════════════

def run_bash(command: str, timeout: int = 30, cwd: str | None = None) -> dict:
    working_dir = cwd or os.getcwd()
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=working_dir, encoding="utf-8", errors="replace",
        )
        return {
            "stdout": result.stdout[-8000:] if result.stdout else "",
            "stderr": result.stderr[-4000:] if result.stderr else "",
            "returncode": result.returncode,
            "command": command,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s: {command}"}
    except Exception as e:
        return {"error": f"Execution error: {e}"}


def run_tests(pattern: str = "", framework: str = "auto") -> dict:
    cwd = os.getcwd()
    if framework == "auto":
        if Path("pyproject.toml").exists() or Path("setup.py").exists():
            cmd = f"python -m pytest {pattern} -v" if pattern else "python -m pytest -v"
        elif Path("package.json").exists():
            cmd = "npm test"
        elif Path("go.mod").exists():
            cmd = f"go test {pattern} -v" if pattern else "go test ./... -v"
        elif Path("Cargo.toml").exists():
            cmd = "cargo test"
        else:
            return {"error": "No test framework detected"}
    elif framework == "pytest":
        cmd = f"python -m pytest {pattern} -v" if pattern else "python -m pytest -v"
    elif framework == "jest":
        cmd = f"npx jest {pattern}" if pattern else "npm test"
    elif framework == "go":
        cmd = f"go test {pattern} -v" if pattern else "go test ./... -v"
    elif framework == "cargo":
        cmd = "cargo test"
    else:
        return {"error": f"Unknown framework: {framework}"}
    return run_bash(cmd, timeout=120)


def run_linter(path: str = ".") -> dict:
    cwd = os.getcwd()
    if Path("pyproject.toml").exists():
        return run_bash(f"python -m ruff check {path}", timeout=30)
    elif Path("package.json").exists():
        return run_bash(f"npx eslint {path}", timeout=30)
    elif Path("go.mod").exists():
        return run_bash(f"golangci-lint run {path}", timeout=30)
    elif Path("Cargo.toml").exists():
        return run_bash("cargo clippy -- -D warnings", timeout=30)
    return {"error": "No linter config detected"}


def run_formatter(path: str = ".") -> dict:
    if Path("pyproject.toml").exists():
        return run_bash(f"python -m ruff format {path}", timeout=30)
    elif Path("package.json").exists():
        return run_bash(f"npx prettier --write {path}", timeout=30)
    elif Path("go.mod").exists():
        return run_bash(f"gofmt -w {path}", timeout=30)
    elif Path("Cargo.toml").exists():
        return run_bash("cargo fmt", timeout=30)
    return {"error": "No formatter config detected"}


# ═══════════════════════════════════════════════════════════════
# GIT TOOLS
# ═══════════════════════════════════════════════════════════════

def git_status() -> dict:
    return run_bash("git status --short")


def git_diff(path: str = "") -> dict:
    cmd = f"git diff {path}" if path else "git diff"
    return run_bash(cmd)


def git_log(count: int = 10) -> dict:
    return run_bash(f"git log --oneline -{count}")


def git_blame(path: str, start_line: int = 0, end_line: int = 0) -> dict:
    cmd = f"git blame -L {start_line},{end_line} {path}" if start_line and end_line else f"git blame {path}"
    return run_bash(cmd, timeout=10)


# ═══════════════════════════════════════════════════════════════
# WEB TOOLS
# ═══════════════════════════════════════════════════════════════

def web_fetch(url: str, max_length: int = 5000) -> dict:
    try:
        import httpx
        r = httpx.get(url, timeout=10, follow_redirects=True)
        r.raise_for_status()
        text = r.text[:max_length]
        return {"url": url, "status": r.status_code, "content": text}
    except Exception as e:
        return {"error": f"Fetch error: {e}"}


def web_search(query: str, max_results: int = 5) -> dict:
    try:
        import httpx
        r = httpx.get(
            "https://api.tavily.com/search",
            json={"query": query, "max_results": max_results},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return {"error": "Web search requires TAVILY_API_KEY"}


# ═══════════════════════════════════════════════════════════════
# TOOL REGISTRY
# ═══════════════════════════════════════════════════════════════

TOOL_MAP = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "patch_file": patch_file,
    "delete_file": delete_file,
    "rename_file": rename_file,
    "copy_file": copy_file,
    "create_directory": create_directory,
    "grep_search": grep_search,
    "glob_search": glob_search,
    "list_directory": list_directory,
    "run_bash": run_bash,
    "run_tests": run_tests,
    "run_linter": run_linter,
    "run_formatter": run_formatter,
    "git_status": git_status,
    "git_diff": git_diff,
    "git_log": git_log,
    "git_blame": git_blame,
    "web_fetch": web_fetch,
    "web_search": web_search,
    "search_files": glob_search,
    "search_content": grep_search,
}

WRITE_TOOLS = {"write_file", "edit_file", "patch_file", "delete_file", "rename_file", "run_bash"}

TOOL_DEFINITIONS = [
    {"type": "function", "function": {"name": "read_file", "description": "Read file contents with line numbers", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "offset": {"type": "integer", "default": 0}, "limit": {"type": "integer", "default": 200}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write content to a file (creates parent dirs)", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "edit_file", "description": "Replace exact string in file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "old_string": {"type": "string"}, "new_string": {"type": "string"}}, "required": ["path", "old_string", "new_string"]}}},
    {"type": "function", "function": {"name": "run_bash", "description": "Execute shell command", "parameters": {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "integer", "default": 30}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "grep_search", "description": "Search file contents with regex", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string", "default": "."}, "include": {"type": "string", "default": "*"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {"name": "glob_search", "description": "Find files by glob pattern", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string", "default": "."}}, "required": ["pattern"]}}},
    {"type": "function", "function": {"name": "list_directory", "description": "List directory contents", "parameters": {"type": "object", "properties": {"path": {"type": "string", "default": "."}}}}},
    {"type": "function", "function": {"name": "run_tests", "description": "Run project tests (auto-detects framework)", "parameters": {"type": "object", "properties": {"pattern": {"type": "string", "default": ""}, "framework": {"type": "string", "default": "auto"}}}}},
    {"type": "function", "function": {"name": "run_linter", "description": "Run linter on project", "parameters": {"type": "object", "properties": {"path": {"type": "string", "default": "."}}}}},
    {"type": "function", "function": {"name": "run_formatter", "description": "Run code formatter", "parameters": {"type": "object", "properties": {"path": {"type": "string", "default": "."}}}}},
    {"type": "function", "function": {"name": "git_status", "description": "Show git status", "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "git_diff", "description": "Show git diff", "parameters": {"type": "object", "properties": {"path": {"type": "string", "default": ""}}}}},
    {"type": "function", "function": {"name": "git_log", "description": "Show recent git commits", "parameters": {"type": "object", "properties": {"count": {"type": "integer", "default": 10}}}}},
    {"type": "function", "function": {"name": "web_fetch", "description": "Fetch content from URL", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
    {"type": "function", "function": {"name": "patch_file", "description": "Apply unified diff to file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "diff": {"type": "string"}}, "required": ["path", "diff"]}}},
    {"type": "function", "function": {"name": "delete_file", "description": "Delete a file or directory", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "rename_file", "description": "Rename a file", "parameters": {"type": "object", "properties": {"old_path": {"type": "string"}, "new_path": {"type": "string"}}, "required": ["old_path", "new_path"]}}},
    {"type": "function", "function": {"name": "copy_file", "description": "Copy a file or directory", "parameters": {"type": "object", "properties": {"src": {"type": "string"}, "dst": {"type": "string"}}, "required": ["src", "dst"]}}},
    {"type": "function", "function": {"name": "create_directory", "description": "Create a directory", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "git_blame", "description": "Show git blame for file", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "start_line": {"type": "integer", "default": 0}, "end_line": {"type": "integer", "default": 0}}, "required": ["path"]}}},
]


def execute_tool(name: str, arguments: dict) -> dict:
    func = TOOL_MAP.get(name)
    if not func:
        return {"error": f"Unknown tool: {name}. Available: {', '.join(TOOL_MAP.keys())}"}
    try:
        return func(**arguments)
    except TypeError as e:
        return {"error": f"Invalid arguments for {name}: {e}"}
    except Exception as e:
        return {"error": f"Tool error: {e}"}
