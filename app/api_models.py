"""Public response contracts deliberately exclude evaluation truth and raw payloads."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PublicListing(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    source_id: str
    agency_id: str
    original_source_id: str
    url: str
    municipality: str
    address: str | None
    description: str
    property_type: str
    asking_price_eur: Decimal | None = Field(
        description="Asking price, never a verified sale price"
    )
    area_sqm: float | None
    rooms: int | None
    floor: int | None
    condition: str | None
    lift: bool | None
    latitude: float | None
    longitude: float | None
    coordinate_accuracy_m: float | None
    coordinate_provenance: str
    availability: Literal["active", "temporarily_unavailable", "removed"]
    published_at: datetime
    first_seen_at: datetime
    last_seen_at: datetime
    state_updated_at: datetime
    synthetic: Literal[True]
    missing_attributes: list[str]
    attributes: dict


class PropertySummary(BaseModel):
    id: uuid.UUID
    synthetic: Literal[True]
    transaction_status: Literal["unknown"]
    deduplication_confidence: float
    listing_count: int
    representative_listing: PublicListing


class PropertyDetail(BaseModel):
    id: uuid.UUID
    synthetic: Literal[True]
    transaction_status: Literal["unknown"]
    deduplication_confidence: float
    listings: list[PublicListing]


class Page[T](BaseModel):
    synthetic: Literal[True]
    total: int
    limit: int
    offset: int
    items: list[T]


class RunView(BaseModel):
    id: uuid.UUID
    source_id: str
    observed_at: datetime
    started_at: datetime
    finished_at: datetime
    complete: bool
    scope: list[str]
    status: str
    stats: dict[str, int]
    synthetic: Literal[True]


class ObservationView(BaseModel):
    observed_at: datetime
    availability: str
    asking_price_eur: Decimal | None
    inferred: bool


class PriceView(BaseModel):
    observed_at: datetime
    previous_price_eur: Decimal | None
    asking_price_eur: Decimal
    event_type: Literal["initial", "change"]


class HistoryView(BaseModel):
    listing_id: uuid.UUID
    synthetic: Literal[True]
    transaction_status: Literal["unknown"]
    total_observations: int
    total_price_events: int
    limit: int
    offset: int
    observations: list[ObservationView]
    asking_price_history: list[PriceView]


class ComparableItem(PublicListing):
    distance_m: float
    microzone_id: str | None
    deduplication_confidence: float
    coordinate_accuracy_indicator: str
    transaction_status: Literal["unknown"]


class ComparableView(BaseModel):
    synthetic: Literal[True]
    search_radius_used_m: float
    attempted_radii_m: list[float]
    origin_microzone: str | None
    cross_microzone_allowed: bool
    cross_microzone_expansion: bool
    coordinate_accuracy_limit_m: float
    comparable_listing_count: int
    count_basis: str
    minimum_met: bool
    asking_price_statistics_eur: dict[str, float | int | None]
    items: list[ComparableItem]
    limit: int
    offset: int
    data_limitations: list[str]


class MetricsView(BaseModel):
    synthetic: Literal[True]
    evaluation: str
    labeled_listings: int
    unlabeled_listings: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float | None
    recall: float | None
    f1: float | None


class QualityView(BaseModel):
    model_config = ConfigDict(extra="allow")
    synthetic: Literal[True]
    validation_label: str
    as_of: datetime | None
    simulation_days: int
    total_raw_listings: int
    distinct_source_advertisements: int
    unique_deduplicated_properties: int
    active_advertisements: int
    removed_advertisements: int
    price_change_events: int
    missing_field_percentages: dict[str, float]
    coordinate_accuracy_distribution: dict[str, int]
    deduplication: MetricsView
    ingestion: dict
    data_freshness: dict
    costs: dict
    alerts: list[dict]
    data_limitations: list[str]
