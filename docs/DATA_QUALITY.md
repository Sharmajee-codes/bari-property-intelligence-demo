# Deterministic data quality and local monitoring

`python -m app.cli quality-report` derives a JSON and Markdown report from stored observations and current inventory. Repeating it with the same database/configuration produces byte-identical files. The reference time is the latest simulated snapshot, not the wall clock. The reporting CLI uses repeatable-read isolation; ingestion uses atomic transactions. Report persistence is content-addressed.

Checks cover missing asking prices and ancillary attributes, invalid area/coordinates from preserved quarantine reasons, declared accuracy distribution, duplicate normalized source identifiers, schema drift, stale active observations, collection failures, aggregate deduplication precision/recall, municipality coverage and unexpected source-response volume changes. Reports distinguish repeated raw rows across runs from distinct advertisements and deduplicated properties. Zero invalid inputs in the clean default dataset do not imply that validation is untested; malformed inputs are exercised in integration tests.

| Configuration environment variable | Default | Meaning |
|---|---:|---|
| MIN_DEDUP_PRECISION | .98 | Alert below precision |
| MIN_DEDUP_RECALL | .75 | Alert below recall |
| MAX_VOLUME_CHANGE | .30 | Absolute change fraction between successive collection volumes |
| STALE_DAYS | 3 | Active observation age beyond this number of simulated days |
| MAX_USABLE_ACCURACY_M | 200 | Maximum uncertainty for usable cost-denominator inventory |

Thresholds are validated through Pydantic settings. Missing municipality coverage, quarantine and failed runs also produce alerts. The seeded conservative matcher may intentionally trigger the recall alert; the report shows the evidence rather than suppressing it. Alerts are structured local JSON log events and report entries. No real emails, SMS or external notifications are sent.

`GET /api/v1/quality/summary` computes the current public report. `GET /api/v1/ingestion/runs` exposes paginated statuses/timings/statistics. Health checks require a database connection, PostGIS and the migration version; 503 indicates database unavailability. The optional reporting worker is enabled with `docker compose --profile worker up -d worker`, with a default hourly interval. It is a simple local scheduler, not an operational SLA or durable external monitoring service.

The 14-day simulation contains 14 chronological synthetic collection events, not 14 days of continuous operation. Freshness is reported against the final simulated event; evaluating wall-clock freshness would require live source timestamps and real operation. Production needs per-source thresholds, severity/routing, observed latency/error metrics, trusted geocodes, independent matching labels and auditable escalation.
