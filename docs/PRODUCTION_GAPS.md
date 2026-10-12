# Production-readiness gaps

This project proves executable engineering patterns using synthetic data. It is not a completed deployment, a valuation engine or an operated client pilot.

1. Obtain authorized feeds and documented source entitlements. The current adapter reads local synthetic snapshots only and intentionally enforces synthetic input.
2. Add authentication/authorization, service roles, secrets management, TLS termination, rate limiting and security review before exposure beyond loopback.
3. Introduce durable entity IDs/aliases, a provenance-aware canonical attribute model and a human review queue for probable/uncertain matches. Current anchor IDs can change, and re-evaluation updates pair/rule decisions rather than retaining an append-only decision-event audit.
4. Independently label real match examples, calibrate error rates across municipalities/types and improve candidate blocking. Synthetic precision/recall are not transferable performance claims.
5. Validate source coordinates and use licensed/official boundaries when justified. Current microzones are fictional rectangles, and query-origin uncertainty is not modeled.
6. Add transaction evidence under a separate contract before representing completed sales. Removed listings stay unknown; asking-price statistics never establish verified market value.
7. Add real operation metrics, per-source baselines, scheduler state, durable acquisition checkpoints, failure routing and tested retries/recovery for database outages. The simple worker and accelerated 14-day simulation are not an SLA.
8. Add automated off-machine backups, point-in-time recovery, restore drills, retention and recovery objectives. Named volumes alone are not production backup protection.
9. Benchmark actual workloads and candidate density; partition long-lived observations and constrain batch scheduling based on measurement. Current resolution loads all demo listings/candidates in memory and serializes writers.
10. Validate costs against actual invoices/contracts, including licensing, review, backups, traffic, VAT and engineering support. Demo rates are assumptions only.
11. Add image/content fingerprinting only with authorized asset rights, address parsing suitable for Italian addresses, richer unit-level attributes and independent ambiguity evidence. Missing floor/address deliberately reduces automatic matches.
12. Pin container digests, scan dependencies, review third-party redistribution terms and independently execute CI after publication. Docker Desktop on Apple Silicon currently emulates the amd64 PostGIS image.
