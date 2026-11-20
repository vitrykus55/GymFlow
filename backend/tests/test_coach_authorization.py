from typing import Any

import pytest
from fastapi import HTTPException

from app.api.deps import get_current_coach
from app.models.enums import UserRole
from app.models.user import User


class CoachAuthorizationSession:
    def __init__(self, *, has_active_membership: bool) -> None:
        self.has_active_membership = has_active_membership

    def scalar(self, statement: Any) -> int | None:
        return 1 if self.has_active_membership else None


def _user(*, role: UserRole) -> User:
    return User(
        id=1,
        email="coach@example.com",
        password_hash="password-hash",
        first_name="Coach",
        last_name="User",
        role=role,
        is_active=True,
    )


def test_active_coach_membership_authorizes_coach() -> None:
    user = _user(role=UserRole.COACH)
    db = CoachAuthorizationSession(has_active_membership=True)

    assert get_current_coach(user, db) is user


def test_regular_user_cannot_access_coach_functionality() -> None:
    user = _user(role=UserRole.CLIENT)
    db = CoachAuthorizationSession(has_active_membership=True)

    with pytest.raises(HTTPException) as exception:
        get_current_coach(user, db)

    assert exception.value.status_code == 403
    assert exception.value.detail == "Coach status is required."


@pytest.mark.parametrize("reason", ["inactive", "expired", "cancelled"])
def test_coach_without_current_active_membership_is_rejected(reason: str) -> None:
    user = _user(role=UserRole.COACH)
    db = CoachAuthorizationSession(has_active_membership=False)

    with pytest.raises(HTTPException) as exception:
        get_current_coach(user, db)

    assert exception.value.status_code == 403
    assert exception.value.detail == "An active Coach Membership is required."
