"""Dagster assets for vessel data harmonisation pipeline.

Pipeline structure:
1. spreadsheet_data - Load the Excel spreadsheet and discover operators
2. extracted_vessel_json - Extract JSON for each operator (partitioned)
3. vessel_rdf_graph - Harmonise to RDF for each operator (partitioned)
4. validated_vessel_ttl - Validate and write TTL files (partitioned)
5. combined_vessel_graph - Combine all RDF graphs
6. graphdb_upload - Upload to GraphDB (placeholder)
"""

from pathlib import Path

from dagster import (
    AssetExecutionContext,
    Config,
    DynamicPartitionsDefinition,
    MetadataValue,
    asset,
)
from rdflib import Graph

from dagster_pipeline.extraction import (
    discover_vessels_from_sheets,
    extract_vessel_for_operator,
    load_spreadsheet_sheets,
)
from dagster_pipeline.resources import ShaclValidator
from twinship_harmonisation import harmonise_twinship_vessel
from twinship_harmonisation.utils import bind_namespaces

# =============================================================================
# Partitions Definition
# =============================================================================

vessel_partitions_def = DynamicPartitionsDefinition(name="vessels")


# =============================================================================
# Configuration Classes
# =============================================================================


class SpreadsheetConfig(Config):
    """Configuration for spreadsheet asset."""

    spreadsheet_path: str = "data/TwinShip-table-schema-specification.xlsx"


class ValidationConfig(Config):
    """Configuration for SHACL validation."""

    shapes_path: str = "shacl/twinship_shapes.ttl"
    output_dir: str = "output"


class CombinedGraphConfig(Config):
    """Configuration for combined graph."""

    output_dir: str = "output"
    combined_output: str = "output/all_vessels.ttl"


# =============================================================================
# Assets
# =============================================================================


@asset(
    group_name="extraction",
    description="Load the TwinShip Excel spreadsheet and discover vessels",
)
def spreadsheet_data(context: AssetExecutionContext, config: SpreadsheetConfig) -> dict:
    """Load all sheets from the TwinShip spreadsheet and discover vessels."""
    spreadsheet_path = Path(config.spreadsheet_path)
    if not spreadsheet_path.exists():
        raise FileNotFoundError(f"Spreadsheet not found: {spreadsheet_path}")

    sheets = load_spreadsheet_sheets(str(spreadsheet_path))
    for name, df in sheets.items():
        context.log.info(f"Loaded {name}: {len(df)} rows")

    vessels = discover_vessels_from_sheets(sheets)
    context.log.info(f"Discovered {len(vessels)} vessels: {list(vessels.keys())}")

    context.add_output_metadata({
        "vessels": MetadataValue.text(", ".join(vessels.keys())),
        "vessel_count": MetadataValue.int(len(vessels)),
        "sheet_count": MetadataValue.int(len(sheets)),
    })

    return {"sheets": sheets, "vessels": vessels}


@asset(
    group_name="extraction",
    partitions_def=vessel_partitions_def,
    description="Extract vessel JSON for a specific vessel from spreadsheet",
)
def extracted_vessel_json(context: AssetExecutionContext, spreadsheet_data: dict) -> dict:
    """Extract vessel data for the current vessel partition."""
    namespace = context.partition_key
    sheets = spreadsheet_data["sheets"]
    vessels = spreadsheet_data["vessels"]

    if namespace not in vessels:
        context.log.error(f"Unknown vessel namespace: {namespace}")
        return {}

    vessel_info = vessels[namespace]
    data = extract_vessel_for_operator(
        sheets,
        vessel_info["prefix"],
        namespace,
        vessel_info["name"],
    )

    vessel_id = data.get("vessel", {}).get("id", "unknown")
    context.log.info(
        f"Extracted {namespace}: vessel={vessel_id}, "
        f"main_engines={len(data['main_engines'])}, "
        f"aux_engines={len(data['auxiliary_engines'])}, "
        f"propellers={len(data['propellers'])}, "
        f"gearboxes={len(data['gearboxes'])}"
    )

    context.add_output_metadata({
        "vessel_id": MetadataValue.text(vessel_id),
        "main_engine_count": MetadataValue.int(len(data["main_engines"])),
        "auxiliary_engine_count": MetadataValue.int(len(data["auxiliary_engines"])),
    })

    return data


@asset(
    group_name="harmonisation",
    partitions_def=vessel_partitions_def,
    description="Harmonise vessel JSON to RDF graph for a specific vessel",
)
def vessel_rdf_graph(context: AssetExecutionContext, extracted_vessel_json: dict) -> Graph:
    """Convert extracted vessel data to RDF triples."""
    namespace = context.partition_key

    if not extracted_vessel_json:
        context.log.warning(f"No data for {namespace}, returning empty graph")
        return Graph()

    g = harmonise_twinship_vessel(extracted_vessel_json)

    vessel_id = extracted_vessel_json.get("vessel", {}).get("id", "unknown")
    context.log.info(f"Generated {len(g)} triples for {namespace} ({vessel_id})")

    context.add_output_metadata({"triple_count": MetadataValue.int(len(g))})

    return g


@asset(
    group_name="validation",
    partitions_def=vessel_partitions_def,
    description="Validate RDF graph and write TTL file for a specific vessel",
)
def validated_vessel_ttl(
    context: AssetExecutionContext,
    config: ValidationConfig,
    vessel_rdf_graph: Graph,
    shacl_validator: ShaclValidator,
) -> str:
    """Validate RDF graph and serialize to TTL file."""
    namespace = context.partition_key
    shapes_path = Path(config.shapes_path)
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if vessel_rdf_graph is None or len(vessel_rdf_graph) == 0:
        context.log.warning(f"Empty graph for {namespace}, skipping")
        return ""

    # Validate with SHACL (warning only)
    if shapes_path.exists():
        conforms, report = shacl_validator.validate(vessel_rdf_graph, shapes_path)
        if conforms:
            context.log.info(f"SHACL validation passed for {namespace}")
        else:
            context.log.warning(f"SHACL validation issues for {namespace}:\n{report}")

    # Serialize to TTL
    output_path = output_dir / f"{namespace}.ttl"
    vessel_rdf_graph.serialize(destination=str(output_path), format="turtle")
    context.log.info(f"Wrote {len(vessel_rdf_graph)} triples to {output_path}")

    context.add_output_metadata({
        "output_path": MetadataValue.path(str(output_path)),
        "triple_count": MetadataValue.int(len(vessel_rdf_graph)),
    })

    return str(output_path)


@asset(
    group_name="output",
    deps=[validated_vessel_ttl],
    description="Combine all validated RDF graphs into one",
)
def combined_vessel_graph(context: AssetExecutionContext, config: CombinedGraphConfig) -> Graph:
    """Combine all operator TTL files into a single graph."""
    g = Graph()
    output_dir = Path(config.output_dir)
    combined_output = Path(config.combined_output)

    ttl_files = list(output_dir.glob("*.ttl"))
    for ttl_file in ttl_files:
        if ttl_file == combined_output:
            continue
        try:
            operator_graph = Graph()
            operator_graph.parse(ttl_file, format="turtle")
            g += operator_graph
            context.log.info(f"Added {len(operator_graph)} triples from {ttl_file.name}")
        except Exception as e:
            context.log.warning(f"Could not parse {ttl_file}: {e}")

    g = bind_namespaces(g)

    combined_output.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(combined_output), format="turtle")
    context.log.info(f"Combined graph: {len(g)} triples written to {combined_output}")

    context.add_output_metadata({
        "output_path": MetadataValue.path(str(combined_output)),
        "triple_count": MetadataValue.int(len(g)),
        "source_files": MetadataValue.int(len(ttl_files) - 1),
    })

    return g


@asset(
    group_name="output",
    description="Upload combined graph to GraphDB (not yet implemented)",
)
def graphdb_upload(context: AssetExecutionContext, combined_vessel_graph: Graph) -> str:
    """Placeholder for GraphDB upload - to be implemented later."""
    context.log.info(
        f"GraphDB upload not yet implemented. "
        f"Combined graph has {len(combined_vessel_graph)} triples."
    )
    return ""
