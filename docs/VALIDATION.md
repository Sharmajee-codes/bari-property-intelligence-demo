# Executed validation evidence

Executed locally on **12 October 2026 (Asia/Kolkata)**. This describes actual checks on a synthetic technical demonstration, not a production deployment or operated pilot.

Environment: Python 3.12.13, PostgreSQL 16 / PostGIS 3.5 container, Docker Desktop on Apple Silicon using amd64 PostGIS emulation. Dedicated integration database: `bari_test`. Migration: `a7186a141f72`.

## Checks actually completed

- `docker compose up --build -d`: successful; init exited 0; database/API healthy on local ports 55439/8089.
- Alembic upgrade, downgrade to base and upgrade to head: executed by the disposable integration-test fixture. Spatial/identifier indexes verified by tests.
- `alembic check`: `No new upgrade operations detected.`
- `ruff check .`: `All checks passed!`
- `ruff format --check .`: successful.
- Full suite after public response contracts and migration-roundtrip checks: **30 passed, 1 warning in 263.95s**. The non-failing warning is Starlette's deprecation notice concerning its httpx TestClient integration.
- A subsequently added CLI regression (`test_cli_partial_run_exits_with_error_but_preserves_evidence`): **1 passed in 0.66s**, executed serially after the full suite. All **31 current tests** have therefore been executed successfully across those two runs; the whole 31-test suite has not been represented as a single run.
- Actual container commands `run-demo --days 14` and `quality-report`: successful.
- All eight documented HTTP endpoints: actual 200 responses captured in [API_EXAMPLES.md](API_EXAMPLES.md); OpenAPI's comparable response contract verified.
- Public responses checked to exclude ground-truth identifiers.
- Browser displayed inventory, localized comparable results and an advertisement's retained availability/asking-price history. A later in-app refresh during container rebuilding entered a browser navigation guard; subsequent endpoint checks confirmed API health. The initial browser verification is not represented as a fresh post-restart screenshot.
- Integration tests verify byte-identical Markdown/JSON reports after replay and repeated reporting, including the 14-day simulation.

The initial local checks above predate publication. The GitHub Actions verification below was subsequently executed successfully. No production performance benchmarks or actual operating expenses were measured. Source acquisition retry is simulated in a test; there are no real provider calls.

## Measured synthetic results

| Metric | Three-cycle simulation | 14-day simulation |
|---|---:|---:|
| Raw records across distinct runs | 4,440 | 21,380 |
| Distinct source advertisements | 1,600 | 1,600 |
| Inferred deduplicated properties | 1,162 | 1,162 |
| Active advertisements | 1,510 | 1,540 |
| Removed advertisements | 60 | 60 |
| Temporarily unavailable advertisements | 30 | 0 |
| Retained asking-price changes | 122 | 661 |
| Ground-truth precision | 1.00 | 1.00 |
| Ground-truth recall | .73 | .73 |
| Ground-truth F1 | .8439306358 | .8439306358 |
| True / false positives / false negatives | 438 / 0 / 162 | 438 / 0 / 162 |
| Simulated cost per 1,000 usable inferred properties, EUR | 3.298446 | 15.433574 |

The seeded generator contains 1,000 underlying properties, but conservative resolution leaves 162 duplicate pairs unmerged. Zero observed false positives on this synthetic dataset does not demonstrate a zero real-world error rate. The .73 recall is below the configurable .75 alert threshold and intentionally appears in the report.

Committed reproducible examples:

- [Three-cycle JSON](../reports/sample-three-day.json), [Markdown](../reports/sample-three-day.md)
- [14-day JSON](../reports/sample-fourteen-day.json), [Markdown](../reports/sample-fourteen-day.md)

JSON SHA-256:

```text
three-day:    bc63e0323d83a037909cc74fa1fe6b6e6f324fbc1f6b0c15bf6ec9b61dd4aaa2
fourteen-day: 8e80230a9679041fc9bd7d021cc90667f45ac813b44904f2f9b0144dbb813dd4
```

These are simulated data-quality/cost reports. They are not evidence of 14 days of continuous production operation, verified market values, completed transactions or paid source coverage.


## GitHub Actions verification after publication

Executed **12 October 2026**, on Ubuntu/Python 3.12 with a PostgreSQL/PostGIS service container.

[Public successful workflow run](https://github.com/Sharmajee-codes/bari-property-intelligence-demo/actions/runs/38212601376) verifies commit `918803c2dc00560f6cc22b7bf4d5ab95f24fe6c5`:

- PostGIS service initialization, dependency installation and editable package installation succeeded.
- Ruff lint and formatting checks passed.
- The **complete 31-test suite passed in one run: 31 passed, 1 warning in 187.69s**.
- `python -m app.cli run-demo --days 14` succeeded.
- `python -m app.cli quality-report` succeeded.
- The workflow uploaded `synthetic-validation-reports` as a downloadable artifact; artifacts have GitHub retention limits, while the committed sample reports remain available in the repository.

The first published workflow run failed before tests because of health-check argument quoting. That configuration was corrected, and the linked subsequent run passed all steps. Later documentation-only changes do not alter the verified application code. No production-operation or actual-cost claims are inferred from CI execution.
