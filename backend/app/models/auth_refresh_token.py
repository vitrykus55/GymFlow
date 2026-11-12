from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class AuthRefreshToken(Base):
    __tablename__ = "auth_refresh_tokens"

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_auth_refresh_tokens_token_hash"),
        Index("ix_auth_refresh_tokens_user_id", "user_id"),
        Index("ix_auth_refresh_tokens_family_id", "family_id"),
        Index("ix_auth_refresh_tokens_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="auth_refresh_tokens_user_id_fkey", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    family_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_token_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "auth_refresh_tokens.id",
            name="auth_refresh_tokens_replaced_by_token_id_fkey",
            ondelete="SET NULL",
        )
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    user: Mapped[User] = relationship(back_populates="refresh_tokens")
    replaced_by_token: Mapped[AuthRefreshToken | None] = relationship(
        foreign_keys=[replaced_by_token_id], remote_side="AuthRefreshToken.id", uselist=False
    )
