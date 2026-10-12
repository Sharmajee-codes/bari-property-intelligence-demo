import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api_models import (
    ComparableView,
    HistoryView,
    MetricsView,
    Page,
    PropertyDetail,
    PropertySummary,
    QualityView,
    RunView,
)
from app.db import get_session
from app.models import Attributes, IngestionRun, Listing, Observation, PriceEvent, Property
from app.services.deduplication import metrics
from app.services.geospatial import ComparableQuery, comparables, public_listing
from app.services.quality import quality_report

DISCLAIMER = (
    "This repository is an independently developed technical demonstration using synthetic data. "
    "It is not affiliated with Immobiliare.it or Gruppo Loseto S.r.l. and does not represent "
    "a completed production deployment."
)
app = FastAPI(
    title="Bari Property Intelligence — Synthetic Demonstration",
    version="0.1.0",
    description=DISCLAIMER + "\n\nAll prices are asking prices in EUR. "
    "Removed listings do not establish a sale. Ground truth is evaluation-only.",
)
DB = Annotated[Session, Depends(get_session)]
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse("app/static/index.html")


@app.get("/health", tags=["Operations"], responses={503: {"description": "Database unavailable"}})
def health(session: DB):
    try:
        version = session.scalar(text("SELECT PostGIS_Version()"))
        migrated = session.scalar(text("SELECT version_num FROM alembic_version"))
        return {"status": "ok", "synthetic": True, "postgis": version, "migration": migrated}
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "unavailable", "synthetic": True})


def listing_view(session: Session, listing: Listing) -> dict:
    data = {
        c.name: getattr(listing, c.name) for c in Listing.__table__.columns if c.name != "location"
    }
    attrs = session.get(Attributes, listing.id)
    data["attributes"] = attrs.values if attrs else {}
    return public_listing(data)


@app.get(
    "/api/v1/properties",
    tags=["Inventory"],
    summary="Paginated deduplicated inventory",
    response_model=Page[PropertySummary],
)
def properties(
    session: DB,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    municipality: str | None = None,
    property_type: Annotated[str | None, Query(pattern="^(apartment|house|villa)$")] = None,
    availability: Annotated[
        str | None, Query(pattern="^(active|temporarily_unavailable|removed)$")
    ] = None,
):
    filters = []
    for field, value in [
        ("municipality", municipality),
        ("property_type", property_type),
        ("availability", availability),
    ]:
        if value is not None:
            filters.append(getattr(Listing, field) == value)
    pids = select(Listing.property_id).where(*filters).distinct()
    all_ids = session.scalars(
        select(Property.id).where(Property.id.in_(pids)).order_by(Property.id)
    ).all()
    items = []
    for pid in all_ids[offset : offset + limit]:
        prop = session.get(Property, pid)
        listing = session.scalar(
            select(Listing)
            .where(Listing.property_id == pid, *filters)
            .order_by((Listing.availability == "active").desc(), Listing.id)
            .limit(1)
        )
        count = len(session.scalars(select(Listing.id).where(Listing.property_id == pid)).all())
        items.append(
            {
                "id": pid,
                "synthetic": True,
                "transaction_status": prop.transaction_status,
                "deduplication_confidence": prop.deduplication_confidence,
                "listing_count": count,
                "representative_listing": listing_view(session, listing),
            }
        )
    return {
        "synthetic": True,
        "total": len(all_ids),
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@app.get(
    "/api/v1/properties/{property_id}",
    response_model=PropertyDetail,
    tags=["Inventory"],
    responses={404: {"description": "Property not found"}},
)
def property_detail(property_id: uuid.UUID, session: DB):
    prop = session.get(Property, property_id)
    if not prop:
        raise HTTPException(404, "Property not found")
    listings = session.scalars(
        select(Listing).where(Listing.property_id == property_id).order_by(Listing.id)
    ).all()
    return {
        "id": prop.id,
        "synthetic": True,
        "transaction_status": prop.transaction_status,
        "deduplication_confidence": prop.deduplication_confidence,
        "listings": [listing_view(session, x) for x in listings],
    }


@app.get(
    "/api/v1/listings/{listing_id}/history",
    response_model=HistoryView,
    tags=["History"],
    description=(
        "Immutable asking-price events and availability observations. Removal never means sold."
    ),
    responses={404: {"description": "Listing not found"}},
)
def history(
    listing_id: uuid.UUID,
    session: DB,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    listing = session.get(Listing, listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    observations = session.scalars(
        select(Observation)
        .where(Observation.listing_id == listing_id)
        .order_by(Observation.observed_at)
    ).all()
    prices = session.scalars(
        select(PriceEvent)
        .where(PriceEvent.listing_id == listing_id)
        .order_by(PriceEvent.observed_at)
    ).all()
    return {
        "listing_id": listing_id,
        "synthetic": True,
        "transaction_status": "unknown",
        "total_observations": len(observations),
        "total_price_events": len(prices),
        "limit": limit,
        "offset": offset,
        "observations": [
            {
                "observed_at": o.observed_at,
                "availability": o.availability,
                "asking_price_eur": o.asking_price_eur,
                "inferred": o.inferred,
            }
            for o in observations[offset : offset + limit]
        ],
        "asking_price_history": [
            {
                "observed_at": p.observed_at,
                "previous_price_eur": p.previous_price_eur,
                "asking_price_eur": p.asking_price_eur,
                "event_type": p.event_type,
            }
            for p in prices[offset : offset + limit]
        ],
    }


@app.get(
    "/api/v1/comparables",
    response_model=ComparableView,
    tags=["Geographic search"],
    description="ST_DWithin in metres; expansion stays within synthetic origin microzone "
    "unless explicitly allowed. Accuracy must be at most half the search radius and 200m.",
)
def search_comparables(query: Annotated[ComparableQuery, Query()], session: DB):
    return comparables(session, query)


@app.get("/api/v1/quality/summary", tags=["Monitoring"], response_model=QualityView)
def quality_summary(session: DB):
    return quality_report(session)


@app.get("/api/v1/ingestion/runs", tags=["Monitoring"], response_model=Page[RunView])
def runs(
    session: DB,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    all_runs = session.scalars(
        select(IngestionRun).order_by(IngestionRun.observed_at.desc(), IngestionRun.id)
    ).all()
    return {
        "synthetic": True,
        "total": len(all_runs),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": r.id,
                "source_id": r.source_id,
                "observed_at": r.observed_at,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
                "complete": r.complete,
                "scope": r.scope,
                "status": r.status,
                "stats": r.stats,
                "synthetic": True,
            }
            for r in all_runs[offset : offset + limit]
        ],
    }


@app.get(
    "/api/v1/deduplication/metrics",
    response_model=MetricsView,
    tags=["Entity resolution"],
    description=(
        "Aggregate evaluation against private synthetic truth; no truth identifiers exposed."
    ),
)
def dedup_metrics(session: DB):
    return metrics(session)
