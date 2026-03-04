"""Dagster assets for vessel data harmonisation pipeline.

Pipeline structure:
1. spreadsheet_data - Load the Excel spreadsheet and discover vessels
2. extracted_vessel_json - Extract JSON for each vessel (partitioned)
3. validated_vessel_json - Validate extracted JSON (partitioned)
4. vessel_rdf_graph - Harmonise to RDF for each vessel (partitioned)
5a. vessel_ttl - Serialize RDF graph to TTL file (partitioned)
5b. shacl_validation_report - SHACL validation of RDF graph (partitioned)
6. graphdb_upload - Upload vessel TTL to per-vessel GraphDB repository (partitioned)
7. sparql_summary - SPARQL summary tables queried from all vessel repositories
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
from dagster_pipeline.validation.json_validation import validate_vessel_json
from twinship_harmonisation import harmonise_twinship_vessel

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


class TtlOutputConfig(Config):
    """Configuration for TTL file output."""

    output_dir: str = "output"


class ShaclConfig(Config):
    """Configuration for SHACL validation."""

    shapes_path: str = "shacl/"
    fail_on_validation_error: bool = True


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


@asset(
    group_name="extraction",
    partitions_def=vessel_partitions_def,
    description="Validate extracted vessel JSON (ID formats, referential integrity, types/fuels)",
    kinds={"pydantic"},
)
def validated_vessel_json(context: AssetExecutionContext, extracted_vessel_json: dict) -> dict:
    """Validate the extracted vessel JSON and pass it through."""
    namespace = context.partition_key

    report = validate_vessel_json(extracted_vessel_json)

    for w in report.warnings:
        context.log.warning(f"[{namespace}] JSON validation: {w}")

    context.add_output_metadata(
        {
            "json_validation_warnings": MetadataValue.int(len(report.warnings)),
            "sample_warnings": MetadataValue.md("\n".join(f"- {w}" for w in report.warnings[:10])),
        }
    )

    if not report.ok():
        raise ValueError(f"[{namespace}] JSON validation failed:\n" + "\n".join(report.errors))

    return extracted_vessel_json


# =============================================================================
# Harmonisation Assets
# =============================================================================


@asset(
    group_name="harmonisation",
    partitions_def=vessel_partitions_def,
    description="Harmonise vessel JSON to RDF graph for a specific vessel",
    kinds={"RDF", "python"},
)
def vessel_rdf_graph(context: AssetExecutionContext, validated_vessel_json: dict) -> Graph:
    """Convert extracted vessel data to RDF triples."""
    namespace = context.partition_key

    # Validate that we have extracted data for this vessel before attempting harmonisation
    if not validated_vessel_json:
        context.log.warning(f"No data for {namespace}, returning empty graph")
        return Graph()

    # Harmonise the extracted vessel data into RDF triples
    g = harmonise_twinship_vessel(**validated_vessel_json)

    # Log the number of triples generated
    vessel_id = validated_vessel_json.get("vessel", {}).get("id", "unknown")
    context.log.info(f"Generated {len(g)} triples for {namespace} ({vessel_id})")

    # Add metadata about the harmonised graph to the context for Dagster UI
    context.add_output_metadata({"triple_count": MetadataValue.int(len(g))})

    return g


# =============================================================================
# Validation Assets
# =============================================================================


@asset(
    group_name="harmonisation",
    partitions_def=vessel_partitions_def,
    description="Serialize RDF graph to TTL file for a specific vessel",
    kinds={"turtle"},
)
def vessel_ttl(
    context: AssetExecutionContext,
    config: TtlOutputConfig,
    vessel_rdf_graph: Graph,
) -> str:
    """Serialize RDF graph to TTL file."""
    namespace = context.partition_key
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if vessel_rdf_graph is None or len(vessel_rdf_graph) == 0:
        context.log.warning(f"Empty graph for {namespace}, skipping")
        return ""

    output_path = output_dir / f"{namespace}.ttl"
    vessel_rdf_graph.serialize(destination=str(output_path), format="turtle")
    context.log.info(f"Wrote {len(vessel_rdf_graph)} triples to {output_path}")

    context.add_output_metadata(
        {
            "output_path": MetadataValue.path(str(output_path)),
            "triple_count": MetadataValue.int(len(vessel_rdf_graph)),
        }
    )

    return str(output_path)


@asset(
    group_name="harmonisation",
    partitions_def=vessel_partitions_def,
    description="Run SHACL validation on RDF graph for a specific vessel",
    kinds={"SHACL"},
)
def shacl_validation_report(
    context: AssetExecutionContext,
    config: ShaclConfig,
    vessel_rdf_graph: Graph,
    shacl_validator: ShaclValidator,
) -> str:
    """Validate RDF graph against SHACL shapes and return the report."""
    namespace = context.partition_key
    shapes_path = Path(config.shapes_path)

    if vessel_rdf_graph is None or len(vessel_rdf_graph) == 0:
        context.log.warning(f"Empty graph for {namespace}, skipping validation")
        return "SKIPPED"

    if not shapes_path.exists():
        context.log.warning(f"Shapes path {shapes_path} not found, skipping validation")
        return "SKIPPED"

    conforms, report = shacl_validator.validate(vessel_rdf_graph, shapes_path)

    if conforms:
        context.log.info(f"SHACL validation passed for {namespace}")
        context.add_output_metadata(
            {
                "conforms": MetadataValue.bool(True),
                "report": MetadataValue.md("SHACL validation **passed**."),
            }
        )
        return "PASSED"

    if config.fail_on_validation_error:
        context.add_output_metadata(
            {
                "conforms": MetadataValue.bool(False),
                "report": MetadataValue.md(f"```\n{report}\n```"),
            }
        )
        raise ValueError(f"SHACL validation failed for {namespace}:\n{report}")

    context.log.warning(f"SHACL validation issues for {namespace}:\n{report}")
    context.add_output_metadata(
        {
            "conforms": MetadataValue.bool(False),
            "report": MetadataValue.md(f"```\n{report}\n```"),
        }
    )
    return report


# =============================================================================
# Output Assets
# =============================================================================


@asset(
    group_name="output",
    partitions_def=vessel_partitions_def,
    description="Upload vessel TTL to its own per-vessel GraphDB repository",
    kinds={"GraphDB"},
)
def graphdb_upload(
    context: AssetExecutionContext,
    config: TtlOutputConfig,
    graphdb_client: GraphDBClient,
    vessel_ttl: str,
    shacl_validation_report: str,
) -> str:
    """Upload a single vessel's TTL file to its own GraphDB repository."""
    vessel = context.partition_key
    repo_id = vessel
    repo_title = f"TwinShip - {vessel}"

    if not vessel_ttl:
        context.log.warning(f"No TTL output for {vessel}, skipping upload")
        return ""

    ttl_path = Path(vessel_ttl)
    if not ttl_path.exists():
        context.log.warning(f"TTL file {ttl_path} not found for {vessel}, skipping upload")
        return ""

    graphdb_client.wait_for_readiness()
    repo_created = graphdb_client.ensure_repository(repo_id=repo_id, title=repo_title)

    if graphdb_client.clear_before_upload:
        graphdb_client.clear_repository(repo_id=repo_id)

    g = Graph()
    g.parse(ttl_path, format="turtle")
    triple_count = len(g)
    graphdb_client.upload_ttl(g.serialize(format="turtle"), repo_id=repo_id)
    context.log.info(f"Uploaded {triple_count} triples to repository '{repo_id}'")

    remote_triple_count = graphdb_client.triple_count(repo_id=repo_id)

    metadata: dict[str, Any] = {
        "graphdb_base_url": MetadataValue.text(graphdb_client.normalized_base_url),
        "repository_id": MetadataValue.text(repo_id),
        "uploaded_triples": MetadataValue.int(triple_count),
        "repository_created": MetadataValue.text(str(repo_created)),
        "repository_cleared_before_upload": MetadataValue.text(
            str(graphdb_client.clear_before_upload)
        ),
    }
    if remote_triple_count is not None:
        metadata["remote_triple_count"] = MetadataValue.int(remote_triple_count)

    context.add_output_metadata(metadata)
    return f"{graphdb_client.normalized_base_url}/repositories/{repo_id}"


@asset(
    group_name="output",
    deps=[graphdb_upload],
    description="Run SPARQL queries against all per-vessel GraphDB repositories",
    kinds={"SPARQL"},
)
def sparql_summary(
    context: AssetExecutionContext,
    graphdb_client: GraphDBClient,
) -> None:
    """Run SPARQL queries on all vessel repositories and show combined results."""
    import pandas as pd

    queries_dir = Path(__file__).parent.parent / "queries"

    # Discover vessel repositories by listing all registered partitions
    vessel_partitions = list(context.instance.get_dynamic_partitions(vessel_partitions_def.name))

    if not vessel_partitions:
        context.log.warning("No vessel partitions registered, skipping SPARQL summary")
        return

    all_vessels = []
    all_engines = []
    all_fuels = []
    total_triples = 0

    for repo_id in vessel_partitions:
        count = graphdb_client.triple_count(repo_id=repo_id)
        if count is None or count == 0:
            context.log.info(f"Repository '{repo_id}' empty or missing, skipping")
            continue

        total_triples += count

        vessel_df = graphdb_client.run_select_query(
            (queries_dir / "vessel_overview.rq").read_text(), repo_id=repo_id
        )
        if not vessel_df.empty:
            all_vessels.append(vessel_df)

        engine_df = graphdb_client.run_select_query(
            (queries_dir / "engine_details.rq").read_text(), repo_id=repo_id
        )
        if not engine_df.empty:
            all_engines.append(engine_df)

        fuel_df = graphdb_client.run_select_query(
            (queries_dir / "fuel_usage.rq").read_text(), repo_id=repo_id
        )
        if not fuel_df.empty:
            all_fuels.append(fuel_df)

    vessel_combined = pd.concat(all_vessels, ignore_index=True) if all_vessels else pd.DataFrame()
    engine_combined = pd.concat(all_engines, ignore_index=True) if all_engines else pd.DataFrame()
    fuel_combined = pd.concat(all_fuels, ignore_index=True) if all_fuels else pd.DataFrame()

    if not vessel_combined.empty:
        vessel_combined.columns = [
            "Vessel",
            "Label",
            "Main Engines",
            "Aux Engines",
            "Propellers",
            "Gearboxes",
        ]
    if not engine_combined.empty:
        engine_combined.columns = ["Engine", "Label", "Power (kW)", "Fuels"]
    if not fuel_combined.empty:
        fuel_combined.columns = ["Fuel", "Consumers"]

    context.add_output_metadata(
        {
            "vessel_overview": MetadataValue.md(
                vessel_combined.to_markdown(index=False)
                if not vessel_combined.empty
                else "_No data_"
            ),
            "engine_details": MetadataValue.md(
                engine_combined.to_markdown(index=False)
                if not engine_combined.empty
                else "_No data_"
            ),
            "fuel_usage": MetadataValue.md(
                fuel_combined.to_markdown(index=False) if not fuel_combined.empty else "_No data_"
            ),
            "repositories_queried": MetadataValue.text(", ".join(vessel_partitions)),
            "total_triples": MetadataValue.int(total_triples),
        }
    )
