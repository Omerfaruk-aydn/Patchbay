"""Session - Conversation persistence and management.

Stores conversations as JSON files in ~/.patchbay/sessions/.
Supports save, load, list, delete operations.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

SESSION_DIR = Path.home() / ".patchbay" / "sessions"


def _ensure_dir() -> Path:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_DIR


def save_session(session_id: str, messages: list[dict], metadata: dict | None = None) -> None:
    """Save a conversation to disk.

    Args:
        session_id: Unique session identifier
        messages: Conversation messages
        metadata: Optional metadata (provider, model, etc.)
    """
    _ensure_dir()
    session_file = SESSION_DIR / f"{session_id}.json"
    data = {
        "id": session_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "message_count": len(messages),
        "messages": messages,
        "metadata": metadata or {},
    }
    session_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_session(session_id: str) -> dict[str, Any] | None:
    """Load a conversation from disk.

    Args:
        session_id: Session identifier

    Returns:
        Session data dict or None if not found
    """
    session_file = SESSION_DIR / f"{session_id}.json"
    if session_file.exists():
        try:
            return json.loads(session_file.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def list_sessions(limit: int = 20) -> list[dict]:
    """List all saved sessions, most recent first.

    Args:
        limit: Maximum number of sessions to return

    Returns:
        List of session summary dicts
    """
    _ensure_dir()
    sessions = []
    for f in SESSION_DIR.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append({
                "id": data.get("id", f.stem),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
                "count": len(data.get("messages", [])),
                "metadata": data.get("metadata", {}),
            })
        except Exception:
            continue
    sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return sessions[:limit]


def delete_session(session_id: str) -> bool:
    """Delete a session.

    Args:
        session_id: Session identifier

    Returns:
        True if deleted, False if not found
    """
    session_file = SESSION_DIR / f"{session_id}.json"
    if session_file.exists():
        session_file.unlink()
        return True
    return False


def update_session(session_id: str, messages: list[dict]) -> None:
    """Update an existing session's messages and timestamp.

    Args:
        session_id: Session identifier
        messages: Updated messages
    """
    session_file = SESSION_DIR / f"{session_id}.json"
    if session_file.exists():
        try:
            data = json.loads(session_file.read_text(encoding="utf-8"))
            data["messages"] = messages
            data["updated_at"] = datetime.now().isoformat()
            data["message_count"] = len(messages)
            session_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
