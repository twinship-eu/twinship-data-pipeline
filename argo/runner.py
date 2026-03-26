"""Argo Workflow runner for TwinShip pipeline profiling.

Each pipeline step runs a Dagster asset via materialize(), using a custom
IO manager that reads/writes to a shared volume. This profiles the full
Dagster execution framework (IO manager, resources, metadata, logging)
while passing data between Argo containers.

Usage:
    python runner.py extract-spreadsheet
    python runner.py extract-vessel grimaldi-roro
    python runner.py harmonise-vessel grimaldi-roro
    python runner.py validate-vessel grimaldi-roro
"""

import pickle
import sys
from pathlib import Path

from dagster import DagsterInstance, InputContext, IOManager, OutputContext, io_manager, materialize

from dagster_pipeline.assets.harmonisation import (
    extracted_vessel_json,
    shacl_validation_report,
    spreadsheet_data,
    validated_vessel_json,
    vessel_rdf_graph,
    vessel_ttl,
)
from dagster_pipeline.resources import shacl_validator

SHARED = Path("/tmp/pipeline")
VESSELS = ["grimaldi-roro", "stena-ropax", "stena-tanker", "futuristic-vessel"]

# Output dir on shared volume so TTL files persist across containers
OUTPUT_DIR = str(SHARED / "output")


# =============================================================================
# Custom IO manager: shares data between Argo containers via pickle files
# =============================================================================


class SharedVolumeIOManager(IOManager):
    """IO manager that persists asset outputs to a shared volume as pickle files."""

    def _path_for(self, asset_key: str, partition_key: str | None = None) -> Path:
        SHARED.mkdir(parents=True, exist_ok=True)
        if partition_key:
            return SHARED / f"{asset_key}__{partition_key}.pkl"
        return SHARED / f"{asset_key}.pkl"

    def handle_output(self, context: OutputContext, obj):
        partition_key = context.partition_key if context.has_partition_key else None
        path = self._path_for(context.asset_key.to_user_string(), partition_key)
        with open(path, "wb") as f:
            pickle.dump(obj, f)
        context.log.info(f"Saved output to {path}")

    def load_input(self, context: InputContext):
        asset_key = context.asset_key.to_user_string()
        partition_key = context.partition_key if context.has_partition_key else None
        path = self._path_for(asset_key, partition_key)
        if not path.exists() and partition_key:
            # Upstream asset may be non-partitioned
            path = self._path_for(asset_key, None)
        context.log.info(f"Loading input from {path}")
        with open(path, "rb") as f:
            return pickle.load(f)


@io_manager
def shared_volume_io_manager(_):
    return SharedVolumeIOManager()


def make_instance():
    """Create an ephemeral Dagster instance with dynamic partitions registered."""
    instance = DagsterInstance.ephemeral()
    instance.add_dynamic_partitions("vessels", VESSELS)
    return instance


# =============================================================================
# Asset materialization functions
# =============================================================================


def materialize_spreadsheet():
    result = materialize(
        [spreadsheet_data],
        resources={"io_manager": shared_volume_io_manager},
        instance=make_instance(),
    )
    assert result.success


def materialize_vessel_json(vessel: str):
    result = materialize(
        [spreadsheet_data, extracted_vessel_json, validated_vessel_json],
        resources={"io_manager": shared_volume_io_manager},
        instance=make_instance(),
        partition_key=vessel,
        selection=["extracted_vessel_json", "validated_vessel_json"],
    )
    assert result.success


def materialize_rdf_graph(vessel: str):
    result = materialize(
        [spreadsheet_data, extracted_vessel_json, validated_vessel_json, vessel_rdf_graph],
        resources={"io_manager": shared_volume_io_manager},
        instance=make_instance(),
        partition_key=vessel,
        selection=["vessel_rdf_graph"],
    )
    assert result.success


def materialize_validated_ttl(vessel: str):
    result = materialize(
        [
            spreadsheet_data,
            extracted_vessel_json,
            validated_vessel_json,
            vessel_rdf_graph,
            vessel_ttl,
            shacl_validation_report,
        ],
        resources={
            "io_manager": shared_volume_io_manager,
            "shacl_validator": shacl_validator,
        },
        instance=make_instance(),
        partition_key=vessel,
        selection=["vessel_ttl", "shacl_validation_report"],
        run_config={
            "ops": {
                "vessel_ttl": {
                    "config": {
                        "output_dir": OUTPUT_DIR,
                    }
                },
                "shacl_validation_report": {
                    "config": {
                        "shapes_path": "shacl/",
                    }
                },
            }
        },
    )
    assert result.success


STEPS = {
    "extract-spreadsheet": materialize_spreadsheet,
    "extract-vessel": materialize_vessel_json,
    "harmonise-vessel": materialize_rdf_graph,
    "validate-vessel": materialize_validated_ttl,
}

if __name__ == "__main__":
    # Parse command-line arguments
    step = sys.argv[1]
    # Some steps require a vessel name as a partition key argument (e.g. "grimaldi-roro"), others ignore it
    vessel = sys.argv[2] if len(sys.argv) > 2 else ""

    if step not in STEPS:
        print(f"Unknown step: {step}")
        print(f"Available: {list(STEPS.keys())}")
        sys.exit(1)

    # Run the selected step, passing the vessel name if required
    print(f"=== Running: {step} {vessel} ===")
    if vessel:
        STEPS[step](vessel)
    else:
        STEPS[step]()
    print(f"=== Done: {step} {vessel} ===")
