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

Process a single vessel JSON file:

```python
from twinship_harmonisation import harmonise_twinship_vessel_file

g = harmonise_twinship_vessel_file("data/grimaldi.json")
print(g.serialize(format="turtle"))
```

Process all vessel files in a directory:

```python
from twinship_harmonisation import harmonise_all_twinship_vessels

g = harmonise_all_twinship_vessels("data")
g.serialize(destination="output/all_vessels.ttl", format="turtle")
```

Process vessel data from a dictionary:

```python
from twinship_harmonisation import harmonise_twinship_vessel

data = {
    "namespace": "test",
    "vessel": {
        "id": "IMO-1234567",
        "label": "Test Vessel",
        "type": "RoPax",
    },
    "main_engines": [
        {
            "id": "ME-1",
            "name": "Main Engine 1",
            "types": ["TwoStroke"],
            "fuels": ["HFO", "MGO"],
        }
    ],
    "auxiliary_engines": [],
    "propellers": [],
    "gearboxes": [],
    "boilers": [],
}
g = harmonise_twinship_vessel(**data)
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
│   └── high_level/             # User-facing workflows
├── dagster_pipeline/           # Dagster assets and jobs
│   ├── assets/                 # Data transformation assets
│   └── resources/              # SHACL validator, etc.
├── shacl/                      # SHACL shape files
├── data/                       # Input data (JSON)
├── tests/                      # Unit tests
└── docker-compose.yml          # Docker deployment
```

## Data Format

The harmonisation library expects JSON files with the following structure:

```json
{
  "namespace": "grimaldi",
  "vessel": {
    "id": "GRI-RR-1",
    "label": "GRIMALDI EUROCARGO GENOVA RORO CARGO SHIP",
    "type": "RoRo",
    "displacement_max_mt": 25000
  },
  "main_engines": [...],
  "auxiliary_engines": [...],
  "propellers": [...],
  "gearboxes": [...],
  "boilers": [...]
}
```

Use `scripts/extract_vessel_data.py` to extract data from the TwinShip Excel spreadsheet into this format.

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
