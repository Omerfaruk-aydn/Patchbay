from __future__ import annotations

import bcrypt
import secrets

from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone

from patchbay_gateway.core.config import get_settings


def generate_virtual_key() -> tuple[str, str, str]:
    """Generate a virtual key.

    Returns: (raw_key_for_user, hash_for_db, prefix_for_ui)
    """
    raw = f"pk_live_{secrets.token_urlsafe(32)}"
    key_hash = bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()
    prefix = raw[:12] + "..."
    return raw, key_hash, prefix


def verify_virtual_key(raw_key: str, key_hash: str) -> bool:
    """Verify a virtual key against its stored hash."""
    return bcrypt.checkpw(raw_key.encode(), key_hash.encode())


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token. Returns payload or None."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
