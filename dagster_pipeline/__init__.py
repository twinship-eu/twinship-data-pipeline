"""Dagster pipeline for TwinShip data processing with dynamic partitioning.

Pipeline structure:
    spreadsheet_data (non-partitioned)
           │
           ├─► sensor discovers operators and registers partitions
           ▼
    extracted_vessel_json (partitioned by operator)
           │
           ▼
    vessel_rdf_graph (partitioned by operator)
           │
           ▼
    validated_vessel_ttl (partitioned by operator)
           │
           ▼
    combined_vessel_graph (non-partitioned)
           │
           ▼
    graphdb_upload (non-partitioned)

Workflow:
1. Materialize spreadsheet_data first
2. Enable the operator_discovery_sensor (Automation → Sensors)
3. The sensor registers discovered operators as partitions
4. Run the partitioned assets via backfill
"""

from dagster import AssetSelection, Definitions, define_asset_job

from dagster_pipeline.assets.harmonisation import (
    combined_vessel_graph,
    extracted_vessel_json,
    graphdb_upload,
    spreadsheet_data,
    validated_vessel_ttl,
    vessel_rdf_graph,
)
from dagster_pipeline.resources import shacl_validator
from dagster_pipeline.sensors import operator_discovery_sensor

# Job to run the full pipeline
full_pipeline_job = define_asset_job(
    name="full_pipeline",
    selection=AssetSelection.all(),
    description="Run the complete pipeline: extract → harmonise → validate → upload",
)

# Job for just extraction
extraction_job = define_asset_job(
    name="extraction_pipeline",
    selection=AssetSelection.groups("extraction"),
    description="Extract vessel data from spreadsheet to JSON",
)

# Job for harmonisation and validation
harmonisation_job = define_asset_job(
    name="harmonisation_pipeline",
    selection=AssetSelection.groups("harmonisation", "validation"),
    description="Harmonise JSON to RDF and validate",
)

# Job for output (combine and upload)
output_job = define_asset_job(
    name="output_pipeline",
    selection=AssetSelection.groups("output"),
    description="Combine TTL files and upload to GraphDB",
)

defs = Definitions(
    assets=[
        # Extraction
        spreadsheet_data,
        extracted_vessel_json,
        # Harmonisation
        vessel_rdf_graph,
        # Validation
        validated_vessel_ttl,
        # Output
        combined_vessel_graph,
        graphdb_upload,
    ],
    jobs=[full_pipeline_job, extraction_job, harmonisation_job, output_job],
    sensors=[operator_discovery_sensor],
    resources={"shacl_validator": shacl_validator},
)
