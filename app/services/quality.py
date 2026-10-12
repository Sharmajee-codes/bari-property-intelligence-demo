import hashlib
import json
from collections import Counter
from datetime import timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.logging import event
from app.models import (
    Attributes,
    IngestionRun,
    Listing,
    PriceEvent,
    Property,
    QualityResult,
    SourceCost,
)
from app.services.deduplication import metrics
from app.services.geospatial import LIMITATIONS
from app.synthetic import CENTERS, stable_id


def quality_report(session: Session) -> dict:
    listings = session.scalars(select(Listing)).all()
    runs = session.scalars(
        select(IngestionRun).order_by(IngestionRun.observed_at, IngestionRun.id)
    ).all()
    as_of = max((r.observed_at for r in runs), default=None)
    attrs = {a.listing_id: a.values for a in session.scalars(select(Attributes)).all()}
    n = len(listings)
    active = [x for x in listings if x.availability == "active"]
    usable = [
        x
        for x in active
        if x.asking_price_eur is not None
        and x.area_sqm is not None
        and x.latitude is not None
        and x.coordinate_accuracy_m is not None
        and x.coordinate_accuracy_m <= settings.max_usable_accuracy_m
    ]
    usable_properties = {x.property_id for x in usable}
    missing = {
        k: round(100 * sum(getattr(x, k) is None for x in listings) / n, 4) if n else 0
        for k in ("asking_price_eur", "area_sqm", "address", "rooms", "floor", "condition", "lift")
    }
    for key in (
        "bathrooms",
        "energy_class",
        "building_year",
        "balcony",
        "terrace",
        "parking",
        "storage",
        "garden",
    ):
        missing[key] = (
            round(100 * sum(attrs[x.id].get(key) is None for x in listings) / n, 4) if n else 0
        )
    accuracy = Counter(
        "missing"
        if x.coordinate_accuracy_m is None
        else (
            "precise_0_20m"
            if x.coordinate_accuracy_m <= 20
            else "approximate_21_200m"
            if x.coordinate_accuracy_m <= 200
            else "coarse_over_200m"
        )
        for x in listings
    )
    stale = (
        sum(x.last_seen_at < as_of - timedelta(days=settings.stale_days) for x in active)
        if as_of
        else 0
    )
    ages = sorted((as_of - x.last_seen_at).total_seconds() / 86400 for x in active) if as_of else []
    evaluated = metrics(session)
    total_provider = float(session.scalar(select(func.sum(SourceCost.provider_eur))) or 0)
    total_processing = float(session.scalar(select(func.sum(SourceCost.processing_eur))) or 0)
    days = (as_of.date() - runs[0].observed_at.date()).days + 1 if runs else 0
    infrastructure = days * settings.simulated_infrastructure_per_day_eur
    total = total_provider + total_processing + infrastructure
    alerts = []
    if evaluated["precision"] is not None and evaluated["precision"] < settings.min_dedup_precision:
        alerts.append(
            {
                "check": "deduplication_precision",
                "value": evaluated["precision"],
                "threshold": settings.min_dedup_precision,
            }
        )
    if evaluated["recall"] is not None and evaluated["recall"] < settings.min_dedup_recall:
        alerts.append(
            {
                "check": "deduplication_recall",
                "value": evaluated["recall"],
                "threshold": settings.min_dedup_recall,
            }
        )
    for previous, current in zip(runs, runs[1:], strict=False):
        before, after = previous.stats["raw_records"], current.stats["raw_records"]
        if before and abs(after - before) / before > settings.max_volume_change:
            alerts.append(
                {
                    "check": "unexpected_record_volume",
                    "observed_at": current.observed_at.isoformat(),
                    "change_fraction": round(abs(after - before) / before, 6),
                    "threshold": settings.max_volume_change,
                }
            )
    if stale:
        alerts.append(
            {
                "check": "stale_active_observations",
                "count": stale,
                "threshold_days": settings.stale_days,
            }
        )
    failures = sum(r.status == "failed" for r in runs)
    quarantined = sum(r.stats.get("quarantined", 0) for r in runs)
    if failures or quarantined:
        alerts.append(
            {
                "check": "ingestion_failures_or_quarantine",
                "failed_runs": failures,
                "quarantined_records": quarantined,
            }
        )
    coverage = dict(sorted(Counter(x.municipality for x in listings).items()))
    for city in CENTERS:
        if coverage.get(city, 0) == 0:
            alerts.append({"check": "source_coverage", "missing_municipality": city})
    report = {
        "synthetic": True,
        "validation_label": f"{days}-day simulation; not a continuously operated pilot",
        "as_of": as_of.isoformat() if as_of else None,
        "simulation_days": days,
        "total_raw_listings": sum(r.stats["raw_records"] for r in runs),
        "raw_count_basis": "input rows across runs, including quarantine; replays excluded",
        "distinct_source_advertisements": n,
        "unique_deduplicated_properties": session.scalar(
            select(func.count()).select_from(Property)
        ),
        "active_advertisements": len(active),
        "removed_advertisements": sum(x.availability == "removed" for x in listings),
        "temporarily_unavailable_advertisements": sum(
            x.availability == "temporarily_unavailable" for x in listings
        ),
        "price_change_events": session.scalar(
            select(func.count()).select_from(PriceEvent).where(PriceEvent.event_type == "change")
        ),
        "missing_field_percentages": missing,
        "coordinate_accuracy_distribution": dict(sorted(accuracy.items())),
        "validation": {
            "quarantined_records": quarantined,
            "invalid_area_records": 0,
            "duplicate_source_identifiers": sum(
                r.stats.get("duplicate_source_identifiers", 0) for r in runs
            ),
            "schema_changes": sum(r.stats.get("schema_changes", 0) for r in runs),
        },
        "deduplication": evaluated,
        "ingestion": {
            "processing_runs": len(runs),
            "successful_runs": sum(r.status == "success" for r in runs),
            "partial_runs": sum(r.status == "partial" for r in runs),
            "failed_runs": failures,
            "success_rate": sum(r.status == "success" for r in runs) / len(runs) if runs else None,
        },
        "data_freshness": {
            "stale_active_listings": stale,
            "stale_threshold_days": settings.stale_days,
            "max_active_age_days": max(ages) if ages else None,
            "basis": "latest simulated observation time, not wall-clock operation",
        },
        "source_coverage": coverage,
        "costs": {
            "simulated": True,
            "currency": "EUR",
            "provider_charges": round(total_provider, 6),
            "processing_charges": round(total_processing, 6),
            "infrastructure_charges": round(infrastructure, 6),
            "total_operational_cost": round(total, 6),
            "usable_listings": len(usable),
            "usable_deduplicated_count": len(usable_properties),
            "cost_per_1000_usable": round(total / len(usable_properties) * 1000, 6)
            if usable_properties
            else None,
            "denominator": "active deduplicated properties with at least one usable advertisement",
            "usable_criteria": {
                "price_required": True,
                "positive_area_required": True,
                "coordinates_required": True,
                "max_accuracy_m": settings.max_usable_accuracy_m,
            },
            "rates": {
                "provider_eur_per_raw_record": settings.simulated_provider_per_record_eur,
                "processing_eur_per_run": settings.simulated_processing_per_run_eur,
                "infrastructure_eur_per_simulated_day": (
                    settings.simulated_infrastructure_per_day_eur
                ),
            },
        },
        "alerts": alerts,
        "data_limitations": LIMITATIONS
        + [
            "Availability changes are not transaction evidence; transaction statuses are unknown.",
            "Cost rates are illustrative assumptions, not invoices or quoted provider prices.",
        ],
    }
    # Validation counts are derived from preserved raw quarantine records, never guessed.
    from app.models import RawRecord

    reasons = session.scalars(
        select(RawRecord.quarantine_reason).where(RawRecord.quarantine_reason.is_not(None))
    ).all()
    report["validation"]["invalid_area_records"] = sum("area_sqm" in r for r in reasons)
    report["validation"]["invalid_coordinate_records"] = sum(
        "latitude" in r or "longitude" in r or "coordinate" in r for r in reasons
    )
    return report


def save_report(session: Session, directory: Path) -> dict:
    report = quality_report(session)
    encoded = json.dumps(report, sort_keys=True, indent=2) + "\n"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "quality-report.json").write_text(encoded, encoding="utf-8")
    lines = [
        "# Synthetic property quality report",
        "",
        report["validation_label"],
        "",
        f"As of: {report['as_of']}",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for name in (
        "total_raw_listings",
        "distinct_source_advertisements",
        "unique_deduplicated_properties",
        "active_advertisements",
        "removed_advertisements",
        "temporarily_unavailable_advertisements",
        "price_change_events",
    ):
        lines.append(f"| {name} | {report[name]} |")
    lines += [
        "",
        "## Deduplication (private synthetic ground-truth evaluation)",
        "",
        "```json",
        json.dumps(report["deduplication"], indent=2),
        "```",
    ]
    for name in (
        "missing_field_percentages",
        "coordinate_accuracy_distribution",
        "validation",
        "ingestion",
        "data_freshness",
        "source_coverage",
        "costs",
        "alerts",
    ):
        lines += [
            "",
            f"## {name.replace('_', ' ').title()}",
            "",
            "```json",
            json.dumps(report[name], sort_keys=True, indent=2),
            "```",
        ]
    lines += ["", "## Limitations", ""] + [f"- {x}" for x in report["data_limitations"]]
    (directory / "quality-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if report["as_of"]:
        rid = stable_id("report:" + hashlib.sha256(encoded.encode()).hexdigest())
        session.execute(
            insert(QualityResult)
            .values(id=rid, as_of=report["as_of"], report=report)
            .on_conflict_do_nothing(index_elements=["id"])
        )
    for alert in report["alerts"]:
        event("quality_alert", **alert)
    return report
