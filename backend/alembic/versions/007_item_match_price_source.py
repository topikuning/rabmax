"""item_matches: price_source (ringkasan sumber harga untuk audit)

Revision ID: 007_price_source
Revises: 006_bu_geo
Create Date: 2026-06-07

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007_price_source"
down_revision: str | Sequence[str] | None = "006_bu_geo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("item_matches", sa.Column("price_source", sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("item_matches", "price_source")
