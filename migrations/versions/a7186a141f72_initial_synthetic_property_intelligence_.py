"""initial synthetic property intelligence schema"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a7186a141f72"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.create_table(
        "agencies",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "data_quality_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "data_sources",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "microzones",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("municipality", sa.String(), nullable=False),
        sa.Column(
            "boundary",
            geoalchemy2.types.Geometry(
                geometry_type="POLYGON",
                srid=4326,
                dimension=2,
                spatial_index=False,
                from_text="ST_GeomFromEWKT",
                name="geometry",
                nullable=False,
            ),
            nullable=False,
        ),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_microzones_boundary", "microzones", ["boundary"], unique=False, postgresql_using="gist"
    )
    op.create_table(
        "properties",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("representative_listing_id", sa.UUID(), nullable=False),
        sa.Column("deduplication_confidence", sa.Float(), nullable=False),
        sa.Column("transaction_status", sa.String(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.CheckConstraint("transaction_status = 'unknown'"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("representative_listing_id"),
    )
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.String(length=80), nullable=False),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("complete", sa.Boolean(), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint"),
    )
    op.create_table(
        "listings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("property_id", sa.UUID(), nullable=False),
        sa.Column("source_id", sa.String(length=80), nullable=False),
        sa.Column("agency_id", sa.String(length=80), nullable=False),
        sa.Column("original_source_id", sa.String(), nullable=False),
        sa.Column("normalized_source_id", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("municipality", sa.String(), nullable=False),
        sa.Column("address", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("property_type", sa.String(), nullable=False),
        sa.Column("asking_price_eur", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("rooms", sa.Integer(), nullable=True),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("condition", sa.String(), nullable=True),
        sa.Column("lift", sa.Boolean(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column(
            "location",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                spatial_index=False,
                from_text="ST_GeogFromText",
                name="geography",
            ),
            nullable=True,
        ),
        sa.Column("coordinate_accuracy_m", sa.Float(), nullable=True),
        sa.Column("coordinate_provenance", sa.String(), nullable=False),
        sa.Column("availability", sa.String(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.CheckConstraint("availability IN ('active','temporarily_unavailable','removed')"),
        sa.CheckConstraint("area_sqm IS NULL OR area_sqm > 0"),
        sa.CheckConstraint("asking_price_eur IS NULL OR asking_price_eur > 0"),
        sa.CheckConstraint("coordinate_accuracy_m IS NULL OR coordinate_accuracy_m > 0"),
        sa.CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90"),
        sa.CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180"),
        sa.CheckConstraint("synthetic = true"),
        sa.ForeignKeyConstraint(
            ["agency_id"],
            ["agencies.id"],
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "normalized_source_id"),
    )
    op.create_index(
        "idx_listings_location", "listings", ["location"], unique=False, postgresql_using="gist"
    )
    op.create_index("ix_listing_type_area", "listings", ["property_type", "area_sqm"], unique=False)
    op.create_index(op.f("ix_listings_availability"), "listings", ["availability"], unique=False)
    op.create_index(op.f("ix_listings_last_seen_at"), "listings", ["last_seen_at"], unique=False)
    op.create_index(op.f("ix_listings_municipality"), "listings", ["municipality"], unique=False)
    op.create_index(op.f("ix_listings_property_id"), "listings", ["property_id"], unique=False)
    op.create_index(op.f("ix_listings_property_type"), "listings", ["property_type"], unique=False)
    op.create_table(
        "deduplication_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("left_id", sa.UUID(), nullable=False),
        sa.Column("right_id", sa.UUID(), nullable=False),
        sa.Column("features", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("feature_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("rule_version", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["left_id"],
            ["listings.id"],
        ),
        sa.ForeignKeyConstraint(
            ["right_id"],
            ["listings.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("left_id", "right_id", "rule_version"),
    )
    op.create_index(
        op.f("ix_deduplication_candidates_left_id"),
        "deduplication_candidates",
        ["left_id"],
        unique=False,
    )
    op.create_table(
        "demo_ground_truth",
        sa.Column("listing_id", sa.UUID(), nullable=False),
        sa.Column("truth_property_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.id"],
        ),
        sa.PrimaryKeyConstraint("listing_id"),
    )
    op.create_index(
        op.f("ix_demo_ground_truth_truth_property_id"),
        "demo_ground_truth",
        ["truth_property_id"],
        unique=False,
    )
    op.create_table(
        "listing_observations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("listing_id", sa.UUID(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("asking_price_eur", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("availability", sa.String(), nullable=False),
        sa.Column("normalized_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("inferred", sa.Boolean(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.id"],
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["ingestion_runs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("listing_id", "observed_at"),
    )
    op.create_index(
        op.f("ix_listing_observations_listing_id"),
        "listing_observations",
        ["listing_id"],
        unique=False,
    )
    op.create_table(
        "property_attributes",
        sa.Column("listing_id", sa.UUID(), nullable=False),
        sa.Column("values", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.id"],
        ),
        sa.PrimaryKeyConstraint("listing_id"),
    )
    op.create_table(
        "raw_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quarantine_reason", sa.String(), nullable=True),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["ingestion_runs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "ordinal"),
    )
    op.create_index(op.f("ix_raw_records_run_id"), "raw_records", ["run_id"], unique=False)
    op.create_table(
        "source_costs",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("provider_eur", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("processing_eur", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("simulated", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["ingestion_runs.id"],
        ),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_table(
        "deduplication_decisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("classification", sa.String(), nullable=False),
        sa.Column("merged", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rule_version", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["id"],
            ["deduplication_candidates.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_deduplication_decisions_classification"),
        "deduplication_decisions",
        ["classification"],
        unique=False,
    )
    op.create_table(
        "price_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("listing_id", sa.UUID(), nullable=False),
        sa.Column("observation_id", sa.UUID(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_price_eur", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("asking_price_eur", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.id"],
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"],
            ["listing_observations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("observation_id"),
    )
    op.create_index(
        op.f("ix_price_history_listing_id"), "price_history", ["listing_id"], unique=False
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_price_history_listing_id"), table_name="price_history")
    op.drop_table("price_history")
    op.drop_index(
        op.f("ix_deduplication_decisions_classification"), table_name="deduplication_decisions"
    )
    op.drop_table("deduplication_decisions")
    op.drop_table("source_costs")
    op.drop_index(op.f("ix_raw_records_run_id"), table_name="raw_records")
    op.drop_table("raw_records")
    op.drop_table("property_attributes")
    op.drop_index(op.f("ix_listing_observations_listing_id"), table_name="listing_observations")
    op.drop_table("listing_observations")
    op.drop_index(op.f("ix_demo_ground_truth_truth_property_id"), table_name="demo_ground_truth")
    op.drop_table("demo_ground_truth")
    op.drop_index(
        op.f("ix_deduplication_candidates_left_id"), table_name="deduplication_candidates"
    )
    op.drop_table("deduplication_candidates")
    op.drop_index(op.f("ix_listings_property_type"), table_name="listings")
    op.drop_index(op.f("ix_listings_property_id"), table_name="listings")
    op.drop_index(op.f("ix_listings_municipality"), table_name="listings")
    op.drop_index(op.f("ix_listings_last_seen_at"), table_name="listings")
    op.drop_index(op.f("ix_listings_availability"), table_name="listings")
    op.drop_index("ix_listing_type_area", table_name="listings")
    op.drop_index("idx_listings_location", table_name="listings", postgresql_using="gist")
    op.drop_table("listings")
    op.drop_table("ingestion_runs")
    op.drop_table("properties")
    op.drop_index("idx_microzones_boundary", table_name="microzones", postgresql_using="gist")
    op.drop_table("microzones")
    op.drop_table("data_sources")
    op.drop_table("data_quality_results")
    op.drop_table("agencies")
    # ### end Alembic commands ###
