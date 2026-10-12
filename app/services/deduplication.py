"""Explainable scoring followed by complete-link clustering. No truth access in resolution."""

import hashlib
import json
import math
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from itertools import combinations

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Candidate, Decision, GroundTruth, Listing, Property
from app.synthetic import stable_id


@dataclass(frozen=True)
class MatchRules:
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "geo": 0.20,
            "address": 0.28,
            "area": 0.20,
            "type": 0.10,
            "floor": 0.10,
            "rooms": 0.07,
            "lift": 0.025,
            "condition": 0.025,
        }
    )
    confirmed: float = 0.90
    probable: float = 0.78
    uncertain: float = 0.60
    candidate_radius_m: float = 500
    max_confirmed_accuracy_m: float = 80

    def __post_init__(self):
        if not 0 <= self.uncertain <= self.probable <= self.confirmed <= 1:
            raise ValueError("thresholds must be ordered within [0, 1]")
        if set(self.weights) != {
            "geo",
            "address",
            "area",
            "type",
            "floor",
            "rooms",
            "lift",
            "condition",
        }:
            raise ValueError("provide weights for all eight matching features")
        if any(v < 0 for v in self.weights.values()) or sum(self.weights.values()) <= 0:
            raise ValueError("weights must be nonnegative with a positive total")
        if self.candidate_radius_m <= 0 or self.max_confirmed_accuracy_m <= 0:
            raise ValueError("distance and accuracy limits must be positive")

    @property
    def version(self) -> str:
        return (
            "complete-link-v1-"
            + hashlib.sha256(json.dumps(self.__dict__, sort_keys=True).encode()).hexdigest()[:12]
        )


def haversine(a: Listing, b: Listing) -> float:
    lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
    dlat, dlon = lat2 - lat1, math.radians(b.longitude - a.longitude)
    v = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371000 * 2 * math.asin(min(1, math.sqrt(v)))


def score_pair(a: Listing, b: Listing, rules: MatchRules) -> dict:
    distance = haversine(a, b)
    address = (
        SequenceMatcher(None, (a.address or "").casefold(), (b.address or "").casefold()).ratio()
        if a.address and b.address
        else 0
    )
    area = (
        max(0, 1 - abs(a.area_sqm - b.area_sqm) / max(a.area_sqm, b.area_sqm))
        if a.area_sqm and b.area_sqm
        else 0
    )
    scores = {"geo": max(0, 1 - distance / 200), "address": address, "area": area}
    for key, attr in [
        ("type", "property_type"),
        ("floor", "floor"),
        ("rooms", "rooms"),
        ("lift", "lift"),
        ("condition", "condition"),
    ]:
        x, y = getattr(a, attr), getattr(b, attr)
        scores[key] = float(x is not None and y is not None and x == y)
    confidence = sum(scores[k] * w for k, w in rules.weights.items()) / sum(rules.weights.values())
    hard_conflict = a.property_type != b.property_type or (
        a.floor is not None and b.floor is not None and a.floor != b.floor
    )
    strong = (
        address == 1
        and area >= 0.95
        and scores["floor"] == 1
        and scores["rooms"] == 1
        and max(a.coordinate_accuracy_m, b.coordinate_accuracy_m) <= rules.max_confirmed_accuracy_m
        and distance <= 100
        and a.agency_id != b.agency_id
    )
    if hard_conflict:
        classification, reason = "non_match", "conflicting property type or known floor"
    elif confidence >= rules.confirmed and strong:
        classification, reason = "confirmed", "strong address/area/floor/room/coordinate agreement"
    elif confidence >= rules.probable:
        classification, reason = "probable", "insufficient strong evidence for automatic merge"
    elif confidence >= rules.uncertain:
        classification, reason = "uncertain", "partial feature agreement"
    else:
        classification, reason = "non_match", "low similarity"
    return {
        "score": round(confidence, 6),
        "classification": classification,
        "reason": reason,
        "feature_scores": scores,
        "features": {
            "distance_m": round(distance, 3),
            "left_address": a.address,
            "right_address": b.address,
            "left_area_sqm": a.area_sqm,
            "right_area_sqm": b.area_sqm,
            "left_floor": a.floor,
            "right_floor": b.floor,
            "left_rooms": a.rooms,
            "right_rooms": b.rooms,
            "left_accuracy_m": a.coordinate_accuracy_m,
            "right_accuracy_m": b.coordinate_accuracy_m,
        },
    }


def complete_link_clusters(ids: list, confirmed: dict) -> list[list]:
    clusters = {i: {i} for i in ids}
    owner = {i: i for i in ids}
    for (a, b), _confidence in sorted(confirmed.items(), key=lambda x: (-x[1], str(x[0]))):
        ca, cb = owner[a], owner[b]
        if ca == cb:
            continue
        left, right = clusters[ca], clusters[cb]
        if not all(tuple(sorted((x, y), key=str)) in confirmed for x in left for y in right):
            continue
        combined = left | right
        anchor = min(combined, key=str)
        del clusters[ca], clusters[cb]
        clusters[anchor] = combined
        for member in combined:
            owner[member] = anchor
    return [sorted(c, key=str) for _, c in sorted(clusters.items(), key=lambda x: str(x[0]))]


def bulk_upsert(session: Session, model, rows: list[dict], update_fields: tuple[str, ...]) -> None:
    """Bound batches to avoid one database round trip per scored candidate."""
    for offset in range(0, len(rows), 500):
        statement = insert(model).values(rows[offset : offset + 500])
        session.execute(
            statement.on_conflict_do_update(
                index_elements=["id"],
                set_={key: getattr(statement.excluded, key) for key in update_fields},
            )
        )


def resolve(session: Session, rules: MatchRules | None = None) -> dict:
    rules = rules or MatchRules()
    session.execute(text("SELECT pg_advisory_xact_lock(742018)"))
    listings = {x.id: x for x in session.scalars(select(Listing)).all()}
    as_of = max((x.state_updated_at for x in listings.values()), default=None)
    pairs = session.execute(
        text("""
        SELECT a.id, b.id FROM listings a JOIN listings b
          ON a.id < b.id AND a.agency_id <> b.agency_id
         AND a.property_type = b.property_type
         AND ST_DWithin(a.location, b.location, :radius)
        WHERE a.location IS NOT NULL AND b.location IS NOT NULL
    """),
        {"radius": rules.candidate_radius_m},
    ).all()
    confirmed, candidates, decisions = {}, [], []
    for aid, bid in pairs:
        result = score_pair(listings[aid], listings[bid], rules)
        pair = tuple(sorted((aid, bid), key=str))
        cid = stable_id(f"candidate:{pair[0]}:{pair[1]}:{rules.version}")
        candidates.append(
            dict(
                id=cid,
                left_id=pair[0],
                right_id=pair[1],
                features=result["features"],
                feature_scores=result["feature_scores"],
                score=result["score"],
                rule_version=rules.version,
            )
        )
        if result["classification"] == "confirmed":
            confirmed[pair] = result["score"]
        decisions.append((cid, pair, result))
    bulk_upsert(session, Candidate, candidates, ("features", "feature_scores", "score"))
    groups = complete_link_clusters(list(listings), confirmed)
    targets, property_rows = {}, []
    for group in groups:
        anchor = group[0]
        pid = stable_id(f"property:{anchor}")
        confidences = [confirmed[tuple(sorted(p, key=str))] for p in combinations(group, 2)]
        property_rows.append(
            dict(
                id=pid,
                representative_listing_id=anchor,
                deduplication_confidence=min(confidences) if confidences else 1.0,
                transaction_status="unknown",
                synthetic=True,
            )
        )
        for lid in group:
            targets[lid] = pid
    bulk_upsert(session, Property, property_rows, ("deduplication_confidence",))
    for lid, pid in targets.items():
        listings[lid].property_id = pid
    session.flush()
    session.execute(delete(Property).where(Property.id.not_in([p["id"] for p in property_rows])))
    decision_rows = []
    for cid, pair, result in decisions:
        merged = targets[pair[0]] == targets[pair[1]]
        reason = result["reason"]
        if result["classification"] == "confirmed" and not merged:
            reason += "; complete-link cluster guard prevented merge"
        decision_rows.append(
            dict(
                id=cid,
                classification=result["classification"],
                merged=merged,
                reason=reason,
                decided_at=as_of,
                rule_version=rules.version,
            )
        )
    bulk_upsert(
        session, Decision, decision_rows, ("classification", "merged", "reason", "decided_at")
    )
    return {
        "candidates": len(pairs),
        "confirmed_pairs": len(confirmed),
        "unique_properties": len(groups),
        "rule_version": rules.version,
    }


def metrics(session: Session) -> dict:
    rows = session.execute(
        select(Listing.id, Listing.property_id, GroundTruth.truth_property_id).join(GroundTruth)
    ).all()
    truth_groups, predicted_groups = {}, {}
    for lid, pid, tid in rows:
        truth_groups.setdefault(tid, []).append(lid)
        predicted_groups.setdefault(pid, []).append(lid)
    actual = {frozenset(p) for g in truth_groups.values() for p in combinations(g, 2)}
    predicted = {frozenset(p) for g in predicted_groups.values() for p in combinations(g, 2)}
    tp, fp, fn = len(actual & predicted), len(predicted - actual), len(actual - predicted)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else 0.0
    )
    total = session.scalar(select(text("count(*)")).select_from(Listing))
    return {
        "synthetic": True,
        "evaluation": "pairwise final clusters; all truth pairs, including blocked candidates",
        "labeled_listings": len(rows),
        "unlabeled_listings": total - len(rows),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }
