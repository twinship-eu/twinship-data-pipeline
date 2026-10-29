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

import xml.etree.ElementTree as ET
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
from dagster_pipeline.futuristic_extraction import (
    discover_futuristic_vessels,
    extract_futuristic_vessel,
    load_futuristic_sheets,
)
from dagster_pipeline.resources import GraphDBClient, ShaclValidator
from dagster_pipeline.utils import vessel_data_dir
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

    # Optional; only processed when the file exists.
    spreadsheet_path: str = str(vessel_data_dir() / "TwinShip-table-schema-specification.xlsx")
    futuristic_spreadsheet_path: str = "data/RoRo Futuristic Vessel KG Working File.xlsx"


class TtlOutputConfig(Config):
    """Configuration for TTL file output."""

    output_dir: str = "output"


class ShaclConfig(Config):
    """Configuration for SHACL validation."""

    shapes_path: str = "shacl/"
    fail_on_validation_error: bool = True


ONTOLOGY_CATALOG = Path(__file__).resolve().parents[2] / "ontology" / "catalog-v001.xml"
CATALOG_NS = "urn:oasis:names:tc:entity:xmlns:xml:catalog"


def ontology_server_files(catalog: Path = ONTOLOGY_CATALOG) -> list[str]:
    """Ontology files to import into each per-vessel repo, read from the ontology catalog.

    Paths are relative to the GraphDB import dir, where ontology/ is mounted.
    graphdb/init.sh derives the same list from the same catalog.
    """
    uris = (e.get("uri") for e in ET.parse(catalog).getroot().iter(f"{{{CATALOG_NS}}}uri"))
    return sorted({f"ontology/{uri}" for uri in uris})


# =============================================================================
# Extraction Assets
# =============================================================================


@asset(
    group_name="extraction",
    description="Load the TwinShip Excel spreadsheet and discover vessels",
    kinds={"excel"},
)
def spreadsheet_data(context: AssetExecutionContext, config: SpreadsheetConfig) -> dict:
    """Load all sheets from both TwinShip spreadsheets and discover vessels."""
    # Load conventional spreadsheet if it exists (kept outside the repository)
    spreadsheet_path = Path(config.spreadsheet_path)
    sheets: dict = {}
    vessels: dict = {}
    if spreadsheet_path.exists():
        sheets = load_spreadsheet_sheets(str(spreadsheet_path))
        for name, df in sheets.items():
            context.log.info(f"Loaded {name}: {len(df)} rows")
        vessels = discover_vessels_from_sheets(sheets)
    else:
        context.log.info(f"Spreadsheet not found at {spreadsheet_path}, skipping its vessels")

    # Load futuristic spreadsheet if it exists
    fv_path = Path(config.futuristic_spreadsheet_path)
    fv_sheets: dict = {}
    if fv_path.exists():
        fv_sheets = load_futuristic_sheets(str(fv_path))
        for name, df in fv_sheets.items():
            context.log.info(f"Loaded futuristic {name}: {len(df)} rows")

        fv_vessels = discover_futuristic_vessels(fv_sheets)
        vessels.update(fv_vessels)
    else:
        context.log.info(f"Futuristic spreadsheet not found at {fv_path}, skipping")

    context.log.info(f"Discovered {len(vessels)} vessels: {list(vessels.keys())}")

    context.add_output_metadata(
        {
            "vessels": MetadataValue.text(", ".join(vessels.keys())),
            "vessel_count": MetadataValue.int(len(vessels)),
            "sheet_count": MetadataValue.int(len(sheets) + len(fv_sheets)),
        }
    )

    return {"sheets": sheets, "fv_sheets": fv_sheets, "vessels": vessels}


@asset(
    group_name="extraction",
    partitions_def=vessel_partitions_def,
    description="Extract vessel JSON for a specific vessel from spreadsheet",
    kinds={"json"},
)
def extracted_vessel_json(context: AssetExecutionContext, spreadsheet_data: dict) -> dict:
    """Extract vessel data for the current vessel partition."""
    namespace = context.partition_key
    vessels = spreadsheet_data["vessels"]

    if namespace not in vessels:
        context.log.error(f"Unknown vessel namespace: {namespace}")
        return {}

    vessel_info = vessels[namespace]
    prefix = vessel_info["prefix"]

    # Route extraction by prefix: FV uses futuristic spreadsheet
    if prefix == "FV":
        data = extract_futuristic_vessel(
            spreadsheet_data["fv_sheets"],
            prefix,
            namespace,
        )
    else:
        data = extract_vessel_for_operator(
            spreadsheet_data["sheets"],
            prefix,
            namespace,
        )

    vessel_id = data.get("vessel", {}).get("id", "unknown")
    context.log.info(
        f"Extracted {namespace}: vessel={vessel_id}, "
        f"main_engines={len(data.get('main_engines', []))}, "
        f"gensets={len(data.get('gensets', []))}, "
        f"propellers={len(data.get('propellers', []))}"
    )

    context.add_output_metadata(
        {
            "vessel_id": MetadataValue.text(vessel_id),
            "main_engine_count": MetadataValue.int(len(data.get("main_engines", []))),
            "genset_count": MetadataValue.int(len(data.get("gensets", []))),
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

    # Determine source file based on vessel type
    GITHUB_BASE = "https://github.com/twinship-eu/twinship-data-pipeline/blob/main/data"
    is_futuristic = bool(validated_vessel_json.get("gensets"))
    if is_futuristic:
        source_file = f"{GITHUB_BASE}/RoRo%20Futuristic%20Vessel%20KG%20Working%20File.xlsx"
    else:
        source_file = f"{GITHUB_BASE}/TwinShip-table-schema-specification.xlsx"

    # Harmonise the extracted vessel data into RDF triples
    g = harmonise_twinship_vessel(
        **validated_vessel_json,
        source_file=source_file,
        pipeline_version="0.1.0",
    )

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

    # Import ontology files so RDFS+ reasoning works on vessel data
    context.log.info(f"Importing ontology into '{repo_id}'...")
    graphdb_client.import_server_files(ontology_server_files(), repo_id=repo_id)
    graphdb_client.wait_for_import(repo_id=repo_id)
    context.log.info(f"Ontology import complete for '{repo_id}'")

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
