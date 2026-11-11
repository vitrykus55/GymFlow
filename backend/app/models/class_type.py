from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, CheckConstraint, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.class_session import ClassSession


class ClassType(Base):
    __tablename__ = "class_types"

    __table_args__ = (
        CheckConstraint("default_capacity > 0", name="ck_class_types_capacity"),
        CheckConstraint("duration_minutes > 0", name="ck_class_types_duration"),
        UniqueConstraint("name", name="class_types_name_key"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    default_capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    class_sessions: Mapped[list[ClassSession]] = relationship(back_populates="class_type")
