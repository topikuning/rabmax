"""ahsp_components: harga_satuan nasional (baseline dari AHSP CK 2026)

Revision ID: 005_comp_harga
Revises: 004_pricing
Create Date: 2026-06-07

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005_comp_harga"
down_revision: str | Sequence[str] | None = "004_pricing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ahsp_components",
        sa.Column("harga_satuan", sa.Numeric(precision=18, scale=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ahsp_components", "harga_satuan")
