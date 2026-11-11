from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Index, text
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
        CheckConstraint("end_date >= start_date", name="ck_membership_dates"),
        Index("ix_memberships_status_end", "status", "end_date"),
        Index("ix_memberships_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="memberships_user_id_fkey", ondelete="CASCADE"), nullable=False
    )
    membership_type_id: Mapped[int] = mapped_column(
        ForeignKey("membership_types.id", name="memberships_membership_type_id_fkey"),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[MembershipStatus] = mapped_column(
        membership_status_enum, nullable=False, server_default=text("'active'")
    )
    created_at: Mapped[datetime] = mapped_column(
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
