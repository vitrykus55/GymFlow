from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

COACH_MEMBERSHIP_CODE = "coach"

if TYPE_CHECKING:
    from app.models.membership import Membership


class MembershipType(Base):
    __tablename__ = "membership_types"

    __table_args__ = (
        CheckConstraint(
            "duration_days IS NULL OR duration_days > 0", name="ck_membership_types_duration"
        ),
        CheckConstraint(
            "max_entries IS NULL OR max_entries > 0", name="ck_membership_types_entries"
        ),
        CheckConstraint("price IS NULL OR price >= 0", name="ck_membership_types_price"),
        UniqueConstraint("name", name="membership_types_name_key"),
        UniqueConstraint("code", name="uq_membership_types_code"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    duration_days: Mapped[int | None] = mapped_column(Integer)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    max_entries: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    memberships: Mapped[list[Membership]] = relationship(back_populates="membership_type")
