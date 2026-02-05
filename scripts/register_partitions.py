#!/usr/bin/env python
"""Register dynamic partitions for vessels discovered in the spreadsheet.

Run this script before manually launching pipeline runs to ensure partitions exist.
Alternatively, use the vessel_discovery_sensor which does this automatically.

Usage:
    uv run python scripts/register_partitions.py
    uv run python scripts/register_partitions.py --spreadsheet path/to/file.xlsx
"""

import argparse
from pathlib import Path

from dagster import DagsterInstance

from dagster_pipeline.assets.harmonisation import vessel_partitions_def
from dagster_pipeline.extraction import (
    discover_vessels_from_sheets,
    load_spreadsheet_sheets,
)


def main():
    parser = argparse.ArgumentParser(description="Register dynamic partitions for vessels")
    parser.add_argument(
        "--spreadsheet",
        default="data/TwinShip-table-schema-specification.xlsx",
        help="Path to the TwinShip spreadsheet",
    )
    args = parser.parse_args()

    spreadsheet_path = Path(args.spreadsheet)
    if not spreadsheet_path.exists():
        print(f"Error: Spreadsheet not found: {spreadsheet_path}")
        return 1

    # Load spreadsheet and discover vessels
    print(f"Loading spreadsheet: {spreadsheet_path}")
    sheets = load_spreadsheet_sheets(str(spreadsheet_path))
    vessels = discover_vessels_from_sheets(sheets)

    if not vessels:
        print("No vessels found in spreadsheet")
        return 1

    namespaces = set(vessels.keys())
    print(f"Discovered vessels: {sorted(namespaces)}")

    # Register partitions with Dagster
    with DagsterInstance.get() as instance:
        existing = set(instance.get_dynamic_partitions(vessel_partitions_def.name))
        new_partitions = namespaces - existing

        if new_partitions:
            instance.add_dynamic_partitions(vessel_partitions_def.name, list(new_partitions))
            print(f"Registered new partitions: {sorted(new_partitions)}")
        else:
            print("All partitions already registered")

        all_partitions = existing | new_partitions
        print(f"\nAll registered partitions: {sorted(all_partitions)}")

    return 0


if __name__ == "__main__":
    exit(main())
