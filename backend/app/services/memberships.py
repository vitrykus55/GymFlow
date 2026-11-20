from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import MembershipStatus, UserRole
from app.models.membership import Membership
from app.models.membership_type import COACH_MEMBERSHIP_CODE, MembershipType
from app.models.user import User


class MembershipLifecycleError(ValueError):
    """Raised when a requested membership transition is not valid."""


class MembershipNotFoundError(LookupError):
    """Raised when a membership required by trusted application logic is absent."""


def create_membership(
    db: Session,
    *,
    user_id: int,
    membership_type: MembershipType,
    starts_at: datetime,
    expires_at: datetime,
) -> Membership:
    """Create a pending entitlement using trusted application logic only."""
    starts_at, expires_at = _validated_interval(starts_at, expires_at)
    if not membership_type.is_active:
        raise MembershipLifecycleError("Cannot create a membership for an inactive type.")

    membership = Membership(
        user_id=user_id,
        membership_type_id=membership_type.id,
        membership_type=membership_type,
        status=MembershipStatus.PENDING,
        starts_at=starts_at,
        expires_at=expires_at,
    )
    db.add(membership)
    _commit_or_rollback(db)
    return membership


def activate_coach_membership(
    db: Session,
    *,
    user_id: int,
    starts_at: datetime,
    expires_at: datetime,
    pending_membership: Membership | None = None,
) -> Membership:
    """Activate Coach access after a trusted caller has verified payment externally.

    The caller supplies the entitlement interval. This intentionally has no payment-provider
    coupling and is not exposed through an API route.
    """
    starts_at, expires_at = _validated_interval(starts_at, expires_at)
    now = datetime.now(UTC)
    user = db.get(User, user_id)
    if user is None:
        raise MembershipNotFoundError("User does not exist.")

    coach_type = db.scalar(
        select(MembershipType)
        .where(
            MembershipType.code == COACH_MEMBERSHIP_CODE,
            MembershipType.is_active.is_(True),
        )
        .with_for_update()
    )
    if coach_type is None:
        raise MembershipNotFoundError("Active Coach Membership type does not exist.")

    expired_memberships = db.scalars(
        select(Membership)
        .where(
            Membership.user_id == user_id,
            Membership.membership_type_id == coach_type.id,
            Membership.status == MembershipStatus.ACTIVE,
            Membership.expires_at <= now,
        )
        .with_for_update()
    )
    for membership in expired_memberships:
        membership.status = MembershipStatus.EXPIRED
        membership.updated_at = now

    active_membership = db.scalar(
        select(Membership)
        .where(
            Membership.user_id == user_id,
            Membership.membership_type_id == coach_type.id,
            Membership.status == MembershipStatus.ACTIVE,
            Membership.starts_at <= now,
            Membership.expires_at > now,
        )
        .with_for_update()
    )
    if active_membership is not None:
        if user.role is not UserRole.COACH:
            user.role = UserRole.COACH
        _commit_or_rollback(db)
        return active_membership

    if pending_membership is not None:
        _activate_pending_membership(
            pending_membership,
            user_id=user_id,
            coach_type=coach_type,
            starts_at=starts_at,
            expires_at=expires_at,
            updated_at=now,
        )
        membership = pending_membership
    else:
        membership = Membership(
            user_id=user_id,
            membership_type_id=coach_type.id,
            membership_type=coach_type,
            status=MembershipStatus.ACTIVE,
            starts_at=starts_at,
            expires_at=expires_at,
        )
        db.add(membership)

    user.role = UserRole.COACH
    _commit_or_rollback(db)
    return membership


def cancel_membership(db: Session, *, membership_id: int) -> Membership:
    """Cancel a pending or active membership while retaining its history."""
    membership = db.get(Membership, membership_id)
    if membership is None:
        raise MembershipNotFoundError("Membership does not exist.")
    if membership.status not in {MembershipStatus.PENDING, MembershipStatus.ACTIVE}:
        raise MembershipLifecycleError("Membership cannot be cancelled from its current status.")

    membership.status = MembershipStatus.CANCELLED
    membership.updated_at = datetime.now(UTC)
    _commit_or_rollback(db)
    return membership


def expire_memberships(db: Session, *, now: datetime | None = None) -> int:
    """Persist the expired state for memberships whose entitlement has ended."""
    expiry_time = _to_utc(now or datetime.now(UTC))
    memberships = db.scalars(
        select(Membership)
        .where(
            Membership.status == MembershipStatus.ACTIVE,
            Membership.expires_at <= expiry_time,
        )
        .with_for_update()
    )
    expired_count = 0
    for membership in memberships:
        membership.status = MembershipStatus.EXPIRED
        membership.updated_at = expiry_time
        expired_count += 1
    if expired_count:
        _commit_or_rollback(db)
    return expired_count


def is_membership_active(membership: Membership, *, now: datetime | None = None) -> bool:
    """Return whether the entitlement is active at the supplied UTC instant."""
    current_time = _to_utc(now or datetime.now(UTC))
    return (
        membership.status is MembershipStatus.ACTIVE
        and membership.starts_at <= current_time < membership.expires_at
    )


def has_active_coach_membership(db: Session, *, user_id: int, now: datetime | None = None) -> bool:
    """Check Coach access without relying on a background expiration task."""
    current_time = _to_utc(now or datetime.now(UTC))
    return (
        db.scalar(
            select(Membership.id)
            .join(MembershipType, Membership.membership_type_id == MembershipType.id)
            .where(
                Membership.user_id == user_id,
                Membership.status == MembershipStatus.ACTIVE,
                Membership.starts_at <= current_time,
                Membership.expires_at > current_time,
                MembershipType.code == COACH_MEMBERSHIP_CODE,
            )
            .limit(1)
        )
        is not None
    )


def _activate_pending_membership(
    membership: Membership,
    *,
    user_id: int,
    coach_type: MembershipType,
    starts_at: datetime,
    expires_at: datetime,
    updated_at: datetime,
) -> None:
    if membership.user_id != user_id or membership.membership_type_id != coach_type.id:
        raise MembershipLifecycleError(
            "Pending membership does not match the requested Coach access."
        )
    if membership.status is not MembershipStatus.PENDING:
        raise MembershipLifecycleError("Only pending memberships can be activated.")
    membership.status = MembershipStatus.ACTIVE
    membership.starts_at = starts_at
    membership.expires_at = expires_at
    membership.updated_at = updated_at


def _validated_interval(starts_at: datetime, expires_at: datetime) -> tuple[datetime, datetime]:
    starts_at = _to_utc(starts_at)
    expires_at = _to_utc(expires_at)
    if expires_at <= starts_at:
        raise MembershipLifecycleError("Membership expiration must be after its start time.")
    return starts_at, expires_at


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise MembershipLifecycleError("Membership timestamps must be timezone-aware.")
    return value.astimezone(UTC)


def _commit_or_rollback(db: Session) -> None:
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
