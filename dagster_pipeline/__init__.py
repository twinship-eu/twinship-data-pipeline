"""Dagster pipeline for TwinShip data processing."""

from dagster import Definitions

from dagster_pipeline.assets.harmonisation import (
    harmonised_vessel_graph,
    validated_vessel_graph,
    vessel_data,
)
from dagster_pipeline.resources import shacl_validator

defs = Definitions(
    assets=[vessel_data, harmonised_vessel_graph, validated_vessel_graph],
    resources={"shacl_validator": shacl_validator},
)
