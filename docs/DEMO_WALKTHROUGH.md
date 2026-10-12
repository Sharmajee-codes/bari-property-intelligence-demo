# Suggested five-minute technical demonstration

Prepare with `docker compose up --build -d` and confirm API/DB health. Open the README, `/docs`, the read-only UI and generated report. Explain first that all data is synthetic and this is independent technical work, not a client deployment.

| Time | Show | Explain |
|---|---|---|
| 0:00–0:40 | README architecture, Compose health and `/health` | Rebuildable ownership, migration-backed PostGIS, source adapter separation |
| 0:40–1:30 | `/api/v1/properties`, detail and listing history | Original source identity, agency disagreement, retained asking-price changes; removed does not mean sold |
| 1:30–2:20 | Deduplication metrics and stored pair feature scores | Objective private truth evaluation, conservative precision/recall tradeoff, same-building floor conflict and complete-link guard |
| 2:20–3:20 | `/api/v1/comparables` starting at 50m | Progressive expansion, accuracy exclusions, explicit microzone crossing and asking-price limitations |
| 3:20–4:15 | Quality JSON/Markdown, costs and ingestion runs | Missing fields, coverage/freshness, replay counts, simulated EUR costs and explicit denominator |
| 4:15–5:00 | Tests, 14-day simulation command and production gaps | Evidence from real tests; accelerated history is not a 14-day operated pilot; licensed feeds, security, review and recovery remain future work |

Copy property/listing UUIDs from the inventory response rather than inventing IDs. To show idempotence, run `python -m app.cli ingest --cycle 2` inside the API container and compare the price-event/run counts before/after. To show historical simulation, run `python -m app.cli run-demo --days 14`; explicitly introduce it as an accelerated 14-day simulation. The [captured sample responses](API_EXAMPLES.md) and [actual validation record](VALIDATION.md) are useful when time is limited.
