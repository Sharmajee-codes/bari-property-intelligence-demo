from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ListingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    synthetic: Literal[True]
    source_id: str = Field(min_length=1, max_length=80)
    source_listing_id: str = Field(min_length=1, max_length=100)
    agency_id: str = Field(min_length=1, max_length=80)
    url: str
    municipality: str
    address: str | None
    description: str
    property_type: Literal["apartment", "house", "villa"]
    asking_price_eur: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    area_sqm: float | None = Field(default=None, gt=0, le=2000)
    rooms: int | None = Field(default=None, ge=1, le=30)
    bathrooms: int | None = Field(default=None, ge=1, le=10)
    floor: int | None = Field(default=None, ge=-1, le=30)
    lift: bool | None = None
    condition: Literal["renovated", "good", "needs_renovation"] | None = None
    balcony: bool | None = None
    terrace: bool | None = None
    parking: bool | None = None
    storage: bool | None = None
    garden: bool | None = None
    building_year: int | None = Field(default=None, ge=1800, le=2026)
    building_units: int | None = Field(default=None, ge=1, le=200)
    energy_class: Literal["A", "B", "C", "D", "E", "F", "G"] | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    coordinate_accuracy_m: float | None = Field(default=None, gt=0, le=10000)
    coordinate_provenance: Literal["synthetic_exact", "synthetic_approximate"]
    availability: Literal["active", "temporarily_unavailable", "removed"] = "active"
    published_at: datetime
    observed_at: datetime

    @model_validator(mode="after")
    def consistency(self):
        from urllib.parse import urlparse

        if not (urlparse(self.url).hostname or "").endswith(".invalid"):
            raise ValueError("Only fictional .invalid listing URLs are accepted")
        if not self.source_listing_id.strip():
            raise ValueError("empty normalized source identifier")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("coordinates require both latitude and longitude")
        if self.latitude is not None and self.coordinate_accuracy_m is None:
            raise ValueError("coordinate accuracy is required with coordinates")
        if self.observed_at.tzinfo is None or self.published_at.tzinfo is None:
            raise ValueError("timestamps must include timezones")
        if self.published_at > self.observed_at:
            raise ValueError("publication cannot follow observation")
        return self


class Snapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    synthetic: Literal[True] = True
    source_id: str
    schema_version: str = "1"
    observed_at: datetime
    complete: bool = True
    successful: bool = True
    scope: list[str]
    records: list[dict]

    @model_validator(mode="after")
    def valid_inventory(self):
        if self.observed_at.tzinfo is None or not self.scope:
            raise ValueError("snapshot requires a timezone and a nonempty explicit scope")
        return self
