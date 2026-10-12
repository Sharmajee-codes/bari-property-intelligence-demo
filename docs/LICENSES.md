# Dependency and license inventory

Original demonstration code: [MIT](../LICENSE). All dataset records are independently generated synthetic data; no real listings or source-site text, photos or proprietary datasets are included.

[DEPENDENCIES.md](DEPENDENCIES.md) and [dependency-licenses.json](dependency-licenses.json) were generated from the locked development environment with `pip-licenses`; they include direct/transitive Python runtime and development packages. Package metadata is a discovery inventory, not a substitute for redistribution review. Preserve dependency copyright/license files when distributing containers or bundles. Regenerate with:

```bash
pip-licenses --format=markdown --with-urls --output-file=docs/DEPENDENCIES.md
pip-licenses --format=json --with-urls --output-file=docs/dependency-licenses.json
```

The container also includes Python (PSF license) and Debian system packages with their own notices under `/usr/share/doc`. PostgreSQL uses the PostgreSQL license; PostGIS uses GPL-2.0-or-later and its container distribution includes additional libraries/tools under separate licenses. psycopg and bundled native libraries have their own distribution terms. Docker/Compose and GitHub Actions are external execution tools, not original MIT code. Review the upstream image and full native-library notices before commercial redistribution; this document does not relicense dependencies.

No secrets are included. Demo and CI credentials are public local-only examples; use real secret stores and independent service roles for live deployments.
