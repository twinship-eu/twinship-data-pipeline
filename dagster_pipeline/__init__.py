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
           ├─► vessel_ttl (partitioned by vessel)
           │
           └─► shacl_validation_report (partitioned by vessel)
           │
           ▼
    graphdb_upload (partitioned, per-vessel repository)
           │
           ▼
    sparql_summary (SPARQL data tables from all vessel repositories)

Workflow:
1. Materialize spreadsheet_data first
2. The vessel_discovery_sensor runs automatically, registers discovered vessels
   as partitions, and triggers the full pipeline for each new vessel
"""

from dagster import Definitions

from dagster_pipeline.assets.futuristic_voyages import futuristic_voyage_upload
from dagster_pipeline.assets.harmonisation import (
    extracted_vessel_json,
    graphdb_upload,
    shacl_validation_report,
    sparql_summary,
    spreadsheet_data,
    validated_vessel_json,
    vessel_rdf_graph,
    vessel_ttl,
)
from dagster_pipeline.jobs import (
    extraction_job,
    full_pipeline_job,
    harmonisation_job,
    output_job,
    spreadsheet_job,
)
from dagster_pipeline.resources import graphdb_client, keycloak_token_provider, shacl_validator
from dagster_pipeline.sensors import vessel_discovery_sensor

defs = Definitions(
    assets=[
        # Extraction
        spreadsheet_data,
        extracted_vessel_json,
        validated_vessel_json,
        # Harmonisation
        vessel_rdf_graph,
        vessel_ttl,
        # Validation
        shacl_validation_report,
        # Output
        sparql_summary,
        graphdb_upload,
        futuristic_voyage_upload,
    ],
    jobs=[full_pipeline_job, extraction_job, harmonisation_job, output_job, spreadsheet_job],
    sensors=[vessel_discovery_sensor],
    resources={
        "shacl_validator": shacl_validator,
        "graphdb_client": graphdb_client,
        "keycloak_token_provider": keycloak_token_provider,
    },
)
