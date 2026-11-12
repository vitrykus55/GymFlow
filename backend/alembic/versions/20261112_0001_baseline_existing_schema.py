"""baseline existing schema

Revision ID: 20261112_0001
Revises:
Create Date: 2026-11-12

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261112_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

user_role = postgresql.ENUM(
    "client", "trainer", "admin", name="user_role", create_type=False
)
membership_status = postgresql.ENUM(
    "active", "expired", "cancelled", name="membership_status", create_type=False
)
payment_status = postgresql.ENUM(
    "pending", "paid", "failed", "refunded", name="payment_status", create_type=False
)
payment_method = postgresql.ENUM(
    "card", "cash", "transfer", "simulated", name="payment_method", create_type=False
)
booking_status = postgresql.ENUM(
    "confirmed",
    "waitlist",
    "cancelled",
    "attended",
    "no_show",
    name="booking_status",
    create_type=False,
)
checkin_method = postgresql.ENUM("qr", "manual", "card", name="checkin_method", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        user_role,
        membership_status,
        payment_status,
        payment_method,
        booking_status,
        checkin_method,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("role", user_role, server_default=sa.text("'client'"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="users_pkey"),
    )
    op.create_index("ix_users_role", "users", ["role"], unique=False)
    op.create_index(
        "ux_users_email_lower", "users", [sa.text("lower((email)::text)")], unique=True
    )

    op.create_table(
        "class_types",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("default_capacity", sa.Integer(), nullable=False),
        sa.CheckConstraint("default_capacity > 0", name="ck_class_types_capacity"),
        sa.CheckConstraint("duration_minutes > 0", name="ck_class_types_duration"),
        sa.PrimaryKeyConstraint("id", name="class_types_pkey"),
        sa.UniqueConstraint("name", name="class_types_name_key"),
    )

    op.create_table(
        "membership_types",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("max_entries", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("duration_days > 0", name="ck_membership_types_duration"),
        sa.CheckConstraint(
            "max_entries IS NULL OR max_entries > 0", name="ck_membership_types_entries"
        ),
        sa.CheckConstraint("price >= 0", name="ck_membership_types_price"),
        sa.PrimaryKeyConstraint("id", name="membership_types_pkey"),
        sa.UniqueConstraint("name", name="membership_types_name_key"),
    )

    op.create_table(
        "class_sessions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("class_type_id", sa.BigInteger(), nullable=False),
        sa.Column("trainer_id", sa.BigInteger(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("room", sa.String(length=50), nullable=True),
        sa.Column("is_cancelled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("capacity > 0", name="ck_session_capacity"),
        sa.CheckConstraint("ends_at > starts_at", name="ck_session_time"),
        sa.ForeignKeyConstraint(
            ["class_type_id"], ["class_types.id"], name="class_sessions_class_type_id_fkey"
        ),
        sa.ForeignKeyConstraint(
            ["trainer_id"], ["users.id"], name="class_sessions_trainer_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="class_sessions_pkey"),
    )
    op.create_index("ix_class_sessions_starts_at", "class_sessions", ["starts_at"], unique=False)
    op.create_index(
        "ix_class_sessions_trainer", "class_sessions", ["trainer_id", "starts_at"], unique=False
    )

    op.create_table(
        "memberships",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("membership_type_id", sa.BigInteger(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("status", membership_status, server_default=sa.text("'active'"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("end_date >= start_date", name="ck_membership_dates"),
        sa.ForeignKeyConstraint(
            ["membership_type_id"],
            ["membership_types.id"],
            name="memberships_membership_type_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="memberships_user_id_fkey", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="memberships_pkey"),
    )
    op.create_index(
        "ix_memberships_status_end", "memberships", ["status", "end_date"], unique=False
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"], unique=False)

    op.create_table(
        "payments",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("membership_id", sa.BigInteger(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'PLN'"), nullable=False),
        sa.Column("status", payment_status, server_default=sa.text("'pending'"), nullable=False),
        sa.Column("method", payment_method, server_default=sa.text("'simulated'"), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount >= 0", name="ck_payments_amount"),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["memberships.id"],
            name="payments_membership_id_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="payments_user_id_fkey"),
        sa.PrimaryKeyConstraint("id", name="payments_pkey"),
    )
    op.create_index("ix_payments_paid_at", "payments", ["paid_at"], unique=False)
    op.create_index("ix_payments_user_id", "payments", ["user_id"], unique=False)

    op.create_table(
        "bookings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", booking_status, server_default=sa.text("'confirmed'"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["class_sessions.id"],
            name="bookings_session_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="bookings_user_id_fkey", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="bookings_pkey"),
        sa.UniqueConstraint("session_id", "user_id", name="ux_booking_session_user"),
    )
    op.create_index("ix_bookings_session", "bookings", ["session_id", "status"], unique=False)
    op.create_index("ix_bookings_user_id", "bookings", ["user_id"], unique=False)

    op.create_table(
        "check_ins",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("membership_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "checked_in_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("checked_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("method", checkin_method, server_default=sa.text("'manual'"), nullable=False),
        sa.CheckConstraint(
            "checked_out_at IS NULL OR checked_out_at >= checked_in_at",
            name="ck_checkout_after_checkin",
        ),
        sa.ForeignKeyConstraint(
            ["membership_id"],
            ["memberships.id"],
            name="check_ins_membership_id_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="check_ins_user_id_fkey", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="check_ins_pkey"),
    )
    op.create_index("ix_check_ins_checked_in_at", "check_ins", ["checked_in_at"], unique=False)
    op.create_index(
        "ix_check_ins_user_time", "check_ins", ["user_id", "checked_in_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_check_ins_user_time", table_name="check_ins")
    op.drop_index("ix_check_ins_checked_in_at", table_name="check_ins")
    op.drop_table("check_ins")

    op.drop_index("ix_bookings_user_id", table_name="bookings")
    op.drop_index("ix_bookings_session", table_name="bookings")
    op.drop_table("bookings")

    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_index("ix_payments_paid_at", table_name="payments")
    op.drop_table("payments")

    op.drop_index("ix_memberships_user_id", table_name="memberships")
    op.drop_index("ix_memberships_status_end", table_name="memberships")
    op.drop_table("memberships")

    op.drop_index("ix_class_sessions_trainer", table_name="class_sessions")
    op.drop_index("ix_class_sessions_starts_at", table_name="class_sessions")
    op.drop_table("class_sessions")

    op.drop_table("membership_types")
    op.drop_table("class_types")

    op.drop_index("ux_users_email_lower", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_type in (
        checkin_method,
        booking_status,
        payment_method,
        payment_status,
        membership_status,
        user_role,
    ):
        enum_type.drop(bind, checkfirst=True)
