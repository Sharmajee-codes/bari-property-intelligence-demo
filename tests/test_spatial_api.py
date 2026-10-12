import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.db import get_session
from app.main import app
from app.schemas import Snapshot
from app.services.geospatial import ComparableQuery, comparables, initialize_microzones
from app.services.ingestion import ingest
from app.synthetic import SOURCE, START, generate

pytestmark = pytest.mark.integration


def spatial_data(session):
    initialize_microzones(session)
    template = generate()[0][0].records[1]
    rows = []
    # Around the fictional Bari zone seam at longitude 16.8719.
    for i, (lat, lon, accuracy) in enumerate(
        [
            (41.1171, 16.8710, 8),  # ~75m from origin; same zone
            (41.1171, 16.8700, 8),  # ~159m from origin; same zone
            (41.1171, 16.8720, 8),  # nearby, other zone
            (41.1171, 16.8718, 600),  # close point but too inaccurate
        ]
    ):
        row = dict(template)
        row.update(
            source_listing_id=f"spatial-{i}",
            municipality="Bari",
            latitude=lat,
            longitude=lon,
            coordinate_accuracy_m=accuracy,
            asking_price_eur=200000 + i * 10000,
            area_sqm=90,
            observed_at=START.isoformat(),
        )
        rows.append(row)
    ingest(session, Snapshot(source_id=SOURCE, observed_at=START, scope=["Bari"], records=rows))


def test_progressive_radius_microzone_and_uncertainty(session):
    spatial_data(session)
    result = comparables(
        session,
        ComparableQuery(latitude=41.1171, longitude=16.87189, min_comparables=2, max_radius_m=300),
    )
    assert result["attempted_radii_m"] == [50, 100, 200]
    assert result["comparable_listing_count"] == 2 and result["minimum_met"]
    assert not result["cross_microzone_expansion"]
    assert all(x["coordinate_accuracy_m"] == 8 for x in result["items"])
    crossing = comparables(
        session,
        ComparableQuery(
            latitude=41.1171,
            longitude=16.87189,
            allow_cross_microzone=True,
            min_comparables=3,
            max_radius_m=300,
        ),
    )
    assert crossing["comparable_listing_count"] == 3 and crossing["cross_microzone_expansion"]
    assert crossing["asking_price_statistics_eur"]["mean"] == 210000


def test_radius_cap_unknown_zone_and_filters(session):
    spatial_data(session)
    capped = comparables(
        session,
        ComparableQuery(latitude=41.1171, longitude=16.87189, min_comparables=20, max_radius_m=75),
    )
    assert capped["search_radius_used_m"] == 75 and not capped["minimum_met"]
    outside = comparables(session, ComparableQuery(latitude=0, longitude=0))
    assert outside["origin_microzone"] is None and outside["items"] == []
    filtered = comparables(
        session,
        ComparableQuery(
            latitude=41.1171,
            longitude=16.87189,
            min_price_eur=205000,
            max_price_eur=215000,
            min_comparables=1,
            max_radius_m=300,
        ),
    )
    assert filtered["comparable_listing_count"] == 1
    assert float(filtered["items"][0]["asking_price_eur"]) == 210000


def test_api_validation_status_codes_pagination_and_no_truth(session):
    spatial_data(session)
    app.dependency_overrides[get_session] = lambda: session
    try:
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
            assert client.get("/").status_code == 200
            assert client.get("/static/demo.js").status_code == 200
            assert (
                client.get(
                    "/api/v1/comparables", params={"latitude": 91, "longitude": 16}
                ).status_code
                == 422
            )
            assert (
                client.get(
                    "/api/v1/comparables",
                    params={
                        "latitude": 41,
                        "longitude": 16,
                        "initial_radius_m": 100,
                        "max_radius_m": 50,
                    },
                ).status_code
                == 422
            )
            assert client.get("/api/v1/properties", params={"limit": 0}).status_code == 422
            assert (
                client.get("/api/v1/properties", params={"availability": "sold"}).status_code == 422
            )
            assert client.get("/api/v1/properties/not-a-uuid").status_code == 422
            assert client.get(f"/api/v1/properties/{uuid.uuid4()}").status_code == 404
            inventory = client.get("/api/v1/properties", params={"limit": 1, "offset": 1}).json()
            assert inventory["total"] == 4 and len(inventory["items"]) == 1
            item = inventory["items"][0]
            assert client.get(f"/api/v1/properties/{item['id']}").status_code == 200
            lid = item["representative_listing"]["id"]
            history = client.get(f"/api/v1/listings/{lid}/history").json()
            assert history["transaction_status"] == "unknown" and history["total_observations"] == 1
            assert "truth_property_id" not in str(inventory)
            assert "synthetic-property-" not in str(inventory)
            assert client.get("/api/v1/ingestion/runs").json()["total"] == 1
            assert client.get("/api/v1/quality/summary").status_code == 200
            assert client.get("/api/v1/deduplication/metrics").json()["unlabeled_listings"] == 4
            spec = client.get("/openapi.json").json()
            assert "/api/v1/comparables" in spec["paths"]
            assert client.get("/docs").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_invalid_range_pairs():
    with pytest.raises(ValidationError):
        ComparableQuery(latitude=41, longitude=16, min_area_sqm=100, max_area_sqm=90)


def test_stale_observation_quality_alert(session):
    spatial_data(session)
    # Partial empty collection is not disappearance evidence; active inventory becomes stale.
    ingest(
        session,
        Snapshot(
            source_id=SOURCE,
            observed_at=START + timedelta(days=5),
            scope=["Bari"],
            complete=False,
            records=[],
        ),
    )
    from app.services.quality import quality_report

    report = quality_report(session)
    assert report["data_freshness"]["stale_active_listings"] == 4
    assert any(a["check"] == "stale_active_observations" for a in report["alerts"])
