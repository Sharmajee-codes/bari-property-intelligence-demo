# Bari Property Intelligence Demo

**This repository is an independently developed technical demonstration using synthetic data. It is not affiliated with Immobiliare.it or Gruppo Loseto S.r.l. and does not represent a completed production deployment.**

[![PostGIS tests and lint](https://github.com/Sharmajee-codes/bari-property-intelligence-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/Sharmajee-codes/bari-property-intelligence-demo/actions/workflows/ci.yml)

For a quick technical review, see the [executed validation evidence](docs/VALIDATION.md), [14-day synthetic simulation report](reports/sample-fourteen-day.md), and [five-minute walkthrough](docs/DEMO_WALKTHROUGH.md). The simulation is not a continuously operated pilot; its cost assumptions are simulated.

A runnable data-engineering demonstration for evaluating Italian property intelligence workflows: acquisition, normalization, historical asking prices, advertisement availability, conservative entity resolution, and geographic comparable searches. The code, database, configuration, and reports are owned by whoever operates this repository. There are no paid services, live listing integrations, real addresses, or source-site content.

## Run the complete demonstration

Requirements: Docker with Compose, approximately 2 GB free disk space, and available local ports `8089` and `55439`. The PostGIS image uses amd64; Docker Desktop on Apple Silicon runs it with emulation.

```bash
cd bari-property-intelligence-demo
docker compose up --build -d
docker compose ps
docker compose logs init
curl http://localhost:8089/health
```

Compose waits for PostgreSQL, runs Alembic migrations, creates synthetic microzones, generates the three-cycle dataset, ingests it, evaluates deduplication and writes reports. The API starts only after initialization succeeds. First startup downloads images and Python packages. No `.env` file is needed for Compose; `.env.example` documents local settings; Compose forwards the listed thresholds and simulated rates. Change the generator seed only with a fresh database. Bindings are loopback-only and credentials are deliberately public **local demo defaults**.

Open the [read-only demonstration](http://localhost:8089), [interactive OpenAPI documentation](http://localhost:8089/docs), or [OpenAPI JSON](http://localhost:8089/openapi.json).

Migrations and incremental cycles can also be run explicitly:

```bash
docker compose exec api python -m app.cli migrate
docker compose exec api python -m app.cli generate --days 3
docker compose exec api python -m app.cli ingest --cycle 1
docker compose exec api python -m app.cli ingest --cycle 2
docker compose exec api python -m app.cli ingest --cycle 3
docker compose exec api python -m app.cli deduplicate
docker compose exec api python -m app.cli quality-report
```

Replaying identical snapshots does not create new observations, price events, runs, or simulated acquisition charges. The `bootstrap` command safely replays the default dataset on restart; it does not rewind a later simulation.

## What is demonstrated

- Seeded generator: 1,000 underlying fictional properties and 1,600 advertisements from six fictional agencies. Initial cycle has 1,400 advertisements; later cycles introduce new properties, agency duplicates, price/attribute changes, 60 missing advertisements and 30 temporary unavailability events.
- Coverage across Bari, Modugno, Bitonto, Triggiano, Mola di Bari, Giovinazzo, Noicattaro and Conversano. Coordinates are plausible demonstration points; synthetic block/unit labels do not identify actual properties.
- Immutable raw input, validation/quarantine, identifier normalization, source-schema drift detection, scoped inventory semantics, and bounded transient acquisition retries.
- PostGIS geography points with GiST indexes, declared accuracy/provenance, separate synthetic microzone polygons, and progressive `ST_DWithin` searches in metres.
- Explainable eight-feature weighted matching, four classifications, complete-link automatic clustering, and private ground-truth precision/recall/F1 evaluation.
- Asking-price history, first/last actual observations, and inferred removals. Every transaction status remains `unknown`.
- JSON/Markdown quality reports, configurable local alerts, simulated provider/processing/infrastructure costs, and a reproducible accelerated 14-day simulation.
- FastAPI request/response schemas, pagination, input bounds, 404/422/503 semantics, PostgreSQL integration tests, Ruff, and GitHub Actions.

## Architecture

```mermaid
flowchart LR
    G[Seeded synthetic generator] --> S[Scoped source adapter]
    G --> T[Private synthetic truth]
    S --> R[Bounded acquisition retry]
    R --> V[Raw preservation and validation]
    V --> Q[Quarantine and schema drift]
    V --> N[Normalization and writer lock]
    N --> DB[(PostgreSQL 16 / PostGIS)]
    DB --> H[Price and availability history]
    DB --> D[Geographic candidates / weighted scoring]
    D --> C[Conservative complete-link clusters]
    C --> DB
    T --> E[Aggregate evaluation only]
    DB --> E
    DB --> P[Microzone / accuracy-aware comparables]
    DB --> M[Quality / simulated cost reporting]
    E --> M
    P --> API[FastAPI / OpenAPI / read-only UI]
    H --> API
    M --> API
    M --> L[Local structured alerts and reports]
```

Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, GeoAlchemy2, psycopg 3, Alembic, PostgreSQL 16/PostGIS 3.5, tenacity, pytest, Ruff, Docker Compose. Exact Python versions are frozen in `requirements.lock`; update deliberately and rerun the tests. The optional simple worker periodically writes local quality reports and handles shutdown signals; no queue or paid notification service is required.

## Reproducible 14-day validation simulation

```bash
docker compose exec api python -m app.cli run-demo --days 14
docker compose exec api python -m app.cli quality-report
docker compose cp api:/srv/reports/quality-report.json ./quality-report.json
docker compose cp api:/srv/reports/quality-report.md ./quality-report.md
```

This simulates daily observations from **1–14 January 2026** in accelerated execution. It is a **14-day simulation**, not an actual continuously operated pilot. Repeated reports use the latest simulated observation as their reference time and exclude wall-clock execution timings. Generated inputs and private truth live under `data/demo`; reports live under `reports` (named Docker volumes in Compose).

To return to a fresh three-cycle demo, remove **only this project's** volumes, after exporting any wanted reports:

```bash
docker compose down -v
docker compose up --build -d
```

## API examples

```bash
curl 'http://localhost:8089/api/v1/properties?municipality=Bari&limit=5&offset=0'
curl 'http://localhost:8089/api/v1/comparables?latitude=41.1171&longitude=16.8719&initial_radius_m=50&max_radius_m=1000&min_comparables=5&property_type=apartment'
curl 'http://localhost:8089/api/v1/quality/summary'
curl 'http://localhost:8089/api/v1/ingestion/runs?limit=3'
curl 'http://localhost:8089/api/v1/deduplication/metrics'
# Use IDs returned by the inventory endpoint:
curl 'http://localhost:8089/api/v1/properties/PROPERTY_UUID'
curl 'http://localhost:8089/api/v1/listings/LISTING_UUID/history'
```

Comparable filters also include floor area, asking price, condition, floor, and lift. Radius doubles until the minimum is found or the maximum is reached. Crossing a synthetic microzone requires `allow_cross_microzone=true`, and the response explicitly flags whether returned results cross the origin zone. Prices use decimal strings in listing/history contracts; aggregated statistics use numeric EUR. See [API examples](docs/API_EXAMPLES.md) for captured responses.

## Deduplication and coordinate methodology

Matching uses geography, address similarity, area, property type, known floor, rooms, lift and condition. Strong address/area/floor/room evidence, different agencies, and sufficiently accurate coordinates are required for automatic confirmed merges. Probable and uncertain pairs remain separate. Two apartments in the same building with different known floors are hard negatives. All cross-cluster pairs must independently be confirmed before a cluster grows, preventing naive transitive merging.

Private synthetic truth is separate from source payloads and public responses, and is consulted **only for aggregate evaluation**. Recall includes duplicates missed by candidate blocking. Precision and recall describe this seeded dataset and do not establish real-world performance. Singleton confidence `1.0` means there is no contested merge, not that the identity is independently verified.

For a localized comparable search, the declared coordinate error bound must be no greater than half the radius and 200m. A 50m search therefore excludes advertisements with accuracy worse than 25m. Widening the radius can admit more uncertain coordinates. These are configurable demo boundaries and heuristics, not official Italian microzones or geocoding guarantees.

## Quality and simulated costs

Reports include raw rows across collection runs, distinct advertisements, inferred unique properties, active/removed/temporary availability, asking-price changes, missing attributes, coordinate distribution, quarantine/drift counts, freshness, coverage, volume alerts, ingestion success, and ground-truth evaluation.

A usable advertisement is active and has a positive asking price, positive floor area, coordinates and a declared accuracy no worse than `MAX_USABLE_ACCURACY_M` (200m by default). The denominator is **distinct inferred properties with at least one usable advertisement**.

```text
total_operational_cost = simulated_provider + simulated_processing + simulated_infrastructure
cost_per_1000_usable = total_operational_cost / usable_deduplicated_count * 1000
```

Illustrative defaults: EUR 0.0002 per raw record, EUR 0.015 per ingestion run, EUR 0.75 per simulated day. These are assumptions, **not measured expenses or provider quotations**. See [cost model](docs/COST_MODEL.md).

## Development and tests

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
pip install --no-deps -e .
ruff check .
ruff format --check .
python -m pytest -q -m 'not integration'
```

The full suite requires a dedicated disposable PostgreSQL/PostGIS test database. Tests apply migrations and roll back per-test changes; never point tests at important data.

```bash
docker compose exec db createdb -U demo bari_test
TEST_DATABASE_URL=postgresql+psycopg://demo:demo_local_only@localhost:55439/bari_test python -m pytest -q
```

Inside the already built container, use its installed pytest and the internal database address:

```bash
docker compose exec -e TEST_DATABASE_URL=postgresql+psycopg://demo:demo_local_only@db:5432/bari_test api python -m pytest -q
```

Without `TEST_DATABASE_URL`, database tests are skipped, which is **not full acceptance**. [Validation evidence](docs/VALIDATION.md) records actual executed checks; the [published GitHub Actions run](https://github.com/Sharmajee-codes/bari-property-intelligence-demo/actions/runs/38212601376) passed all 31 tests, lint/format checks and the 14-day simulation/report commands.

## Ownership, limitations and expansion

No external infrastructure account is required. `docker compose down` stops services and retains data. [Handover](docs/HANDOVER.md) covers configuration, backups and recovery. The original code uses the [MIT license](LICENSE); [dependency inventory](docs/DEPENDENCIES.md) and [license notes](docs/LICENSES.md) cover separate third-party terms.

This is a local demonstration without authentication, transaction evidence, licensed live feeds, production backups, independent geocoding validation, verified valuation, or a human matching-review workflow. Raw ingestion and histories are durable, but entity assignments are recomputed and property IDs can change when the anchor changes; production needs durable entity aliases and append-only decision audits. The single writer and in-memory candidate scoring target a small reviewable dataset, not national throughput.

National expansion would begin with licensed regional adapters, source-level scoped reconciliation, partitioned observation retention, measured candidate blocking and geospatial indexes, a review queue, RBAC, operational telemetry and tested recovery. It does not automatically require Kafka, Kubernetes or Elasticsearch. See [architecture](docs/ARCHITECTURE.md) and [production gaps](docs/PRODUCTION_GAPS.md).

Additional documentation: [data model](docs/DATA_MODEL.md), [ingestion](docs/INGESTION.md), [deduplication](docs/DEDUPLICATION.md), [geographic search](docs/GEOSPATIAL_SEARCH.md), [data quality](docs/DATA_QUALITY.md), and [5-minute walkthrough](docs/DEMO_WALKTHROUGH.md).
