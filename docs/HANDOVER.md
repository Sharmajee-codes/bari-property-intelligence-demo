# Handover and ownership

Everything required to rebuild is in this repository: source code, a dependency lock, migrations, container definitions, tests, seeded data generator and documentation. No proprietary account, external listing provider, API key or hosted database is required. Original code is MIT licensed; third-party dependencies retain their own licenses.

Start with `docker compose up --build -d`. Check `docker compose ps`, `docker compose logs init` and `/health`. The API binds locally on 8089; PostgreSQL binds locally on 55439. Override `API_PORT` or `DB_PORT` in a local `.env` when needed. `.env` and generated private dataset/report directories are ignored by Git. Compose's internal database URL remains the service name `db`; host port changes only affect local Python clients.

Named volumes persist database, synthetic data and reports. `docker compose down` retains them. `docker compose down -v` permanently removes this demo's volumes; export anything wanted first. Restarting initialization replays the default snapshots safely rather than rewinding a 14-day database. To inspect earlier states, use an independent fresh database or reset the demo volumes.

Export reports:

```bash
docker compose exec api python -m app.cli quality-report
docker compose cp api:/srv/reports/quality-report.md ./quality-report.md
docker compose cp api:/srv/reports/quality-report.json ./quality-report.json
```

Local logical backup / restore rehearsal:

```bash
docker compose exec -T db pg_dump -U demo -d bari_demo -Fc > bari-demo.dump
# Create a separate recovery database; do not overwrite the demonstration database.
docker compose exec db createdb -U demo bari_recovery
docker compose exec -T db pg_restore -U demo -d bari_recovery < bari-demo.dump
```

These commands are a manual local handover path, not automated production backup coverage. Store exports outside Git, test recovery and retention, and set appropriate production database roles, secret rotation, encryption and access controls before any live use. The API is read-only but currently unauthenticated, so it is intended for loopback use only.

Update Python dependencies deliberately by regenerating `requirements.lock`, running Ruff/full PostgreSQL tests and regenerating the license inventory. CI runs the same lint and migration-backed suite on Ubuntu/Python 3.12. The PostGIS tag is versioned but not digest-pinned; production supply-chain policy should pin digests and review actions/dependencies. The checked-in validation evidence describes actual local and GitHub Actions checks, not guaranteed future CI status.
