from collections import Counter

import pytest
from pydantic import ValidationError

from app.schemas import ListingRecord
from app.services.deduplication import MatchRules, complete_link_clusters
from app.synthetic import generate, listing_id


def test_seeded_generation_and_private_truth():
    snapshots, truth = generate()
    again, again_truth = generate()
    assert snapshots == again and truth == again_truth
    assert generate(seed=42) != (snapshots, truth)
    assert len(truth) == 1600 and len(set(truth.values())) == 1000
    assert len(snapshots[0].records) == 1400
    assert len(snapshots[1].records) == 1500
    assert len(snapshots[2].records) == 1540
    for snapshot in snapshots:
        for record in snapshot.records:
            validated = ListingRecord.model_validate(record)
            assert validated.synthetic
            assert "synthetic-property" not in str(record)
            assert "truth_property_id" not in record
    assert len(Counter(r["municipality"] for r in snapshots[0].records)) == 8


def test_fourteen_day_simulation():
    snapshots, _ = generate(days=14)
    assert len(snapshots) == 14
    assert (snapshots[-1].observed_at - snapshots[0].observed_at).days == 13
    assert snapshots[-1] == generate(days=14)[0][-1]


def test_identifier_normalization():
    assert listing_id("source", " AD-1 ") == listing_id("source", "ad-1")
    assert listing_id("source", "AD-1") != listing_id("other", "AD-1")


def test_real_urls_and_non_synthetic_records_rejected():
    rec = generate()[0][0].records[0].copy()
    rec["synthetic"] = False
    with pytest.raises(ValidationError):
        ListingRecord.model_validate(rec)
    rec["synthetic"] = True
    rec["url"] = "https://example.com/listing"
    with pytest.raises(ValidationError):
        ListingRecord.model_validate(rec)


def test_no_naive_transitive_merge():
    groups = complete_link_clusters(["a", "b", "c"], {("a", "b"): 0.99, ("b", "c"): 0.98})
    assert sorted(map(len, groups)) == [1, 2]
    assert complete_link_clusters(
        ["a", "b", "c"],
        {
            ("a", "b"): 0.99,
            ("b", "c"): 0.98,
            ("a", "c"): 0.97,
        },
    ) == [["a", "b", "c"]]


def test_rule_configuration_validated():
    with pytest.raises(ValueError):
        MatchRules(confirmed=0.5, probable=0.8)
    with pytest.raises(ValueError):
        MatchRules(weights={"geo": 1})
    assert MatchRules().version != MatchRules(confirmed=0.95).version
