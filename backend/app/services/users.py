from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.users import UpdateUserProfileRequest
from app.services.auth import EMAIL_UNIQUE_CONSTRAINT, EmailAlreadyRegisteredError


def update_user_profile(
    db: Session,
    user: User,
    profile_update: UpdateUserProfileRequest,
) -> User:
    """Apply an authenticated user's explicitly supplied profile fields."""
    updates = profile_update.model_dump(exclude_unset=True)
    email = updates.get("email")
    if email is not None:
        existing_user_id = db.scalar(
            select(User.id).where(func.lower(User.email) == email, User.id != user.id)
        )
        if existing_user_id is not None:
            raise EmailAlreadyRegisteredError

    for field_name, value in updates.items():
        setattr(user, field_name, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if _is_duplicate_email_error(exc):
            raise EmailAlreadyRegisteredError from exc
        raise

    db.refresh(user)
    return user


def _is_duplicate_email_error(error: IntegrityError) -> bool:
    original_error = error.orig
    diagnostics = getattr(original_error, "diag", None)
    return (
        getattr(original_error, "sqlstate", None) == "23505"
        and getattr(diagnostics, "constraint_name", None) == EMAIL_UNIQUE_CONSTRAINT
    )
