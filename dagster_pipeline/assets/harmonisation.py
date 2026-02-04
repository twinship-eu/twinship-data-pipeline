"""Assets for vessel data harmonisation pipeline with dynamic partitioning.

Pipeline structure:
1. spreadsheet_data - Load the Excel spreadsheet and discover operators (non-partitioned)
2. extracted_vessel_json - Extract JSON for each operator (partitioned)
3. vessel_rdf_graph - Harmonise to RDF for each operator (partitioned)
4. validated_vessel_ttl - Validate and write TTL files (partitioned)
5. combined_vessel_graph - Combine all RDF graphs (non-partitioned)
6. graphdb_upload - Upload to GraphDB (non-partitioned)

Operators are discovered automatically from the spreadsheet:
- Entity IDs contain operator prefixes (e.g., "GRI-VV-1")
- The prefix is the first segment before the hyphen
- No code changes needed when adding new operators - just add data to spreadsheet

Workflow:
1. Materialize spreadsheet_data first
2. Enable and start the operator_discovery_sensor
3. The sensor registers discovered operators as partitions
4. Then run the partitioned assets (use "Materialize all" or backfill)
"""

from pathlib import Path

import pandas as pd
from dagster import (
    AssetExecutionContext,
    Config,
    DynamicPartitionsDefinition,
    MetadataValue,
    asset,
)
from rdflib import Graph

from dagster_pipeline.resources import ShaclValidator
from twinship_harmonisation import harmonise_vessel_data
from twinship_harmonisation.utils import bind_namespaces

# =============================================================================
# Dynamic Partitions Definition
# =============================================================================
# Operators are registered dynamically by the sensor after spreadsheet_data
# is materialized. Each operator becomes a partition.

operator_partitions_def = DynamicPartitionsDefinition(name="operators")


# =============================================================================
# Operator Configuration
# =============================================================================
# Operators are discovered automatically from the spreadsheet.
# The operator prefix is the first segment before the hyphen in entity IDs
# (e.g., "GRI" from "GRI-VV-1").
#
# Known operators get descriptive namespaces (see KNOWN_OPERATORS).
# Unknown operators default to lowercase prefix as namespace.


def extract_operator_prefix(entity_id: str, position: int = 0) -> str | None:
    """Extract the operator prefix from an entity ID.

    Entity IDs follow different patterns:
    - position=0: PREFIX-TYPE-NUMBER (e.g., "GRI-VV-1" -> "GRI")
    - position=1: TYPE-PREFIX-NUMBER (e.g., "CPP-GRI-1" -> "GRI")

    Args:
        entity_id: The entity ID string
        position: Which segment contains the operator prefix (0=first, 1=second)
    """
    if pd.isna(entity_id):
        return None
    parts = str(entity_id).split("-")
    if len(parts) >= 2 and position < len(parts):
        return parts[position].upper()
    return None


def parse_types(type_string: str | None) -> list[str]:
    """Parse types from spreadsheet format like '[tws:FourStroke, tws:DieselEngine]'.

    Returns a list of type names without the 'tws:' prefix.
    """
    if not type_string or pd.isna(type_string):
        return []

    types = []
    # Remove brackets and split by comma
    cleaned = str(type_string).replace("[", "").replace("]", "")
    for part in cleaned.split(","):
        part = part.strip()
        if part.startswith("tws:"):
            types.append(part[4:].strip())
        elif part:
            types.append(part.strip())
    return types


# Known operator mappings (prefix -> namespace, display name)
# Add new operators here for better names, or they'll default to lowercase prefix
KNOWN_OPERATORS = {
    "GRI": ("grimaldi", "Grimaldi"),
    "STL": ("stena-scandinavica", "Stena Line"),
    "STT": ("stena-tanker", "Stena Tanker"),
}


def prefix_to_namespace(prefix: str) -> str:
    """Convert an operator prefix to a namespace."""
    if prefix.upper() in KNOWN_OPERATORS:
        return KNOWN_OPERATORS[prefix.upper()][0]
    return prefix.lower()


def prefix_to_name(prefix: str) -> str:
    """Convert an operator prefix to a display name."""
    if prefix.upper() in KNOWN_OPERATORS:
        return KNOWN_OPERATORS[prefix.upper()][1]
    return prefix.title()


def entity_belongs_to_operator(entity_id: str, operator_prefix: str, position: int = 0) -> bool:
    """Check if an entity ID belongs to a specific operator.

    Args:
        entity_id: The entity ID string
        operator_prefix: The operator prefix to match (e.g., "GRI")
        position: Which segment contains the operator prefix (0=first, 1=second)
    """
    return extract_operator_prefix(entity_id, position) == operator_prefix


# =============================================================================
# Step 1: Load Spreadsheet (Non-partitioned)
# =============================================================================


class SpreadsheetConfig(Config):
    """Configuration for spreadsheet asset."""

    spreadsheet_path: str = "data/TwinShip-table-schema-specification.xlsx"


def discover_operators_from_sheets(sheets: dict[str, pd.DataFrame]) -> dict[str, dict]:
    """Discover all operator prefixes from entity IDs in the spreadsheet.

    Only uses Vessel and Main_Engine IDs for discovery since they have
    consistent format (operator-type-number like "GRI-RR-1", "STL-ME-1").
    Other sheets have different formats (type-operator-number).

    Returns a dict mapping namespace to {prefix, name}.
    """
    prefixes = set()

    # Only use sheets with consistent ID format (operator-type-number)
    id_columns = {
        "Vessel": "TWINSHIP-VESSEL-ID",
        "Main_Engine": "TWINSHIP-MAIN-ENGINE-ID",
    }

    for sheet_name, id_col in id_columns.items():
        if sheet_name in sheets and id_col in sheets[sheet_name].columns:
            for entity_id in sheets[sheet_name][id_col]:
                prefix = extract_operator_prefix(entity_id)
                if prefix:
                    prefixes.add(prefix)

    # Convert to dict with namespace as key
    return {
        prefix_to_namespace(prefix): {"prefix": prefix, "name": prefix_to_name(prefix)}
        for prefix in sorted(prefixes)
    }


@asset(
    group_name="extraction",
    description="Load the TwinShip Excel spreadsheet and discover operators",
)
def spreadsheet_data(
    context: AssetExecutionContext, config: SpreadsheetConfig
) -> dict:
    """Load all sheets from the TwinShip spreadsheet and discover operators.

    This asset discovers operators and outputs their namespaces in metadata
    so the sensor can register them as dynamic partitions.

    Returns a dictionary with:
    - 'sheets': mapping of sheet names to DataFrames
    - 'operators': dict of discovered operators {namespace: {prefix, name}}
    """
    spreadsheet_path = Path(config.spreadsheet_path)
    if not spreadsheet_path.exists():
        context.log.error(f"Spreadsheet not found: {spreadsheet_path}")
        raise FileNotFoundError(f"Spreadsheet not found: {spreadsheet_path}")

    # Read all relevant sheets
    # Map internal names to actual spreadsheet sheet names
    sheets = {}
    sheet_mapping = {
        "Vessel": "VESSEL System",
        "Main_Engine": "MAIN ENGINE System",
        "Auxiliary_Engine": "AUXILIARY GENSET System",
        "Propeller": "PROPELLER System",
        "Gearbox": "GEARBOX System",
        "PMS": "PMS System",
        "Other": "OTHER Systems",
    }

    for internal_name, actual_sheet_name in sheet_mapping.items():
        if actual_sheet_name is None:
            continue
        try:
            # Read with header on row 1 (0-indexed), which contains column names like "TWINSHIP-VESSEL-ID"
            # Skip row 2 which contains data types
            df = pd.read_excel(
                spreadsheet_path,
                sheet_name=actual_sheet_name,
                header=1,  # Use row with "TWINSHIP-*" column names
                skiprows=[2],  # Skip the data type row
            )
            # Handle duplicate column names
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
            sheets[internal_name] = df
            context.log.info(f"Loaded {internal_name} (from '{actual_sheet_name}'): {len(df)} rows")
        except Exception as e:
            context.log.warning(f"Could not load sheet {internal_name}: {e}")

    # Discover operators from entity IDs
    operators = discover_operators_from_sheets(sheets)

    context.log.info(f"Discovered {len(operators)} operators: {list(operators.keys())}")

    # Output operators as metadata so the sensor can read them
    context.add_output_metadata({
        "operators": MetadataValue.text(", ".join(operators.keys())),
        "operator_count": MetadataValue.int(len(operators)),
        "sheet_count": MetadataValue.int(len(sheets)),
    })

    return {"sheets": sheets, "operators": operators}


# =============================================================================
# Step 2: Extract JSON for Each Operator (Partitioned)
# =============================================================================


def clean_value(val):
    """Clean a value for JSON serialization."""
    if pd.isna(val):
        return None
    if isinstance(val, float) and val != val:  # NaN check
        return None
    return val


def extract_vessel_for_operator(
    sheets: dict[str, pd.DataFrame], operator_prefix: str, namespace: str, operator_name: str
) -> dict:
    """Extract vessel data for a specific operator."""
    result = {
        "namespace": namespace,
        "operator": operator_name,
        "vessel": {},
        "main_engines": [],
        "auxiliary_engines": [],
        "propellers": [],
        "gearboxes": [],
        "boilers": [],
        "pms": [],
        "emergency_generators": [],
        "thrusters": [],
        "shaft_generators": [],
    }

    # Extract vessel (ID format: OPERATOR-TYPE-NUMBER, e.g., "GRI-RR-1")
    if "Vessel" in sheets:
        df = sheets["Vessel"]
        for _, row in df.iterrows():
            vessel_id = row.get("TWINSHIP-VESSEL-ID")
            if entity_belongs_to_operator(vessel_id, operator_prefix, position=0):
                types = parse_types(row.get("TWINSHIP-VESSEL-TYPE"))
                vessel_type = types[0] if types else None

                result["vessel"] = {
                    "id": clean_value(vessel_id),
                    "label": clean_value(row.get("TWINSHIP-VESSEL-NAME")),
                    "type": vessel_type,
                    "displacement_max_mt": clean_value(row.get("TWINSHIP-DISPLACEMENT-MAX-IN-MT")),
                    "draft_aft_max_m": clean_value(row.get("TWINSHIP-VESSEL-DRAFT-AFT-MAX-IN-M")),
                    "draft_for_max_m": clean_value(row.get("TWINSHIP-VESSEL-DRAFT-FOR-MAX-IN-M")),
                    "draft_mid_port_max_m": clean_value(row.get("TWINSHIP-VESSEL-DRAFT-MID-PORT-MAX-IN-M")),
                    "draft_mid_stbd_max_m": clean_value(row.get("TWINSHIP-VESSEL-DRAFT-MID-STBD-MAX-IN-M")),
                    "depth_of_water_max_m": clean_value(row.get("TWINSHIP-VESSEL-DEPTH-OF-WATER-MAX-IN-M")),
                }
                break

    # Extract main engines (ID format: OPERATOR-TYPE-NUMBER, e.g., "GRI-ME-1")
    if "Main_Engine" in sheets:
        df = sheets["Main_Engine"]
        for _, row in df.iterrows():
            engine_id = row.get("TWINSHIP-MAIN-ENGINE-ID")
            if entity_belongs_to_operator(engine_id, operator_prefix, position=0):
                types = parse_types(row.get("TWINSHIP-MAIN-ENGINE-TYPE"))

                # Fuels - default to HFO, MDO, MGO if fuel mode column exists
                fuels = ["HFO", "MDO", "MGO"]

                result["main_engines"].append(
                    {
                        "id": clean_value(engine_id),
                        "name": clean_value(row.get("TWINSHIP-MAIN-ENGINE-NAME")),
                        "types": types,
                        "shaft_torque_max_knm": clean_value(row.get("TWINSHIP-SHAFT-TORQUE-MAX-IN-kNm")),
                        "shaft_speed_max_rpm": clean_value(row.get("TWINSHIP-SHAFT-SPEED-MAX-IN-REV-PER_MIN")),
                        "shaft_power_max_kw": clean_value(row.get("TWINSHIP-SHAFT-POWER-MAX-IN-kW")),
                        "flowrate_max_kg_per_hr": clean_value(row.get("TWINSHIP-FLOWRATE-MAX-IN-KG_PER_HR")),
                        "fuel_flow_temp_max_c": clean_value(row.get("TWINSHIP-FUEL-FLOW-TEMPERATURE-MAX-IN-°C")),
                        "inlet_air_pressure_max_hpa": clean_value(
                            row.get("TWINSHIP-INLET-AIR-PRESSURE-MAX-IN-hPa")
                        ),
                        "inlet_air_temp_max_c": clean_value(row.get("TWINSHIP-INLET-AIR-TEMPERATURE-MAX-IN-°C")),
                        "me_cooling_water_temp_max_c": clean_value(
                            row.get("TWINSHIP-ME-COOLING-WATER-TEMPERATURE-MAX-IN-°C")
                        ),
                        "lt_cooling_seawater_1_temp_max_c": clean_value(
                            row.get("TWINSHIP-LT-COOLING-SEAWATER-1-TEMPERATURE-MAX-IN-°C")
                        ),
                        "lt_cooling_seawater_2_temp_max_c": clean_value(
                            row.get("TWINSHIP-LT-COOLING-SEAWATER-2-TEMPERATURE-MAX-IN-°C")
                        ),
                        "scavenger_air_rec_temp_max_c": clean_value(
                            row.get("TWINSHIP-SCAVENGER-AIR-REC-TEMPERATURE-MAX-IN-°C")
                        ),
                        "common_do_mode": clean_value(row.get("TWINSHIP-COMMON-DO-MODE")),
                        "common_fuel_mode": clean_value(row.get("TWINSHIP-COMMOM-FUEL-MODE")),
                        "fuel_consumption_total_mt": clean_value(row.get("TWINSHIP-FUEL-CONSUMPTION-TOTAL-IN-MT")),
                        "power_propulsion_total_kw": clean_value(row.get("TWINSHIP-POWER-PROPULSION-TOTAL-IN-kW")),
                        "fuels": fuels,
                        "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
                        "gearbox_id": clean_value(row.get("TWINSHIP-GEARBOX-ID")),
                    }
                )

    # Extract auxiliary engines (ID format: OPERATOR-TYPE-NUMBER, e.g., "GRI-AU-1")
    if "Auxiliary_Engine" in sheets:
        df = sheets["Auxiliary_Engine"]
        for _, row in df.iterrows():
            engine_id = row.get("TWINSHIP-AUXILIARY-ENGINE-ID")
            if entity_belongs_to_operator(engine_id, operator_prefix, position=0):
                types = parse_types(row.get("TWINSHIP-AUXILIARY-ENGINE-TYPE"))

                # Fuels - default to HFO, MDO, MGO
                fuels = ["HFO", "MDO", "MGO"]

                result["auxiliary_engines"].append(
                    {
                        "id": clean_value(engine_id),
                        "name": clean_value(row.get("TWINSHIP-AUXILIARY-ENGINE-NAME")),
                        "types": types,
                        "diesel_engine_power_max_kw": clean_value(
                            row.get("TWINSHIP-DIESEL-ENGINE-POWER-MAX-IN-KW")
                        ),
                        "diesel_engine_speed_rpm": clean_value(
                            row.get("TWINSHIP-DIESEL-ENGINE-SPEED-IN-REV-PER-MIN")
                        ),
                        "generator_power_max_kw": clean_value(row.get("TWINSHIP-GENERATOR-POWER-MAX-IN-KW")),
                        "generator_speed_rpm": clean_value(row.get("TWINSHIP-GENERATOR-SPEED-IN-REV-PER-MIN")),
                        "auxiliary_do_mode": clean_value(row.get("TWINSHIP-AUXILIARY-DO-MODE")),
                        "fuel_rate_mass_net_kg_per_hr": clean_value(
                            row.get("TWINSHIP-AUXILIARY-FUEL-RATE-MASS-NET-KG-PER-HOUR")
                        ),
                        "fuels": fuels,
                        "pms_id": clean_value(row.get("TWINSHIP-PMS-ID")),
                        "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
                    }
                )

    # Extract gearboxes (ID format: TYPE-OPERATOR-NUMBER, e.g., "DD-GRI-1")
    if "Gearbox" in sheets:
        df = sheets["Gearbox"]
        for _, row in df.iterrows():
            gearbox_id = row.get("TWINSHIP-GEARBOX-ID")
            # Gearbox IDs have operator in position 1 (e.g., "DD-GRI-1")
            if entity_belongs_to_operator(gearbox_id, operator_prefix, position=1):
                types = parse_types(row.get("TWINSHIP-GEARBOX-TYPE"))

                result["gearboxes"].append(
                    {
                        "id": clean_value(gearbox_id),
                        "name": clean_value(row.get("TWINSHIP-GEARBOX-NAME")),
                        "types": types,
                        "efficiency": clean_value(row.get("TWINSHIP-GEARBOX-EFFICIENCY")),
                        "ratio": clean_value(row.get("TWINSHIP-GEARBOX-RATIO")),
                        "shaft_generator": clean_value(row.get("TWINSHIP-GEARBOX-SHAFT-GENERATOR")),
                        "engine_id": clean_value(row.get("TWINSHIP-ENGINE-ID")),
                        "propeller_id": clean_value(row.get("TWINSHIP-PROPELLER-ID")),
                        "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
                    }
                )

    # Extract propellers (ID format: TYPE-OPERATOR-NUMBER, e.g., "CPP-GRI-1")
    if "Propeller" in sheets:
        df = sheets["Propeller"]
        for _, row in df.iterrows():
            propeller_id = row.get("TWINSHIP-PROPELLER-ID")
            # Propeller IDs have operator in position 1 (e.g., "CPP-GRI-1")
            if entity_belongs_to_operator(propeller_id, operator_prefix, position=1):
                types = parse_types(row.get("TWINSHIP-PROPELLER-TYPE"))

                result["propellers"].append(
                    {
                        "id": clean_value(propeller_id),
                        "name": clean_value(row.get("TWINSHIP-PROPEELER-NAME")),  # Note: typo in spreadsheet
                        "types": types,
                        "efficiency": clean_value(row.get("TWINSHIP-PROPELLER-EFFICIENCY")),
                        "pitch_max_percentage": clean_value(row.get("TWINSHIP-PROPELLER-PITCH-MAX-IN-PERCENTAGE")),
                        "diameter_mm": clean_value(row.get("TWINSHIP-PROPELLER-DIAMETER-MM")),
                        "blades": clean_value(row.get("TWINSHIP-PROPELLER-BLADES")),
                        "pitch_diameter_ratio": clean_value(row.get("TWINSHIP-PROPELLER-PITCH-DIAMETER -RATIO")),
                        "skew_angle_degree": clean_value(row.get("TWINSHIP-PROPELLER-SKEW-ANGLE-DEGREE")),
                        "expanded_area_ratio_percentage": clean_value(
                            row.get("TWINSHIP-PROPELLER-EXPANDED-AREA-RATIO-PERCENTAGE")
                        ),
                        "hub_ratio": clean_value(row.get("TWINSHIP-PROPELLER-HUB-RATIO")),
                        "rudder_angle_degree": clean_value(row.get("TWINSHIP-RUDDER-ANGLE-DEGREE")),
                        "gearbox_id": clean_value(row.get("TWINSHIP-GEARBOX-ID")),
                        "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
                    }
                )

    # Extract PMS (ID format: PMS-OPERATOR-NUMBER, e.g., "PMS-GRI-1")
    if "PMS" in sheets:
        df = sheets["PMS"]
        for _, row in df.iterrows():
            pms_id = row.get("TWINSHIP-PMS-ID")
            # PMS IDs have operator in position 1 (e.g., "PMS-GRI-1")
            if entity_belongs_to_operator(pms_id, operator_prefix, position=1):
                types = parse_types(row.get("TWINSHIP-PMS-TYPE"))

                result["pms"].append(
                    {
                        "id": clean_value(pms_id),
                        "name": clean_value(row.get("TWINSHIP-PMS-NAME")),
                        "types": types,
                        "auxiliary_engine_id": clean_value(row.get("TWINSHIP-AUXILIARY-ENGINE-ID")),
                        "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
                    }
                )

    # Extract from OTHER Systems (emergency generators, thrusters, shaft generators, boilers)
    if "Other" in sheets:
        df = sheets["Other"]
        for _, row in df.iterrows():
            component_id = row.get("TWINSHIP-COMPONENT-ID")
            if not component_id or pd.isna(component_id):
                continue

            # OTHER Systems IDs have operator in position 1 (e.g., "EG-GRI-1", "TH-GRI-1")
            if not entity_belongs_to_operator(component_id, operator_prefix, position=1):
                continue

            types = parse_types(row.get("TWINSHIP-COMPONENT-TYPE"))
            component_name = clean_value(row.get("TWINSHIP-COMPONENT-NAME"))
            power_max_kw = clean_value(row.get("TWINSHIP-COMPONENT-POWER-MAX-IN-kW"))
            speed_max_rpm = clean_value(row.get("TWINSHIP-COMPONENT-SPEED-MAX-IN-REV-PER-MIN"))

            # Categorize by ID prefix
            id_prefix = str(component_id).split("-")[0].upper()

            if id_prefix == "EG":
                # Emergency Generator
                result["emergency_generators"].append(
                    {
                        "id": clean_value(component_id),
                        "name": component_name,
                        "types": types,
                        "power_max_kw": power_max_kw,
                        "speed_max_rpm": speed_max_rpm,
                        "do_mode": clean_value(row.get("TWINSHIP-COMPONENT-EMERG-DO-MODE")),
                    }
                )
            elif id_prefix == "TH":
                # Thruster (bow or stern)
                is_bow = "BOW" in str(component_name).upper()
                result["thrusters"].append(
                    {
                        "id": clean_value(component_id),
                        "name": component_name,
                        "types": types,
                        "power_max_kw": power_max_kw,
                        "speed_max_rpm": speed_max_rpm,
                        "is_bow": is_bow,
                    }
                )
            elif id_prefix == "SG":
                # Shaft Generator
                result["shaft_generators"].append(
                    {
                        "id": clean_value(component_id),
                        "name": component_name,
                        "types": types,
                        "power_max_kw": power_max_kw,
                        "speed_max_rpm": speed_max_rpm,
                    }
                )
            elif id_prefix in ("BLR", "CMP"):
                # Boiler
                result["boilers"].append(
                    {
                        "id": clean_value(component_id),
                        "name": component_name,
                        "types": types,
                        "power_max_kw": power_max_kw,
                        "speed_max_rpm": speed_max_rpm,
                    }
                )

    return result


@asset(
    group_name="extraction",
    partitions_def=operator_partitions_def,
    description="Extract vessel JSON for a specific operator from spreadsheet",
)
def extracted_vessel_json(
    context: AssetExecutionContext,
    spreadsheet_data: dict,
) -> dict:
    """Extract vessel data for the current operator partition."""
    namespace = context.partition_key
    sheets = spreadsheet_data["sheets"]
    operators = spreadsheet_data["operators"]

    if namespace not in operators:
        context.log.error(f"Unknown operator namespace: {namespace}")
        return {}

    operator_info = operators[namespace]
    prefix = operator_info["prefix"]
    name = operator_info["name"]

    data = extract_vessel_for_operator(sheets, prefix, namespace, name)

    vessel_id = data.get("vessel", {}).get("id", "unknown")
    context.log.info(
        f"Extracted {namespace}: vessel={vessel_id}, "
        f"main_engines={len(data['main_engines'])}, "
        f"aux_engines={len(data['auxiliary_engines'])}, "
        f"propellers={len(data['propellers'])}, "
        f"gearboxes={len(data['gearboxes'])}, "
        f"pms={len(data['pms'])}, "
        f"emergency_generators={len(data['emergency_generators'])}, "
        f"thrusters={len(data['thrusters'])}, "
        f"shaft_generators={len(data['shaft_generators'])}, "
        f"boilers={len(data['boilers'])}"
    )

    context.add_output_metadata({
        "vessel_id": MetadataValue.text(vessel_id),
        "main_engine_count": MetadataValue.int(len(data["main_engines"])),
        "auxiliary_engine_count": MetadataValue.int(len(data["auxiliary_engines"])),
        "other_components": MetadataValue.int(
            len(data["pms"]) + len(data["emergency_generators"]) +
            len(data["thrusters"]) + len(data["shaft_generators"]) + len(data["boilers"])
        ),
    })

    return data


# =============================================================================
# Step 3: Harmonise to RDF (Partitioned)
# =============================================================================


@asset(
    group_name="harmonisation",
    partitions_def=operator_partitions_def,
    description="Harmonise vessel JSON to RDF graph for a specific operator",
)
def vessel_rdf_graph(
    context: AssetExecutionContext,
    extracted_vessel_json: dict,
) -> Graph:
    """Convert extracted vessel data to RDF triples."""
    namespace = context.partition_key

    if not extracted_vessel_json:
        context.log.warning(f"No data for {namespace}, returning empty graph")
        return Graph()

    g = harmonise_vessel_data(extracted_vessel_json)

    vessel_id = extracted_vessel_json.get("vessel", {}).get("id", "unknown")
    context.log.info(f"Generated {len(g)} triples for {namespace} ({vessel_id})")

    context.add_output_metadata({
        "triple_count": MetadataValue.int(len(g)),
    })

    return g


# =============================================================================
# Step 4: Validate and Write TTL (Partitioned)
# =============================================================================


class ValidationConfig(Config):
    """Configuration for SHACL validation."""

    shapes_path: str = "shacl/twinship_shapes.ttl"
    output_dir: str = "output"


@asset(
    group_name="validation",
    partitions_def=operator_partitions_def,
    description="Validate RDF graph and write TTL file for a specific operator",
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

    # Validate with SHACL (warning only - doesn't block pipeline)
    if shapes_path.exists():
        conforms, report = shacl_validator.validate(vessel_rdf_graph, shapes_path)
        if conforms:
            context.log.info(f"SHACL validation passed for {namespace}")
        else:
            context.log.warning(f"SHACL validation issues for {namespace}:\n{report}")
    else:
        context.log.warning(f"SHACL shapes not found: {shapes_path}")

    # Serialize to TTL
    output_path = output_dir / f"{namespace}.ttl"
    vessel_rdf_graph.serialize(destination=str(output_path), format="turtle")
    context.log.info(f"Wrote {len(vessel_rdf_graph)} triples to {output_path}")

    context.add_output_metadata({
        "output_path": MetadataValue.path(str(output_path)),
        "triple_count": MetadataValue.int(len(vessel_rdf_graph)),
    })

    return str(output_path)


# =============================================================================
# Step 5: Combine All TTL Files (Non-partitioned)
# =============================================================================


class CombinedGraphConfig(Config):
    """Configuration for combined graph."""

    output_dir: str = "output"
    combined_output: str = "output/all_vessels.ttl"


@asset(
    group_name="output",
    deps=[validated_vessel_ttl],
    description="Combine all validated RDF graphs into one",
)
def combined_vessel_graph(
    context: AssetExecutionContext,
    config: CombinedGraphConfig,
) -> Graph:
    """Combine all operator TTL files into a single graph.

    This asset depends on validated_vessel_ttl but reads the TTL files
    from disk rather than taking them as inputs (since they are partitioned).
    """
    g = Graph()
    output_dir = Path(config.output_dir)

    # Read all TTL files from output directory
    ttl_files = list(output_dir.glob("*.ttl"))
    combined_output = Path(config.combined_output)

    for ttl_file in ttl_files:
        if ttl_file == combined_output:
            continue  # Skip the combined output file itself
        try:
            operator_graph = Graph()
            operator_graph.parse(ttl_file, format="turtle")
            g += operator_graph
            context.log.info(f"Added {len(operator_graph)} triples from {ttl_file.name}")
        except Exception as e:
            context.log.warning(f"Could not parse {ttl_file}: {e}")

    if len(g) == 0:
        context.log.warning("No triples to combine")

    g = bind_namespaces(g)

    # Write combined output
    combined_output.parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=str(combined_output), format="turtle")

    context.log.info(f"Combined graph: {len(g)} triples written to {combined_output}")

    context.add_output_metadata({
        "output_path": MetadataValue.path(str(combined_output)),
        "triple_count": MetadataValue.int(len(g)),
        "source_files": MetadataValue.int(len(ttl_files) - 1),  # Exclude combined file
    })

    return g


# =============================================================================
# Step 6: Upload to GraphDB (Non-partitioned) - PLACEHOLDER
# =============================================================================


@asset(
    group_name="output",
    description="Upload combined graph to GraphDB (not yet implemented)",
)
def graphdb_upload(
    context: AssetExecutionContext,
    combined_vessel_graph: Graph,
) -> str:
    """Placeholder for GraphDB upload - to be implemented later."""
    context.log.info(
        f"GraphDB upload not yet implemented. "
        f"Combined graph has {len(combined_vessel_graph)} triples."
    )
    return ""
