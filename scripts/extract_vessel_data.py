"""Extract vessel data from TwinShip Excel spreadsheet into JSON files.

This script reads the TwinShip-table-schema-specification.xlsx file and
extracts the data into separate JSON files per operator (Grimaldi, Stena Line, Stena Tanker).
"""

import json
import re
from pathlib import Path

import pandas as pd

# Operator prefixes and their metadata
OPERATORS = {
    "GRI": {
        "namespace": "grimaldi",
        "label": "Grimaldi",
        "vessel_type": "RoRo",
    },
    "STL": {
        "namespace": "stena-scandinavica",
        "label": "Stena Line",
        "vessel_type": "RoPax",
    },
    "STT": {
        "namespace": "stena-tanker",
        "label": "Stena Tanker",
        "vessel_type": "Tanker",
    },
}


def clean_column_name(name: str) -> str:
    """Convert TWINSHIP-MAIN-ENGINE-ID to main_engine_id."""
    if not isinstance(name, str):
        return None
    # Remove TWINSHIP- prefix
    name = re.sub(r"^TWINSHIP-", "", name)
    # Convert to lowercase and replace hyphens with underscores
    name = name.lower().replace("-", "_")
    return name


def parse_type_list(value: str) -> list[str]:
    """Parse [tws:FourStroke, tws:DieselEngine] into list of types."""
    if not isinstance(value, str) or not value.startswith("["):
        return []
    # Remove brackets and split
    inner = value.strip("[]")
    types = [t.strip().replace("tws:", "").replace(" ", "") for t in inner.split(",")]
    return [t for t in types if t]


def parse_id_list(value: str) -> list[str]:
    """Parse [HFO, MGO, MDO] into list of IDs."""
    if not isinstance(value, str):
        if pd.isna(value):
            return []
        return [str(value)]
    if value.startswith("["):
        inner = value.strip("[]")
        return [t.strip() for t in inner.split(",") if t.strip()]
    return [value]


def get_operator_prefix(entity_id: str) -> str | None:
    """Extract operator prefix from entity ID.

    Handles both formats:
    - GRI-ME-1 (operator first)
    - CPP-GRI-1 (operator in middle)
    """
    if not isinstance(entity_id, str):
        return None
    for prefix in OPERATORS.keys():
        if prefix in entity_id:
            return prefix
    return None


def read_sheet(xlsx: pd.ExcelFile, sheet_name: str) -> pd.DataFrame:
    """Read a sheet with proper header handling."""
    df = pd.read_excel(xlsx, sheet_name=sheet_name, header=None)

    # Row 1 contains column names, row 2 contains types, data starts at row 3
    columns = df.iloc[1].tolist()
    df = df.iloc[3:].reset_index(drop=True)

    # Clean column names and deduplicate by adding suffix
    clean_columns = []
    seen = {}
    for c in columns:
        clean = clean_column_name(c)
        if clean is None:
            clean_columns.append(None)
        elif clean in seen:
            # Suffix duplicate columns (usually relation columns)
            seen[clean] += 1
            clean_columns.append(f"{clean}_rel")
        else:
            seen[clean] = 1
            clean_columns.append(clean)

    df.columns = clean_columns

    # Remove columns with None names
    valid_cols = [c for c in df.columns if c is not None]
    df = df[valid_cols]

    return df


def extract_vessels(xlsx: pd.ExcelFile) -> dict[str, dict]:
    """Extract vessel data grouped by operator."""
    df = read_sheet(xlsx, "VESSEL System")

    vessels = {}
    for _, row in df.iterrows():
        vessel_id = row.get("vessel_id")
        if pd.isna(vessel_id) or not vessel_id:
            continue

        prefix = get_operator_prefix(vessel_id)
        if not prefix:
            continue

        vessel = {
            "id": vessel_id,
            "name": row.get("vessel_name"),
            "types": parse_type_list(row.get("vessel_type", "")),
            "displacement_max_mt": row.get("displacement_max_in_mt"),
            "draft_aft_max_m": row.get("vessel_draft_aft_max_in_m"),
            "draft_for_max_m": row.get("vessel_draft_for_max_in_m"),
            "draft_mid_port_max_m": row.get("vessel_draft_mid_port_max_in_m"),
            "draft_mid_stbd_max_m": row.get("vessel_draft_mid_stbd_max_in_m"),
            "depth_of_water_max_m": row.get("vessel_depth_of_water_max_in_m"),
        }

        # Clean up -1 values (unknown)
        vessel = {k: (None if v == -1 else v) for k, v in vessel.items()}

        vessels[prefix] = vessel

    return vessels


def extract_main_engines(xlsx: pd.ExcelFile) -> dict[str, list[dict]]:
    """Extract main engine data grouped by operator."""
    df = read_sheet(xlsx, "MAIN ENGINE System")

    engines = {prefix: [] for prefix in OPERATORS}
    for _, row in df.iterrows():
        engine_id = row.get("main_engine_id")
        if pd.isna(engine_id) or not engine_id:
            continue

        prefix = get_operator_prefix(engine_id)
        if not prefix:
            continue

        engine = {
            "id": engine_id,
            "name": row.get("main_engine_name"),
            "types": parse_type_list(row.get("main_engine_type", "")),
            "shaft_torque_max_knm": row.get("shaft_torque_max_in_knm"),
            "shaft_speed_max_rpm": row.get("shaft_speed_max_in_rev_per_min"),
            "shaft_power_max_kw": row.get("shaft_power_max_in_kw"),
            "flowrate_max_kg_per_hr": row.get("flowrate_max_in_kg_per_hr"),
            "fuel_flow_temp_max_c": row.get("fuel_flow_temperature_max_in_°c"),
            "inlet_air_pressure_max_hpa": row.get("inlet_air_pressure_max_in_hpa"),
            "inlet_air_temp_max_c": row.get("inlet_air_temperature_max_in_°c"),
            "me_cooling_water_temp_max_c": row.get("me_cooling_water_temperature_max_in_°c"),
            "lt_cooling_seawater_1_temp_max_c": row.get(
                "lt_cooling_seawater_1_temperature_max_in_°c"
            ),
            "lt_cooling_seawater_2_temp_max_c": row.get(
                "lt_cooling_seawater_2_temperature_max_in_°c"
            ),
            "scavenger_air_rec_temp_max_c": row.get("scavenger_air_rec_temperature_max_in_°c"),
            "fuels": parse_id_list(row.get("fuel_id", "")),
            "vessel_id": row.get("vessel_id"),
            "gearbox_id": row.get("gearbox_id"),
        }

        # Clean up -1 values
        engine = {k: (None if v == -1 else v) for k, v in engine.items()}

        engines[prefix].append(engine)

    return engines


def extract_auxiliary_engines(xlsx: pd.ExcelFile) -> dict[str, list[dict]]:
    """Extract auxiliary engine data grouped by operator."""
    df = read_sheet(xlsx, "AUXILIARY GENSET System")

    engines = {prefix: [] for prefix in OPERATORS}
    for _, row in df.iterrows():
        engine_id = row.get("auxiliary_engine_id")
        if pd.isna(engine_id) or not engine_id:
            continue

        prefix = get_operator_prefix(engine_id)
        if not prefix:
            continue

        engine = {
            "id": engine_id,
            "name": row.get("auxiliary_engine_name"),
            "types": parse_type_list(row.get("auxiliary_engine_type", "")),
            "diesel_engine_power_max_kw": row.get("diesel_engine_power_max_in_kw"),
            "diesel_engine_speed_rpm": row.get("diesel_engine_speed_in_rev_per_min"),
            "generator_power_max_kw": row.get("generator_power_max_in_kw"),
            "generator_speed_rpm": row.get("generator_speed_in_rev_per_min"),
            "auxiliary_do_mode": row.get("auxiliary_do_mode"),
            "fuel_rate_mass_net_kg_per_hr": row.get("auxiliary_fuel_rate_mass_net_kg_per_hour"),
            "fuels": parse_id_list(row.get("fuel_id", "")),
            "vessel_id": row.get("vessel_id"),
            "pms_id": row.get("pms_id"),
        }

        # Clean up -1 values
        engine = {k: (None if v == -1 else v) for k, v in engine.items()}

        engines[prefix].append(engine)

    return engines


def extract_propellers(xlsx: pd.ExcelFile) -> dict[str, list[dict]]:
    """Extract propeller data grouped by operator."""
    df = read_sheet(xlsx, "PROPELLER System")

    propellers = {prefix: [] for prefix in OPERATORS}
    for _, row in df.iterrows():
        propeller_id = row.get("propeller_id")
        if pd.isna(propeller_id) or not propeller_id:
            continue

        prefix = get_operator_prefix(str(propeller_id))
        if not prefix:
            continue

        propeller = {
            "id": propeller_id,
            # Note: spreadsheet has typo "propeeler"
            "name": row.get("propeeler_name") or row.get("propeller_name"),
            "types": parse_type_list(str(row.get("propeller_type", ""))),
            "diameter_mm": row.get("propeller_diameter_mm"),
            "blades": row.get("propeller_blades"),
            "pitch_diameter_ratio": row.get("propeller_pitch_diameter__ratio"),  # has extra space
            "pitch_max_percentage": row.get("propeller_pitch_max_in_percentage"),
            "expanded_area_ratio_percentage": row.get("propeller_expanded_area_ratio_percentage"),
            "hub_ratio": row.get("propeller_hub_ratio"),
            "skew_angle_degree": row.get("propeller_skew_angle_degree"),
            "efficiency": row.get("propeller_efficiency"),
            "vessel_id": row.get("vessel_id"),
            "gearbox_id": row.get("gearbox_id"),
        }

        # Clean up -1 values
        propeller = {k: (None if v == -1 else v) for k, v in propeller.items()}

        propellers[prefix].append(propeller)

    return propellers


def extract_gearboxes(xlsx: pd.ExcelFile) -> dict[str, list[dict]]:
    """Extract gearbox data grouped by operator."""
    df = read_sheet(xlsx, "GEARBOX System")

    gearboxes = {prefix: [] for prefix in OPERATORS}
    for _, row in df.iterrows():
        gearbox_id = row.get("gearbox_id")
        if pd.isna(gearbox_id) or not gearbox_id:
            continue

        prefix = get_operator_prefix(gearbox_id)
        if not prefix:
            continue

        gearbox = {
            "id": gearbox_id,
            "name": row.get("gearbox_name"),
            "types": parse_type_list(row.get("gearbox_type", "")),
            "ratio": row.get("gearbox_ratio"),
            "efficiency": row.get("gearbox_efficiency"),
            "shaft_generator": row.get("gearbox_shaft_generator"),
            "vessel_id": row.get("vessel_id"),
            "engine_id": row.get("engine_id"),
            "propeller_id": row.get("propeller_id"),
        }

        # Clean up -1 values
        gearbox = {k: (None if v == -1 else v) for k, v in gearbox.items()}

        gearboxes[prefix].append(gearbox)

    return gearboxes


def extract_boilers(xlsx: pd.ExcelFile) -> dict[str, list[dict]]:
    """Extract boiler data from OTHER Systems sheet."""
    df = read_sheet(xlsx, "OTHER Systems")

    boilers = {prefix: [] for prefix in OPERATORS}
    for _, row in df.iterrows():
        component_id = row.get("component_id")
        if pd.isna(component_id) or not component_id:
            continue

        # Check if this is a boiler (BLR in ID)
        if "BLR" not in str(component_id):
            continue

        prefix = get_operator_prefix(component_id)
        if not prefix:
            continue

        boiler = {
            "id": component_id,
            "name": row.get("component_name"),
            "types": parse_type_list(row.get("component_type", "")),
            "power_max_kw": row.get("power_max_in_kw"),
            "speed_max_rpm": row.get("speed_max_in_rev_per_min"),
            "fuels": parse_id_list(row.get("fuel_id", "")),
            "vessel_id": row.get("vessel_id"),
        }

        # Clean up -1 values
        boiler = {k: (None if v == -1 else v) for k, v in boiler.items()}

        boilers[prefix].append(boiler)

    return boilers


def clean_nan(obj):
    """Recursively replace NaN with None in dicts/lists."""
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(v) for v in obj]
    elif isinstance(obj, float) and pd.isna(obj):
        return None
    return obj


def build_operator_json(
    prefix: str,
    vessels: dict,
    main_engines: dict,
    auxiliary_engines: dict,
    propellers: dict,
    gearboxes: dict,
    boilers: dict,
) -> dict:
    """Build complete JSON structure for an operator."""
    operator_info = OPERATORS[prefix]
    vessel = vessels.get(prefix, {})

    return {
        "namespace": operator_info["namespace"],
        "operator": operator_info["label"],
        "vessel": {
            "id": vessel.get("id"),
            "label": vessel.get("name"),
            "type": operator_info["vessel_type"],
            "displacement_max_mt": vessel.get("displacement_max_mt"),
            "draft_aft_max_m": vessel.get("draft_aft_max_m"),
            "draft_for_max_m": vessel.get("draft_for_max_m"),
        },
        "main_engines": main_engines.get(prefix, []),
        "auxiliary_engines": auxiliary_engines.get(prefix, []),
        "propellers": propellers.get(prefix, []),
        "gearboxes": gearboxes.get(prefix, []),
        "boilers": boilers.get(prefix, []),
    }


def main():
    """Extract all data and write to JSON files."""
    data_dir = Path(__file__).parent.parent / "data"
    xlsx_path = data_dir / "TwinShip-table-schema-specification.xlsx"

    print(f"Reading {xlsx_path}...")
    xlsx = pd.ExcelFile(xlsx_path)

    # Extract all data
    print("Extracting vessels...")
    vessels = extract_vessels(xlsx)

    print("Extracting main engines...")
    main_engines = extract_main_engines(xlsx)

    print("Extracting auxiliary engines...")
    auxiliary_engines = extract_auxiliary_engines(xlsx)

    print("Extracting propellers...")
    propellers = extract_propellers(xlsx)

    print("Extracting gearboxes...")
    gearboxes = extract_gearboxes(xlsx)

    print("Extracting boilers...")
    boilers = extract_boilers(xlsx)

    # Write JSON files per operator
    for prefix, info in OPERATORS.items():
        output_path = data_dir / f"{info['namespace']}.json"

        data = build_operator_json(
            prefix, vessels, main_engines, auxiliary_engines, propellers, gearboxes, boilers
        )

        # Clean NaN values before writing
        data = clean_nan(data)

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Wrote {output_path}")
        print(f"  - {len(data['main_engines'])} main engines")
        print(f"  - {len(data['auxiliary_engines'])} auxiliary engines")
        print(f"  - {len(data['propellers'])} propellers")
        print(f"  - {len(data['gearboxes'])} gearboxes")
        print(f"  - {len(data['boilers'])} boilers")


if __name__ == "__main__":
    main()
