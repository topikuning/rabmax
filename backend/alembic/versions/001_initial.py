"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-06-06

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # projects
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("lokasi", sa.String(300), nullable=True),
        sa.Column("tahun_anggaran", sa.Integer(), nullable=True),
        sa.Column("target_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("mode", sa.String(30), nullable=False, server_default="generate"),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("input_file_path", sa.String(500), nullable=True),
        sa.Column("output_file_path", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # bahan_upah_items
    op.create_table(
        "bahan_upah_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nama", sa.String(300), nullable=False),
        sa.Column("satuan", sa.String(20), nullable=False),
        sa.Column("harga", sa.Numeric(18, 2), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("tier", sa.String(5), nullable=False),
        sa.Column("tkdn_factor", sa.Numeric(5, 4), server_default="1.0"),
        sa.Column("source_label", sa.String(300), nullable=False),
        sa.Column("provinsi", sa.String(50), nullable=True),
        sa.Column("kota", sa.String(100), nullable=True),
        sa.Column("tahun", sa.Integer(), nullable=False, server_default="2025"),
        sa.Column("aliases", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "last_updated",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_bu_nama", "bahan_upah_items", ["nama"])
    op.create_index("idx_bu_provinsi_tahun", "bahan_upah_items", ["provinsi", "tahun"])

    # ahsp_codes
    op.create_table(
        "ahsp_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kode", sa.String(50), nullable=False),
        sa.Column("uraian", sa.Text(), nullable=False),
        sa.Column("satuan", sa.String(20), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("version", sa.String(30), nullable=True),
        sa.Column(
            "confidence_tier",
            sa.String(30),
            nullable=False,
            server_default="single_source",
        ),
        sa.Column("work_group", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_ahsp_kode", "ahsp_codes", ["kode"])
    op.create_index("idx_ahsp_work_group", "ahsp_codes", ["work_group"])

    # ahsp_components
    op.create_table(
        "ahsp_components",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ahsp_id",
            sa.Integer(),
            sa.ForeignKey("ahsp_codes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kategori", sa.String(20), nullable=False),
        sa.Column("nama_material", sa.String(300), nullable=False),
        sa.Column("koefisien", sa.Numeric(18, 6), nullable=False),
        sa.Column("satuan", sa.String(20), nullable=False),
        sa.Column("formula_modifier", sa.String(50), nullable=True),
        sa.Column(
            "bahan_upah_id",
            sa.Integer(),
            sa.ForeignKey("bahan_upah_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("urutan", sa.Integer(), server_default="0"),
    )

    # paket_items
    op.create_table(
        "paket_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sheet_name", sa.String(100), nullable=False),
        sa.Column("excel_row", sa.Integer(), nullable=False),
        sa.Column("no_label", sa.String(30), nullable=True),
        sa.Column("uraian", sa.Text(), nullable=False),
        sa.Column("satuan", sa.String(30), nullable=False),
        sa.Column("volume", sa.Numeric(18, 4), nullable=False),
        sa.Column("parent_uraian", sa.Text(), nullable=True),
        sa.Column("norm_uraian", sa.Text(), nullable=False),
        sa.Column("norm_satuan", sa.String(30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_paket_project_sheet", "paket_items", ["project_id", "sheet_name"])
    op.create_index("idx_paket_norm_uraian", "paket_items", ["norm_uraian"])

    # item_matches
    op.create_table(
        "item_matches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "paket_item_id",
            sa.Integer(),
            sa.ForeignKey("paket_items.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("match_type", sa.String(30), nullable=False),
        sa.Column("method", sa.String(30), nullable=False),
        sa.Column(
            "ahsp_id",
            sa.Integer(),
            sa.ForeignKey("ahsp_codes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("lumpsum_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("lumpsum_source", sa.String(300), nullable=True),
        sa.Column("final_hsp", sa.Numeric(18, 2), nullable=True),
        sa.Column("tkdn_factor", sa.Numeric(5, 4), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), server_default="0.0"),
        sa.Column("reviewed_by_user", sa.Boolean(), server_default="false"),
        sa.Column("user_notes", sa.Text(), nullable=True),
        sa.Column("calibration_multiplier", sa.Numeric(8, 6), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # profit_analyses
    op.create_table(
        "profit_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("hps_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("hps_total_incl_ppn", sa.Numeric(18, 2), nullable=False),
        sa.Column("estimated_cost_total", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "estimated_cost_breakdown",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("gross_profit", sa.Numeric(18, 2), nullable=False),
        sa.Column("gross_profit_margin_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("risk_items", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("per_paket_breakdown", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("assumptions", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), server_default="0.0"),
        sa.Column("items_resolved", sa.Integer(), server_default="0"),
        sa.Column("items_total", sa.Integer(), server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("profit_analyses")
    op.drop_table("item_matches")
    op.drop_index("idx_paket_norm_uraian", table_name="paket_items")
    op.drop_index("idx_paket_project_sheet", table_name="paket_items")
    op.drop_table("paket_items")
    op.drop_table("ahsp_components")
    op.drop_index("idx_ahsp_work_group", table_name="ahsp_codes")
    op.drop_index("idx_ahsp_kode", table_name="ahsp_codes")
    op.drop_table("ahsp_codes")
    op.drop_index("idx_bu_provinsi_tahun", table_name="bahan_upah_items")
    op.drop_index("idx_bu_nama", table_name="bahan_upah_items")
    op.drop_table("bahan_upah_items")
    op.drop_table("projects")
