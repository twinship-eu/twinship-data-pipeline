"""Sensors for automatic operator discovery.

The operator_discovery_sensor monitors the spreadsheet_data asset and
automatically registers new operators as dynamic partitions.

Workflow:
1. Materialize spreadsheet_data (discovers operators from the Excel file)
2. Sensor runs and registers discovered operators as partitions
3. Partitioned assets can now be materialized for each operator
"""

from dagster import (
    SensorEvaluationContext,
    SensorResult,
    SkipReason,
    sensor,
)

from dagster_pipeline.assets.harmonisation import operator_partitions_def


@sensor(
    minimum_interval_seconds=30,
    description="Discovers operators from spreadsheet_data and registers them as partitions",
)
def operator_discovery_sensor(context: SensorEvaluationContext) -> SensorResult | SkipReason:
    """Discover operators from the spreadsheet and register them as dynamic partitions.

    This sensor checks the spreadsheet_data asset's latest materialization and
    registers any new operators as dynamic partitions. This allows the partitioned
    assets to run for each discovered operator.
    """
    instance = context.instance

    # Get the latest materialization of spreadsheet_data
    from dagster import AssetKey

    asset_key = AssetKey("spreadsheet_data")

    # Get latest materialization event
    events = instance.get_latest_materialization_event(asset_key)

    if events is None:
        return SkipReason("spreadsheet_data has not been materialized yet. Materialize it first.")

    # Get the metadata from the materialization
    metadata = events.asset_materialization.metadata if events.asset_materialization else {}

    # Look for operators in metadata
    operators_meta = metadata.get("operators")
    if operators_meta is None:
        return SkipReason("No operators metadata found in spreadsheet_data")

    # Parse operators from metadata
    try:
        # The metadata value should contain the operator namespaces
        operators_text = operators_meta.text if hasattr(operators_meta, "text") else str(operators_meta)
        # Parse comma-separated list
        discovered_operators = [op.strip() for op in operators_text.split(",") if op.strip()]
    except Exception as e:
        return SkipReason(f"Could not parse operators metadata: {e}")

    if not discovered_operators:
        return SkipReason("No operators discovered from spreadsheet")

    # Get existing partitions
    existing_partitions = set(
        instance.get_dynamic_partitions(operator_partitions_def.name)
    )

    # Find new operators to register
    new_operators = [op for op in discovered_operators if op not in existing_partitions]

    if not new_operators:
        return SkipReason(
            f"All {len(discovered_operators)} operators already registered: {discovered_operators}"
        )

    # Register new partitions
    context.log.info(f"Registering {len(new_operators)} new operators: {new_operators}")

    return SensorResult(
        dynamic_partitions_requests=[
            operator_partitions_def.build_add_request(new_operators)
        ],
        run_requests=[],  # Don't auto-trigger runs, let user decide
    )
