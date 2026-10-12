# Implementation plan

1. Bootstrap Python, Docker/PostGIS, configuration, migrations and CI.
2. Generate seeded properties and 3-cycle / 14-day synthetic snapshots with separate ground truth.
3. Implement validated raw ingestion, quarantine, idempotent observations and availability/price history.
4. Implement explainable geographic candidate scoring and conservative complete-link clustering.
5. Implement PostGIS comparable search, uncertainty filtering and synthetic microzones.
6. Expose versioned FastAPI endpoints with validation, pagination and OpenAPI examples.
7. Produce deterministic quality/cost reports and local structured alerts.
8. Verify unit and PostgreSQL integration tests, Compose startup and sample API requests.
9. Write technical handover, license inventory, demonstration instructions and minimal read-only UI.

Each slice includes executable tests and documentation. The optional UI follows backend verification.
