"""TwinShip spreadsheet extraction utilities.

This module handles parsing the TwinShip Excel spreadsheet and extracting
vessel data for each operator.
"""

import pandas as pd

# =============================================================================
# Operator Configuration
# =============================================================================

# Known operator mappings (prefix -> namespace, display name)
# Add new operators here for better names, or they'll default to lowercase prefix
KNOWN_OPERATORS = {
    "GRI": ("grimaldi", "Grimaldi"),
    "STL": ("stena-scandinavica", "Stena Line"),
    "STT": ("stena-tanker", "Stena Tanker"),
}

# Mapping of internal sheet names to actual Excel sheet names
SHEET_MAPPING = {
    "Vessel": "VESSEL System",
    "Main_Engine": "MAIN ENGINE System",
    "Auxiliary_Engine": "AUXILIARY GENSET System",
    "Propeller": "PROPELLER System",
    "Gearbox": "GEARBOX System",
    "PMS": "PMS System",
    "Other": "OTHER Systems",
}


# =============================================================================
# Helper Functions
# =============================================================================


def clean_value(val):
    """Clean a value for JSON serialization."""
    if pd.isna(val):
        return None
    if isinstance(val, float) and val != val:  # NaN check
        return None
    return val


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
    cleaned = str(type_string).replace("[", "").replace("]", "")
    for part in cleaned.split(","):
        part = part.strip()
        if part.startswith("tws:"):
            types.append(part[4:].strip())
        elif part:
            types.append(part.strip())
    return types


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
    """Check if an entity ID belongs to a specific operator."""
    return extract_operator_prefix(entity_id, position) == operator_prefix


# =============================================================================
# Spreadsheet Loading
# =============================================================================


def load_spreadsheet_sheets(spreadsheet_path: str) -> dict[str, pd.DataFrame]:
    """Load all relevant sheets from the TwinShip spreadsheet.

    Args:
        spreadsheet_path: Path to the Excel file.

    Returns:
        Dict mapping internal sheet names to DataFrames.
    """
    sheets = {}

    for internal_name, actual_sheet_name in SHEET_MAPPING.items():
        try:
            df = pd.read_excel(
                spreadsheet_path,
                sheet_name=actual_sheet_name,
                header=1,  # Row with "TWINSHIP-*" column names
                skiprows=[2],  # Skip the data type row
            )
            # Handle duplicate column names
            cols = df.columns.tolist()
            seen: dict[str, int] = {}
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
        except Exception:
            pass  # Sheet not found or error reading

    return sheets


def discover_vessels_from_sheets(sheets: dict[str, pd.DataFrame]) -> dict[str, dict]:
    """Discover all vessels from entity IDs in the spreadsheet.

    Only uses Vessel and Main_Engine IDs for discovery since they have
    consistent format (prefix-type-number like "GRI-RR-1", "STL-ME-1").

    Returns a dict mapping namespace to {prefix, name}.
    """
    prefixes: set[str] = set()

    id_columns = {
        "Vessel": "TWINSHIP-VESSEL-ID",
        "Main_Engine": "TWINSHIP-MAIN-ENGINE-ID",
    }

    # Look through specified sheets and columns to find all unique operator prefixes
    for sheet_name, id_col in id_columns.items():
        if sheet_name in sheets and id_col in sheets[sheet_name].columns:
            for entity_id in sheets[sheet_name][id_col]:
                prefix = extract_operator_prefix(entity_id)
                if prefix:
                    prefixes.add(prefix)

    # Convert prefixes to namespaces and display names
    return {
        prefix_to_namespace(prefix): {"prefix": prefix, "name": prefix_to_name(prefix)}
        for prefix in sorted(prefixes)
    }


# =============================================================================
# Vessel Data Extraction
# =============================================================================


def extract_vessel_for_operator(
    sheets: dict[str, pd.DataFrame],
    operator_prefix: str,
    namespace: str,
    operator_name: str,
) -> dict:
    """Extract vessel data for a specific operator.

    Args:
        sheets: Dict of sheet name to DataFrame.
        operator_prefix: The operator prefix (e.g., "GRI").
        namespace: The namespace for URIs (e.g., "grimaldi").
        operator_name: Display name (e.g., "Grimaldi").

    Returns:
        Dict with vessel data ready for harmonisation.
    """
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

    _extract_vessel(sheets, operator_prefix, result)
    _extract_main_engines(sheets, operator_prefix, result)
    _extract_auxiliary_engines(sheets, operator_prefix, result)
    _extract_gearboxes(sheets, operator_prefix, result)
    _extract_propellers(sheets, operator_prefix, result)
    _extract_pms(sheets, operator_prefix, result)
    _extract_other_systems(sheets, operator_prefix, result)

    return result


def _extract_vessel(sheets: dict, operator_prefix: str, result: dict) -> None:
    """Extract vessel data."""
    if "Vessel" not in sheets:
        return

    for _, row in sheets["Vessel"].iterrows():
        vessel_id = row.get("TWINSHIP-VESSEL-ID")
        if entity_belongs_to_operator(vessel_id, operator_prefix, position=0):
            types = parse_types(row.get("TWINSHIP-VESSEL-TYPE"))
            result["vessel"] = {
                "id": clean_value(vessel_id),
                "label": clean_value(row.get("TWINSHIP-VESSEL-NAME")),
                "type": types[0] if types else None,
                "displacement_max_mt": clean_value(row.get("TWINSHIP-DISPLACEMENT-MAX-IN-MT")),
                "draft_aft_max_m": clean_value(row.get("TWINSHIP-VESSEL-DRAFT-AFT-MAX-IN-M")),
                "draft_for_max_m": clean_value(row.get("TWINSHIP-VESSEL-DRAFT-FOR-MAX-IN-M")),
                "draft_mid_port_max_m": clean_value(row.get("TWINSHIP-VESSEL-DRAFT-MID-PORT-MAX-IN-M")),
                "draft_mid_stbd_max_m": clean_value(row.get("TWINSHIP-VESSEL-DRAFT-MID-STBD-MAX-IN-M")),
                "depth_of_water_max_m": clean_value(row.get("TWINSHIP-VESSEL-DEPTH-OF-WATER-MAX-IN-M")),
            }
            break


def _extract_main_engines(sheets: dict, operator_prefix: str, result: dict) -> None:
    """Extract main engine data."""
    if "Main_Engine" not in sheets:
        return

    for _, row in sheets["Main_Engine"].iterrows():
        engine_id = row.get("TWINSHIP-MAIN-ENGINE-ID")
        if entity_belongs_to_operator(engine_id, operator_prefix, position=0):
            types = parse_types(row.get("TWINSHIP-MAIN-ENGINE-TYPE"))
            result["main_engines"].append({
                "id": clean_value(engine_id),
                "name": clean_value(row.get("TWINSHIP-MAIN-ENGINE-NAME")),
                "types": types,
                "shaft_torque_max_knm": clean_value(row.get("TWINSHIP-SHAFT-TORQUE-MAX-IN-kNm")),
                "shaft_speed_max_rpm": clean_value(row.get("TWINSHIP-SHAFT-SPEED-MAX-IN-REV-PER_MIN")),
                "shaft_power_max_kw": clean_value(row.get("TWINSHIP-SHAFT-POWER-MAX-IN-kW")),
                "flowrate_max_kg_per_hr": clean_value(row.get("TWINSHIP-FLOWRATE-MAX-IN-KG_PER_HR")),
                "fuel_flow_temp_max_c": clean_value(row.get("TWINSHIP-FUEL-FLOW-TEMPERATURE-MAX-IN-°C")),
                "inlet_air_pressure_max_hpa": clean_value(row.get("TWINSHIP-INLET-AIR-PRESSURE-MAX-IN-hPa")),
                "inlet_air_temp_max_c": clean_value(row.get("TWINSHIP-INLET-AIR-TEMPERATURE-MAX-IN-°C")),
                "me_cooling_water_temp_max_c": clean_value(row.get("TWINSHIP-ME-COOLING-WATER-TEMPERATURE-MAX-IN-°C")),
                "lt_cooling_seawater_1_temp_max_c": clean_value(row.get("TWINSHIP-LT-COOLING-SEAWATER-1-TEMPERATURE-MAX-IN-°C")),
                "lt_cooling_seawater_2_temp_max_c": clean_value(row.get("TWINSHIP-LT-COOLING-SEAWATER-2-TEMPERATURE-MAX-IN-°C")),
                "scavenger_air_rec_temp_max_c": clean_value(row.get("TWINSHIP-SCAVENGER-AIR-REC-TEMPERATURE-MAX-IN-°C")),
                "common_do_mode": clean_value(row.get("TWINSHIP-COMMON-DO-MODE")),
                "common_fuel_mode": clean_value(row.get("TWINSHIP-COMMOM-FUEL-MODE")),
                "fuel_consumption_total_mt": clean_value(row.get("TWINSHIP-FUEL-CONSUMPTION-TOTAL-IN-MT")),
                "power_propulsion_total_kw": clean_value(row.get("TWINSHIP-POWER-PROPULSION-TOTAL-IN-kW")),
                "fuels": ["HFO", "MDO", "MGO"],
                "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
                "gearbox_id": clean_value(row.get("TWINSHIP-GEARBOX-ID")),
            })


def _extract_auxiliary_engines(sheets: dict, operator_prefix: str, result: dict) -> None:
    """Extract auxiliary engine data."""
    if "Auxiliary_Engine" not in sheets:
        return

    for _, row in sheets["Auxiliary_Engine"].iterrows():
        engine_id = row.get("TWINSHIP-AUXILIARY-ENGINE-ID")
        if entity_belongs_to_operator(engine_id, operator_prefix, position=0):
            types = parse_types(row.get("TWINSHIP-AUXILIARY-ENGINE-TYPE"))
            result["auxiliary_engines"].append({
                "id": clean_value(engine_id),
                "name": clean_value(row.get("TWINSHIP-AUXILIARY-ENGINE-NAME")),
                "types": types,
                "diesel_engine_power_max_kw": clean_value(row.get("TWINSHIP-DIESEL-ENGINE-POWER-MAX-IN-KW")),
                "diesel_engine_speed_rpm": clean_value(row.get("TWINSHIP-DIESEL-ENGINE-SPEED-IN-REV-PER-MIN")),
                "generator_power_max_kw": clean_value(row.get("TWINSHIP-GENERATOR-POWER-MAX-IN-KW")),
                "generator_speed_rpm": clean_value(row.get("TWINSHIP-GENERATOR-SPEED-IN-REV-PER-MIN")),
                "auxiliary_do_mode": clean_value(row.get("TWINSHIP-AUXILIARY-DO-MODE")),
                "fuel_rate_mass_net_kg_per_hr": clean_value(row.get("TWINSHIP-AUXILIARY-FUEL-RATE-MASS-NET-KG-PER-HOUR")),
                "fuels": ["HFO", "MDO", "MGO"],
                "pms_id": clean_value(row.get("TWINSHIP-PMS-ID")),
                "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
            })


def _extract_gearboxes(sheets: dict, operator_prefix: str, result: dict) -> None:
    """Extract gearbox data."""
    if "Gearbox" not in sheets:
        return

    for _, row in sheets["Gearbox"].iterrows():
        gearbox_id = row.get("TWINSHIP-GEARBOX-ID")
        # Gearbox IDs have operator in position 1 (e.g., "DD-GRI-1")
        if entity_belongs_to_operator(gearbox_id, operator_prefix, position=1):
            types = parse_types(row.get("TWINSHIP-GEARBOX-TYPE"))
            result["gearboxes"].append({
                "id": clean_value(gearbox_id),
                "name": clean_value(row.get("TWINSHIP-GEARBOX-NAME")),
                "types": types,
                "efficiency": clean_value(row.get("TWINSHIP-GEARBOX-EFFICIENCY")),
                "ratio": clean_value(row.get("TWINSHIP-GEARBOX-RATIO")),
                "shaft_generator": clean_value(row.get("TWINSHIP-GEARBOX-SHAFT-GENERATOR")),
                "engine_id": clean_value(row.get("TWINSHIP-ENGINE-ID")),
                "propeller_id": clean_value(row.get("TWINSHIP-PROPELLER-ID")),
                "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
            })


def _extract_propellers(sheets: dict, operator_prefix: str, result: dict) -> None:
    """Extract propeller data."""
    if "Propeller" not in sheets:
        return

    for _, row in sheets["Propeller"].iterrows():
        propeller_id = row.get("TWINSHIP-PROPELLER-ID")
        # Propeller IDs have operator in position 1 (e.g., "CPP-GRI-1")
        if entity_belongs_to_operator(propeller_id, operator_prefix, position=1):
            types = parse_types(row.get("TWINSHIP-PROPELLER-TYPE"))
            result["propellers"].append({
                "id": clean_value(propeller_id),
                "name": clean_value(row.get("TWINSHIP-PROPEELER-NAME")),  # Note: typo in spreadsheet
                "types": types,
                "efficiency": clean_value(row.get("TWINSHIP-PROPELLER-EFFICIENCY")),
                "pitch_max_percentage": clean_value(row.get("TWINSHIP-PROPELLER-PITCH-MAX-IN-PERCENTAGE")),
                "diameter_mm": clean_value(row.get("TWINSHIP-PROPELLER-DIAMETER-MM")),
                "blades": clean_value(row.get("TWINSHIP-PROPELLER-BLADES")),
                "pitch_diameter_ratio": clean_value(row.get("TWINSHIP-PROPELLER-PITCH-DIAMETER -RATIO")),
                "skew_angle_degree": clean_value(row.get("TWINSHIP-PROPELLER-SKEW-ANGLE-DEGREE")),
                "expanded_area_ratio_percentage": clean_value(row.get("TWINSHIP-PROPELLER-EXPANDED-AREA-RATIO-PERCENTAGE")),
                "hub_ratio": clean_value(row.get("TWINSHIP-PROPELLER-HUB-RATIO")),
                "rudder_angle_degree": clean_value(row.get("TWINSHIP-RUDDER-ANGLE-DEGREE")),
                "gearbox_id": clean_value(row.get("TWINSHIP-GEARBOX-ID")),
                "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
            })


def _extract_pms(sheets: dict, operator_prefix: str, result: dict) -> None:
    """Extract PMS data."""
    if "PMS" not in sheets:
        return

    for _, row in sheets["PMS"].iterrows():
        pms_id = row.get("TWINSHIP-PMS-ID")
        # PMS IDs have operator in position 1 (e.g., "PMS-GRI-1")
        if entity_belongs_to_operator(pms_id, operator_prefix, position=1):
            types = parse_types(row.get("TWINSHIP-PMS-TYPE"))
            result["pms"].append({
                "id": clean_value(pms_id),
                "name": clean_value(row.get("TWINSHIP-PMS-NAME")),
                "types": types,
                "auxiliary_engine_id": clean_value(row.get("TWINSHIP-AUXILIARY-ENGINE-ID")),
                "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
            })


def _extract_other_systems(sheets: dict, operator_prefix: str, result: dict) -> None:
    """Extract emergency generators, thrusters, shaft generators, and boilers."""
    if "Other" not in sheets:
        return

    for _, row in sheets["Other"].iterrows():
        component_id = row.get("TWINSHIP-COMPONENT-ID")
        if not component_id or pd.isna(component_id):
            continue

        # OTHER Systems IDs have operator in position 1 (e.g., "EG-GRI-1")
        if not entity_belongs_to_operator(component_id, operator_prefix, position=1):
            continue

        types = parse_types(row.get("TWINSHIP-COMPONENT-TYPE"))
        component_name = clean_value(row.get("TWINSHIP-COMPONENT-NAME"))
        power_max_kw = clean_value(row.get("TWINSHIP-COMPONENT-POWER-MAX-IN-kW"))
        speed_max_rpm = clean_value(row.get("TWINSHIP-COMPONENT-SPEED-MAX-IN-REV-PER-MIN"))

        id_prefix = str(component_id).split("-")[0].upper()

        if id_prefix == "EG":
            result["emergency_generators"].append({
                "id": clean_value(component_id),
                "name": component_name,
                "types": types,
                "power_max_kw": power_max_kw,
                "speed_max_rpm": speed_max_rpm,
                "do_mode": clean_value(row.get("TWINSHIP-COMPONENT-EMERG-DO-MODE")),
            })
        elif id_prefix == "TH":
            is_bow = "BOW" in str(component_name).upper()
            result["thrusters"].append({
                "id": clean_value(component_id),
                "name": component_name,
                "types": types,
                "power_max_kw": power_max_kw,
                "speed_max_rpm": speed_max_rpm,
                "is_bow": is_bow,
            })
        elif id_prefix == "SG":
            result["shaft_generators"].append({
                "id": clean_value(component_id),
                "name": component_name,
                "types": types,
                "power_max_kw": power_max_kw,
                "speed_max_rpm": speed_max_rpm,
            })
        elif id_prefix in ("BLR", "CMP"):
            result["boilers"].append({
                "id": clean_value(component_id),
                "name": component_name,
                "types": types,
                "power_max_kw": power_max_kw,
                "speed_max_rpm": speed_max_rpm,
            })
