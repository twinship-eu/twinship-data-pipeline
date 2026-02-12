"""Dagster assets for vessel data harmonisation pipeline.

Pipeline structure:
1. spreadsheet_data - Load the Excel spreadsheet and discover vessels
2. extracted_vessel_json - Extract JSON for each vessel (partitioned)
3. vessel_rdf_graph - Harmonise to RDF for each vessel (partitioned)
4. validated_vessel_ttl - Validate and write TTL files (partitioned)
5. combined_vessel_graph - Combine all RDF graphs
6. sparql_summary - SPARQL data tables for the Dagster UI
7. graphdb_upload - Upload the combined graph to GraphDB
"""

import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dagster import (
    AssetExecutionContext,
    Config,
    DynamicPartitionsDefinition,
    Failure,
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


def _env_bool(var_name: str, default: bool) -> bool:
    raw = os.getenv(var_name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(var_name: str, default: int) -> int:
    raw = os.getenv(var_name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


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


class GraphDBConfig(Config):
    """Configuration for GraphDB upload."""

    base_url: str = os.getenv("GRAPHDB_BASE_URL", "http://localhost:7200")
    repository_id: str = os.getenv("GRAPHDB_REPOSITORY_ID", "twinship")
    repository_title: str = os.getenv("GRAPHDB_REPOSITORY_TITLE", "TwinShip Data Repository")
    clear_repository_before_upload: bool = _env_bool("GRAPHDB_CLEAR_BEFORE_UPLOAD", True)
    timeout_seconds: int = _env_int("GRAPHDB_TIMEOUT_SECONDS", 30)
    max_readiness_checks: int = _env_int("GRAPHDB_MAX_READINESS_CHECKS", 20)
    readiness_check_interval_seconds: int = _env_int(
        "GRAPHDB_READINESS_CHECK_INTERVAL_SECONDS", 3
    )
    username: str | None = os.getenv("GRAPHDB_USERNAME")
    password: str | None = os.getenv("GRAPHDB_PASSWORD")


# =============================================================================
# GraphDB Helpers
# =============================================================================


def _normalize_graphdb_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _graphdb_auth(config: GraphDBConfig) -> tuple[str, str] | None:
    if not config.username and not config.password:
        return None
    if not config.username or not config.password:
        raise Failure(
            "GraphDB credentials misconfigured: both username and password are required."
        )
    return config.username, config.password


def _ttl_escape_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _create_graphdb_repo_config(repository_id: str, title: str) -> str:
    escaped_repo_id = _ttl_escape_literal(repository_id)
    escaped_title = _ttl_escape_literal(title)
    return f"""@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.
@prefix rep: <http://www.openrdf.org/config/repository#>.
@prefix sr: <http://www.openrdf.org/config/repository/sail#>.
@prefix sail: <http://www.openrdf.org/config/sail#>.
@prefix graphdb: <http://www.ontotext.com/config/graphdb#>.

[] a rep:Repository ;
    rep:repositoryID "{escaped_repo_id}" ;
    rdfs:label "{escaped_title}" ;
    rep:repositoryImpl [
        rep:repositoryType "graphdb:SailRepository" ;
        sr:sailImpl [
            sail:sailType "graphdb:Sail" ;
            graphdb:ruleset "empty" ;
            graphdb:check-for-inconsistencies "false" ;
            graphdb:disable-sameAs "true" ;
            graphdb:enable-context-index "true"
        ]
    ].
"""


def _raise_graphdb_error(message: str, response: requests.Response | None = None) -> None:
    if response is None:
        raise Failure(message)

    body = response.text.strip()
    if len(body) > 400:
        body = f"{body[:397]}..."

    raise Failure(
        f"{message}. HTTP {response.status_code} {response.reason}. "
        f"Response: {body or '<empty>'}"
    )


def _wait_for_graphdb(base_url: str, auth: tuple[str, str] | None, config: GraphDBConfig) -> None:
    repositories_url = f"{base_url}/rest/repositories"
    attempts = config.max_readiness_checks

    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(
                repositories_url,
                auth=auth,
                timeout=config.timeout_seconds,
            )
        except requests.RequestException:
            response = None

        if response is not None and response.status_code == 200:
            return

        if response is not None and response.status_code in {401, 403}:
            _raise_graphdb_error(
                "GraphDB is reachable but authentication failed while listing repositories",
                response,
            )

        if attempt < attempts:
            time.sleep(config.readiness_check_interval_seconds)

    _raise_graphdb_error(
        f"GraphDB at {base_url} did not become ready after "
        f"{attempts} checks with {config.readiness_check_interval_seconds}s interval"
    )


def _repository_exists(
    base_url: str,
    auth: tuple[str, str] | None,
    repository_id: str,
    timeout_seconds: int,
) -> bool:
    try:
        response = requests.get(
            f"{base_url}/rest/repositories/{repository_id}",
            auth=auth,
            timeout=timeout_seconds,
        )
    except requests.RequestException as e:
        _raise_graphdb_error(f"Could not reach GraphDB while checking repository: {e}")

    if response.status_code == 200:
        return True
    if response.status_code == 404:
        return False
    _raise_graphdb_error(f"Could not check repository '{repository_id}'", response)
    return False


def _create_repository_if_missing(
    base_url: str,
    auth: tuple[str, str] | None,
    config: GraphDBConfig,
) -> bool:
    if _repository_exists(base_url, auth, config.repository_id, config.timeout_seconds):
        return False

    try:
        response = requests.post(
            f"{base_url}/rest/repositories",
            auth=auth,
            files={
                "config": (
                    "repo-config.ttl",
                    _create_graphdb_repo_config(config.repository_id, config.repository_title),
                    "text/turtle",
                )
            },
            timeout=config.timeout_seconds,
        )
    except requests.RequestException as e:
        _raise_graphdb_error(
            f"Could not reach GraphDB while creating repository '{config.repository_id}': {e}"
        )

    if response.status_code not in {200, 201, 204}:
        _raise_graphdb_error(
            f"Could not create GraphDB repository '{config.repository_id}'",
            response,
        )

    return True


def _clear_repository(
    base_url: str,
    auth: tuple[str, str] | None,
    repository_id: str,
    timeout_seconds: int,
) -> None:
    try:
        response = requests.delete(
            f"{base_url}/repositories/{repository_id}/statements",
            auth=auth,
            timeout=timeout_seconds,
        )
    except requests.RequestException as e:
        _raise_graphdb_error(f"Could not reach GraphDB while clearing repository '{repository_id}': {e}")

    if response.status_code not in {200, 204}:
        _raise_graphdb_error(
            f"Could not clear GraphDB repository '{repository_id}' before upload",
            response,
        )


def _upload_graph_ttl(
    base_url: str,
    auth: tuple[str, str] | None,
    repository_id: str,
    ttl_data: str,
    timeout_seconds: int,
) -> None:
    try:
        response = requests.post(
            f"{base_url}/repositories/{repository_id}/statements",
            data=ttl_data.encode("utf-8"),
            headers={"Content-Type": "text/turtle; charset=utf-8"},
            auth=auth,
            timeout=timeout_seconds,
        )
    except requests.RequestException as e:
        _raise_graphdb_error(f"Could not reach GraphDB while uploading data to '{repository_id}': {e}")

    if response.status_code not in {200, 204}:
        _raise_graphdb_error(f"Could not upload data to repository '{repository_id}'", response)


def _repository_triple_count(
    base_url: str,
    auth: tuple[str, str] | None,
    repository_id: str,
    timeout_seconds: int,
) -> int | None:
    try:
        response = requests.get(
            f"{base_url}/repositories/{repository_id}/size",
            auth=auth,
            timeout=timeout_seconds,
        )
    except requests.RequestException:
        return None

    if response.status_code != 200:
        return None
    try:
        return int(response.text.strip())
    except ValueError:
        return None


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
    description="Run SPARQL queries against the combined graph and display results",
    kinds={"python", "SPARQL"},
)
def sparql_summary(context: AssetExecutionContext, combined_vessel_graph: Graph) -> None:
    """Run SPARQL queries and attach results as metadata tables in the Dagster UI."""
    g = combined_vessel_graph
    queries_dir = Path(__file__).parent.parent / "queries"

    # Run SPARQL query to get vessel overview
    vessel_df = pd.DataFrame(g.query((queries_dir / "vessel_overview.rq").read_text()))
    vessel_df.columns = [
        "Vessel",
        "Label",
        "Main Engines",
        "Aux Engines",
        "Propellers",
        "Gearboxes",
    ]

    # Run SPARQL query to get engine details
    engine_df = pd.DataFrame(g.query((queries_dir / "engine_details.rq").read_text()))
    engine_df.columns = ["Engine", "Label", "Power (kW)", "Fuels"]

    # Run SPARQL query to get fuel usage summary
    fuel_df = pd.DataFrame(g.query((queries_dir / "fuel_usage.rq").read_text()))
    fuel_df.columns = ["Fuel", "Consumers"]

    context.add_output_metadata(
        {
            "vessel_overview": MetadataValue.md(vessel_df.to_markdown(index=False)),
            "engine_details": MetadataValue.md(engine_df.to_markdown(index=False)),
            "fuel_usage": MetadataValue.md(fuel_df.to_markdown(index=False)),
            "total_triples": MetadataValue.int(len(g)),
        }
    )


@asset(
    group_name="output",
    description="Upload combined graph to GraphDB",
    kinds={"python", "GraphDB"},
)
def graphdb_upload(
    context: AssetExecutionContext,
    config: GraphDBConfig,
    combined_vessel_graph: Graph,
) -> str:
    """Upload the combined graph to GraphDB via RDF4J HTTP endpoints."""
    triple_count = len(combined_vessel_graph)
    base_url = _normalize_graphdb_base_url(config.base_url)
    auth = _graphdb_auth(config)

    _wait_for_graphdb(base_url, auth, config)
    repo_created = _create_repository_if_missing(base_url, auth, config)

    if config.clear_repository_before_upload:
        _clear_repository(base_url, auth, config.repository_id, config.timeout_seconds)

    ttl_data = combined_vessel_graph.serialize(format="turtle")
    if isinstance(ttl_data, bytes):
        ttl_data = ttl_data.decode("utf-8")
    _upload_graph_ttl(
        base_url,
        auth,
        config.repository_id,
        ttl_data,
        config.timeout_seconds,
    )

    remote_triple_count = _repository_triple_count(
        base_url,
        auth,
        config.repository_id,
        config.timeout_seconds,
    )

    metadata: dict[str, Any] = {
        "graphdb_base_url": MetadataValue.text(base_url),
        "repository_id": MetadataValue.text(config.repository_id),
        "uploaded_triples": MetadataValue.int(triple_count),
        "repository_created": MetadataValue.text(str(repo_created)),
        "repository_cleared_before_upload": MetadataValue.text(
            str(config.clear_repository_before_upload)
        ),
    }
    if remote_triple_count is not None:
        metadata["remote_triple_count"] = MetadataValue.int(remote_triple_count)

    context.add_output_metadata(metadata)
    context.log.info(
        f"Uploaded {triple_count} triples to GraphDB repository '{config.repository_id}' "
        f"at {base_url}."
    )

    return f"{base_url}/repositories/{config.repository_id}"
