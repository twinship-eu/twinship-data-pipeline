"""Dagster pipeline for TwinShip data processing with dynamic partitioning.

Pipeline structure:
    spreadsheet_data (non-partitioned)
           │
           ├─► sensor discovers vessels and registers partitions
           ▼
    extracted_vessel_json (partitioned by vessel)
           │
           ▼
    validated_vessel_json (partitioned by vessel)
           │
           ▼
    vessel_rdf_graph (partitioned by vessel)
           │
           ▼
    validated_vessel_ttl (partitioned by vessel)
           │
           ▼
    combined_vessel_graph (non-partitioned)
           │
           ▼
    graphdb_upload (non-partitioned)
           │
           ▼
    sparql_summary (SPARQL data tables from GraphDB)

Workflow:
1. Materialize spreadsheet_data first
2. The vessel_discovery_sensor runs automatically, registers discovered vessels
   as partitions, and triggers the full pipeline for each new vessel
"""

from dagster import Definitions

from dagster_pipeline.assets.harmonisation import (
    combined_vessel_graph,
    extracted_vessel_json,
    graphdb_upload,
    sparql_summary,
    spreadsheet_data,
    validated_vessel_json,
    validated_vessel_ttl,
    vessel_rdf_graph,
)
from dagster_pipeline.jobs import (
    extraction_job,
    full_pipeline_job,
    harmonisation_job,
    output_job,
    spreadsheet_job,
)
from dagster_pipeline.resources import graphdb_client, shacl_validator
from dagster_pipeline.sensors import vessel_discovery_sensor

defs = Definitions(
    assets=[
        # Extraction
        spreadsheet_data,
        extracted_vessel_json,
        validated_vessel_json,
        # Harmonisation
        vessel_rdf_graph,
        # Validation
        validated_vessel_ttl,
        # Output
        combined_vessel_graph,
        sparql_summary,
        graphdb_upload,
    ],
    jobs=[full_pipeline_job, extraction_job, harmonisation_job, output_job, spreadsheet_job],
    sensors=[vessel_discovery_sensor],
    resources={"shacl_validator": shacl_validator, "graphdb_client": graphdb_client},
)
