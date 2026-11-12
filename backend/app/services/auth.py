from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.auth_refresh_token import AuthRefreshToken
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterUserRequest

EMAIL_UNIQUE_CONSTRAINT = "ux_users_email_lower"


class EmailAlreadyRegisteredError(Exception):
    """Raised when an email address is already registered."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials do not identify a user."""


class InactiveUserError(Exception):
    """Raised when an inactive user attempts to log in."""


class InvalidRefreshTokenError(Exception):
    """Raised when a refresh token cannot establish an active session."""


@dataclass(frozen=True)
class AuthTokens:
    access_token: str
    refresh_token: str
    refresh_token_expires_at: datetime


def register_user(db: Session, registration: RegisterUserRequest) -> User:
    """Create a client account while preserving the email uniqueness invariant."""
    email = registration.email.strip().lower()
    existing_user_id = db.scalar(select(User.id).where(func.lower(User.email) == email))
    if existing_user_id is not None:
        raise EmailAlreadyRegisteredError

    user = User(
        email=email,
        password_hash=hash_password(registration.password),
        first_name=registration.first_name,
        last_name=registration.last_name,
        phone=registration.phone,
        birth_date=registration.birth_date,
        role=UserRole.CLIENT,
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_duplicate_email_error(exc):
            raise EmailAlreadyRegisteredError from exc
        raise

    db.refresh(user)
    return user


def login_user(db: Session, login: LoginRequest) -> AuthTokens:
    """Validate credentials and create an independent persisted refresh-token family."""
    email = login.email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None or not verify_password(login.password, user.password_hash):
        raise InvalidCredentialsError
    if not user.is_active:
        raise InactiveUserError
    return _create_login_session(db, user)


def refresh_user_session(db: Session, raw_refresh_token: str) -> AuthTokens:
    """Atomically rotate a refresh token, revoking its family on reuse."""
    refresh_token = db.scalar(
        select(AuthRefreshToken)
        .where(AuthRefreshToken.token_hash == hash_refresh_token(raw_refresh_token))
        .with_for_update()
    )
    if refresh_token is None:
        raise InvalidRefreshTokenError

    now = datetime.now(UTC)
    if refresh_token.revoked_at is not None:
        _revoke_token_family(db, refresh_token.family_id, now)
        _commit_or_rollback(db)
        raise InvalidRefreshTokenError

    user = db.get(User, refresh_token.user_id)
    if user is None or not user.is_active or refresh_token.expires_at <= now:
        _revoke_token_family(db, refresh_token.family_id, now)
        _commit_or_rollback(db)
        raise InvalidRefreshTokenError

    access_token = create_access_token(user.id)
    raw_replacement_token, replacement_token = _build_refresh_token(
        user_id=user.id,
        family_id=refresh_token.family_id,
    )
    db.add(replacement_token)
    try:
        db.flush()
        refresh_token.revoked_at = now
        refresh_token.replaced_by_token_id = replacement_token.id
        db.commit()
    except Exception:
        db.rollback()
        raise

    return AuthTokens(
        access_token=access_token,
        refresh_token=raw_replacement_token,
        refresh_token_expires_at=replacement_token.expires_at,
    )


def logout_refresh_token(db: Session, raw_refresh_token: str | None) -> None:
    """Revoke the presented token family without affecting other user sessions."""
    if raw_refresh_token is None:
        return

    refresh_token = db.scalar(
        select(AuthRefreshToken)
        .where(AuthRefreshToken.token_hash == hash_refresh_token(raw_refresh_token))
        .with_for_update()
    )
    if refresh_token is not None:
        _revoke_token_family(db, refresh_token.family_id, datetime.now(UTC))
    _commit_or_rollback(db)


def _create_login_session(db: Session, user: User) -> AuthTokens:
    access_token = create_access_token(user.id)
    raw_refresh_token, refresh_token = _build_refresh_token(user_id=user.id, family_id=uuid4())
    db.add(refresh_token)
    _commit_or_rollback(db)
    return AuthTokens(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        refresh_token_expires_at=refresh_token.expires_at,
    )


def _build_refresh_token(*, user_id: int, family_id: UUID) -> tuple[str, AuthRefreshToken]:
    raw_refresh_token = generate_refresh_token()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return raw_refresh_token, AuthRefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(raw_refresh_token),
        family_id=family_id,
        expires_at=expires_at,
    )


def _revoke_token_family(db: Session, family_id: UUID, revoked_at: datetime) -> None:
    db.execute(
        update(AuthRefreshToken)
        .where(
            AuthRefreshToken.family_id == family_id,
            AuthRefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=revoked_at)
    )


def _commit_or_rollback(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


def _is_duplicate_email_error(error: IntegrityError) -> bool:
    original_error = error.orig
    diagnostics = getattr(original_error, "diag", None)
    return (
        getattr(original_error, "sqlstate", None) == "23505"
        and getattr(diagnostics, "constraint_name", None) == EMAIL_UNIQUE_CONSTRAINT
    )
