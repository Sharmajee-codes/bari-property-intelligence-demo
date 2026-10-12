# Data model

All input data is synthetic. Identifiers use deterministic UUIDv5; prices are PostgreSQL `numeric(12,2)` and timestamps are timezone-aware UTC.

| Table | Purpose and identity |
|---|---|
| data_sources | Adapter identity, expected schema version, synthetic flag |
| agencies | Six fictional agency identities |
| properties | Inferred entity cluster; representative listing, merge confidence, unknown transaction status |
| listings | Current advertisement state; unique `(source_id, normalized_source_id)`; original ID and .invalid URL retained |
| property_attributes | One-to-one sparse ancillary attributes per advertisement; contradictions are not discarded |
| raw_records | Original JSONB per run/ordinal, including quarantine reason |
| listing_observations | Immutable normalized source snapshot or explicit inferred absence; unique listing/time |
| price_history | Initial/change asking-price events; unique observation FK prevents replay duplication |
| deduplication_candidates | Listing pair, raw similarity evidence, individual scores, final score and rule version |
| deduplication_decisions | Classification, actual cluster-merge result, reason and simulated decision timestamp |
| ingestion_runs | Snapshot fingerprint, scope, completeness, status, wall-clock timing and statistics |
| data_quality_results | Content-addressed quality snapshots referenced to simulated observation time |
| source_costs | Per-run simulated provider/processing charges |
| microzones | Synthetic configurable demonstration polygons with GiST index |
| demo_ground_truth | Private listing-to-underlying-property labels, used only for evaluation |

Listings store WGS84 `geography(Point,4326)` with a GiST index. Microzones use `geometry(Polygon,4326)`. Latitude/longitude and declared accuracy/provenance are retained for explainability and public serialization. B-tree indexes cover source identifiers, municipality, property/type-area filters, listing history references and observation freshness.

`first_seen_at` is the earliest accepted actual observation; `last_seen_at` is the latest actual observation and does not advance on inferred absence. `state_updated_at` records the latest direct or inferred lifecycle event. `published_at` is independent of collection time. Availability has three allowed values; transaction status has a constraint permitting only `unknown` in this demonstration. Positive price/area, coordinate ranges and positive uncertainty bounds are also constrained.

Property identity is derived from the lowest deterministic listing UUID in a complete-link cluster. A singleton has confidence 1 meaning no merge was performed, not verified identity. Re-resolution can split clusters or change anchors, so public property IDs may change; listing IDs and their histories remain stable. The representative ID is a unique anchor reference without a cyclic database FK; every resolver run assigns it from an existing listing. A production model should add durable entity aliases and canonical-attribute provenance.

Raw/normalized observations are append-only. Candidate evidence and decisions represent the most recent evaluation of each pair/rule version; full decision-event auditing is a documented production gap. Ancillary attributes stay per listing because agencies may disagree. There is no fictitious sold-price or transaction-evidence table.

Alembic's frozen initial migration creates the extension if needed and creates spatial indexes once. Extension-owned PostGIS tables are excluded from autogeneration. Destructive downgrade is for disposable environments only; test fixtures verify a dedicated database and isolate data with transaction rollback.
