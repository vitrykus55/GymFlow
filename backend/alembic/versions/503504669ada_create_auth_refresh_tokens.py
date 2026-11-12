"""create auth refresh tokens

Revision ID: 503504669ada
Revises: 
Create Date: 2026-11-12 23:02:39.144596

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "503504669ada"
down_revision: str | Sequence[str] | None = "20261112_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_refresh_tokens",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_token_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_token_id"],
            ["auth_refresh_tokens.id"],
            name="auth_refresh_tokens_replaced_by_token_id_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="auth_refresh_tokens_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_auth_refresh_tokens_token_hash"),
    )
    op.create_index(
        "ix_auth_refresh_tokens_expires_at", "auth_refresh_tokens", ["expires_at"], unique=False
    )
    op.create_index(
        "ix_auth_refresh_tokens_family_id", "auth_refresh_tokens", ["family_id"], unique=False
    )
    op.create_index(
        "ix_auth_refresh_tokens_user_id", "auth_refresh_tokens", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_auth_refresh_tokens_user_id", table_name="auth_refresh_tokens")
    op.drop_index("ix_auth_refresh_tokens_family_id", table_name="auth_refresh_tokens")
    op.drop_index("ix_auth_refresh_tokens_expires_at", table_name="auth_refresh_tokens")
    op.drop_table("auth_refresh_tokens")
