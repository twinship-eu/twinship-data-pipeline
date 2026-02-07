# TwinShip Data Pipeline

A data processing pipeline for converting maritime vessel data into RDF triples that conform to the [TwinShip ontology](https://github.com/SINTEF/twinship-ontology-demo).

**Pipeline:** Excel spreadsheet → JSON extraction → RDF harmonisation → SHACL validation → TTL output → GraphDB upload

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

## Quick Start (Docker Compose)

```bash
docker compose up -d --build
```

Open http://localhost:3000. The same sensor-driven workflow runs automatically.

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

### Tests

```bash
uv run pytest
```

### Linting and formatting

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting. It runs through uv, no separate install needed:

```bash
uv run ruff check .     # lint
uv run ruff format .    # format
```

### Adding dependencies

```bash
uv add <package>        # runtime dependency
uv add --dev <package>  # dev-only dependency
```

## License

[CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/)
