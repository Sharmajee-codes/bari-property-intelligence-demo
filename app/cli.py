import argparse
import json
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from app.adapters.base import TransientSourceError
from app.adapters.synthetic import SyntheticAdapter
from app.config import settings
from app.db import SessionLocal
from app.models import GroundTruth, Listing
from app.services.deduplication import MatchRules, resolve
from app.services.geospatial import initialize_microzones
from app.services.ingestion import collect_with_retry, ingest
from app.services.quality import save_report
from app.synthetic import write_dataset


def load_truth(session, path: Path) -> None:
    # Explicit evaluation path. Resolver never imports or queries truth.
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("synthetic") is not True:
        raise ValueError("evaluation truth must be synthetic")
    truth = payload["truth"]
    for lid in session.scalars(select(Listing.id)).all():
        if str(lid) in truth:
            session.execute(
                insert(GroundTruth)
                .values(listing_id=lid, truth_property_id=truth[str(lid)])
                .on_conflict_do_update(
                    index_elements=["listing_id"], set_={"truth_property_id": truth[str(lid)]}
                )
            )


def run_cycle(path: Path, truth_path: Path | None = None) -> dict:
    try:
        snapshot = collect_with_retry(SyntheticAdapter(path))
    except (TransientSourceError, OSError, ValidationError) as exc:
        # Failed acquisition records are auditable but cannot infer disappearance.
        from app.schemas import Snapshot
        from app.synthetic import CENTERS, SOURCE, START

        snapshot = Snapshot(
            source_id=SOURCE,
            observed_at=START,
            successful=False,
            complete=False,
            scope=list(CENTERS),
            records=[
                {
                    "synthetic": True,
                    "acquisition_error": str(exc),
                    "input": path.name,
                }
            ],
        )
        with SessionLocal.begin() as session:
            ingest(session, snapshot)
        raise
    with SessionLocal.begin() as session:
        run = ingest(session, snapshot)
        if truth_path and truth_path.exists():
            load_truth(session, truth_path)
        result = {"run_id": str(run.id), "status": run.status, **run.stats}
    if run.status != "success":
        raise RuntimeError(
            f"Ingestion committed with {run.status} status; inspect quarantine/run {run.id}"
        )
    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Synthetic property intelligence demonstration")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--days", type=int, choices=range(3, 15), default=3)
    gen.add_argument("--seed", type=int, default=settings.demo_seed)
    gen.add_argument("--directory", type=Path, default=Path("data/demo"))
    ing = sub.add_parser("ingest")
    ing.add_argument("--cycle", type=int, default=1)
    ing.add_argument("--directory", type=Path, default=Path("data/demo"))
    ing.add_argument("--file", type=Path)
    demo = sub.add_parser("run-demo")
    demo.add_argument("--days", type=int, choices=range(3, 15), default=3)
    demo.add_argument("--directory", type=Path, default=Path("data/demo"))
    sub.add_parser("bootstrap")
    sub.add_parser("migrate")
    dedup = sub.add_parser("deduplicate")
    dedup.add_argument("--rules", type=Path, help="JSON MatchRules overrides")
    report = sub.add_parser("quality-report")
    report.add_argument("--directory", type=Path, default=Path("reports"))
    args = parser.parse_args()
    if args.command in ("bootstrap", "migrate"):
        command.upgrade(Config("alembic.ini"), "head")
        with SessionLocal.begin() as session:
            initialize_microzones(session)
        if args.command == "migrate":
            return
    if args.command == "generate":
        write_dataset(args.directory, args.seed, args.days)
        print(json.dumps({"synthetic": True, "days": args.days, "directory": str(args.directory)}))
        return
    if args.command == "ingest":
        path = args.file or args.directory / f"cycle-{args.cycle:02d}.json"
        print(json.dumps(run_cycle(path, args.directory / "ground-truth.private.json")))
        return
    if args.command in ("bootstrap", "run-demo"):
        days = getattr(args, "days", 3)
        directory = getattr(args, "directory", Path("data/demo"))
        write_dataset(directory, settings.demo_seed, days)
        with SessionLocal.begin() as session:
            initialize_microzones(session)
        for cycle in range(1, days + 1):
            print(
                json.dumps(
                    run_cycle(
                        directory / f"cycle-{cycle:02d}.json",
                        directory / "ground-truth.private.json",
                    )
                )
            )
    if args.command in ("deduplicate", "bootstrap", "run-demo"):
        rules_path = getattr(args, "rules", None)
        rules = MatchRules(**json.loads(rules_path.read_text())) if rules_path else MatchRules()
        with SessionLocal.begin() as session:
            print(json.dumps(resolve(session, rules)))
    if args.command in ("quality-report", "bootstrap", "run-demo"):
        directory = (
            getattr(args, "directory", Path("reports"))
            if args.command == "quality-report"
            else Path("reports")
        )
        with SessionLocal.begin() as session:
            # Snapshot isolation ensures the report cannot mix concurrent ingestion versions.
            session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            report = save_report(session, directory)
            print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
