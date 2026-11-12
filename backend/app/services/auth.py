from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
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


def login_user(db: Session, login: LoginRequest) -> str:
    """Validate credentials and return an access token for an active user."""
    email = login.email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None or not verify_password(login.password, user.password_hash):
        raise InvalidCredentialsError
    if not user.is_active:
        raise InactiveUserError
    return create_access_token(user.id)


def _is_duplicate_email_error(error: IntegrityError) -> bool:
    original_error = error.orig
    diagnostics = getattr(original_error, "diag", None)
    return (
        getattr(original_error, "sqlstate", None) == "23505"
        and getattr(diagnostics, "constraint_name", None) == EMAIL_UNIQUE_CONSTRAINT
    )
