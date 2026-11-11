from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import BookingStatus, booking_status_enum

if TYPE_CHECKING:
    from app.models.class_session import ClassSession
    from app.models.user import User


class Booking(Base):
    __tablename__ = "bookings"

    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="ux_booking_session_user"),
        Index("ix_bookings_session", "session_id", "status"),
        Index("ix_bookings_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("class_sessions.id", name="bookings_session_id_fkey", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="bookings_user_id_fkey", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[BookingStatus] = mapped_column(
        booking_status_enum, nullable=False, server_default=text("'confirmed'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    class_session: Mapped[ClassSession] = relationship(back_populates="bookings")
    user: Mapped[User] = relationship(back_populates="bookings")
