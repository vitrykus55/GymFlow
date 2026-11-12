from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import InvalidAccessTokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Return the active user identified by a valid bearer access token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        _raise_invalid_credentials()

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = _parse_user_id(payload["sub"])
    except (InvalidAccessTokenError, KeyError, TypeError, ValueError):
        _raise_invalid_credentials()

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        _raise_invalid_credentials()
    return user


def _parse_user_id(subject: str) -> int:
    if not subject.isdecimal():
        raise ValueError("Invalid access token subject.")
    return int(subject)


def _raise_invalid_credentials() -> None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def validate_cookie_auth_origin(request: Request) -> None:
    """Reject cookie-authenticated browser mutations from untrusted origins."""
    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.cors_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid request origin.")
