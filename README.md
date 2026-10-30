# TwinShip Data Pipeline

A data processing pipeline for converting maritime vessel data into RDF triples that conform to the [TwinShip ontology](https://github.com/twinship-eu/twinship-ontology).

**Pipeline:** Excel spreadsheet → JSON extraction → RDF harmonisation → SHACL validation → TTL output → GraphDB upload → GraphDB SPARQL summary

## Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — fast Python package manager (replaces pip/venv)
- **Docker** and **Docker Compose** — only needed for containerised deployment

Install uv if you don't have it:

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Data

The repository includes the futuristic vessel data in `data/`; [docs/futuristic-vessel.md](docs/futuristic-vessel.md) describes the files, how they are converted, where they end up in GraphDB, and example Visual Graph queries. To run the pipeline on other input files, set `TWINSHIP_VESSEL_DATA_DIR` in `.env` to the folder that holds them. When the variable is unset or empty, `data/` is used.

## Quick Start (Local)

```bash
# Install dependencies (creates .venv automatically)
uv sync

# Start Dagster dev server
uv run dagster dev
```

Open http://localhost:3000. The **vessel_discovery_sensor** starts automatically and:

1. Materialises `spreadsheet_data` (loads the Excel file)
2. Discovers vessels, registers them as dynamic partitions
3. Triggers the full pipeline for each vessel

You can also manually materialise assets from the UI.

The sensor only triggers runs for vessels it has not seen before. After changing code or input
data, re-run a known vessel yourself: in the Dagster UI, select the vessel's partition and
*Materialize all* (or launch the `full_pipeline` job for that partition).

## Quick Start (Docker Compose)

**Secrets:** copy the example environment file and fill in values (see [Secrets and configuration](#secrets-and-configuration-env) below). This step is optional for a quick disposable local setup (sensible `local-dev-*` defaults are built in), but recommended for anything longer-lived:

```bash
cp .env.example .env
# then edit .env
```

**Host entry required:** GraphDB authenticates via Keycloak using the Docker-internal hostname `keycloak`. Your browser must be able to resolve it:

```bash
# macOS / Linux
echo "127.0.0.1 keycloak" | sudo tee -a /etc/hosts

# Windows (run as administrator)
echo 127.0.0.1 keycloak >> C:\Windows\System32\drivers\etc\hosts
```

Then start the services:

```bash
docker compose up -d --build
```

Open http://localhost:3000. The same sensor-driven workflow runs automatically.

GraphDB is also started by Compose at http://localhost:7200, with these repositories:

- `twinship-ontology`: the ontology only, created by `graphdb/init.sh` on first start.
- One repository per vessel (e.g. `futuristic-vessel`), created by the pipeline.

Each vessel repository has named graphs under `https://twin-ship.eu/graphs/<vessel>/`:
`ontology` (the imported ontology), `components` (the vessel and its components) and, for the
futuristic vessel, `voyages`. The `graphdb_upload` asset creates the repository if missing and
replaces the `ontology` and `components` graphs; `futuristic_voyage_upload` replaces the
`voyages` graph. The `sparql_summary` asset then runs SPARQL queries against GraphDB and shows
result tables in Dagster metadata.

Queries without `FROM` or `GRAPH` see all graphs, including triples inferred by GraphDB. A
query restricted with `FROM <graph>` does not see inferred triples unless it also adds
`FROM <http://www.ontotext.com/implicit>`.

### Logging in

GraphDB accepts only Keycloak logins. The users are defined in
`keycloak/twinship-realm.json.template`; their usernames are fixed there, and only the
passwords come from `.env`:

| Service | URL | Username | Password (`.env`) | Access |
| --- | --- | --- | --- | --- |
| GraphDB Workbench | <http://localhost:7200> | `<vessel>-user`, e.g. `futuristic-vessel-user` | `KEYCLOAK_<VESSEL>_PASSWORD`, e.g. `KEYCLOAK_FUTURISTIC_VESSEL_PASSWORD` | Read access to that vessel's repository |
| Keycloak admin console | <http://localhost:8080> | `KEYCLOAK_ADMIN_USERNAME` | `KEYCLOAK_ADMIN_PASSWORD` | Manage users, roles and clients |
| Dagster UI | <http://localhost:3000> | none | none | Run and inspect the pipeline |

The pipeline itself logs in as the `dagster-pipeline` client (`KEYCLOAK_CLIENT_SECRET`), which
can create and write all repositories. No user has GraphDB administrator rights (`ROLE_ADMIN`),
so administrator functions in the Workbench (e.g. security settings) are not available.
Changes to the realm template or the passwords in `.env` take effect when Keycloak is
recreated (`docker compose up -d --force-recreate keycloak`).

### Reset

To reset all state (database, storage, outputs) and start fresh:

```bash
docker compose down -v
docker compose up -d --build
```

## Project Structure

```
twinship-data-pipeline/
├── twinship_harmonisation/    # Pure functional RDF harmonisation library
│   ├── low_level/             # Primitive triple builders (create_*, build_*)
│   ├── mid_level/             # Component builders (build_*, *_graph)
│   └── high_level/            # Top-level harmonise_twinship_vessel()
├── dagster_pipeline/          # Dagster orchestration
│   ├── assets/                # Pipeline assets (extraction → harmonisation → validation → output)
│   ├── jobs/                  # Job definitions
│   ├── queries/               # SPARQL queries (.rq files)
│   ├── resources/             # SHACL validator resource
│   └── sensors.py             # Vessel discovery sensor
├── shacl/                     # SHACL shape files for validation
│   ├── twinship/              # TwinShip shapes (synced copy, see ontology/VERSION)
│   └── pipeline/              # Pipeline-specific shapes (connections, vessel)
├── ontology/                  # TwinShip ontology (synced copy, see ontology/VERSION)
├── scripts/                   # Maintenance scripts (ontology sync)
├── data/                      # Input spreadsheet
├── tests/                     # Unit tests
├── dagster.yaml               # Local dev config (SQLite)
├── dagster-docker.yaml        # Docker config (PostgreSQL + DockerRunLauncher)
├── docker-compose.yml         # Docker Compose services
└── workspace.yaml             # Dagster code location (Docker only)
```

## Using the Harmonisation Library Directly

```python
from twinship_harmonisation import harmonise_twinship_vessel

g = harmonise_twinship_vessel(
    namespace="test",
    vessel={"id": "IMO-1234567", "label": "Test Vessel", "type": "RoPax"},
    main_engines=[{"id": "ME-1", "name": "Main Engine 1", "types": ["TwoStroke"], "fuels": ["HFO", "MGO"]}],
    auxiliary_engines=[],
    propellers=[],
    gearboxes=[],
    boilers=[],
)
print(g.serialize(format="turtle"))
```

## Development

### Setup

```bash
uv sync                        # install all dependencies
uv run pre-commit install      # set up git hooks (auto-formats code on commit)
```

### Ontology version

`ontology/` and `shacl/twinship/` are copies of the `model/` and `shapes/` directories of one [twinship-ontology](https://github.com/twinship-eu/twinship-ontology) release; the pinned ref and commit are in `ontology/VERSION`. Do not edit them by hand. Pipeline-specific shapes live in `shacl/pipeline/` and are not touched by the sync. To move to another release, with a twinship-ontology clone next to this repository (or `TWINSHIP_ONTOLOGY_PATH` set):

```bash
scripts/sync_ontology.sh v0.1.2
```

### GraphDB configuration

The GraphDB assets read these environment variables (optional):

```bash
GRAPHDB_BASE_URL=http://localhost:7200
GRAPHDB_CLEAR_BEFORE_UPLOAD=true
GRAPHDB_TIMEOUT_SECONDS=30
GRAPHDB_MAX_READINESS_CHECKS=20
GRAPHDB_READINESS_CHECK_INTERVAL_SECONDS=3
```

The pipeline writes to one repository per vessel, named after the vessel, so
`GRAPHDB_REPOSITORY_ID` and `GRAPHDB_REPOSITORY_TITLE` are only fallbacks of the GraphDB client
and are not used by the assets. The pipeline authenticates with a Keycloak token
(`KEYCLOAK_*` variables). `GRAPHDB_USERNAME` and `GRAPHDB_PASSWORD` (basic authentication) are
only used when Keycloak is not configured, e.g. against a GraphDB outside the Docker setup.

### Secrets and configuration (.env)

No credentials are committed to this repository. `docker-compose.yml`, `keycloak/twinship-realm.json.template`, and `graphdb/graphdb.properties` all source secrets and deployment-specific values from a local `.env` file (gitignored), rather than hardcoding them:

- **`.env.example`** is tracked in git and lists every required variable with a placeholder value. Copy it to `.env` and fill in real values before running Docker Compose.
- **Docker Compose** reads `.env` automatically and substitutes `${VAR}` references in `docker-compose.yml` (e.g. `KEYCLOAK_ADMIN_PASSWORD`, `KEYCLOAK_CLIENT_SECRET`). Each of these also has a `local-dev-*` fallback (e.g. `${KEYCLOAK_ADMIN_PASSWORD:-local-dev-admin-password}`), so the stack still runs without a `.env` file for a quick disposable local setup — but any shared or longer-lived deployment should set real values in `.env` rather than relying on these fallbacks.
- **`keycloak/twinship-realm.json.template`** holds placeholder tokens (e.g. `__DAGSTER_CLIENT_SECRET__`) instead of literal secrets. The Keycloak container's entrypoint (`keycloak/render-realm.sh`) substitutes these from its environment and writes the real `twinship-realm.json` before Keycloak imports it — Keycloak's `--import-realm` does not expand placeholders in the JSON file itself, so this rendering step is required.
- **`graphdb/graphdb.properties`** no longer hardcodes `graphdb.auth.openid.issuer`, since it's deployment-specific (e.g. different between local and hosted setups). It's instead injected as a JVM system property via `GDB_JAVA_OPTS` in `docker-compose.yml`, sourced from `GRAPHDB_OIDC_ISSUER` in `.env`.

When adding a new secret or deployment-specific value, add it to `.env.example` with a placeholder, wire it into `docker-compose.yml`/the realm template/`graphdb.properties` as appropriate, and document it here.

### Tests

```bash
uv run pytest                  # data/ only; tests that need other input files are skipped
uv run --env-file .env pytest  # also uses the folder set in TWINSHIP_VESSEL_DATA_DIR
```

### Linting and formatting

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting. If you set up the pre-commit hook above, formatting happens automatically on every commit. You can also run it manually:

```bash
uv run ruff check .     # lint
uv run ruff format .    # format
```

### Adding dependencies

```bash
uv add <package>        # runtime dependency
uv add --dev <package>  # dev-only dependency
```

## Licence

This repository has two licences. [`REUSE.toml`](REUSE.toml) gives the authoritative file-level mapping ([REUSE](https://reuse.software/) specification).

- **Code** (pipeline, deployment configuration, and tests): [MIT](LICENSE).
- **Data, models and documentation** (the synthetic Futuristic Vessel data in `data/`, the SHACL shapes in `shacl/`, the TwinShip ontology copy in `ontology/`, and `docs/`): [CC BY 4.0](LICENSES/CC-BY-4.0.txt).
- **Futuristic vessel voyage data** (`data/RoRo Futuristic Vessel Voyages.dat`): CC BY 4.0. Its weather columns contain Copernicus information; see [Provenance and licence](docs/futuristic-vessel.md#provenance-and-licence) for the attribution.
- **Third-party ontologies** in `ontology/external/` and `ontology/vocabularies/` keep their own licences: IDO (ISO 15926-14) is [CC BY-SA 4.0](LICENSES/CC-BY-SA-4.0.txt) (POSC Caesar Association), QUDT is CC BY 4.0 (QUDT.org), and PAV is [Apache 2.0](LICENSES/Apache-2.0.txt).
- **Pilot-vessel data** are not part of this repository and are not covered by these licences.

The authoritative TwinShip ontology is published at [twinship-eu/twinship-ontology](https://github.com/twinship-eu/twinship-ontology).
