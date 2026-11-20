from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import MembershipStatus, membership_status_enum

if TYPE_CHECKING:
    from app.models.check_in import CheckIn
    from app.models.membership_type import MembershipType
    from app.models.payment import Payment
    from app.models.user import User


class Membership(Base):
    __tablename__ = "memberships"

    __table_args__ = (
        CheckConstraint("expires_at > starts_at", name="ck_membership_timestamps"),
        Index("ix_memberships_status_expires", "status", "expires_at"),
        Index("ix_memberships_user_id", "user_id"),
        Index(
            "uq_memberships_active_user_type",
            "user_id",
            "membership_type_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="memberships_user_id_fkey", ondelete="CASCADE"), nullable=False
    )
    membership_type_id: Mapped[int] = mapped_column(
        ForeignKey("membership_types.id", name="memberships_membership_type_id_fkey"),
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(
        membership_status_enum, nullable=False, server_default=text("'active'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    user: Mapped[User] = relationship(back_populates="memberships")
    membership_type: Mapped[MembershipType] = relationship(back_populates="memberships")
    payments: Mapped[list[Payment]] = relationship(
        back_populates="membership", passive_deletes=True
    )
    check_ins: Mapped[list[CheckIn]] = relationship(
        back_populates="membership", passive_deletes=True
    )
