from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CheckInMethod, checkin_method_enum

if TYPE_CHECKING:
    from app.models.membership import Membership
    from app.models.user import User


class CheckIn(Base):
    __tablename__ = "check_ins"

    __table_args__ = (
        CheckConstraint(
            "checked_out_at IS NULL OR checked_out_at >= checked_in_at",
            name="ck_checkout_after_checkin",
        ),
        Index("ix_check_ins_checked_in_at", "checked_in_at"),
        Index("ix_check_ins_user_time", "user_id", "checked_in_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="check_ins_user_id_fkey", ondelete="CASCADE"), nullable=False
    )
    membership_id: Mapped[int | None] = mapped_column(
        ForeignKey("memberships.id", name="check_ins_membership_id_fkey", ondelete="SET NULL")
    )
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    checked_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    method: Mapped[CheckInMethod] = mapped_column(
        checkin_method_enum, nullable=False, server_default=text("'manual'")
    )

    user: Mapped[User] = relationship(back_populates="check_ins")
    membership: Mapped[Membership | None] = relationship(back_populates="check_ins")
