"""add coach membership foundation

Revision ID: 20261120_0001
Revises: 503504669ada
Create Date: 2026-11-20
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261120_0001"
down_revision: str | Sequence[str] | None = "503504669ada"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _reject_unsupported_roles("client", "trainer")
    op.execute("ALTER TYPE user_role RENAME TO user_role_legacy")
    op.execute("CREATE TYPE user_role AS ENUM ('client', 'coach')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role DROP DEFAULT, "
        "ALTER COLUMN role TYPE user_role USING "
        "CASE WHEN role::text = 'trainer' THEN 'coach'::user_role "
        "ELSE 'client'::user_role END"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'client'")
    op.execute("DROP TYPE user_role_legacy")
    op.execute("ALTER TYPE membership_status ADD VALUE IF NOT EXISTS 'pending' BEFORE 'active'")

    op.add_column("membership_types", sa.Column("code", sa.String(length=50), nullable=True))
    op.execute("UPDATE membership_types SET code = 'legacy-' || id::text WHERE code IS NULL")
    op.alter_column("membership_types", "code", nullable=False)
    op.create_unique_constraint("uq_membership_types_code", "membership_types", ["code"])
    op.alter_column("membership_types", "duration_days", nullable=True)
    op.alter_column("membership_types", "price", nullable=True)
    op.add_column(
        "membership_types",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.execute(
        "INSERT INTO membership_types (code, name, description, duration_days, price, is_active) "
        "VALUES ('coach', 'Coach Membership', "
        "'Grants access to Coach functionality while active.', NULL, NULL, true) "
        "ON CONFLICT (code) DO NOTHING"
    )

    op.drop_constraint("ck_membership_dates", "memberships", type_="check")
    op.drop_index("ix_memberships_status_end", table_name="memberships")
    op.alter_column(
        "memberships",
        "start_date",
        new_column_name="starts_at",
        type_=sa.DateTime(timezone=True),
        postgresql_using="start_date::timestamp AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "memberships",
        "end_date",
        new_column_name="expires_at",
        type_=sa.DateTime(timezone=True),
        postgresql_using="(end_date + 1)::timestamp AT TIME ZONE 'UTC'",
    )
    op.create_check_constraint("ck_membership_timestamps", "memberships", "expires_at > starts_at")
    op.create_index("ix_memberships_status_expires", "memberships", ["status", "expires_at"])
    op.create_index(
        "uq_memberships_active_user_type",
        "memberships",
        ["user_id", "membership_type_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.add_column(
        "memberships",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    _reject_unsupported_roles("client", "coach")
    op.drop_column("memberships", "updated_at")
    op.drop_index("uq_memberships_active_user_type", table_name="memberships")
    op.drop_index("ix_memberships_status_expires", table_name="memberships")
    op.drop_constraint("ck_membership_timestamps", "memberships", type_="check")
    op.alter_column(
        "memberships",
        "expires_at",
        new_column_name="end_date",
        type_=sa.Date(),
        postgresql_using="(expires_at AT TIME ZONE 'UTC')::date - 1",
    )
    op.alter_column(
        "memberships",
        "starts_at",
        new_column_name="start_date",
        type_=sa.Date(),
        postgresql_using="(starts_at AT TIME ZONE 'UTC')::date",
    )
    op.create_check_constraint("ck_membership_dates", "memberships", "end_date >= start_date")
    op.create_index("ix_memberships_status_end", "memberships", ["status", "end_date"])

    op.drop_constraint("uq_membership_types_code", "membership_types", type_="unique")
    op.drop_column("membership_types", "updated_at")
    op.drop_column("membership_types", "code")
    op.alter_column("membership_types", "price", nullable=False)
    op.alter_column("membership_types", "duration_days", nullable=False)

    op.execute("ALTER TYPE user_role RENAME TO user_role_current")
    op.execute("CREATE TYPE user_role AS ENUM ('client', 'trainer', 'admin')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role DROP DEFAULT, "
        "ALTER COLUMN role TYPE user_role USING "
        "CASE WHEN role::text = 'coach' THEN 'trainer'::user_role "
        "ELSE 'client'::user_role END"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'client'")
    op.execute("DROP TYPE user_role_current")


def _reject_unsupported_roles(*supported_roles: str) -> None:
    quoted_roles = ", ".join(f"'{role}'" for role in supported_roles)
    op.execute(
        "DO $$ "
        "DECLARE unsupported_roles text; "
        "BEGIN "
        "SELECT string_agg(DISTINCT role::text, ', ' ORDER BY role::text) "
        "INTO unsupported_roles FROM users "
        f"WHERE role::text NOT IN ({quoted_roles}); "
        "IF unsupported_roles IS NOT NULL THEN "
        "RAISE EXCEPTION USING "
        "MESSAGE = format("
        "'Cannot migrate users.role values: %s. Resolve or remove these roles before retrying.', "
        "unsupported_roles), "
        "ERRCODE = 'check_violation'; "
        "END IF; "
        "END $$;"
    )
