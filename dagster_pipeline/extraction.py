"""TwinShip spreadsheet extraction utilities.

This module handles parsing the TwinShip Excel spreadsheet and extracting
vessel data for each operator (e.g., GRI (grimaldi), STL (stena line), STT (stena tanker)). 

Usage:
    sheets = load_spreadsheet_sheets("path/to/spreadsheet.xlsx")
    vessels = discover_vessels_from_sheets(sheets)

    for namespace, info in vessels.items():
        data = extract_vessel_for_operator(sheets, info["prefix"], namespace)
        # data is now ready for harmonisation to RDF
"""

from typing import Callable

import pandas as pd

from dagster_pipeline.utils import (
    clean_value,
    extract_operator_prefix,
    parse_bracket_list,
    parse_types,
    prefix_to_namespace,
)

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
# Spreadsheet Loading
# =============================================================================


def load_spreadsheet_sheets(spreadsheet_path: str) -> dict[str, pd.DataFrame]:
    """Load all sheets from the TwinShip spreadsheet.

    The spreadsheet structure:
    - Row 0: Human-readable headers (skipped)
    - Row 1: Machine-readable column names like "TWINSHIP-VESSEL-ID"
    - Row 2: Data type annotations (skipped)
    - Row 3+: Data rows
    """
    sheets = {}
    for internal_name, actual_name in SHEET_MAPPING.items():
        try:
            df = pd.read_excel(
                spreadsheet_path, sheet_name=actual_name, header=1, skiprows=[2]
            )
            # Handle duplicate columns by appending "_rel" suffix
            seen: dict[str, int] = {}
            new_cols = []
            for col in df.columns:
                if col in seen:
                    seen[col] += 1
                    new_cols.append(f"{col}_rel")
                else:
                    seen[col] = 0
                    new_cols.append(col)
            df.columns = new_cols
            sheets[internal_name] = df
        except Exception:
            pass
    return sheets


def discover_vessels_from_sheets(sheets: dict[str, pd.DataFrame]) -> dict[str, dict]:
    """Discover all vessels from entity IDs in the spreadsheet.

    Returns dict mapping namespace to {prefix, name}.
    """
    prefixes: set[str] = set()
    id_columns = {
        "Vessel": "TWINSHIP-VESSEL-ID",
        "Main_Engine": "TWINSHIP-MAIN-ENGINE-ID",
    }

    for sheet_name, id_col in id_columns.items():
        if sheet_name in sheets and id_col in sheets[sheet_name].columns:
            for entity_id in sheets[sheet_name][id_col]:
                if prefix := extract_operator_prefix(entity_id):
                    prefixes.add(prefix)

    return {
        prefix_to_namespace(p): {"prefix": p}
        for p in sorted(prefixes)
    }


# =============================================================================
# Generic Row Extraction
# =============================================================================


def extract_rows(
    sheets: dict[str, pd.DataFrame],
    sheet_name: str,
    id_column: str,
    operator_prefix: str,
    field_map: dict[str, str],
    type_column: str | None = None,
    extra: Callable[[pd.Series], dict] | None = None,
) -> list[dict]:
    """Extract rows from a sheet, filtering by operator and mapping columns to fields.

    Args:
        sheets: Dict of sheet name to DataFrame
        sheet_name: Which sheet to extract from
        id_column: Column containing the entity ID (used for operator filtering)
        operator_prefix: Only include rows belonging to this operator
        field_map: Mapping of output field names to spreadsheet column names
        type_column: If set, parse this column as types and add to result
        extra: Optional function to add additional computed fields from row
    """
    if sheet_name not in sheets:
        return []

    results = []
    for _, row in sheets[sheet_name].iterrows():
        entity_id = row.get(id_column)
        if extract_operator_prefix(entity_id) != operator_prefix:
            continue

        item = {field: clean_value(row.get(col)) for field, col in field_map.items()}

        if type_column:
            item["types"] = parse_types(row.get(type_column))

        if extra:
            item.update(extra(row))

        results.append(item)

    return results


# =============================================================================
# Vessel Data Extraction
# =============================================================================


def extract_vessel_for_operator(
    sheets: dict[str, pd.DataFrame],
    operator_prefix: str,
    namespace: str,
) -> dict:
    """Extract all vessel data for a specific operator.

    This is the main entry point. Returns a dict ready for harmonisation.
    """
    other = extract_other_systems(sheets, operator_prefix)

    return {
        "namespace": namespace,
        "vessel": extract_vessel(sheets, operator_prefix),
        "main_engines": extract_main_engines(sheets, operator_prefix),
        "auxiliary_engines": extract_auxiliary_engines(sheets, operator_prefix),
        "propellers": extract_propellers(sheets, operator_prefix),
        "gearboxes": extract_gearboxes(sheets, operator_prefix),
        "pms": extract_pms(sheets, operator_prefix),
        "emergency_generators": other.get("emergency_generators", []),
        "thrusters": other.get("thrusters", []),
        "shaft_generators": other.get("shaft_generators", []),
        "boilers": other.get("boilers", []),
    }


def extract_vessel(sheets: dict, operator_prefix: str) -> dict:
    """Extract vessel data (one per operator)."""
    rows = extract_rows(
        sheets,
        "Vessel",
        "TWINSHIP-VESSEL-ID",
        operator_prefix,
        field_map={
            "id": "TWINSHIP-VESSEL-ID",
            "label": "TWINSHIP-VESSEL-NAME",
            "displacement_max_mt": "TWINSHIP-DISPLACEMENT-MAX-IN-MT",
            "draft_aft_max_m": "TWINSHIP-VESSEL-DRAFT-AFT-MAX-IN-M",
            "draft_for_max_m": "TWINSHIP-VESSEL-DRAFT-FOR-MAX-IN-M",
            "draft_mid_port_max_m": "TWINSHIP-VESSEL-DRAFT-MID-PORT-MAX-IN-M",
            "draft_mid_stbd_max_m": "TWINSHIP-VESSEL-DRAFT-MID-STBD-MAX-IN-M",
            "depth_of_water_max_m": "TWINSHIP-VESSEL-DEPTH-OF-WATER-MAX-IN-M",
        },
        extra=lambda row: {
            "type": (parse_types(row.get("TWINSHIP-VESSEL-TYPE")) or [None])[0]
        },
    )
    return rows[0] if rows else {}


def extract_main_engines(sheets: dict, operator_prefix: str) -> list[dict]:
    """Extract main engine data."""
    return extract_rows(
        sheets,
        "Main_Engine",
        "TWINSHIP-MAIN-ENGINE-ID",
        operator_prefix,
        field_map={
            "id": "TWINSHIP-MAIN-ENGINE-ID",
            "name": "TWINSHIP-MAIN-ENGINE-NAME",
            "shaft_torque_max_knm": "TWINSHIP-SHAFT-TORQUE-MAX-IN-kNm",
            "shaft_speed_max_rpm": "TWINSHIP-SHAFT-SPEED-MAX-IN-REV-PER_MIN",
            "shaft_power_max_kw": "TWINSHIP-SHAFT-POWER-MAX-IN-kW",
            "flowrate_max_kg_per_hr": "TWINSHIP-FLOWRATE-MAX-IN-KG_PER_HR",
            "fuel_flow_temp_max_c": "TWINSHIP-FUEL-FLOW-TEMPERATURE-MAX-IN-°C",
            "inlet_air_pressure_max_hpa": "TWINSHIP-INLET-AIR-PRESSURE-MAX-IN-hPa",
            "inlet_air_temp_max_c": "TWINSHIP-INLET-AIR-TEMPERATURE-MAX-IN-°C",
            "me_cooling_water_temp_max_c": "TWINSHIP-ME-COOLING-WATER-TEMPERATURE-MAX-IN-°C",
            "lt_cooling_seawater_1_temp_max_c": "TWINSHIP-LT-COOLING-SEAWATER-1-TEMPERATURE-MAX-IN-°C",
            "lt_cooling_seawater_2_temp_max_c": "TWINSHIP-LT-COOLING-SEAWATER-2-TEMPERATURE-MAX-IN-°C",
            "scavenger_air_rec_temp_max_c": "TWINSHIP-SCAVENGER-AIR-REC-TEMPERATURE-MAX-IN-°C",
            "common_do_mode": "TWINSHIP-COMMON-DO-MODE",
            "common_fuel_mode": "TWINSHIP-COMMOM-FUEL-MODE",
            "fuel_consumption_total_mt": "TWINSHIP-FUEL-CONSUMPTION-TOTAL-IN-MT",
            "power_propulsion_total_kw": "TWINSHIP-POWER-PROPULSION-TOTAL-IN-kW",
            "vessel_id": "TWINSHIP-VESSEL-ID",
            "gearbox_id": "TWINSHIP-GEARBOX-ID",
        },
        type_column="TWINSHIP-MAIN-ENGINE-TYPE",
        extra=lambda row: {"fuels": parse_bracket_list(row.get("TWINSHIP-FUEL-ID"))},
    )


def extract_auxiliary_engines(sheets: dict, operator_prefix: str) -> list[dict]:
    """Extract auxiliary engine (genset) data."""
    return extract_rows(
        sheets,
        "Auxiliary_Engine",
        "TWINSHIP-AUXILIARY-ENGINE-ID",
        operator_prefix,
        field_map={
            "id": "TWINSHIP-AUXILIARY-ENGINE-ID",
            "name": "TWINSHIP-AUXILIARY-ENGINE-NAME",
            "diesel_engine_power_max_kw": "TWINSHIP-DIESEL-ENGINE-POWER-MAX-IN-KW",
            "diesel_engine_speed_rpm": "TWINSHIP-DIESEL-ENGINE-SPEED-IN-REV-PER-MIN",
            "generator_power_max_kw": "TWINSHIP-GENERATOR-POWER-MAX-IN-KW",
            "generator_speed_rpm": "TWINSHIP-GENERATOR-SPEED-IN-REV-PER-MIN",
            "auxiliary_do_mode": "TWINSHIP-AUXILIARY-DO-MODE",
            "fuel_rate_mass_net_kg_per_hr": "TWINSHIP-AUXILIARY-FUEL-RATE-MASS-NET-KG-PER-HOUR",
            "pms_id": "TWINSHIP-PMS-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-AUXILIARY-ENGINE-TYPE",
        extra=lambda row: {"fuels": parse_bracket_list(row.get("TWINSHIP-FUEL-ID"))},
    )


def extract_gearboxes(sheets: dict, operator_prefix: str) -> list[dict]:
    """Extract gearbox data (DD=Direct Drive, RG=Reduction Gear)."""
    return extract_rows(
        sheets,
        "Gearbox",
        "TWINSHIP-GEARBOX-ID",
        operator_prefix,
        field_map={
            "id": "TWINSHIP-GEARBOX-ID",
            "name": "TWINSHIP-GEARBOX-NAME",
            "efficiency": "TWINSHIP-GEARBOX-EFFICIENCY",
            "ratio": "TWINSHIP-GEARBOX-RATIO",
            "shaft_generator": "TWINSHIP-GEARBOX-SHAFT-GENERATOR",
            "engine_id": "TWINSHIP-ENGINE-ID",
            "propeller_id": "TWINSHIP-PROPELLER-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-GEARBOX-TYPE",
    )


def extract_propellers(sheets: dict, operator_prefix: str) -> list[dict]:
    """Extract propeller data (CPP=Controllable Pitch, FPP=Fixed Pitch)."""
    return extract_rows(
        sheets,
        "Propeller",
        "TWINSHIP-PROPELLER-ID",
        operator_prefix,
        field_map={
            "id": "TWINSHIP-PROPELLER-ID",
            "name": "TWINSHIP-PROPEELER-NAME",  # Typo in spreadsheet
            "efficiency": "TWINSHIP-PROPELLER-EFFICIENCY",
            "pitch_max_percentage": "TWINSHIP-PROPELLER-PITCH-MAX-IN-PERCENTAGE",
            "diameter_mm": "TWINSHIP-PROPELLER-DIAMETER-MM",
            "blades": "TWINSHIP-PROPELLER-BLADES",
            "pitch_diameter_ratio": "TWINSHIP-PROPELLER-PITCH-DIAMETER -RATIO",
            "skew_angle_degree": "TWINSHIP-PROPELLER-SKEW-ANGLE-DEGREE",
            "expanded_area_ratio_percentage": "TWINSHIP-PROPELLER-EXPANDED-AREA-RATIO-PERCENTAGE",
            "hub_ratio": "TWINSHIP-PROPELLER-HUB-RATIO",
            "rudder_angle_degree": "TWINSHIP-RUDDER-ANGLE-DEGREE",
            "gearbox_id": "TWINSHIP-GEARBOX-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-PROPELLER-TYPE",
    )


def extract_pms(sheets: dict, operator_prefix: str) -> list[dict]:
    """Extract Power Management System data."""
    return extract_rows(
        sheets,
        "PMS",
        "TWINSHIP-PMS-ID",
        operator_prefix,
        field_map={
            "id": "TWINSHIP-PMS-ID",
            "name": "TWINSHIP-PMS-NAME",
            "auxiliary_engine_id": "TWINSHIP-AUXILIARY-ENGINE-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-PMS-TYPE",
    )


def extract_other_systems(sheets: dict, operator_prefix: str) -> dict[str, list[dict]]:
    """Extract mixed components from OTHER Systems sheet.

    Routes components to appropriate lists based on ID prefix:
    EG=Emergency Generator, TH=Thruster, SG=Shaft Generator, BLR/CMP=Boiler
    """
    result: dict[str, list[dict]] = {
        "emergency_generators": [],
        "thrusters": [],
        "shaft_generators": [],
        "boilers": [],
    }

    if "Other" not in sheets:
        return result

    for _, row in sheets["Other"].iterrows():
        component_id = row.get("TWINSHIP-COMPONENT-ID")
        if (
            pd.isna(component_id)
            or extract_operator_prefix(component_id) != operator_prefix
        ):
            continue

        base = {
            "id": clean_value(component_id),
            "name": clean_value(row.get("TWINSHIP-COMPONENT-NAME")),
            "types": parse_types(row.get("TWINSHIP-COMPONENT-TYPE")),
            "power_max_kw": clean_value(row.get("TWINSHIP-COMPONENT-POWER-MAX-IN-kW")),
            "speed_max_rpm": clean_value(
                row.get("TWINSHIP-COMPONENT-SPEED-MAX-IN-REV-PER-MIN")
            ),
        }

        id_prefix = str(component_id).split("-")[0].upper()
        if id_prefix == "EG":
            base["do_mode"] = clean_value(row.get("TWINSHIP-COMPONENT-EMERG-DO-MODE"))
            result["emergency_generators"].append(base)
        elif id_prefix == "TH":
            base["is_bow"] = "BOW" in str(base["name"]).upper()
            result["thrusters"].append(base)
        elif id_prefix == "SG":
            result["shaft_generators"].append(base)
        elif id_prefix in ("BLR", "CMP"):
            result["boilers"].append(base)

    return result
