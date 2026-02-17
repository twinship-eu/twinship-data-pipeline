"""Dagster assets for vessel data harmonisation pipeline.

Pipeline structure:
1. spreadsheet_data - Load the Excel spreadsheet and discover vessels
2. extracted_vessel_json - Extract JSON for each vessel (partitioned)
3. vessel_rdf_graph - Harmonise to RDF for each vessel (partitioned)
4. validated_vessel_ttl - Validate and write TTL files (partitioned)
5. combined_vessel_graph - Combine all RDF graphs
6. graphdb_upload - Upload the combined graph to GraphDB
7. sparql_summary - SPARQL summary tables queried from GraphDB
"""

from pathlib import Path
from typing import Any

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
from dagster_pipeline.resources import GraphDBClient, ShaclValidator
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
    fail_on_validation_error: bool = True


class CombinedGraphConfig(Config):
    """Configuration for combined graph."""

    output_dir: str = "output"
    combined_output: str = "output/all_vessels.ttl"


# =============================================================================
# Extraction Assets
# =============================================================================


@asset(
    group_name="extraction",
    description="Load the TwinShip Excel spreadsheet and discover vessels",
    kinds={"excel"},
)
def spreadsheet_data(context: AssetExecutionContext, config: SpreadsheetConfig) -> dict:
    """Load all sheets from the TwinShip spreadsheet and discover vessels."""
    # Load spreadsheet with configured path
    spreadsheet_path = Path(config.spreadsheet_path)
    if not spreadsheet_path.exists():
        raise FileNotFoundError(f"Spreadsheet not found: {spreadsheet_path}")

    # Load all sheets and log their sizes
    sheets = load_spreadsheet_sheets(str(spreadsheet_path))
    for name, df in sheets.items():
        context.log.info(f"Loaded {name}: {len(df)} rows")

    # Discover vessels from entity IDs in the spreadsheet
    vessels = discover_vessels_from_sheets(sheets)
    context.log.info(f"Discovered {len(vessels)} vessels: {list(vessels.keys())}")

    # Add metadata to context so it appears in Dagster UI
    context.add_output_metadata(
        {
            "vessels": MetadataValue.text(", ".join(vessels.keys())),
            "vessel_count": MetadataValue.int(len(vessels)),
            "sheet_count": MetadataValue.int(len(sheets)),
        }
    )

    return {"sheets": sheets, "vessels": vessels}


@asset(
    group_name="extraction",
    partitions_def=vessel_partitions_def,
    description="Extract vessel JSON for a specific vessel from spreadsheet",
    kinds={"json"},
)
def extracted_vessel_json(context: AssetExecutionContext, spreadsheet_data: dict) -> dict:
    """Extract vessel data for the current vessel partition."""
    # Get the current vessel namespace from the partition key (e.g., "grimaldi", "stena-tanker")
    namespace = context.partition_key
    sheets = spreadsheet_data["sheets"]
    vessels = spreadsheet_data["vessels"]

    # Validate that the namespace exists in the discovered vessels
    if namespace not in vessels:
        context.log.error(f"Unknown vessel namespace: {namespace}")
        return {}

    # Extract vessel data for this specific vessel
    vessel_info = vessels[namespace]
    data = extract_vessel_for_operator(
        sheets,
        vessel_info["prefix"],
        namespace,
    )

    # Log summary of extracted data for this vessel
    vessel_id = data.get("vessel", {}).get("id", "unknown")
    context.log.info(
        f"Extracted {namespace}: vessel={vessel_id}, "
        f"main_engines={len(data['main_engines'])}, "
        f"aux_engines={len(data['auxiliary_engines'])}, "
        f"propellers={len(data['propellers'])}, "
        f"gearboxes={len(data['gearboxes'])}"
    )

    # Add metadata about the extracted vessel to the context for Dagster UI
    context.add_output_metadata(
        {
            "vessel_id": MetadataValue.text(vessel_id),
            "main_engine_count": MetadataValue.int(len(data["main_engines"])),
            "auxiliary_engine_count": MetadataValue.int(len(data["auxiliary_engines"])),
        }
    )

    return data


# =============================================================================
# Harmonisation Assets
# =============================================================================


@asset(
    group_name="harmonisation",
    partitions_def=vessel_partitions_def,
    description="Harmonise vessel JSON to RDF graph for a specific vessel",
    kinds={"RDF", "python"},
)
def vessel_rdf_graph(context: AssetExecutionContext, extracted_vessel_json: dict) -> Graph:
    """Convert extracted vessel data to RDF triples."""
    namespace = context.partition_key

    # Validate that we have extracted data for this vessel before attempting harmonisation
    if not extracted_vessel_json:
        context.log.warning(f"No data for {namespace}, returning empty graph")
        return Graph()

    # Harmonise the extracted vessel data into RDF triples
    g = harmonise_twinship_vessel(**extracted_vessel_json)

    # Log the number of triples generated
    vessel_id = extracted_vessel_json.get("vessel", {}).get("id", "unknown")
    context.log.info(f"Generated {len(g)} triples for {namespace} ({vessel_id})")

    # Add metadata about the harmonised graph to the context for Dagster UI
    context.add_output_metadata({"triple_count": MetadataValue.int(len(g))})

    return g


# =============================================================================
# Validation Assets
# =============================================================================


@asset(
    group_name="validation",
    partitions_def=vessel_partitions_def,
    description="Validate RDF graph and write TTL file for a specific vessel",
    kinds={"python", "SHACL", "RDF"},
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

    # Check if the graph is empty before attempting validation or serialization
    if vessel_rdf_graph is None or len(vessel_rdf_graph) == 0:
        context.log.warning(f"Empty graph for {namespace}, skipping")
        return ""

    # Validate with SHACL if shapes file exists
    if shapes_path.exists():
        conforms, report = shacl_validator.validate(vessel_rdf_graph, shapes_path)
        if conforms:
            context.log.info(f"SHACL validation passed for {namespace}")
        else:
            if config.fail_on_validation_error:
                raise ValueError(f"SHACL validation failed for {namespace}:\n{report}")
            else:
                context.log.warning(f"SHACL validation issues for {namespace}:\n{report}")

    # Serialize the RDF graph to TTL format
    output_path = output_dir / f"{namespace}.ttl"
    vessel_rdf_graph.serialize(destination=str(output_path), format="turtle")
    context.log.info(f"Wrote {len(vessel_rdf_graph)} triples to {output_path}")

    # Add metadata about the output file to the context for Dagster UI
    context.add_output_metadata(
        {
            "output_path": MetadataValue.path(str(output_path)),
            "triple_count": MetadataValue.int(len(vessel_rdf_graph)),
        }
    )

    return str(output_path)


# =============================================================================
# Output Assets
# =============================================================================


@asset(
    group_name="output",
    deps=[validated_vessel_ttl],
    description="Combine all validated RDF graphs into one",
    kinds={"python", "RDF"},
)
def combined_vessel_graph(context: AssetExecutionContext, config: CombinedGraphConfig) -> Graph:
    """Combine all vessel TTL files into a single graph."""
    g = Graph()
    output_dir = Path(config.output_dir)
    combined_output = Path(config.combined_output)

    # Read all TTL files in the output directory and combine them into one graph
    ttl_files = list(output_dir.glob("*.ttl"))
    for ttl_file in ttl_files:
        # Skip the combined output file if it already exists from a previous run
        if ttl_file == combined_output:
            continue
        try:
            vessel_graph = Graph()
            vessel_graph.parse(ttl_file, format="turtle")
            g += vessel_graph
            context.log.info(f"Added {len(vessel_graph)} triples from {ttl_file.name}")
        except Exception as e:
            context.log.warning(f"Could not parse {ttl_file}: {e}")

    # Bind standard namespaces for cleaner TTL output
    g = bind_namespaces(g)

    # Write the combined graph to a TTL file
    combined_output.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(combined_output), format="turtle")
    context.log.info(f"Combined graph: {len(g)} triples written to {combined_output}")

    # Add metadata about the combined graph to the context for Dagster UI
    context.add_output_metadata(
        {
            "output_path": MetadataValue.path(str(combined_output)),
            "triple_count": MetadataValue.int(len(g)),
            "source_files": MetadataValue.int(len(ttl_files) - 1),
        }
    )

    return g


@asset(
    group_name="output",
    description="Upload combined graph to GraphDB",
    kinds={"python", "GraphDB"},
)
def graphdb_upload(
    context: AssetExecutionContext,
    graphdb_client: GraphDBClient,
    combined_vessel_graph: Graph,
) -> str:
    """Upload the combined graph to GraphDB via RDF4J HTTP endpoints."""
    triple_count = len(combined_vessel_graph)

    graphdb_client.wait_for_readiness()
    repo_created = graphdb_client.ensure_repository()

    if graphdb_client.clear_before_upload:
        graphdb_client.clear_repository()

    ttl_data = combined_vessel_graph.serialize(format="turtle")
    graphdb_client.upload_ttl(ttl_data)

    remote_triple_count = graphdb_client.triple_count()

    metadata: dict[str, Any] = {
        "graphdb_base_url": MetadataValue.text(graphdb_client._base_url),
        "repository_id": MetadataValue.text(graphdb_client.repository_id),
        "uploaded_triples": MetadataValue.int(triple_count),
        "repository_created": MetadataValue.text(str(repo_created)),
        "repository_cleared_before_upload": MetadataValue.text(
            str(graphdb_client.clear_before_upload)
        ),
    }
    if remote_triple_count is not None:
        metadata["remote_triple_count"] = MetadataValue.int(remote_triple_count)

    context.add_output_metadata(metadata)
    context.log.info(
        f"Uploaded {triple_count} triples to GraphDB repository "
        f"'{graphdb_client.repository_id}' at {graphdb_client._base_url}."
    )

    return f"{graphdb_client._base_url}/repositories/{graphdb_client.repository_id}"


@asset(
    group_name="output",
    description="Run SPARQL queries against GraphDB and display results",
    kinds={"python", "SPARQL"},
)
def sparql_summary(
    context: AssetExecutionContext,
    graphdb_client: GraphDBClient,
    graphdb_upload: str,
) -> None:
    """Run SPARQL queries on GraphDB and attach results as metadata tables in Dagster UI."""
    queries_dir = Path(__file__).parent.parent / "queries"

    vessel_df = graphdb_client.run_select_query((queries_dir / "vessel_overview.rq").read_text())
    vessel_df.columns = [
        "Vessel",
        "Label",
        "Main Engines",
        "Aux Engines",
        "Propellers",
        "Gearboxes",
    ]

    engine_df = graphdb_client.run_select_query((queries_dir / "engine_details.rq").read_text())
    engine_df.columns = ["Engine", "Label", "Power (kW)", "Fuels"]

    fuel_df = graphdb_client.run_select_query((queries_dir / "fuel_usage.rq").read_text())
    fuel_df.columns = ["Fuel", "Consumers"]

    remote_triple_count = graphdb_client.triple_count()

    context.add_output_metadata(
        {
            "vessel_overview": MetadataValue.md(vessel_df.to_markdown(index=False)),
            "engine_details": MetadataValue.md(engine_df.to_markdown(index=False)),
            "fuel_usage": MetadataValue.md(fuel_df.to_markdown(index=False)),
            "graphdb_repository": MetadataValue.text(graphdb_upload),
            "graphdb_repository_id": MetadataValue.text(graphdb_client.repository_id),
            "total_triples": MetadataValue.int(remote_triple_count or 0),
        }
    )
