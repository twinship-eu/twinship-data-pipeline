"""TwinShip futuristic vessel spreadsheet extraction.

The futuristic RoRo vessel uses a different spreadsheet layout: one sheet per
component type (17 sheets) instead of the conventional 7 functional-group sheets.
There is no VESSEL System sheet — the vessel is synthesised from known data.

The EM and ESS sheets each contain multiple component types that are routed by
ID prefix: EM has FV-FC (frequency converters), FV-EMM (electric motors), and
FV-EMSH (electric motor shafts); ESS has FV-ESS (energy storage) and FV-DCB
(DC bus converters).
"""

import pandas as pd

from dagster_pipeline.extraction import extract_rows
from dagster_pipeline.utils import clean_value, parse_bracket_list, parse_types

# Mapping of internal names to actual Excel sheet names in the futuristic spreadsheet
FV_SHEET_MAPPING = {
    "Genset": "GENSET (ENGINE + GENERATOR)",
    "ESS": "ESS ENERGY STORAGE SYSTEM",
    "SCR": "SCR SELECTIVE CATALYTIC REDUCT",
    "PMS": "PMS MAIN SWITCHBOARD AC",
    "AuxLoad": "AUXLD AUXILIARY LOAD",
    "OSP": "OSP SHORE CONNECTION",
    "EM": "EM ELECTRIC MOTOR FREQ CONVENT",
    "CPP": "CPP CONTROLABLE PITCH PROPELLER",
    "GRS": "GRS GATE RUDDER SYSTEM",
    "TH": "TH THRUSTER",
    "Fuel": "FUEL",
    "WASP": "WASP WIND ASSIST PROPULSION",
    "ALS": "ALS AIR LUBRICATION SYSTEM",
    "DW": "DW DYNAMIC WING",
    "AMMCELL": "AMMCELL AMMONIA CELL",
}


def load_futuristic_sheets(spreadsheet_path: str) -> dict[str, pd.DataFrame]:
    """Load all sheets from the futuristic vessel spreadsheet.

    Same row layout as the conventional spreadsheet:
    - Row 0: Human-readable headers (skipped)
    - Row 1: Machine-readable column names
    - Row 2: Data type annotations (skipped)
    - Row 3+: Data rows
    """
    sheets = {}
    for internal_name, actual_name in FV_SHEET_MAPPING.items():
        try:
            df = pd.read_excel(spreadsheet_path, sheet_name=actual_name, header=1, skiprows=[2])
            # Pandas auto-handles duplicate columns by appending .1, .2, etc.
            # We use those suffixes directly when accessing relationship columns.
            sheets[internal_name] = df
        except Exception:
            pass
    return sheets


def discover_futuristic_vessels(sheets: dict[str, pd.DataFrame]) -> dict[str, dict]:
    """Discover futuristic vessels from the spreadsheet.

    The futuristic spreadsheet always contains exactly one vessel (FV).
    We check for FV-prefixed IDs in the Genset sheet to confirm.
    """
    if "Genset" not in sheets:
        return {}

    id_col = "TWINSHIP-MAIN-GENSET-ID"
    if id_col not in sheets["Genset"].columns:
        return {}

    for entity_id in sheets["Genset"][id_col]:
        if pd.notna(entity_id) and str(entity_id).startswith("FV-"):
            return {"futuristic-vessel": {"prefix": "FV"}}

    return {}


def _append_instance_number(components: list[dict]) -> list[dict]:
    """Append the instance number from the ID to each component's name.

    E.g. id="FV-EMM-1", name="ELECTRIC MOTOR" → name="ELECTRIC MOTOR 1"

    Handles two edge cases:
    - Name already ends with the instance number (gensets) → skip
    - Name ends with the type abbreviation from the ID (PMS) → replace with number
    """
    for comp in components:
        entity_id = comp.get("id", "")
        name = comp.get("name", "")
        if entity_id and name:
            # Instance number is the last segment: FV-EMM-1 → 1
            parts = str(entity_id).rsplit("-", 1)
            if len(parts) == 2 and parts[1].isdigit():
                num = parts[1]
                # Already ends with the instance number? Skip.
                if name.endswith(f" {num}"):
                    continue
                # Extract type abbreviation (middle part of ID: FV-PMS-1 → PMS)
                id_parts = str(entity_id).split("-")
                if len(id_parts) >= 3:
                    type_abbrev = "-".join(id_parts[1:-1])
                    # Name ends with the type abbreviation? Replace with number.
                    if name.endswith(f" {type_abbrev}"):
                        comp["name"] = name[: -len(type_abbrev)] + num
                        continue
                comp["name"] = f"{name} {num}"
    return components


def extract_futuristic_vessel(
    sheets: dict[str, pd.DataFrame],
    prefix: str,
    namespace: str,
) -> dict:
    """Extract all futuristic vessel data from the spreadsheet.

    Returns a dict ready for harmonise_twinship_vessel(**data).
    """
    # Synthesise vessel (no VESSEL System sheet for futuristic vessel)
    vessel = {
        "id": f"{prefix}-RR-1",
        "label": "FUTURISTIC RORO VESSEL",
        "type": "RoRo",
        "displacement_max_mt": None,
        "draft_aft_max_m": None,
        "draft_for_max_m": None,
        "draft_mid_port_max_m": None,
        "draft_mid_stbd_max_m": None,
        "depth_of_water_max_m": None,
    }

    gensets = _extract_gensets(sheets, prefix)
    ess_data = _extract_ess_and_dcb(sheets, prefix)
    scrs = _extract_scrs(sheets, prefix)
    pms = _extract_pms(sheets, prefix)
    auxiliary_loads = _extract_auxiliary_loads(sheets, prefix)
    shore_power = _extract_shore_power(sheets, prefix)
    em_data = _extract_em_components(sheets, prefix)
    propellers = _extract_propellers(sheets, prefix)
    gate_rudders = _extract_gate_rudders(sheets, prefix)
    thrusters = _extract_thrusters(sheets, prefix)
    wasps = _extract_wasps(sheets, prefix)
    als = _extract_als(sheets, prefix)
    dynamic_wings = _extract_dynamic_wings(sheets, prefix)
    ammonia_fuel_cells = _extract_ammonia_fuel_cells(sheets, prefix)

    return {
        "namespace": namespace,
        "vessel": vessel,
        # Conventional components (empty for futuristic)
        "main_engines": [],
        "auxiliary_engines": [],
        "gearboxes": [],
        "propellers": _append_instance_number(propellers),
        "boilers": [],
        # Futuristic-specific components
        "gensets": _append_instance_number(gensets),
        "ess": _append_instance_number(ess_data["ess"]),
        "dc_bus_converters": _append_instance_number(ess_data["dc_bus_converters"]),
        "scrs": _append_instance_number(scrs),
        "pms": _append_instance_number(pms),
        "auxiliary_loads": _append_instance_number(auxiliary_loads),
        "shore_power": _append_instance_number(shore_power),
        "frequency_converters": _append_instance_number(em_data["frequency_converters"]),
        "electric_motors": _append_instance_number(em_data["electric_motors"]),
        "electric_motor_shafts": _append_instance_number(em_data["electric_motor_shafts"]),
        "gate_rudders": _append_instance_number(gate_rudders),
        "thrusters": _append_instance_number(thrusters),
        "wasps": _append_instance_number(wasps),
        "als": _append_instance_number(als),
        "dynamic_wings": _append_instance_number(dynamic_wings),
        "ammonia_fuel_cells": _append_instance_number(ammonia_fuel_cells),
    }


def _extract_gensets(sheets: dict[str, pd.DataFrame], prefix: str) -> list[dict]:
    """Extract generator sets from the GENSET sheet."""
    return extract_rows(
        sheets,
        "Genset",
        "TWINSHIP-MAIN-GENSET-ID",
        prefix,
        field_map={
            "id": "TWINSHIP-MAIN-GENSET-ID",
            "name": "TWINSHIP-MAIN-GENSET-NAME",
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
            "fuel_consumption_total_mt": "TWINSHIP-FUEL-CONSUMPTION-TOTAL-IN-MT",
            "power_propulsion_total_kw": "TWINSHIP-POWER-PROPULSION-TOTAL-IN-kW",
            "common_fuel_mode": "TWINSHIP-FUEL-MODE",
            "generator_voltage_v": "TWINSHIP-GENERATOR-VOLTAGE-V",
            "electrical_efficiency_percentage": "TWINSHIP-ELECTRICAL-EFFICIENCY-PERCENTAGE",
            "generator_frequency": "TWINSHIP-GENERATOR-FREQUENCY",
            "pms_id": "TWINSHIP-PMS-ID",
            "scr_id": "TWINSHIP-SCR-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-MAIN-GENSET-TYPE",
        extra=lambda row: {"fuels": parse_bracket_list(row.get("TWINSHIP-FUEL-ID"))},
    )


def _extract_ess_and_dcb(sheets: dict[str, pd.DataFrame], prefix: str) -> dict:
    """Extract ESS and DC Bus Converter from the ESS sheet.

    The ESS sheet contains two component types routed by ID prefix:
    FV-ESS → energy storage systems, FV-DCB → DC bus converters.
    """
    result: dict[str, list[dict]] = {"ess": [], "dc_bus_converters": []}

    if "ESS" not in sheets:
        return result

    for _, row in sheets["ESS"].iterrows():
        entity_id = row.get("TWINSHIP-ESS-ID")
        if pd.isna(entity_id) or not str(entity_id).startswith(f"{prefix}-"):
            continue

        entity_id_str = str(entity_id)
        id_prefix = entity_id_str.split("-")[1] if "-" in entity_id_str else ""

        # ESS sheet: TWINSHIP-ESS-ID appears 3 times (pandas: .1 = self-ref, .2 = partner)
        if id_prefix == "ESS":
            result["ess"].append(
                {
                    "id": clean_value(entity_id),
                    "name": clean_value(row.get("TWINSHIP-ESS-NAME")),
                    "types": parse_types(row.get("TWINSHIP-ESS-TYPE")),
                    "capacity_mwh": clean_value(row.get("TWINSHIP-ESS-CAPACITY-MWH")),
                    "weight_kg": clean_value(row.get("TWINSHIP-ESS-WEIGHT-KG")),
                    "depth_of_discharge_percentage": clean_value(
                        row.get("TWINSHIP-ESS-DPETH-OF-DISCHARGE-PERCENTAGE")
                    ),
                    "cycle_life": clean_value(row.get("TWINSHIP-ESS-CYCLE-LIFE")),
                    "volume_m3": clean_value(row.get("TWINSHIP-ESS-VOLUME-M3")),
                    "c_rate": clean_value(row.get("TWINSHIP-ESS-C-RATE")),
                    "dcb_id": clean_value(row.get("TWINSHIP-ESS-ID.2")),
                    "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
                }
            )
        elif id_prefix == "DCB":
            result["dc_bus_converters"].append(
                {
                    "id": clean_value(entity_id),
                    "name": clean_value(row.get("TWINSHIP-ESS-NAME")),
                    "types": parse_types(row.get("TWINSHIP-ESS-TYPE")),
                    "nominal_voltage": clean_value(row.get("TWINSHIP-DCB-NOMINAL-VOLTAGE")),
                    "max_voltage": clean_value(row.get("TWINSHIP-DCB-MAX-VOLTAGE")),
                    "min_voltage": clean_value(row.get("TWINSHIP-DCB-MIN-VOLTAGE")),
                    "max_current": clean_value(row.get("TWINSHIP-DCB-MAX-CURRENT")),
                    "ess_id": clean_value(row.get("TWINSHIP-ESS-ID.2")),
                    "pms_id": clean_value(row.get("TWINSHIP-PMS-ID")),
                    "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
                }
            )

    return result


def _extract_scrs(sheets: dict[str, pd.DataFrame], prefix: str) -> list[dict]:
    """Extract SCR emissions control systems."""
    return extract_rows(
        sheets,
        "SCR",
        "TWINSHIP-SCR-ID",
        prefix,
        field_map={
            "id": "TWINSHIP-SCR-ID",
            "name": "TWINSHIP-SCR-NAME",
            "no_reduction_efficiency": "TWINSHIP-SCR-NO-REDUCTION-EFFICIENCY",
            "exhaust_gas_flowrate_kg_per_hr": "TWINSHIP-SCR-EXHAUST-GAS-FLOWRATE-KG-PER-HR",
            "op_temp_centigrade": "TWINSHIP-SCR-OP-TEMP-CENTIGRADE",
            "catalyst_volume_m3": "TWINSHIP-SCR-CATALYST-VOLUME-M3",
            "genset_id": "TWINSHIP-GENSET-ID",
            "pms_id": "TWINSHIP-PMS-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-SCR-TYPE",
    )


def _extract_pms(sheets: dict[str, pd.DataFrame], prefix: str) -> list[dict]:
    """Extract PMS (main switchboard) from the PMS sheet."""
    return extract_rows(
        sheets,
        "PMS",
        "TWINSHIP-PMS-ID",
        prefix,
        field_map={
            "id": "TWINSHIP-PMS-ID",
            "name": "TWINSHIP-PMS-NAME",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-PMS-TYPE",
    )


def _extract_auxiliary_loads(sheets: dict[str, pd.DataFrame], prefix: str) -> list[dict]:
    """Extract auxiliary loads (ship services + hotel load)."""
    return extract_rows(
        sheets,
        "AuxLoad",
        "TWINSHIP-AUXLD-ID",
        prefix,
        field_map={
            "id": "TWINSHIP-AUXLD-ID",
            "name": "TWINSHIP-AUXLD-NAME",
            "ship_services_power_kw": "TWINSHIP-AUXLD-SHIP-SERVICES-POWER-kW",
            "hotel_load_power_kw": "TWINSHIP-AUXLD-HOTEL-LOAD-POWER-kW",
            "pms_id": "TWINSHIP-PMS-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-AUXLD-TYPE",
    )


def _extract_shore_power(sheets: dict[str, pd.DataFrame], prefix: str) -> list[dict]:
    """Extract on-shore power connections."""
    return extract_rows(
        sheets,
        "OSP",
        "TWINSHIP-OSP-ID",
        prefix,
        field_map={
            "id": "TWINSHIP-OSP-ID",
            "name": "TWINSHIP-OSP-NAME",
            "power_kwh": "TWINSHIP-OSP-POWER-kWh",
            "time_hours": "TWINSHIP-OSP-TIME-HOURS",
            "pms_id": "TWINSHIP-PMS-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-OSP-TYPE",
    )


def _extract_em_components(sheets: dict[str, pd.DataFrame], prefix: str) -> dict:
    """Extract frequency converters, electric motors, and shafts from the EM sheet.

    The EM sheet contains three component types routed by ID prefix:
    FV-FC → frequency converters, FV-EMM → electric motors,
    FV-EMSH → electric motor shafts.
    """
    result: dict[str, list[dict]] = {
        "frequency_converters": [],
        "electric_motors": [],
        "electric_motor_shafts": [],
    }

    if "EM" not in sheets:
        return result

    for _, row in sheets["EM"].iterrows():
        entity_id = row.get("TWINSHIP-EM-ID")
        if pd.isna(entity_id) or not str(entity_id).startswith(f"{prefix}-"):
            continue

        entity_id_str = str(entity_id)
        id_prefix = entity_id_str.split("-")[1] if "-" in entity_id_str else ""

        # EM sheet: TWINSHIP-EM-ID appears 4 times (pandas: .1=self, .2=ref1, .3=ref2)
        # FC:   .2 = motor_id
        # EMM:  .2 = fc_id, .3 = shaft_id
        # EMSH: .2 = motor_id, .3 = propeller_id
        if id_prefix == "FC":
            result["frequency_converters"].append(
                {
                    "id": clean_value(entity_id),
                    "name": clean_value(row.get("TWINSHIP-EM-NAME")),
                    "types": parse_types(row.get("TWINSHIP-EM-TYPE")),
                    "power_mwh": clean_value(row.get("TWINSHIP-EM-POWER-MWh")),
                    "voltage_volts": clean_value(row.get("TWINSHIP-FC-VOLTAGE-VOLTS")),
                    "frequency_hz": clean_value(row.get("TWINSHIP-FC-FEQUENCY-HZ")),
                    "motor_id": clean_value(row.get("TWINSHIP-EM-ID.2")),
                    "pms_id": clean_value(row.get("TWINSHIP-PMS-ID")),
                    "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
                }
            )
        elif id_prefix == "EMM":
            result["electric_motors"].append(
                {
                    "id": clean_value(entity_id),
                    "name": clean_value(row.get("TWINSHIP-EM-NAME")),
                    "types": parse_types(row.get("TWINSHIP-EM-TYPE")),
                    "power_mwh": clean_value(row.get("TWINSHIP-EM-POWER-MWh")),
                    "voltage_volts": clean_value(row.get("TWINSHIP-FC-VOLTAGE-VOLTS")),
                    "frequency_hz": clean_value(row.get("TWINSHIP-FC-FEQUENCY-HZ")),
                    "fc_id": clean_value(row.get("TWINSHIP-EM-ID.2")),
                    "shaft_id": clean_value(row.get("TWINSHIP-EM-ID.3")),
                    "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
                }
            )
        elif id_prefix == "EMSH":
            result["electric_motor_shafts"].append(
                {
                    "id": clean_value(entity_id),
                    "name": clean_value(row.get("TWINSHIP-EM-NAME")),
                    "speed_rpm": clean_value(row.get("TWINSHIP-EMSH-SPEED-REV-PER-MIN")),
                    "torque_kn": clean_value(row.get("TWINSHIP-EMSH-TORQUE-kN")),
                    "motor_id": clean_value(row.get("TWINSHIP-EM-ID.2")),
                    "propeller_id": clean_value(row.get("TWINSHIP-CPP-ID")),
                    "vessel_id": clean_value(row.get("TWINSHIP-VESSEL-ID")),
                }
            )

    return result


def _extract_propellers(sheets: dict[str, pd.DataFrame], prefix: str) -> list[dict]:
    """Extract CPP propellers from the futuristic spreadsheet."""
    return extract_rows(
        sheets,
        "CPP",
        "TWINSHIP-CPP-ID",
        prefix,
        field_map={
            "id": "TWINSHIP-CPP-ID",
            "name": "TWINSHIP-PROPEELER-NAME",
            "efficiency": "TWINSHIP-CPP-EFFICIENCY",
            "pitch_max_percentage": "TWINSHIP-CPP-PITCH-MAX-IN-PERCENTAGE",
            "diameter_mm": "TWINSHIP-CPP-DIAMETER-MM",
            "blades": "TWINSHIP-CPP-BLADES",
            "pitch_diameter_ratio": "TWINSHIP-CPP-PITCH-DIAMETER -RATIO",
            "skew_angle_degree": "TWINSHIP-CPP-SKEW-ANGLE-DEGREE",
            "expanded_area_ratio_percentage": "TWINSHIP-CPP-EXPANDED-AREA-RATIO-PERCENTAGE",
            "hub_ratio": "TWINSHIP-CPP-HUB-RATIO",
            "rudder_angle_degree": "TWINSHIP-RUDDER-ANGLE-DEGREE",
            "shaft_id": "TWINSHIP-EM-ID",
            "pms_id": "TWINSHIP-PMS-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-CPP-TYPE",
    )


def _extract_gate_rudders(sheets: dict[str, pd.DataFrame], prefix: str) -> list[dict]:
    """Extract gate rudder systems."""
    return extract_rows(
        sheets,
        "GRS",
        "TWINSHIP-GRS-ID",
        prefix,
        field_map={
            "id": "TWINSHIP-GRS-ID",
            "name": "TWINSHIP-GRS-NAME",
            "power_kw": "TWINSHIP-GRS-POWER-kW",
            "power_reduction_efficiency_percentage": "TWINSHIP-GRS-POWER-REDUCTION-EFFICIENCY-PERCENTAGE",
            "pms_id": "TWINSHIP-PMS-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-GRS-TYPE",
    )


def _extract_thrusters(sheets: dict[str, pd.DataFrame], prefix: str) -> list[dict]:
    """Extract bow thrusters."""
    return extract_rows(
        sheets,
        "TH",
        "TWINSHIP-TH-ID",
        prefix,
        field_map={
            "id": "TWINSHIP-TH-ID",
            "name": "TWINSHIP-TH-NAME",
            "power_kw": "TWINSHIP-TH-POWER-kW",
            "pms_id": "TWINSHIP-PMS-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-TH-TYPE",
    )


def _extract_wasps(sheets: dict[str, pd.DataFrame], prefix: str) -> list[dict]:
    """Extract wind-assisted propulsion systems."""
    return extract_rows(
        sheets,
        "WASP",
        "TWINSHIP-WASP-ID",
        prefix,
        field_map={
            "id": "TWINSHIP-WASP-ID",
            "name": "TWINSHIP-WASP-NAME",
            "power_kw": "TWINSHIP-WASP-POWER-kW",
            "power_reduction_efficiency_percentage": "TWINSHIP-WASP-POWER-REDUCTION-EFFICIENCY-PERCENTAGE",
            "pms_id": "TWINSHIP-PMS-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-WASP-TYPE",
    )


def _extract_als(sheets: dict[str, pd.DataFrame], prefix: str) -> list[dict]:
    """Extract air lubrication systems."""
    return extract_rows(
        sheets,
        "ALS",
        "TWINSHIP-ALS-ID",
        prefix,
        field_map={
            "id": "TWINSHIP-ALS-ID",
            "name": "TWINSHIP-ALS-NAME",
            "power_kw": "TWINSHIP-ALS-POWER-kW",
            "power_reduction_efficiency_percentage": "TWINSHIP-ALS-POWER-REDUCTION-EFFICIENCY-PERCENTAGE",
            "pms_id": "TWINSHIP-PMS-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-ALS-TYPE",
    )


def _extract_dynamic_wings(sheets: dict[str, pd.DataFrame], prefix: str) -> list[dict]:
    """Extract dynamic wings."""
    return extract_rows(
        sheets,
        "DW",
        "TWINSHIP-DW-ID",
        prefix,
        field_map={
            "id": "TWINSHIP-DW-ID",
            "name": "TWINSHIP-DW-NAME",
            "power_kw": "TWINSHIP-DW-POWER-kW",
            "power_reduction_efficiency_percentage": "TWINSHIP-DW-POWER-REDUCTION-EFFICIENCY-PERCENTAGE",
            "pms_id": "TWINSHIP-PMS-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-DW-TYPE",
    )


def _extract_ammonia_fuel_cells(sheets: dict[str, pd.DataFrame], prefix: str) -> list[dict]:
    """Extract ammonia fuel cells."""
    return extract_rows(
        sheets,
        "AMMCELL",
        "TWINSHIP-AMMCELL-ID",
        prefix,
        field_map={
            "id": "TWINSHIP-AMMCELL-ID",
            "name": "TWINSHIP-AMMCELL-NAME",
            "power_capacity_kwh": "TWINSHIP-AMMCELL-POWER-CAPACITY-kWh",
            "pms_id": "TWINSHIP-PMS-ID",
            "vessel_id": "TWINSHIP-VESSEL-ID",
        },
        type_column="TWINSHIP-AMMCELL-TYPE",
    )
