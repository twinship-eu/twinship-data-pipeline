"""Sensor for automatic vessel discovery.

The vessel_discovery_sensor monitors the spreadsheet_data asset and
automatically registers new vessels as dynamic partitions, then triggers
the full pipeline for each new vessel.

Workflow:
1. On startup, the sensor triggers spreadsheet_data materialization
2. Once spreadsheet_data is materialized, the sensor discovers vessels,
   registers them as dynamic partitions, and triggers the full pipeline
"""

from dagster import (
    AssetKey,
    DefaultSensorStatus,
    RunRequest,
    SensorEvaluationContext,
    SensorResult,
    SkipReason,
    sensor,
)

from dagster_pipeline.assets.harmonisation import vessel_partitions_def
from dagster_pipeline.jobs import full_pipeline_job, spreadsheet_job


@sensor(
    minimum_interval_seconds=30,
    default_status=DefaultSensorStatus.RUNNING,
    jobs=[spreadsheet_job, full_pipeline_job],
    description="Discovers vessels from spreadsheet_data and registers them as partitions",
)
def vessel_discovery_sensor(
    context: SensorEvaluationContext,
) -> SensorResult | SkipReason:
    """Discover vessels from the spreadsheet and register them as dynamic partitions.

    On first run, triggers spreadsheet_data materialization via the extraction job.
    Once spreadsheet_data is materialized, registers any new vessels as dynamic
    partitions and triggers the full pipeline for each newly discovered vessel.
    """
    instance = context.instance

    # Get the latest materialization of spreadsheet_data
    asset_key = AssetKey("spreadsheet_data")
    events = instance.get_latest_materialization_event(asset_key)

    if events is None:
        context.log.info("spreadsheet_data not materialized — triggering extraction")
        return SensorResult(
            run_requests=[
                RunRequest(
                    run_key="spreadsheet-initial",
                    job_name="spreadsheet_pipeline",
                )
            ],
        )

    # Get the metadata from the materialization
    metadata = events.asset_materialization.metadata if events.asset_materialization else {}

    # Look for vessels in metadata
    vessels_meta = metadata.get("vessels")
    if vessels_meta is None:
        return SkipReason("No vessels metadata found in spreadsheet_data")

    # Parse vessels from metadata
    try:
        vessels_text = vessels_meta.text if hasattr(vessels_meta, "text") else str(vessels_meta)
        discovered_vessels = [v.strip() for v in vessels_text.split(",") if v.strip()]
    except Exception as e:
        return SkipReason(f"Could not parse vessels metadata: {e}")

    if not discovered_vessels:
        return SkipReason("No vessels discovered from spreadsheet")

    # Get existing partitions
    existing_partitions = set(instance.get_dynamic_partitions(vessel_partitions_def.name))

    # Find new vessels to register
    new_vessels = [v for v in discovered_vessels if v not in existing_partitions]

    if not new_vessels:
        return SkipReason(
            f"All {len(discovered_vessels)} vessels already registered: {discovered_vessels}"
        )

    # Register new partitions and trigger runs for each new vessel
    context.log.info(f"Registering {len(new_vessels)} new vessels: {new_vessels}")

    run_requests = [
        RunRequest(
            run_key=f"vessel-{vessel}",
            partition_key=vessel,
            job_name="full_pipeline",
        )
        for vessel in new_vessels
    ]

    return SensorResult(
        dynamic_partitions_requests=[vessel_partitions_def.build_add_request(new_vessels)],
        run_requests=run_requests,
    )
