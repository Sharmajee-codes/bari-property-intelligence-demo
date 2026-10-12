# Project constraints

- This is an independent technical demonstration, not a completed client deployment.
- Use exclusively deterministic synthetic data. Never scrape listing sites or call live providers.
- Preserve source IDs, immutable observations, asking-price events, coordinate provenance, and availability.
- Removed advertisements are never evidence of a completed sale; transaction status stays unknown.
- Ground truth is private evaluation data and must never influence matching or appear in public APIs.
- Only complete, successful scoped snapshots with no rejected records can infer disappearance.
- Auto-merge only conservative confirmed matches; require all cross-cluster pairs to be confirmed.
- Label all price statistics as asking prices and all cost estimates as simulated.
- Label accelerated historical events as a 14-day simulation, never an operated pilot.
- Run real PostgreSQL/PostGIS integration tests and report only results actually observed.
- Keep infrastructure reproducible, local, inexpensive, and owned by the repository user.
- Update TASKS.md with completed verification and remaining work. No secrets or real listing data.
