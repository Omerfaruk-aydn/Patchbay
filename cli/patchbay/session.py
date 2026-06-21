"""Session persistence."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

SESSION_DIR = Path.home() / ".patchbay" / "sessions"


def _dir():
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    return SESSION_DIR


def save(sid: str, messages: list[dict]):
    f = _dir() / f"{sid}.json"
    f.write_text(json.dumps({"id": sid, "updated": datetime.now().isoformat(),
                             "messages": messages}, indent=2, ensure_ascii=False))


def load(sid: str) -> dict | None:
    f = _dir() / f"{sid}.json"
    return json.loads(f.read_text()) if f.exists() else None


def list_all() -> list[dict]:
    sessions = []
    for f in _dir().glob("*.json"):
        try:
            d = json.loads(f.read_text())
            sessions.append({"id": d["id"], "updated": d.get("updated", ""),
                             "count": len(d.get("messages", []))})
        except Exception:
            pass
    sessions.sort(key=lambda x: x["updated"], reverse=True)
    return sessions
