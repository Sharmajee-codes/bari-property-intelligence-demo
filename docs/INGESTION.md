# Synthetic ingestion and lifecycle semantics

```bash
python -m app.cli generate --days 3
python -m app.cli migrate
python -m app.cli ingest --cycle 1
python -m app.cli ingest --cycle 2
python -m app.cli ingest --cycle 3
python -m app.cli deduplicate
```

The source-adapter protocol returns a `Snapshot` with source ID, schema version, observation timestamp, explicit municipality scope, completeness, collection success and raw records. The filesystem adapter performs no network calls. `collect_with_retry` retries declared `TransientSourceError` three times with bounded exponential backoff. Invalid content is not retried. Failed file acquisition is persisted as a failed synthetic run and re-raised; if the database itself is unavailable, logs and exit status are the only immediately available failure evidence.

Ingestion preserves every raw row before parsing and normalizes source identifiers using trimming/case folding while retaining the original string. Composite source identity prevents collisions between different sources. Pydantic checks synthetic marking, .invalid URLs, positive values, geographic ranges, paired coordinates, declared uncertainty and timezone/publication consistency. Unknown columns and unsupported schema versions indicate drift. Both instances of an ambiguous duplicate source ID are quarantined, rather than allowing row order to decide ownership.

A snapshot SHA-256 fingerprint makes exact replays no-ops, including run/cost counts. Listing/time observations are separately unique; conflicting content at an existing time is quarantined. Current-state updates require chronological events. An older unmatched event is quarantined rather than silently corrupting history; reconstruct from chronological snapshots when importing historical data. All writes share a transaction and an advisory writer lock. The CLI exits with an error for partial or failed runs after preserving their quarantine/statistics; initialization cannot silently treat a rejected dataset as success.

An asking-price event is recorded when a positive price differs from the last known price event. The first known price is `initial`; a later difference is `change`. Missing current prices remain missing without erasing earlier price evidence. Replays never create another price event. Unavailability or inferred absence cannot create a price event.

A missing advertisement becomes `removed` only when the snapshot is complete, successful, valid for its declared scope, has the supported schema, and contains no quarantine. Incomplete snapshots and collection errors do not establish absence. A malformed row blocks disappearance inference because it could correspond to a missing listing. Reconciliation only touches listings in the snapshot's source and scope, and never rewinds newer state. Explicit `temporarily_unavailable` is separate from removed; later observations can reactivate either state. **Neither state is evidence of sale.**

The three simulated cycles use 1–3 January 2026. Cycle 1 creates 1,400 advertisements; cycle 2 adds 100 and alters prices/characteristics; cycle 3 introduces another 100, omits 60 from a complete snapshot and marks 30 temporarily unavailable. The optional 14-day generator adds daily observations, further price reductions and temporary recovery; it is accelerated synthetic validation, not production monitoring.

Raw quarantine and detailed matching evidence can be reviewed locally with PostgreSQL; they are intentionally not exposed as broad public raw-data endpoints. Ground truth loads through the CLI's separate evaluation path. A future adapter must declare completeness conservatively and preserve evidence of scope and collection success.
