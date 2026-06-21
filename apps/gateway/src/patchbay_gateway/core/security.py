"""Security utilities — virtual key generation, verification, and JWT tokens.

Key lifecycle:
  1. generate_virtual_key() → (raw_key, key_hash, prefix)
  2. raw_key shown to user ONCE (GitHub PAT pattern)
  3. key_hash stored in database
  4. verify_virtual_key() checks incoming key against stored hash

JWT tokens are used for dashboard authentication (not API auth).
API authentication uses virtual key hashing.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from patchbay_gateway.core.config import get_settings


def generate_virtual_key() -> tuple[str, str, str]:
    """Generate a new virtual API key.

    Returns:
        Tuple of (raw_key_for_user, hash_for_db, prefix_for_ui_display).

    The raw key follows the format: pk_live_{random}
    The hash is bcrypt with auto-generated salt.
    The prefix is the first 12 characters + "..." for UI display.
    """
    raw = f"pk_live_{secrets.token_urlsafe(32)}"
    key_hash = bcrypt.hashpw(raw.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    prefix = raw[:12] + "..."
    return raw, key_hash, prefix


def verify_virtual_key(raw_key: str, key_hash: str) -> bool:
    """Verify a virtual key against its stored bcrypt hash.

    Returns True if the key matches, False otherwise.
    Uses constant-time comparison internally (bcrypt).
    """
    try:
        return bcrypt.checkpw(raw_key.encode("utf-8"), key_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token for dashboard authentication.

    Args:
        data: Payload data (typically {"sub": user_id, "org_id": org_id}).
        expires_delta: Custom expiration time. Defaults to configured value.

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    })
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token.

    Returns:
        Payload dict if valid, None if expired or invalid.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None
