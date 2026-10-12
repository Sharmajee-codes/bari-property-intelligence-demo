from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text

from app.adapters.base import TransientSourceError
from app.models import Listing, Observation, PriceEvent, Property, RawRecord
from app.schemas import Snapshot
from app.services.ingestion import collect_with_retry, ingest
from app.synthetic import SOURCE, START, generate, listing_id

pytestmark = pytest.mark.integration


def sample(day=0, records=None, **kwargs):
    row = generate()[0][0].records[1].copy()
    row["observed_at"] = (START + timedelta(days=day)).isoformat()
    row["asking_price_eur"] = 200000
    return Snapshot(
        source_id=SOURCE,
        observed_at=START + timedelta(days=day),
        scope=[row["municipality"]],
        records=[row] if records is None else records,
        **kwargs,
    )


def count(session, model):
    return session.scalar(select(func.count()).select_from(model))


def test_migration_indexes_and_constraints(session):
    assert session.scalar(text("SELECT version_num FROM alembic_version"))
    assert "GEOS=" in session.scalar(text("SELECT PostGIS_Full_Version()"))
    indexes = (
        session.execute(text("SELECT indexdef FROM pg_indexes WHERE tablename='listings'"))
        .scalars()
        .all()
    )
    assert any("gist" in x and "location" in x for x in indexes)
    assert any("normalized_source_id" in x and "UNIQUE" in x for x in indexes)
    assert (
        "demo_ground_truth"
        in session.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
        .scalars()
        .all()
    )


def test_idempotency_prices_and_original_ids(session):
    first = sample()
    run = ingest(session, first)
    assert ingest(session, first).id == run.id
    assert count(session, Observation) == count(session, PriceEvent) == 1
    second = sample(1)
    second.records[0]["asking_price_eur"] = 185000
    ingest(session, second)
    ingest(session, second)
    third = sample(2)
    third.records[0]["asking_price_eur"] = 185000
    ingest(session, third)
    assert count(session, Observation) == 3 and count(session, PriceEvent) == 2
    price = session.scalar(select(PriceEvent).where(PriceEvent.event_type == "change"))
    assert price.previous_price_eur == Decimal("200000") and price.asking_price_eur == Decimal(
        "185000"
    )
    listing = session.scalar(select(Listing))
    assert listing.original_source_id.startswith(" ") and listing.normalized_source_id == "ad-00001"


@pytest.mark.parametrize(
    "complete,successful,expected",
    [
        (False, True, "active"),
        (True, False, "active"),
        (True, True, "removed"),
    ],
)
def test_disappearance_semantics(session, complete, successful, expected):
    first = sample()
    ingest(session, first)
    last_seen = first.observed_at
    ingest(session, sample(1, records=[], complete=complete, successful=successful))
    listing = session.scalar(select(Listing))
    assert listing.availability == expected and listing.last_seen_at == last_seen
    assert session.scalar(select(Property)).transaction_status == "unknown"
    if expected == "removed":
        obs = session.scalar(select(Observation).where(Observation.inferred.is_(True)))
        assert obs.availability == "removed"


def test_scope_prevents_unrelated_removal(session):
    ingest(session, sample())
    empty = sample(1, records=[])
    empty.scope = ["Conversano"]
    ingest(session, empty)
    assert session.scalar(select(Listing)).availability == "active"


def test_quarantine_and_schema_drift_block_removal(session):
    ingest(session, sample())
    bad = sample(1)
    bad.records[0]["source_listing_id"] = "different"
    bad.records[0]["area_sqm"] = -4
    run = ingest(session, bad)
    assert run.status == "partial" and run.stats["quarantined"] == 1
    assert session.scalar(select(Listing)).availability == "active"
    drift = sample(2)
    drift.records[0]["new_vendor_column"] = True
    assert ingest(session, drift).stats["schema_changes"] == 1
    assert count(session, RawRecord) == 3


def test_duplicate_source_ids_conflicts_and_out_of_order(session):
    first = sample()
    first.records += [dict(first.records[0])]
    run = ingest(session, first)
    assert run.stats["duplicate_source_identifiers"] == 2 and count(session, Listing) == 0
    ingest(session, sample(2))
    older = ingest(session, sample(1))
    assert older.stats["out_of_order"] == 1
    conflict = sample(2)
    conflict.records[0]["asking_price_eur"] = 100000
    assert ingest(session, conflict).stats["quarantined"] == 1
    assert count(session, PriceEvent) == 1


def test_temporarily_unavailable_and_reappearing(session):
    ingest(session, sample())
    temporary = sample(1)
    temporary.records[0]["availability"] = "temporarily_unavailable"
    ingest(session, temporary)
    assert session.scalar(select(Listing)).availability == "temporarily_unavailable"
    ingest(session, sample(2, records=[]))
    ingest(session, sample(3))
    assert session.scalar(select(Listing)).availability == "active"
    assert count(session, PriceEvent) == 1


def test_retry_acquisition_is_bounded():
    class Adapter:
        attempts = 0

        def collect(self):
            self.attempts += 1
            if self.attempts < 3:
                raise TransientSourceError("synthetic timeout")
            return sample()

    adapter = Adapter()
    assert collect_with_retry(adapter).synthetic and adapter.attempts == 3


def test_invalid_coordinates_quarantined(session):
    snapshot = sample()
    snapshot.records[0]["latitude"] = 999
    assert ingest(session, snapshot).stats["quarantined"] == 1
    assert count(session, Listing) == 0


def test_source_identifier_isolation(session):
    snapshot = sample()
    ingest(session, snapshot)
    other = sample()
    other.source_id = "other-synthetic-source"
    other.records[0]["source_id"] = other.source_id
    ingest(session, other)
    assert count(session, Listing) == 2
    assert listing_id(SOURCE, "ad-00001") != listing_id(other.source_id, "ad-00001")


def test_missing_price_does_not_erase_last_known_price(session):
    ingest(session, sample())
    missing = sample(1)
    missing.records[0]["asking_price_eur"] = None
    ingest(session, missing)
    ingest(session, sample(2))
    assert count(session, PriceEvent) == 1
    changed = sample(3)
    changed.records[0]["asking_price_eur"] = 180000
    ingest(session, changed)
    assert count(session, PriceEvent) == 2
    assert session.scalar(
        select(PriceEvent).where(PriceEvent.event_type == "change")
    ).previous_price_eur == Decimal("200000")


def test_unknown_empty_schema_cannot_infer_removal(session):
    ingest(session, sample())
    unknown = sample(1, records=[])
    unknown.schema_version = "future-vendor-schema"
    assert ingest(session, unknown).status == "partial"
    assert session.scalar(select(Listing)).availability == "active"


def test_cli_partial_run_exits_with_error_but_preserves_evidence(session, tmp_path, monkeypatch):
    from contextlib import contextmanager

    from app import cli
    from app.models import IngestionRun

    class TransactionFactory:
        @contextmanager
        def begin(self):
            with session.begin_nested():
                yield session

    monkeypatch.setattr(cli, "SessionLocal", TransactionFactory())
    malformed = sample()
    malformed.records[0]["area_sqm"] = -1
    path = tmp_path / "malformed.json"
    path.write_text(malformed.model_dump_json())
    with pytest.raises(RuntimeError, match="partial"):
        cli.run_cycle(path)
    assert session.scalar(select(IngestionRun)).status == "partial"
    assert count(session, RawRecord) == 1
    assert count(session, Listing) == 0
