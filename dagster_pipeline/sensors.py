"""Sensors for automatic vessel discovery.

The vessel_discovery_sensor monitors the spreadsheet_data asset and
automatically registers new vessels as dynamic partitions.

Workflow:
1. Materialize spreadsheet_data (discovers vessels from the Excel file)
2. Sensor runs and registers discovered vessels as partitions
3. Partitioned assets can now be materialized for each vessel
"""

from dagster import (
    AssetKey,
    SensorEvaluationContext,
    SensorResult,
    SkipReason,
    sensor,
)

from dagster_pipeline.assets.harmonisation import vessel_partitions_def


@sensor(
    minimum_interval_seconds=30,
    description="Discovers vessels from spreadsheet_data and registers them as partitions",
)
def vessel_discovery_sensor(context: SensorEvaluationContext) -> SensorResult | SkipReason:
    """Discover vessels from the spreadsheet and register them as dynamic partitions.

    This sensor checks the spreadsheet_data asset's latest materialization and
    registers any new vessels as dynamic partitions. This allows the partitioned
    assets to run for each discovered vessel.
    """
    instance = context.instance

    # Get the latest materialization of spreadsheet_data
    asset_key = AssetKey("spreadsheet_data")
    events = instance.get_latest_materialization_event(asset_key)

    if events is None:
        return SkipReason("spreadsheet_data has not been materialized yet. Materialize it first.")

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
    existing_partitions = set(
        instance.get_dynamic_partitions(vessel_partitions_def.name)
    )

    # Find new vessels to register
    new_vessels = [v for v in discovered_vessels if v not in existing_partitions]

    if not new_vessels:
        return SkipReason(
            f"All {len(discovered_vessels)} vessels already registered: {discovered_vessels}"
        )

    # Register new partitions
    context.log.info(f"Registering {len(new_vessels)} new vessels: {new_vessels}")

    return SensorResult(
        dynamic_partitions_requests=[
            vessel_partitions_def.build_add_request(new_vessels)
        ],
        run_requests=[],  # Don't auto-trigger runs, let user decide
    )
