#!/usr/bin/env python
"""Register dynamic partitions for operators discovered in the spreadsheet.

Run this script before manually launching pipeline runs to ensure partitions exist.
Alternatively, use the operator_discovery_sensor which does this automatically.

Usage:
    uv run python scripts/register_partitions.py
    uv run python scripts/register_partitions.py --spreadsheet path/to/file.xlsx
"""

import argparse
from pathlib import Path

import pandas as pd
from dagster import DagsterInstance

from dagster_pipeline.assets.harmonisation import (
    discover_operators_from_sheets,
    operator_partitions,
    prefix_to_namespace,
)


def load_sheets(spreadsheet_path: Path) -> dict[str, pd.DataFrame]:
    """Load spreadsheet sheets for operator discovery."""
    sheets = {}
    sheet_names = [
        "Vessel",
        "Main_Engine",
        "Auxiliary_Engine",
        "Propeller",
        "Gearbox",
        "Boiler",
    ]

    for sheet_name in sheet_names:
        try:
            df = pd.read_excel(spreadsheet_path, sheet_name=sheet_name)
            cols = df.columns.tolist()
            seen = {}
            new_cols = []
            for col in cols:
                if col in seen:
                    seen[col] += 1
                    new_cols.append(f"{col}_rel")
                else:
                    seen[col] = 0
                    new_cols.append(col)
            df.columns = new_cols
            sheets[sheet_name] = df
        except Exception as e:
            print(f"Warning: Could not load sheet {sheet_name}: {e}")

    return sheets


def main():
    parser = argparse.ArgumentParser(description="Register dynamic partitions for operators")
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

    # Load spreadsheet and discover operators
    print(f"Loading spreadsheet: {spreadsheet_path}")
    sheets = load_sheets(spreadsheet_path)
    prefixes = discover_operators_from_sheets(sheets)

    if not prefixes:
        print("No operators found in spreadsheet")
        return 1

    print(f"Discovered operators: {sorted(prefixes)}")

    # Convert to namespaces
    namespaces = {prefix_to_namespace(p) for p in prefixes}
    print(f"Namespaces: {sorted(namespaces)}")

    # Register partitions with Dagster
    with DagsterInstance.get() as instance:
        existing = set(instance.get_dynamic_partitions(operator_partitions.name))
        new_partitions = namespaces - existing

        if new_partitions:
            instance.add_dynamic_partitions(operator_partitions.name, list(new_partitions))
            print(f"Registered new partitions: {sorted(new_partitions)}")
        else:
            print("All partitions already registered")

        all_partitions = existing | new_partitions
        print(f"\nAll registered partitions: {sorted(all_partitions)}")

    return 0


if __name__ == "__main__":
    exit(main())
