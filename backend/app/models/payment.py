from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    PaymentMethod,
    PaymentStatus,
    payment_method_enum,
    payment_status_enum,
)

if TYPE_CHECKING:
    from app.models.membership import Membership
    from app.models.user import User


class Payment(Base):
    __tablename__ = "payments"

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_payments_amount"),
        Index("ix_payments_paid_at", "paid_at"),
        Index("ix_payments_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", name="payments_user_id_fkey"), nullable=False
    )
    membership_id: Mapped[int | None] = mapped_column(
        ForeignKey("memberships.id", name="payments_membership_id_fkey", ondelete="SET NULL")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'PLN'"))
    status: Mapped[PaymentStatus] = mapped_column(
        payment_status_enum, nullable=False, server_default=text("'pending'")
    )
    method: Mapped[PaymentMethod] = mapped_column(
        payment_method_enum, nullable=False, server_default=text("'simulated'")
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    user: Mapped[User] = relationship(back_populates="payments")
    membership: Mapped[Membership | None] = relationship(back_populates="payments")
