from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


class InvalidAccessTokenError(ValueError):
    """Raised when an access token cannot be validated."""


def hash_password(password: str) -> str:
    """Return an Argon2id password hash."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return whether a plaintext password matches its stored hash."""
    return password_hash.verify(plain_password, hashed_password)


def hash_refresh_token(token: str) -> str:
    """Return the SHA-256 digest used to persist an opaque refresh token."""
    return sha256(token.encode("utf-8")).hexdigest()


def generate_refresh_token() -> str:
    """Return a URL-safe opaque token backed by 256 bits of randomness."""
    return token_urlsafe(32)


def create_access_token(user_id: int) -> str:
    """Create a signed, short-lived access token for a user."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, _get_jwt_secret_key(), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode a valid access token or raise a safe validation error."""
    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret_key(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "iat", "exp"]},
        )
    except jwt.InvalidTokenError as exc:
        raise InvalidAccessTokenError("Invalid access token.") from exc

    if not isinstance(payload.get("sub"), str):
        raise InvalidAccessTokenError("Invalid access token.")

    return payload


def _get_jwt_secret_key() -> str:
    if settings.jwt_secret_key is None:
        raise RuntimeError("JWT_SECRET_KEY must be configured before issuing access tokens.")
    return settings.jwt_secret_key.get_secret_value()
