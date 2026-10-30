# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Dagster pipeline that turns vessel input data (spreadsheets, time series) into RDF following the [TwinShip ontology](https://github.com/twinship-eu/twinship-ontology), validates it with SHACL and loads it into GraphDB (one repository per vessel, Keycloak-secured). Python 3.11, managed with `uv`.

## Commands

```bash
uv sync                                   # install
uv run dagster dev                        # local Dagster UI at http://localhost:3000
uv run pytest                             # tests (data/ only; tests needing other input are skipped)
uv run --env-file .env pytest             # also uses TWINSHIP_VESSEL_DATA_DIR from .env
uv run pytest tests/test_graphdb.py -k named   # single test file / test
uv run ruff check . && uv run ruff format --check .
uvx --from 'reuse[charset-normalizer]' reuse lint
docker compose up -d --build              # full stack: Keycloak, GraphDB, Postgres, Dagster
scripts/sync_ontology.sh <tag>            # update ontology/ and shacl/twinship/ from a twinship-ontology release
```

CI (`.github/workflows/ci.yml`) runs ruff, ruff format and pytest on PRs to `develop` and `main`.

## Architecture

- `twinship_harmonisation/`: pure RDF library, layered `low_level` (triple builders) → `mid_level` (components) → `high_level` (`harmonise_twinship_vessel`).
- `dagster_pipeline/assets/harmonisation.py`: partitioned by vessel (dynamic partitions registered by `sensors.py`): `spreadsheet_data` → extracted/validated JSON → `vessel_rdf_graph` → `vessel_ttl` + `shacl_validation_report` → `graphdb_upload` → `sparql_summary`. `full_pipeline` selects all assets, so new assets join it automatically.
- `vessel_rdf_graph` also adds `data/RoRo Futuristic Vessel Operational Modes.ttl` (hand-written engine modes and bins, placeholder values) to the futuristic vessel's graph. New `tws:` types written by the pipeline must be added to `KnownTypeShape` in `shacl/pipeline/connections.ttl`, or SHACL fails.
- `dagster_pipeline/assets/futuristic_voyages.py`: futuristic-vessel-only patch that loads voyages into the vessel's repository after `graphdb_upload`. To be reworked for other input (time series should move to a time-series database with OBDA).
- GraphDB layout: repository per vessel with named graphs `https://twin-ship.eu/graphs/<vessel>/{ontology,components,voyages}`; each asset replaces only its own graph. Individuals are under `https://twin-ship.eu/individuals/<vessel>/`.
- `ontology/` and `shacl/twinship/` are synced copies of a twinship-ontology release (pinned in `ontology/VERSION`); never edit by hand. Pipeline-only shapes live in `shacl/pipeline/`. The GraphDB import list is read from `ontology/catalog-v001.xml`.

## Rules

- **Confidential data never goes into the repository.** `data/` holds only the public futuristic vessel data. Other vessel input is read from `TWINSHIP_VESSEL_DATA_DIR` (set in `.env`, defaults to `data/`). Do not name other vessels or operators in new code, docs, commit messages or PR descriptions.
- Unknown values are omitted (no triple), never written as `-1`. The source spreadsheets use `-1` for unknown; `clean_value` maps it to `None`.
- No credentials in tracked files: secrets come from `.env` (template `.env.example`); Keycloak users are defined in `keycloak/twinship-realm.json.template`.
- Branches: work on a branch from `develop` and open PRs into `develop`. `main` only receives release PRs from `develop` (merge commit, not squash), approved by the maintainer.
- Docker tests that need a clean state should use separate volumes rather than the developer's `twinship-data-pipeline_*` volumes.

See `README.md` for setup, logins and configuration, and `docs/futuristic-vessel.md` for the futuristic vessel data.
