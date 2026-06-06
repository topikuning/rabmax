"""bahan_upah: ai_generated flag

Revision ID: 003_bu_ai_flag
Revises: 002_auth
Create Date: 2026-06-06

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "003_bu_ai_flag"
down_revision: str | Sequence[str] | None = "002_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bahan_upah_items",
        sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("bahan_upah_items", "ai_generated")
