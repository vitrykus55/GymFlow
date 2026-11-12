from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole, user_role_enum

if TYPE_CHECKING:
    from app.models.auth_refresh_token import AuthRefreshToken
    from app.models.booking import Booking
    from app.models.check_in import CheckIn
    from app.models.class_session import ClassSession
    from app.models.membership import Membership
    from app.models.payment import Payment


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        Index("ix_users_role", "role"),
        Index("ux_users_email_lower", text("lower((email)::text)"), unique=True),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    birth_date: Mapped[date | None] = mapped_column(Date)
    role: Mapped[UserRole] = mapped_column(
        user_role_enum, nullable=False, server_default=text("'client'")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    bookings: Mapped[list[Booking]] = relationship(back_populates="user", passive_deletes=True)
    memberships: Mapped[list[Membership]] = relationship(
        back_populates="user", passive_deletes=True
    )
    payments: Mapped[list[Payment]] = relationship(back_populates="user")
    check_ins: Mapped[list[CheckIn]] = relationship(back_populates="user", passive_deletes=True)
    refresh_tokens: Mapped[list[AuthRefreshToken]] = relationship(
        back_populates="user", passive_deletes=True
    )
    class_sessions_as_trainer: Mapped[list[ClassSession]] = relationship(
        back_populates="trainer", foreign_keys="ClassSession.trainer_id"
    )
