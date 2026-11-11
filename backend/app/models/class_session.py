from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.class_type import ClassType
    from app.models.user import User


class ClassSession(Base):
    __tablename__ = "class_sessions"

    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_session_capacity"),
        CheckConstraint("ends_at > starts_at", name="ck_session_time"),
        Index("ix_class_sessions_starts_at", "starts_at"),
        Index("ix_class_sessions_trainer", "trainer_id", "starts_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    class_type_id: Mapped[int] = mapped_column(
        ForeignKey("class_types.id", name="class_sessions_class_type_id_fkey"), nullable=False
    )
    trainer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="class_sessions_trainer_id_fkey"), nullable=False
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    room: Mapped[str | None] = mapped_column(String(50))
    is_cancelled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    class_type: Mapped[ClassType] = relationship(back_populates="class_sessions")
    trainer: Mapped[User] = relationship(
        back_populates="class_sessions_as_trainer", foreign_keys=[trainer_id]
    )
    bookings: Mapped[list[Booking]] = relationship(
        back_populates="class_session", passive_deletes=True
    )
