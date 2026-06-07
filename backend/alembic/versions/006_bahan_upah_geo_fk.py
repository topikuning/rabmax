"""bahan_upah_items: FK geografi (provinsi_id, kota_kabupaten_id) untuk SSH per-kota

Revision ID: 006_bu_geo
Revises: 005_comp_harga
Create Date: 2026-06-07

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006_bu_geo"
down_revision: str | Sequence[str] | None = "005_comp_harga"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("bahan_upah_items", sa.Column("provinsi_id", sa.Integer(), nullable=True))
    op.add_column("bahan_upah_items", sa.Column("kota_kabupaten_id", sa.Integer(), nullable=True))
    op.create_index("ix_bahan_upah_items_provinsi_id", "bahan_upah_items", ["provinsi_id"])
    op.create_index("ix_bahan_upah_items_kota_kabupaten_id", "bahan_upah_items", ["kota_kabupaten_id"])
    op.create_foreign_key(
        "fk_bu_provinsi", "bahan_upah_items", "provinsi", ["provinsi_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        "fk_bu_kota", "bahan_upah_items", "kota_kabupaten", ["kota_kabupaten_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("fk_bu_kota", "bahan_upah_items", type_="foreignkey")
    op.drop_constraint("fk_bu_provinsi", "bahan_upah_items", type_="foreignkey")
    op.drop_index("ix_bahan_upah_items_kota_kabupaten_id", "bahan_upah_items")
    op.drop_index("ix_bahan_upah_items_provinsi_id", "bahan_upah_items")
    op.drop_column("bahan_upah_items", "kota_kabupaten_id")
    op.drop_column("bahan_upah_items", "provinsi_id")
