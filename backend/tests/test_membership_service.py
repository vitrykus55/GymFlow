from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.models.enums import MembershipStatus, UserRole
from app.models.membership import Membership
from app.models.membership_type import MembershipType
from app.models.user import User
from app.services.memberships import (
    MembershipLifecycleError,
    activate_coach_membership,
    cancel_membership,
    create_membership,
    expire_memberships,
    has_active_coach_membership,
    is_membership_active,
)


class InMemoryMembershipLifecycleSession:
    def __init__(self) -> None:
        self.user = User(
            id=1,
            email="ada@example.com",
            password_hash="password-hash",
            first_name="Ada",
            last_name="Lovelace",
            role=UserRole.CLIENT,
            is_active=True,
        )
        self.coach_type = MembershipType(
            id=1,
            code="coach",
            name="Coach Membership",
            description=None,
            duration_days=None,
            price=None,
            max_entries=None,
            is_active=True,
        )
        self.memberships: list[Membership] = []
        self.expired_memberships: list[Membership] = []
        self.active_membership: Membership | None = None
        self.active_coach_membership_id: int | None = None
        self.commit_calls = 0
        self.rollback_calls = 0
        self.fail_commit = False

    def get(self, model: type[Any], entity_id: int) -> User | Membership | None:
        if model is User:
            return self.user if entity_id == self.user.id else None
        if model is Membership:
            return next(
                (membership for membership in self.memberships if membership.id == entity_id), None
            )
        raise AssertionError(f"Unexpected model: {model}")

    def scalar(self, statement: Any) -> MembershipType | Membership | int | None:
        entity = statement.column_descriptions[0]["entity"]
        if entity is MembershipType:
            return self.coach_type
        if entity is Membership:
            if statement.column_descriptions[0]["name"] == "id":
                return self.active_coach_membership_id
            return self.active_membership
        raise AssertionError(f"Unexpected statement: {statement}")

    def scalars(self, statement: Any) -> list[Membership]:
        return self.expired_memberships

    def add(self, membership: Membership) -> None:
        membership.id = len(self.memberships) + 1
        self.memberships.append(membership)

    def commit(self) -> None:
        self.commit_calls += 1
        if self.fail_commit:
            raise RuntimeError("database unavailable")

    def rollback(self) -> None:
        self.rollback_calls += 1


def _interval() -> tuple[datetime, datetime]:
    starts_at = datetime(2026, 11, 20, 12, tzinfo=UTC)
    return starts_at, starts_at + timedelta(days=30)


def test_create_membership_creates_pending_entitlement() -> None:
    db = InMemoryMembershipLifecycleSession()
    starts_at, expires_at = _interval()

    membership = create_membership(
        db,
        user_id=db.user.id,
        membership_type=db.coach_type,
        starts_at=starts_at,
        expires_at=expires_at,
    )

    assert membership.status is MembershipStatus.PENDING
    assert membership.starts_at == starts_at
    assert membership.expires_at == expires_at
    assert db.commit_calls == 1


def test_activate_coach_membership_creates_active_membership_and_coach_role() -> None:
    db = InMemoryMembershipLifecycleSession()
    starts_at, expires_at = _interval()

    membership = activate_coach_membership(
        db,
        user_id=db.user.id,
        starts_at=starts_at,
        expires_at=expires_at,
    )

    assert membership.status is MembershipStatus.ACTIVE
    assert membership.membership_type_id == db.coach_type.id
    assert db.user.role is UserRole.COACH
    assert db.commit_calls == 1


def test_activate_coach_membership_is_idempotent_with_existing_active_membership() -> None:
    db = InMemoryMembershipLifecycleSession()
    starts_at, expires_at = _interval()
    existing_membership = Membership(
        id=42,
        user_id=db.user.id,
        membership_type_id=db.coach_type.id,
        status=MembershipStatus.ACTIVE,
        starts_at=starts_at,
        expires_at=expires_at,
    )
    db.active_membership = existing_membership

    activated = activate_coach_membership(
        db,
        user_id=db.user.id,
        starts_at=starts_at,
        expires_at=expires_at,
    )

    assert activated is existing_membership
    assert db.memberships == []
    assert db.user.role is UserRole.COACH


def test_activate_pending_coach_membership_transitions_it_to_active() -> None:
    db = InMemoryMembershipLifecycleSession()
    starts_at, expires_at = _interval()
    pending_membership = Membership(
        id=5,
        user_id=db.user.id,
        membership_type_id=db.coach_type.id,
        status=MembershipStatus.PENDING,
        starts_at=starts_at,
        expires_at=expires_at,
    )

    activated = activate_coach_membership(
        db,
        user_id=db.user.id,
        starts_at=starts_at,
        expires_at=expires_at,
        pending_membership=pending_membership,
    )

    assert activated is pending_membership
    assert activated.status is MembershipStatus.ACTIVE


def test_cancellation_preserves_membership_history_and_rejects_invalid_transition() -> None:
    db = InMemoryMembershipLifecycleSession()
    starts_at, expires_at = _interval()
    membership = Membership(
        id=1,
        user_id=db.user.id,
        membership_type_id=db.coach_type.id,
        status=MembershipStatus.ACTIVE,
        starts_at=starts_at,
        expires_at=expires_at,
    )
    db.memberships.append(membership)

    cancelled = cancel_membership(db, membership_id=membership.id)

    assert cancelled is membership
    assert membership.status is MembershipStatus.CANCELLED
    with pytest.raises(MembershipLifecycleError, match="cannot be cancelled"):
        cancel_membership(db, membership_id=membership.id)


def test_expire_memberships_persists_expired_state() -> None:
    db = InMemoryMembershipLifecycleSession()
    starts_at, expires_at = _interval()
    membership = Membership(
        id=1,
        user_id=db.user.id,
        membership_type_id=db.coach_type.id,
        status=MembershipStatus.ACTIVE,
        starts_at=starts_at,
        expires_at=expires_at,
    )
    db.expired_memberships = [membership]

    expired_count = expire_memberships(db, now=expires_at)

    assert expired_count == 1
    assert membership.status is MembershipStatus.EXPIRED
    assert membership.updated_at == expires_at
    assert db.commit_calls == 1


def test_active_membership_check_rejects_expiration_boundary() -> None:
    starts_at, expires_at = _interval()
    membership = Membership(
        id=1,
        user_id=1,
        membership_type_id=1,
        status=MembershipStatus.ACTIVE,
        starts_at=starts_at,
        expires_at=expires_at,
    )

    assert is_membership_active(membership, now=expires_at - timedelta(microseconds=1)) is True
    assert is_membership_active(membership, now=expires_at) is False


def test_has_active_coach_membership_uses_database_result() -> None:
    db = InMemoryMembershipLifecycleSession()
    db.active_coach_membership_id = 1

    assert has_active_coach_membership(db, user_id=db.user.id) is True
    db.active_coach_membership_id = None
    assert has_active_coach_membership(db, user_id=db.user.id) is False


def test_activation_rolls_back_when_transaction_commit_fails() -> None:
    db = InMemoryMembershipLifecycleSession()
    db.fail_commit = True
    starts_at, expires_at = _interval()

    with pytest.raises(RuntimeError, match="database unavailable"):
        activate_coach_membership(
            db,
            user_id=db.user.id,
            starts_at=starts_at,
            expires_at=expires_at,
        )

    assert db.rollback_calls == 1
