import pytest
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.models import GroundTruth, Listing
from app.services.deduplication import MatchRules, metrics, resolve, score_pair
from app.services.ingestion import ingest
from app.services.quality import quality_report, save_report
from app.synthetic import generate

pytestmark = pytest.mark.integration


def scored_listing(**kwargs):
    defaults = dict(
        latitude=41.1,
        longitude=16.8,
        area_sqm=100,
        address="SYNTHETIC block 1",
        property_type="apartment",
        floor=2,
        rooms=3,
        lift=True,
        condition="good",
        coordinate_accuracy_m=8,
        agency_id="fictional-a",
    )
    return Listing(**(defaults | kwargs))


def test_scoring_hard_negative_and_uncertain():
    left = scored_listing()
    right = scored_listing(agency_id="fictional-b", area_sqm=101)
    result = score_pair(left, right, MatchRules())
    assert result["classification"] == "confirmed" and result["score"] >= 0.9
    assert set(result["feature_scores"]) == set(MatchRules().weights)
    different_floor = scored_listing(agency_id="fictional-b", floor=3)
    assert score_pair(left, different_floor, MatchRules())["classification"] == "non_match"
    coarse = scored_listing(agency_id="fictional-b", coordinate_accuracy_m=600)
    assert score_pair(left, coarse, MatchRules())["classification"] == "probable"


def load_evaluation_truth(session, truth):
    for lid in session.scalars(select(Listing.id)).all():
        session.execute(
            insert(GroundTruth).values(listing_id=lid, truth_property_id=truth[str(lid)])
        )


def test_full_three_cycle_metrics_and_replay(session, tmp_path):
    snapshots, truth = generate()
    for snap in snapshots:
        assert ingest(session, snap).status == "success"
    load_evaluation_truth(session, truth)
    outcome = resolve(session)
    evaluated = metrics(session)
    assert outcome["unique_properties"] < 1600
    assert evaluated["precision"] >= 0.98
    assert evaluated["recall"] >= 0.70
    assert evaluated["false_positives"] == 0
    report = save_report(session, tmp_path)
    json_before = (tmp_path / "quality-report.json").read_bytes()
    md_before = (tmp_path / "quality-report.md").read_bytes()
    for snap in snapshots:
        ingest(session, snap)
    resolve(session)
    assert save_report(session, tmp_path) == report
    assert (tmp_path / "quality-report.json").read_bytes() == json_before
    assert (tmp_path / "quality-report.md").read_bytes() == md_before
    assert report["removed_advertisements"] == 60
    assert report["temporarily_unavailable_advertisements"] == 30
    assert report["price_change_events"] > 100
    assert report["ingestion"]["processing_runs"] == 3
    assert report["deduplication"]["labeled_listings"] == 1600
    assert report["costs"]["simulated"]
    expected = (
        report["costs"]["total_operational_cost"]
        / report["costs"]["usable_deduplicated_count"]
        * 1000
    )
    assert report["costs"]["cost_per_1000_usable"] == pytest.approx(expected, abs=1e-6)


def test_fourteen_day_report_reproducible(session, tmp_path):
    snapshots, truth = generate(days=14)
    for snapshot in snapshots:
        ingest(session, snapshot)
    load_evaluation_truth(session, truth)
    resolve(session)
    report = save_report(session, tmp_path)
    before = (tmp_path / "quality-report.json").read_bytes()
    assert report["simulation_days"] == 14 and report["ingestion"]["processing_runs"] == 14
    assert report["validation_label"].startswith("14-day simulation")
    assert report["data_freshness"]["max_active_age_days"] == 0
    assert report["costs"]["infrastructure_charges"] == 14 * 0.75
    assert save_report(session, tmp_path) == report
    assert (tmp_path / "quality-report.json").read_bytes() == before


def test_truth_never_controls_merging(session):
    snapshots, _ = generate()
    snap = snapshots[0].model_copy(deep=True)
    snap.complete = False
    snap.records = [snap.records[0], snap.records[8]]
    ingest(session, snap)
    first = resolve(session)
    # Deliberately false truth claims do not affect deduplication.
    for lid in session.scalars(select(Listing.id)).all():
        session.add(
            GroundTruth(listing_id=lid, truth_property_id="deliberately-wrong-synthetic-truth")
        )
    session.flush()
    assert resolve(session) == first and first["unique_properties"] == 2
    assert metrics(session)["false_negatives"] == 1


def test_empty_quality_report_has_no_invented_metrics(session):
    report = quality_report(session)
    assert report["deduplication"]["precision"] is None
    assert report["deduplication"]["recall"] is None
    assert report["costs"]["cost_per_1000_usable"] is None
    assert report["ingestion"]["success_rate"] is None
