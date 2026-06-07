"""pricing intelligence: geografi, vendor registry, snapshots/consensus, transport, umk

Revision ID: 004_pricing
Revises: 003_bu_ai_flag
Create Date: 2026-06-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004_pricing"
down_revision: str | Sequence[str] | None = "003_bu_ai_flag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "provinsi",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kode", sa.String(5), nullable=False),
        sa.Column("nama", sa.String(100), nullable=False),
        sa.Column("nama_singkat", sa.String(20)),
        sa.Column("ibukota", sa.String(100)),
        sa.Column("pulau", sa.String(50)),
        sa.Column("region", sa.String(50)),
        sa.Column("latitude", sa.Numeric(9, 6)),
        sa.Column("longitude", sa.Numeric(9, 6)),
    )
    op.create_index("ix_provinsi_kode", "provinsi", ["kode"], unique=True)

    op.create_table(
        "kota_kabupaten",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provinsi_id", sa.Integer(), sa.ForeignKey("provinsi.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kode", sa.String(10), nullable=False),
        sa.Column("nama", sa.String(100), nullable=False),
        sa.Column("tipe", sa.String(15), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6)),
        sa.Column("longitude", sa.Numeric(9, 6)),
    )
    op.create_index("ix_kota_kabupaten_kode", "kota_kabupaten", ["kode"], unique=True)
    op.create_index("idx_kotkab_provinsi", "kota_kabupaten", ["provinsi_id"])

    op.create_table(
        "provinsi_adjacency",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provinsi_id", sa.Integer(), sa.ForeignKey("provinsi.id", ondelete="CASCADE"), nullable=False),
        sa.Column("neighbor_id", sa.Integer(), sa.ForeignKey("provinsi.id", ondelete="CASCADE"), nullable=False),
        sa.Column("travel_mode", sa.String(15), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="1"),
        sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("provinsi_id", "neighbor_id"),
    )

    op.create_table(
        "umk",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kota_kabupaten_id", sa.Integer(), sa.ForeignKey("kota_kabupaten.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provinsi_id", sa.Integer(), sa.ForeignKey("provinsi.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tahun", sa.Integer(), nullable=False),
        sa.Column("umk", sa.Numeric(18, 2), nullable=False),
        sa.Column("sk_nomor", sa.String(100)),
        sa.Column("sk_tanggal", sa.Date()),
        sa.Column("sumber_url", sa.String(500)),
        sa.Column("sumber_label", sa.String(300)),
        sa.Column("upah_pekerja_harian", sa.Numeric(18, 2)),
        sa.Column("upah_tukang_harian", sa.Numeric(18, 2)),
        sa.Column("upah_kepala_tukang_harian", sa.Numeric(18, 2)),
        sa.Column("upah_mandor_harian", sa.Numeric(18, 2)),
        sa.Column("last_scraped_at", _TS),
        sa.UniqueConstraint("kota_kabupaten_id", "tahun"),
    )
    op.create_index("ix_umk_tahun", "umk", ["tahun"])

    op.create_table(
        "item_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("item_categories.id", ondelete="SET NULL")),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("level", sa.Integer(), server_default="0"),
        sa.Column("standard_unit", sa.String(20)),
        sa.Column("typical_brands", sa.JSON()),
        sa.Column("typical_specs", sa.JSON()),
        sa.Column("search_keywords", sa.JSON()),
    )
    op.create_index("ix_item_categories_code", "item_categories", ["code"], unique=True)

    op.create_table(
        "item_classifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("norm_item_name", sa.String(300), nullable=False),
        sa.Column("satuan", sa.String(20), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("item_categories.id", ondelete="SET NULL")),
        sa.Column("detected_brand", sa.String(100)),
        sa.Column("detected_specs", sa.JSON()),
        sa.Column("classified_at", _TS, server_default=sa.func.now()),
        sa.Column("classifier_llm", sa.String(50)),
        sa.Column("confidence", sa.Numeric(4, 3), server_default="0"),
        sa.UniqueConstraint("norm_item_name", "satuan"),
    )
    op.create_index("ix_item_classifications_norm_item_name", "item_classifications", ["norm_item_name"])

    op.create_table(
        "vendors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("domain", sa.String(200), nullable=False),
        sa.Column("canonical_url", sa.String(500)),
        sa.Column("source_type", sa.String(40), server_default="unknown"),
        sa.Column("reliability_score", sa.Numeric(4, 3), server_default="0.5"),
        sa.Column("domain_verified", sa.Boolean(), server_default=sa.false()),
        sa.Column("total_snapshots", sa.Integer(), server_default="0"),
        sa.Column("successful_scrapes", sa.Integer(), server_default="0"),
        sa.Column("failed_scrapes", sa.Integer(), server_default="0"),
        sa.Column("last_validated_at", _TS),
        sa.Column("scraper_recipe", sa.JSON()),
        sa.Column("recipe_generated_at", _TS),
        sa.Column("recipe_last_tested", _TS),
        sa.Column("recipe_works", sa.Boolean(), server_default=sa.true()),
        sa.Column("rate_limit_per_min", sa.Integer(), server_default="20"),
        sa.Column("requires_javascript", sa.Boolean(), server_default=sa.false()),
        sa.Column("robots_txt_allowed", sa.Boolean()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.Column("discovered_at", _TS, server_default=sa.func.now()),
        sa.Column("last_used_at", _TS),
        sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("domain"),
    )
    op.create_index("ix_vendors_domain", "vendors", ["domain"])

    op.create_table(
        "vendor_specialties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("item_categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("items_priced", sa.Integer(), server_default="0"),
        sa.Column("avg_confidence", sa.Numeric(4, 3), server_default="0"),
        sa.Column("last_item_at", _TS),
        sa.UniqueConstraint("vendor_id", "category_id"),
    )

    op.create_table(
        "vendor_service_areas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("provinsi_id", sa.Integer(), sa.ForeignKey("provinsi.id", ondelete="SET NULL")),
        sa.Column("kota_kabupaten_id", sa.Integer(), sa.ForeignKey("kota_kabupaten.id", ondelete="SET NULL")),
        sa.Column("center_lat", sa.Numeric(9, 6)),
        sa.Column("center_lon", sa.Numeric(9, 6)),
        sa.Column("radius_km", sa.Integer()),
        sa.Column("delivery_free_threshold", sa.Numeric(18, 2)),
        sa.Column("delivery_base_cost", sa.Numeric(18, 2)),
        sa.Column("delivery_per_km_cost", sa.Numeric(18, 2)),
        sa.Column("discovered_at", _TS, server_default=sa.func.now()),
        sa.Column("confidence", sa.Numeric(4, 3), server_default="0.5"),
    )
    op.create_index("idx_vsa_vendor", "vendor_service_areas", ["vendor_id"])
    op.create_index("idx_vsa_kota", "vendor_service_areas", ["kota_kabupaten_id"])

    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("item_categories.id", ondelete="SET NULL")),
        sa.Column("classification_id", sa.Integer(), sa.ForeignKey("item_classifications.id", ondelete="SET NULL")),
        sa.Column("nama_material", sa.String(300), nullable=False),
        sa.Column("norm_nama", sa.String(300), nullable=False),
        sa.Column("satuan", sa.String(20), nullable=False),
        sa.Column("spesifikasi", sa.Text()),
        sa.Column("merek", sa.String(100)),
        sa.Column("harga", sa.Numeric(18, 2), nullable=False),
        sa.Column("satuan_jual", sa.String(50)),
        sa.Column("konversi_factor", sa.Numeric(8, 4)),
        sa.Column("harga_standar", sa.Numeric(18, 2), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("page_quote", sa.Text(), nullable=False),
        sa.Column("discovered_via", sa.String(20), nullable=False),
        sa.Column("vendor_provinsi_id", sa.Integer(), sa.ForeignKey("provinsi.id", ondelete="SET NULL")),
        sa.Column("vendor_kota_id", sa.Integer(), sa.ForeignKey("kota_kabupaten.id", ondelete="SET NULL")),
        sa.Column("delivery_scope", sa.String(100)),
        sa.Column("scraped_at", _TS, server_default=sa.func.now()),
        sa.Column("expires_at", _TS),
        sa.Column("tahun", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), server_default="0"),
        sa.Column("is_outlier", sa.Boolean(), server_default=sa.false()),
        sa.Column("variance_from_median", sa.Numeric(8, 4)),
        sa.Column("llm_provider", sa.String(50)),
        sa.Column("llm_model", sa.String(100)),
        sa.Column("llm_reasoning", sa.Text()),
        sa.Column("raw_response", sa.JSON()),
    )
    op.create_index("ix_price_snapshots_norm_nama", "price_snapshots", ["norm_nama"])
    op.create_index("ix_price_snapshots_tahun", "price_snapshots", ["tahun"])
    op.create_index("idx_snap_lookup", "price_snapshots", ["norm_nama", "satuan", "tahun", "expires_at"])
    op.create_index("idx_snap_vendor_cat", "price_snapshots", ["vendor_id", "category_id"])
    op.create_index("idx_snap_location", "price_snapshots", ["vendor_kota_id", "vendor_provinsi_id"])

    op.create_table(
        "price_consensus",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("norm_nama", sa.String(300), nullable=False),
        sa.Column("satuan", sa.String(20), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("item_categories.id", ondelete="SET NULL")),
        sa.Column("provinsi_id", sa.Integer(), sa.ForeignKey("provinsi.id", ondelete="SET NULL")),
        sa.Column("kota_kabupaten_id", sa.Integer(), sa.ForeignKey("kota_kabupaten.id", ondelete="SET NULL")),
        sa.Column("tahun", sa.Integer(), nullable=False),
        sa.Column("n_sources", sa.Integer(), server_default="0"),
        sa.Column("median_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("mean_price", sa.Numeric(18, 2)),
        sa.Column("min_price", sa.Numeric(18, 2)),
        sa.Column("max_price", sa.Numeric(18, 2)),
        sa.Column("std_deviation", sa.Numeric(18, 2)),
        sa.Column("variance_pct", sa.Numeric(6, 2)),
        sa.Column("confidence", sa.Numeric(4, 3), server_default="0"),
        sa.Column("needs_review", sa.Boolean(), server_default=sa.false()),
        sa.Column("contributing_snapshot_ids", sa.JSON()),
        sa.Column("last_computed_at", _TS, server_default=sa.func.now()),
        sa.Column("expires_at", _TS),
        sa.UniqueConstraint("norm_nama", "satuan", "provinsi_id", "kota_kabupaten_id", "tahun"),
    )
    op.create_index("ix_price_consensus_norm_nama", "price_consensus", ["norm_nama"])

    op.create_table(
        "transport_rates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("origin_provinsi_id", sa.Integer(), sa.ForeignKey("provinsi.id", ondelete="CASCADE"), nullable=False),
        sa.Column("origin_kota_id", sa.Integer(), sa.ForeignKey("kota_kabupaten.id", ondelete="SET NULL")),
        sa.Column("dest_provinsi_id", sa.Integer(), sa.ForeignKey("provinsi.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dest_kota_id", sa.Integer(), sa.ForeignKey("kota_kabupaten.id", ondelete="SET NULL")),
        sa.Column("transport_mode", sa.String(30), nullable=False),
        sa.Column("rate_per_kg", sa.Numeric(18, 4)),
        sa.Column("rate_per_m3", sa.Numeric(18, 2)),
        sa.Column("rate_per_ton", sa.Numeric(18, 2)),
        sa.Column("rate_flat_per_truk", sa.Numeric(18, 2)),
        sa.Column("min_charge", sa.Numeric(18, 2)),
        sa.Column("transit_time_days", sa.Integer()),
        sa.Column("source_provider", sa.String(100), nullable=False),
        sa.Column("source_url", sa.String(500)),
        sa.Column("last_scraped_at", _TS),
        sa.UniqueConstraint("origin_provinsi_id", "dest_provinsi_id", "transport_mode", "source_provider"),
    )

    op.create_table(
        "material_logistics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("item_categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("berat_jenis_kg_per_m3", sa.Numeric(18, 2)),
        sa.Column("is_fragile", sa.Boolean(), server_default=sa.false()),
        sa.Column("requires_special_handling", sa.Boolean(), server_default=sa.false()),
        sa.Column("is_oversized", sa.Boolean(), server_default=sa.false()),
        sa.Column("is_hazardous", sa.Boolean(), server_default=sa.false()),
        sa.Column("preferred_mode", sa.String(30)),
        sa.Column("handling_surcharge_pct", sa.Numeric(5, 2), server_default="0"),
        sa.Column("notes", sa.Text()),
        sa.UniqueConstraint("category_id"),
    )

    op.create_table(
        "discovery_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("triggered_by", sa.String(30), nullable=False),
        sa.Column("triggered_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("query_item", sa.String(300), nullable=False),
        sa.Column("query_satuan", sa.String(20)),
        sa.Column("query_provinsi_id", sa.Integer(), sa.ForeignKey("provinsi.id", ondelete="SET NULL")),
        sa.Column("query_kota_id", sa.Integer(), sa.ForeignKey("kota_kabupaten.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(20), server_default="queued"),
        sa.Column("started_at", _TS, server_default=sa.func.now()),
        sa.Column("finished_at", _TS),
        sa.Column("llm_provider", sa.String(50)),
        sa.Column("llm_model", sa.String(100)),
        sa.Column("web_search_queries", sa.JSON()),
        sa.Column("total_input_tokens", sa.Integer(), server_default="0"),
        sa.Column("total_output_tokens", sa.Integer(), server_default="0"),
        sa.Column("estimated_cost_usd", sa.Numeric(10, 4), server_default="0"),
        sa.Column("vendors_discovered", sa.JSON()),
        sa.Column("snapshots_created", sa.JSON()),
        sa.Column("final_consensus_id", sa.Integer(), sa.ForeignKey("price_consensus.id", ondelete="SET NULL")),
        sa.Column("error_log", sa.Text()),
    )

    op.create_table(
        "manual_price_overrides",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("kota_kabupaten_id", sa.Integer(), sa.ForeignKey("kota_kabupaten.id", ondelete="SET NULL")),
        sa.Column("nama_material", sa.String(300), nullable=False),
        sa.Column("norm_nama", sa.String(300), nullable=False),
        sa.Column("satuan", sa.String(20), nullable=False),
        sa.Column("harga", sa.Numeric(18, 2), nullable=False),
        sa.Column("source_label", sa.String(300), nullable=False),
        sa.Column("source_url", sa.String(500)),
        sa.Column("bukti_dukung_file", sa.String(500)),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_until", sa.Date()),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", _TS, server_default=sa.func.now()),
        sa.Column("updated_at", _TS, server_default=sa.func.now()),
    )
    op.create_index("ix_manual_price_overrides_norm_nama", "manual_price_overrides", ["norm_nama"])

    # Project: kolom lokasi
    op.add_column("projects", sa.Column("kota_kabupaten_id", sa.Integer(), nullable=True))
    op.add_column("projects", sa.Column("provinsi_id", sa.Integer(), nullable=True))
    op.add_column("projects", sa.Column("lokasi_detail", sa.String(500), nullable=True))
    op.add_column("projects", sa.Column("tahun_pricing", sa.Integer(), nullable=True))
    op.create_index("ix_projects_kota_kabupaten_id", "projects", ["kota_kabupaten_id"])
    op.create_foreign_key("fk_projects_kota", "projects", "kota_kabupaten", ["kota_kabupaten_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_projects_provinsi", "projects", "provinsi", ["provinsi_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_projects_provinsi", "projects", type_="foreignkey")
    op.drop_constraint("fk_projects_kota", "projects", type_="foreignkey")
    op.drop_index("ix_projects_kota_kabupaten_id", table_name="projects")
    for col in ("tahun_pricing", "lokasi_detail", "provinsi_id", "kota_kabupaten_id"):
        op.drop_column("projects", col)
    for t in (
        "manual_price_overrides", "discovery_jobs", "material_logistics", "transport_rates",
        "price_consensus", "price_snapshots", "vendor_service_areas", "vendor_specialties",
        "vendors", "item_classifications", "item_categories", "umk", "provinsi_adjacency",
        "kota_kabupaten", "provinsi",
    ):
        op.drop_table(t)
