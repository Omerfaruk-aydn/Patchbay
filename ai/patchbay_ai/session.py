"""Session - Conversation history management."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


SESSION_DIR = Path.home() / ".patchbay-ai" / "sessions"


def get_session_dir() -> Path:
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_DIR


def save_session(session_id: str, messages: list[dict], metadata: dict | None = None):
    """Save conversation to disk."""
    session_file = get_session_dir() / f"{session_id}.json"
    data = {
        "id": session_id,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": messages,
        "metadata": metadata or {},
    }
    session_file.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def load_session(session_id: str) -> dict[str, Any] | None:
    """Load a conversation from disk."""
    session_file = get_session_dir() / f"{session_id}.json"
    if session_file.exists():
        return json.loads(session_file.read_text())
    return None


def list_sessions() -> list[dict]:
    """List all saved sessions."""
    sessions = []
    for f in get_session_dir().glob("*.json"):
        try:
            data = json.loads(f.read_text())
            sessions.append({
                "id": data.get("id", f.stem),
                "created_at": data.get("created_at", ""),
                "updated_at": data.get("updated_at", ""),
                "message_count": len(data.get("messages", [])),
            })
        except Exception:
            continue
    sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return sessions


def delete_session(session_id: str) -> bool:
    """Delete a session."""
    session_file = get_session_dir() / f"{session_id}.json"
    if session_file.exists():
        session_file.unlink()
        return True
    return False
