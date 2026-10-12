import uuid
from datetime import datetime
from decimal import Decimal

from geoalchemy2 import Geography, Geometry
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "data_sources"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str]
    schema_version: Mapped[str]
    synthetic: Mapped[bool] = mapped_column(default=True)


class Agency(Base):
    __tablename__ = "agencies"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str]
    synthetic: Mapped[bool] = mapped_column(default=True)


class Property(Base):
    __tablename__ = "properties"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    representative_listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True)
    deduplication_confidence: Mapped[float] = mapped_column(Float, default=1.0)
    transaction_status: Mapped[str] = mapped_column(default="unknown")
    synthetic: Mapped[bool] = mapped_column(default=True)
    __table_args__ = (CheckConstraint("transaction_status = 'unknown'"),)


class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"))
    agency_id: Mapped[str] = mapped_column(ForeignKey("agencies.id"))
    original_source_id: Mapped[str]
    normalized_source_id: Mapped[str]
    url: Mapped[str]
    municipality: Mapped[str] = mapped_column(index=True)
    address: Mapped[str | None]
    description: Mapped[str]
    property_type: Mapped[str] = mapped_column(index=True)
    asking_price_eur: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    area_sqm: Mapped[float | None]
    rooms: Mapped[int | None]
    floor: Mapped[int | None]
    condition: Mapped[str | None]
    lift: Mapped[bool | None]
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    location: Mapped[object | None] = mapped_column(Geography("POINT", srid=4326))
    coordinate_accuracy_m: Mapped[float | None]
    coordinate_provenance: Mapped[str]
    availability: Mapped[str] = mapped_column(index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    state_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    synthetic: Mapped[bool] = mapped_column(default=True)
    __table_args__ = (
        UniqueConstraint("source_id", "normalized_source_id"),
        CheckConstraint("area_sqm IS NULL OR area_sqm > 0"),
        CheckConstraint("asking_price_eur IS NULL OR asking_price_eur > 0"),
        CheckConstraint("latitude IS NULL OR latitude BETWEEN -90 AND 90"),
        CheckConstraint("longitude IS NULL OR longitude BETWEEN -180 AND 180"),
        CheckConstraint("coordinate_accuracy_m IS NULL OR coordinate_accuracy_m > 0"),
        CheckConstraint("availability IN ('active','temporarily_unavailable','removed')"),
        CheckConstraint("synthetic = true"),
        Index("ix_listing_type_area", "property_type", "area_sqm"),
    )


class Attributes(Base):
    __tablename__ = "property_attributes"
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), primary_key=True)
    values: Mapped[dict] = mapped_column(JSONB)


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id"))
    fingerprint: Mapped[str] = mapped_column(unique=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    complete: Mapped[bool]
    scope: Mapped[list] = mapped_column(JSONB)
    status: Mapped[str]
    stats: Mapped[dict] = mapped_column(JSONB)
    synthetic: Mapped[bool] = mapped_column(default=True)


class RawRecord(Base):
    __tablename__ = "raw_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingestion_runs.id"), index=True)
    ordinal: Mapped[int]
    payload: Mapped[dict] = mapped_column(JSONB)
    quarantine_reason: Mapped[str | None]
    synthetic: Mapped[bool] = mapped_column(default=True)
    __table_args__ = (UniqueConstraint("run_id", "ordinal"),)


class Observation(Base):
    __tablename__ = "listing_observations"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingestion_runs.id"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    asking_price_eur: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    availability: Mapped[str]
    normalized_payload: Mapped[dict] = mapped_column(JSONB)
    inferred: Mapped[bool] = mapped_column(default=False)
    synthetic: Mapped[bool] = mapped_column(default=True)
    __table_args__ = (UniqueConstraint("listing_id", "observed_at"),)


class PriceEvent(Base):
    __tablename__ = "price_history"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), index=True)
    observation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("listing_observations.id"), unique=True
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    previous_price_eur: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    asking_price_eur: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    event_type: Mapped[str]
    synthetic: Mapped[bool] = mapped_column(default=True)


class Candidate(Base):
    __tablename__ = "deduplication_candidates"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    left_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), index=True)
    right_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"))
    features: Mapped[dict] = mapped_column(JSONB)
    feature_scores: Mapped[dict] = mapped_column(JSONB)
    score: Mapped[float]
    rule_version: Mapped[str]
    __table_args__ = (UniqueConstraint("left_id", "right_id", "rule_version"),)


class Decision(Base):
    __tablename__ = "deduplication_decisions"
    id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deduplication_candidates.id"), primary_key=True
    )
    classification: Mapped[str] = mapped_column(index=True)
    merged: Mapped[bool]
    reason: Mapped[str]
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rule_version: Mapped[str]


class GroundTruth(Base):
    __tablename__ = "demo_ground_truth"
    listing_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("listings.id"), primary_key=True)
    truth_property_id: Mapped[str] = mapped_column(index=True)


class Microzone(Base):
    __tablename__ = "microzones"
    id: Mapped[str] = mapped_column(primary_key=True)
    municipality: Mapped[str]
    boundary: Mapped[object] = mapped_column(Geometry("POLYGON", srid=4326))
    synthetic: Mapped[bool] = mapped_column(default=True)


class QualityResult(Base):
    __tablename__ = "data_quality_results"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    report: Mapped[dict] = mapped_column(JSONB)
    synthetic: Mapped[bool] = mapped_column(default=True)


class SourceCost(Base):
    __tablename__ = "source_costs"
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ingestion_runs.id"), primary_key=True)
    provider_eur: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    processing_eur: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
