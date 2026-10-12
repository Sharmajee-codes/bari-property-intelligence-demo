from statistics import mean, median

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Microzone
from app.synthetic import CENTERS

LIMITATIONS = [
    "All records and microzone boundaries are synthetic demonstration data.",
    "Statistics describe asking prices, not completed sales or verified market values.",
    "Coordinate accuracy is a declared synthetic error bound, not a measured geocode guarantee.",
    "Conservative deduplication may leave probable duplicates counted separately.",
]


class ComparableQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    initial_radius_m: float = Field(50, ge=10, le=10000)
    max_radius_m: float = Field(1000, ge=10, le=10000)
    min_comparables: int = Field(5, ge=1, le=100)
    property_type: str | None = Field(None, pattern="^(apartment|house|villa)$")
    min_area_sqm: float | None = Field(None, gt=0)
    max_area_sqm: float | None = Field(None, gt=0)
    min_price_eur: float | None = Field(None, gt=0)
    max_price_eur: float | None = Field(None, gt=0)
    condition: str | None = Field(None, pattern="^(renovated|good|needs_renovation)$")
    floor: int | None = Field(None, ge=-1, le=30)
    lift: bool | None = None
    allow_cross_microzone: bool = False
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)

    @model_validator(mode="after")
    def ranges(self):
        if self.initial_radius_m > self.max_radius_m:
            raise ValueError("initial radius must not exceed maximum radius")
        for low, high in [("min_area_sqm", "max_area_sqm"), ("min_price_eur", "max_price_eur")]:
            if getattr(self, low) is not None and getattr(self, high) is not None:
                if getattr(self, low) > getattr(self, high):
                    raise ValueError(f"{low} must not exceed {high}")
        return self


def initialize_microzones(session: Session) -> None:
    # Two configurable fictional rectangular zones per municipality. No official cadastral claim.
    for city, (lat, lon) in CENTERS.items():
        for side, left, right in [("west", lon - 0.016, lon), ("east", lon, lon + 0.016)]:
            lo, hi = lat - 0.012, lat + 0.012
            polygon = (
                f"SRID=4326;POLYGON(({left} {lo},{right} {lo},"
                f"{right} {hi},{left} {hi},{left} {lo}))"
            )
            session.execute(
                insert(Microzone)
                .values(id=f"{city}:{side}", municipality=city, boundary=polygon, synthetic=True)
                .on_conflict_do_nothing(index_elements=["id"])
            )


def public_listing(row: dict) -> dict:
    fields = [
        "id",
        "property_id",
        "source_id",
        "agency_id",
        "original_source_id",
        "url",
        "municipality",
        "address",
        "description",
        "property_type",
        "asking_price_eur",
        "area_sqm",
        "rooms",
        "floor",
        "condition",
        "lift",
        "latitude",
        "longitude",
        "coordinate_accuracy_m",
        "coordinate_provenance",
        "availability",
        "published_at",
        "first_seen_at",
        "last_seen_at",
        "state_updated_at",
        "synthetic",
    ]
    data = {k: row[k] for k in fields}
    data["missing_attributes"] = [
        k
        for k in ("asking_price_eur", "area_sqm", "rooms", "floor", "condition", "lift", "address")
        if row[k] is None
    ]
    data["attributes"] = row.get("attributes", {})
    return data


def comparables(session: Session, query: ComparableQuery) -> dict:
    origin = func.ST_SetSRID(func.ST_MakePoint(query.longitude, query.latitude), 4326)
    origin_zone = session.scalar(
        select(Microzone.id)
        .where(func.ST_Covers(Microzone.boundary, origin))
        .order_by(Microzone.id)
        .limit(1)
    )
    filters = [
        "l.availability = 'active'",
        "l.asking_price_eur IS NOT NULL",
        "l.area_sqm IS NOT NULL",
        "l.location IS NOT NULL",
        "l.coordinate_accuracy_m <= :accuracy",
        "ST_DWithin(l.location, "
        "CAST(ST_SetSRID(ST_MakePoint(:lon,:lat),4326) AS geography), :radius)",
    ]
    params = {"lon": query.longitude, "lat": query.latitude}
    for name, sql in {
        "property_type": "l.property_type = :property_type",
        "condition": "l.condition = :condition",
        "floor": "l.floor = :floor",
        "lift": "l.lift = :lift",
        "min_area_sqm": "l.area_sqm >= :min_area_sqm",
        "max_area_sqm": "l.area_sqm <= :max_area_sqm",
        "min_price_eur": "l.asking_price_eur >= :min_price_eur",
        "max_price_eur": "l.asking_price_eur <= :max_price_eur",
    }.items():
        value = getattr(query, name)
        if value is not None:
            params[name] = value
            filters.append(sql)
    if not query.allow_cross_microzone:
        if origin_zone:
            filters.append(
                "ST_Covers((SELECT boundary FROM microzones WHERE id=:zone), l.location::geometry)"
            )
            params["zone"] = origin_zone
        else:
            filters.append("FALSE")
    radius = query.initial_radius_m
    attempted = []
    while True:
        params.update(radius=radius, accuracy=min(200, radius / 2))
        attempted.append(radius)
        # One representative advertisement per inferred property; price preference is never used.
        rows = (
            session.execute(
                text(
                    """
            SELECT DISTINCT ON (l.property_id) l.*, a.values AS attributes,
              p.deduplication_confidence,
              ST_Distance(l.location,
                CAST(ST_SetSRID(ST_MakePoint(:lon,:lat),4326) AS geography)) AS distance_m,
              (SELECT id FROM microzones z WHERE ST_Covers(z.boundary, l.location::geometry)
               ORDER BY id LIMIT 1) AS microzone_id
            FROM listings l JOIN properties p ON p.id=l.property_id
            JOIN property_attributes a ON a.listing_id=l.id
            WHERE """
                    + " AND ".join(filters)
                    + """
            ORDER BY l.property_id, l.coordinate_accuracy_m, l.last_seen_at DESC, l.id
        """
                ),
                params,
            )
            .mappings()
            .all()
        )
        if len(rows) >= query.min_comparables or radius >= query.max_radius_m:
            break
        radius = min(query.max_radius_m, radius * 2)
    rows = sorted(rows, key=lambda r: (r["distance_m"], str(r["id"])))
    prices = [float(r["asking_price_eur"]) for r in rows]
    items = []
    for row in rows[query.offset : query.offset + query.limit]:
        item = public_listing(row)
        item.update(
            distance_m=round(row["distance_m"], 2),
            microzone_id=row["microzone_id"],
            deduplication_confidence=row["deduplication_confidence"],
            coordinate_accuracy_indicator="precise"
            if row["coordinate_accuracy_m"] <= 20
            else "approximate",
            transaction_status="unknown",
        )
        items.append(item)
    return {
        "synthetic": True,
        "search_radius_used_m": radius,
        "attempted_radii_m": attempted,
        "origin_microzone": origin_zone,
        "cross_microzone_allowed": query.allow_cross_microzone,
        "cross_microzone_expansion": any(r["microzone_id"] != origin_zone for r in rows),
        "coordinate_accuracy_limit_m": min(200, radius / 2),
        "comparable_listing_count": len(rows),
        "count_basis": "one advertisement per deduplicated property",
        "minimum_met": len(rows) >= query.min_comparables,
        "asking_price_statistics_eur": {
            "count": len(prices),
            "mean": round(mean(prices), 2) if prices else None,
            "median": median(prices) if prices else None,
            "min": min(prices) if prices else None,
            "max": max(prices) if prices else None,
        },
        "items": items,
        "limit": query.limit,
        "offset": query.offset,
        "data_limitations": LIMITATIONS,
    }
