"""Seeded, fictional inputs. Ground truth is written separately and never matched on."""

import json
import math
import random
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.schemas import Snapshot

START = datetime(2026, 1, 1, 9, tzinfo=UTC)
CENTERS = {
    "Bari": (41.1171, 16.8719),
    "Modugno": (41.0837, 16.7795),
    "Bitonto": (41.1100, 16.6900),
    "Triggiano": (41.0667, 16.9250),
    "Mola di Bari": (41.0594, 17.0900),
    "Giovinazzo": (41.1867, 16.6700),
    "Noicattaro": (41.0344, 16.9892),
    "Conversano": (40.9680, 17.1140),
}
SOURCE = "synthetic-network"
NAMESPACE = uuid.UUID("26b0ffcd-681d-418b-95ad-bcfd843f5ccc")


def stable_id(value: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, value)


def listing_id(source: str, original: str) -> uuid.UUID:
    return stable_id(f"listing:{source}:{original.strip().casefold()}")


def generate(seed: int = 20260101, days: int = 3) -> tuple[list[Snapshot], dict[str, str]]:
    if not 3 <= days <= 14:
        raise ValueError("choose between 3 and 14 simulation days")
    rng = random.Random(seed)
    properties = []
    cities = list(CENTERS)
    for i in range(1000):
        city = cities[i % 8]
        lat, lon = CENTERS[city]
        # Dense fictional blocks plus wider suburbs; no real street/address data.
        block = rng.randrange(35)
        lat += (block // 7 - 2) * 0.0018 + rng.uniform(-0.00035, 0.00035)
        lon += (block % 7 - 3) * 0.0022 + rng.uniform(-0.0004, 0.0004)
        area = rng.randrange(45, 186)
        floor = rng.randrange(0, 7)
        properties.append(
            {
                "municipality": city,
                "address": f"SYNTHETIC block {i // 8:03d}, unit {i % 8}",
                "description": "SYNTHETIC property; no correspondence to a real listing.",
                "property_type": rng.choices(["apartment", "house", "villa"], [85, 10, 5])[0],
                "asking_price_eur": round(area * rng.randrange(1100, 2800) / 1000) * 1000,
                "area_sqm": area,
                "rooms": max(2, round(area / 28)),
                "bathrooms": 1 if area < 95 else 2,
                "floor": floor,
                "lift": floor > 2 and rng.random() > 0.25,
                "condition": rng.choice(["renovated", "good", "needs_renovation"]),
                "balcony": rng.random() < 0.7,
                "terrace": rng.random() < 0.2,
                "parking": rng.random() < 0.3,
                "storage": rng.random() < 0.4,
                "garden": rng.random() < 0.15,
                "building_year": rng.randrange(1950, 2020),
                "building_units": rng.randrange(4, 25),
                "energy_class": rng.choice("ABCDEFG"),
                "latitude": lat,
                "longitude": lon,
            }
        )
    # Hard negatives: same fictional building, nearly equal area, different floors.
    for i in range(0, 800, 40):
        a, b = properties[i], properties[i + 8]
        b.update({k: a[k] for k in ("latitude", "longitude", "address", "property_type", "rooms")})
        b["area_sqm"] = a["area_sqm"] + 1
        b["floor"] = a["floor"] + 1
        b["description"] = "SYNTHETIC difficult case: different apartment in the same building."
    advertisements = []
    truth = {}
    for n in range(1600):
        p = n if n < 1000 else n - 1000
        rec = dict(properties[p])
        agency = (p % 6) if n < 1000 else (p % 6 + 1) % 6
        accuracy = rng.choices([8, 20, 80, 250, 600], [62, 20, 10, 5, 3])[0]
        angle = rng.random() * math.tau
        offset = rng.random() * accuracy * 0.7
        rec["latitude"] += math.sin(angle) * offset / 111320
        rec["longitude"] += math.cos(angle) * offset / (111320 * math.cos(math.radians(41)))
        rec.update(
            {
                "synthetic": True,
                "source_id": SOURCE,
                "source_listing_id": f" AD-{n:05d} ",
                "agency_id": f"fictional-agency-{agency}",
                "url": f"https://fictional-agency-{agency}.invalid/synthetic/AD-{n:05d}",
                "coordinate_accuracy_m": accuracy,
                "coordinate_provenance": "synthetic_exact"
                if accuracy <= 20
                else "synthetic_approximate",
                "availability": "active",
                "published_at": (START - timedelta(days=p % 20)).isoformat(),
            }
        )
        if n >= 1000:
            rec["area_sqm"] += rng.choice([-2, -1, 0, 1, 2])
            rec["asking_price_eur"] += rng.choice([-5000, 0, 5000])
            rec["description"] = "SYNTHETIC alternative agency description; may conflict."
            if n % 19 == 0:
                rec["condition"] = "renovated"
        for field, chance in [
            ("asking_price_eur", 0.025),
            ("area_sqm", 0.018),
            ("address", 0.035),
            ("energy_class", 0.06),
            ("bathrooms", 0.03),
        ]:
            if rng.random() < chance:
                rec[field] = None
        advertisements.append(rec)
        truth[str(listing_id(SOURCE, rec["source_listing_id"]))] = f"synthetic-property-{p:04d}"
    snapshots = []
    for day in range(days):
        observed = START + timedelta(days=day)
        records = []
        for n, base in enumerate(advertisements):
            if day == 0 and (950 <= n < 1000 or n >= 1450):
                continue
            if day == 1 and n >= 1500:
                continue
            if day >= 2 and 100 <= n < 160:
                continue
            rec = dict(base)
            rec["observed_at"] = observed.isoformat()
            if day >= 1 and n % 11 == 0 and rec["asking_price_eur"]:
                rec["asking_price_eur"] = round(rec["asking_price_eur"] * 0.95)
            if day >= 1 and n % 23 == 0:
                rec["condition"] = "renovated"
            if day >= 2 and 200 <= n < 230:
                rec["availability"] = "temporarily_unavailable"
            if day >= 3:
                if n % 31 == 0 and rec["asking_price_eur"]:
                    rec["asking_price_eur"] -= (day - 2) * 500
                if day >= 5 and 200 <= n < 230:
                    rec["availability"] = "active"
            records.append(rec)
        snapshots.append(
            Snapshot(source_id=SOURCE, observed_at=observed, scope=cities, records=records)
        )
    return snapshots, truth


def write_dataset(directory: Path, seed: int, days: int) -> None:
    snapshots, truth = generate(seed, days)
    directory.mkdir(parents=True, exist_ok=True)
    for i, snapshot in enumerate(snapshots, 1):
        (directory / f"cycle-{i:02d}.json").write_text(
            snapshot.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
    (directory / "ground-truth.private.json").write_text(
        json.dumps({"synthetic": True, "seed": seed, "truth": truth}, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    (directory / "manifest.json").write_text(
        json.dumps(
            {
                "synthetic": True,
                "seed": seed,
                "days": days,
                "underlying_properties": 1000,
                "advertisements": 1600,
                "label": f"{days}-day simulation; no actual pilot operation",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
