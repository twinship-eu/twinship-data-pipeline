# TwinShip Data Pipeline

A data processing pipeline for converting maritime vessel data into RDF triples that conform to the [TwinShip ontology](https://github.com/SINTEF/twinship-ontology-demo).

## Features

- **Python harmonisation library** - Convert vessel data to RDF using composable functions
- **Dagster pipeline** - Orchestrated data processing with validation
- **SHACL validation** - Ensure data conforms to ontology constraints
- **Docker deployment** - Containerized pipeline with PostgreSQL storage

## Installation

### Using uv (recommended)

```bash
uv sync
```

### Development dependencies

```bash
uv sync --dev
```

## Usage

### Python Library

```python
from twinship_harmonisation.high_level import harmonise_vessel_data

g = harmonise_vessel_data(
    vessel_id="IMO-1234567",
    namespace="my-vessel",
    vessel_label="MV Example",
    vessel_type="RoPax",
    main_engines=[
        {
            "id": "ME-1",
            "label": "Main Engine 1",
            "power_max_kw": 12000,
            "fuels": ["HFO", "MGO"],
        }
    ],
)

print(g.serialize(format="turtle"))
```

### Dagster Pipeline

Run locally:

```bash
uv run dagster dev
```

Open http://localhost:3000 to access the Dagster UI.

### Docker Deployment

```bash
docker-compose up -d
```

Access the Dagster webserver at http://localhost:3000.

## Project Structure

```
twinship-data-pipeline/
├── twinship_harmonisation/     # Python library
│   ├── low_level/              # Primitive triple builders
│   ├── mid_level/              # Ontology design patterns
│   └── high_level/             # User-facing workflows
├── dagster_pipeline/           # Dagster assets and jobs
│   ├── assets/                 # Data transformation assets
│   └── resources/              # SHACL validator, etc.
├── shacl/                      # SHACL shape files
├── data/                       # Input data (JSON)
├── tests/                      # Unit tests
└── docker-compose.yml          # Docker deployment
```

## Testing

```bash
uv run pytest
```

## Linting

```bash
uv run ruff check .
uv run ruff format .
```

## License

MIT
