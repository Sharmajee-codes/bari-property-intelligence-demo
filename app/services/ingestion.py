import hashlib
import uuid
from collections import Counter
from datetime import UTC, datetime

from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.adapters.base import SourceAdapter, TransientSourceError
from app.config import settings
from app.logging import event
from app.models import (
    Agency,
    Attributes,
    IngestionRun,
    Listing,
    Observation,
    PriceEvent,
    Property,
    RawRecord,
    Source,
    SourceCost,
)
from app.schemas import ListingRecord, Snapshot
from app.synthetic import listing_id, stable_id

ATTRIBUTES = (
    "bathrooms",
    "balcony",
    "terrace",
    "parking",
    "storage",
    "garden",
    "building_year",
    "building_units",
    "energy_class",
)
CURRENT = (
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
)


@retry(
    retry=retry_if_exception_type(TransientSourceError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.1, max=1),
    reraise=True,
)
def collect_with_retry(adapter: SourceAdapter) -> Snapshot:
    return adapter.collect()


def point(lat: float | None, lon: float | None) -> str | None:
    return None if lat is None else f"SRID=4326;POINT({lon} {lat})"


def ingest(session: Session, snapshot: Snapshot) -> IngestionRun:
    """Atomic snapshot ingestion. Caller owns commit/rollback; writer lock serializes histories."""
    session.execute(text("SELECT pg_advisory_xact_lock(742018)"))
    fingerprint = hashlib.sha256(snapshot.model_dump_json().encode()).hexdigest()
    existing = session.scalar(select(IngestionRun).where(IngestionRun.fingerprint == fingerprint))
    if existing:
        event("ingestion_replay", run_id=existing.id)
        return existing
    source = session.get(Source, snapshot.source_id)
    if source is None:
        source = Source(
            id=snapshot.source_id, name="Fictional synthetic inventory network", schema_version="1"
        )
        session.add(source)
        session.flush()
    now = datetime.now(UTC)
    run = IngestionRun(
        id=stable_id(f"run:{fingerprint}"),
        source_id=source.id,
        fingerprint=fingerprint,
        observed_at=snapshot.observed_at,
        started_at=now,
        finished_at=now,
        complete=snapshot.complete,
        scope=snapshot.scope,
        status="running",
        stats={},
    )
    session.add(run)
    session.flush()
    stats = dict(
        raw_records=len(snapshot.records),
        accepted=0,
        quarantined=0,
        observations=0,
        price_changes=0,
        inferred_removals=0,
        duplicate_source_identifiers=0,
        schema_changes=int(snapshot.schema_version != source.schema_version),
        out_of_order=0,
    )
    ids = Counter(str(r.get("source_listing_id", "")).strip().casefold() for r in snapshot.records)
    seen: set[uuid.UUID] = set()
    for ordinal, payload in enumerate(snapshot.records):
        raw = RawRecord(run_id=run.id, ordinal=ordinal, payload=payload)
        session.add(raw)
        try:
            if not snapshot.successful:
                raise ValueError("source response explicitly unsuccessful")
            if snapshot.schema_version != source.schema_version:
                stats["schema_changes"] += 1
                raise ValueError(f"unsupported source schema version {snapshot.schema_version}")
            rec = ListingRecord.model_validate(payload)
            if rec.source_id != source.id or rec.municipality not in snapshot.scope:
                raise ValueError("record outside declared source/snapshot scope")
            if rec.observed_at != snapshot.observed_at:
                raise ValueError("observation timestamp differs from snapshot")
            if ids[rec.source_listing_id.strip().casefold()] > 1:
                stats["duplicate_source_identifiers"] += 1
                raise ValueError("ambiguous duplicate source identifier in snapshot")
            lid = listing_id(rec.source_id, rec.source_listing_id)
            seen.add(lid)
            listing = session.get(Listing, lid)
            oid = stable_id(f"observation:{lid}:{rec.observed_at.isoformat()}")
            old_obs = session.get(Observation, oid)
            normalized = rec.model_dump(mode="json")
            if old_obs:
                if old_obs.normalized_payload != normalized or old_obs.inferred:
                    raise ValueError("conflicting content at an already observed timestamp")
                stats["accepted"] += 1
                continue
            if listing and rec.observed_at <= listing.state_updated_at:
                stats["out_of_order"] += 1
                raise ValueError(
                    "out-of-order observation; replay chronologically to import history"
                )
            if session.get(Agency, rec.agency_id) is None:
                session.add(Agency(id=rec.agency_id, name=f"Fictional agency {rec.agency_id}"))
                session.flush()
            previous = (
                session.scalar(
                    select(PriceEvent.asking_price_eur)
                    .where(PriceEvent.listing_id == lid)
                    .order_by(PriceEvent.observed_at.desc())
                    .limit(1)
                )
                if listing
                else None
            )
            if listing is None:
                pid = stable_id(f"property:{lid}")
                session.add(Property(id=pid, representative_listing_id=lid))
                session.flush()
                listing = Listing(
                    id=lid,
                    property_id=pid,
                    source_id=rec.source_id,
                    agency_id=rec.agency_id,
                    original_source_id=rec.source_listing_id,
                    normalized_source_id=rec.source_listing_id.strip().casefold(),
                    url=rec.url,
                    published_at=rec.published_at,
                    first_seen_at=rec.observed_at,
                )
                session.add(listing)
            elif listing.agency_id != rec.agency_id:
                raise ValueError("source identifier cannot change agency ownership")
            for field in CURRENT:
                setattr(listing, field, getattr(rec, field))
            listing.url = rec.url
            listing.last_seen_at = rec.observed_at
            listing.state_updated_at = rec.observed_at
            listing.location = point(rec.latitude, rec.longitude)
            session.flush()
            attrs = session.get(Attributes, lid)
            if attrs is None:
                attrs = Attributes(listing_id=lid)
                session.add(attrs)
            attrs.values = {k: normalized[k] for k in ATTRIBUTES}
            session.add(
                Observation(
                    id=oid,
                    listing_id=lid,
                    run_id=run.id,
                    observed_at=rec.observed_at,
                    asking_price_eur=rec.asking_price_eur,
                    availability=rec.availability,
                    normalized_payload=normalized,
                )
            )
            session.flush()
            if rec.asking_price_eur is not None and previous != rec.asking_price_eur:
                session.add(
                    PriceEvent(
                        id=stable_id(f"price:{oid}"),
                        listing_id=lid,
                        observation_id=oid,
                        observed_at=rec.observed_at,
                        previous_price_eur=previous,
                        asking_price_eur=rec.asking_price_eur,
                        event_type="initial" if previous is None else "change",
                    )
                )
                stats["price_changes"] += int(previous is not None)
            stats["observations"] += 1
            stats["accepted"] += 1
        except (ValidationError, ValueError) as exc:
            raw.quarantine_reason = str(exc)
            stats["quarantined"] += 1
            if isinstance(exc, ValidationError) and any(
                e["type"] == "extra_forbidden" for e in exc.errors()
            ):
                stats["schema_changes"] += 1
            event("record_quarantined", run_id=run.id, ordinal=ordinal, reason=str(exc))
    # Any quarantine blocks inferred absence: a malformed row may be the missing listing.
    if (
        snapshot.complete
        and snapshot.successful
        and stats["quarantined"] == 0
        and snapshot.schema_version == source.schema_version
    ):
        listings = session.scalars(
            select(Listing).where(
                Listing.source_id == source.id,
                Listing.municipality.in_(snapshot.scope),
                Listing.availability != "removed",
                Listing.state_updated_at < snapshot.observed_at,
            )
        ).all()
        for listing in listings:
            if listing.id in seen:
                continue
            oid = stable_id(f"observation:{listing.id}:{snapshot.observed_at.isoformat()}")
            session.add(
                Observation(
                    id=oid,
                    listing_id=listing.id,
                    run_id=run.id,
                    observed_at=snapshot.observed_at,
                    asking_price_eur=listing.asking_price_eur,
                    availability="removed",
                    normalized_payload={
                        "synthetic": True,
                        "reason": "absent from complete successful scope",
                    },
                    inferred=True,
                )
            )
            listing.availability = "removed"
            listing.state_updated_at = snapshot.observed_at
            # last_seen_at intentionally remains the last actual observation.
            stats["inferred_removals"] += 1
    run.stats = stats
    run.status = (
        "failed"
        if not snapshot.successful
        else ("partial" if stats["quarantined"] or stats["schema_changes"] else "success")
    )
    run.finished_at = datetime.now(UTC)
    session.add(
        SourceCost(
            run_id=run.id,
            provider_eur=len(snapshot.records) * settings.simulated_provider_per_record_eur,
            processing_eur=settings.simulated_processing_per_run_eur,
        )
    )
    session.flush()
    event("ingestion_finished", run_id=run.id, status=run.status, **stats)
    return run
