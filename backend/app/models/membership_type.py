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

if TYPE_CHECKING:
    from app.models.membership import Membership


class MembershipType(Base):
    __tablename__ = "membership_types"

    __table_args__ = (
        CheckConstraint("duration_days > 0", name="ck_membership_types_duration"),
        CheckConstraint(
            "max_entries IS NULL OR max_entries > 0", name="ck_membership_types_entries"
        ),
        CheckConstraint("price >= 0", name="ck_membership_types_price"),
        UniqueConstraint("name", name="membership_types_name_key"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_entries: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    memberships: Mapped[list[Membership]] = relationship(back_populates="membership_type")
