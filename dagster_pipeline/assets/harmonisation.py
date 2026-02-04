"""Assets for vessel data harmonisation."""

import json
from pathlib import Path

from dagster import AssetExecutionContext, Config, asset
from rdflib import Graph

from dagster_pipeline.resources import ShaclValidator
from twinship_harmonisation.high_level import harmonise_vessel_data
from twinship_harmonisation.utils import bind_namespaces


class VesselDataConfig(Config):
    """Configuration for vessel data asset."""

    data_path: str = "data/vessel.json"


@asset(
    description="Load vessel data from JSON file",
)
def vessel_data(context: AssetExecutionContext, config: VesselDataConfig) -> dict:
    """Load vessel specification data from JSON."""
    data_path = Path(config.data_path)
    if not data_path.exists():
        context.log.warning(f"Data file not found: {data_path}")
        return {}

    with open(data_path) as f:
        data = json.load(f)

    context.log.info(f"Loaded vessel data: {data.get('vessel_id', 'unknown')}")
    return data


@asset(
    description="Transform vessel data into RDF triples",
)
def harmonised_vessel_graph(context: AssetExecutionContext, vessel_data: dict) -> Graph:
    """Harmonise vessel data into TwinShip RDF triples."""
    if not vessel_data:
        context.log.warning("No vessel data to harmonise")
        return bind_namespaces(Graph())

    g = harmonise_vessel_data(
        vessel_id=vessel_data["vessel_id"],
        namespace=vessel_data["namespace"],
        vessel_label=vessel_data.get("vessel_label"),
        vessel_type=vessel_data.get("vessel_type"),
        main_engines=vessel_data.get("main_engines"),
        auxiliary_engines=vessel_data.get("auxiliary_engines"),
    )

    context.log.info(f"Generated {len(g)} triples")
    return g


class ValidationConfig(Config):
    """Configuration for SHACL validation."""

    shapes_path: str = "shacl/twinship_shapes.ttl"
    output_path: str = "output/vessel.ttl"


@asset(
    description="Validate and serialize RDF graph",
)
def validated_vessel_graph(
    context: AssetExecutionContext,
    config: ValidationConfig,
    harmonised_vessel_graph: Graph,
    shacl_validator: ShaclValidator,
) -> str:
    """Validate the harmonised graph against SHACL shapes and serialize."""
    if len(harmonised_vessel_graph) == 0:
        context.log.warning("Empty graph, skipping validation")
        return ""

    # Validate with SHACL
    shapes_path = Path(config.shapes_path)
    if shapes_path.exists():
        conforms, report = shacl_validator.validate(harmonised_vessel_graph, shapes_path)
        if conforms:
            context.log.info("SHACL validation passed")
        else:
            context.log.error(f"SHACL validation failed:\n{report}")
            raise ValueError("SHACL validation failed")
    else:
        context.log.warning(f"SHACL shapes not found: {shapes_path}")

    # Serialize output
    output_path = Path(config.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    harmonised_vessel_graph.serialize(destination=str(output_path), format="turtle")

    context.log.info(f"Serialized graph to {output_path}")
    return str(output_path)
