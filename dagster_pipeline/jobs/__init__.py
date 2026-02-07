"""Dagster jobs for TwinShip pipeline."""

from dagster import AssetSelection, define_asset_job

# Job to run the full pipeline
full_pipeline_job = define_asset_job(
    name="full_pipeline",
    selection=AssetSelection.all(),
    description="Run the complete pipeline: extract → harmonise → validate → upload",
)

# Job for just the spreadsheet (non-partitioned, used by sensor on first tick)
spreadsheet_job = define_asset_job(
    name="spreadsheet_pipeline",
    selection=AssetSelection.assets("spreadsheet_data"),
    description="Load the spreadsheet so the sensor can discover vessels",
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
