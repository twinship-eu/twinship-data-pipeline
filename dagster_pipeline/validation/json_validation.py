"""JSON Validation

This script validates the JSON because the pipeline uses JSON as the real input.

The JSON files are generated from Excel, so sometimes they contain:
    - real data (used by harmonisation)
    - leftover/spec fields (not used by harmonisation)

The proposed rule to follow:
    - ERROR = the pipleines would likely break or produce the wrong graph
    - WARNING = unclean inptu, but pipeline can proceed
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# =============================================================================
# ID patterns (based on current JSON files)
# =============================================================================

# Validate IDs with regex to catch typos like "STL-RP" or "STL--RP-1".
# These are "format checks" only.
VESSEL_ID_RE = re.compile(r"^[A-Z]{2,3}-[A-Z]{2,}-\d+$")  # GRI-RR-1, STL-RP-1, FV-RR-1
ENGINE_ID_RE = re.compile(r"^[A-Z]{3}-(ME|AU)-\d+$")  # STL-ME-1, STT-AU-4
GEARBOX_ID_RE = re.compile(r"^(DD|RG)-[A-Z]{3}-\d+$")  # DD-GRI-1, RG-STL-2
PROPELLER_ID_RE = re.compile(r"^(CPP|FPP)-[A-Z]{3}-\d+$")  # CPP-STL-1, FPP-STT-1
PMS_ID_RE = re.compile(r"^PMS-[A-Z]{3}-\d+$")  # PMS-STL-1
BOILER_ID_RE = re.compile(r"^(BLR-[A-Z]{3}-\d+|CMP-BLR-[A-Z]{3}-\d+)$")  # BLR-STT-1, CMP-BLR-STT-1

# Futuristic vessel ID patterns (FV-<COMPONENT>-<N>)
FV_GENSET_ID_RE = re.compile(r"^FV-GN-\d+$")
FV_ESS_ID_RE = re.compile(r"^FV-ESS-\d+$")
FV_DCB_ID_RE = re.compile(r"^FV-DCB-\d+$")
FV_SCR_ID_RE = re.compile(r"^FV-SCR-\d+$")
FV_PMS_ID_RE = re.compile(r"^FV-PMS-\d+$")
FV_AUXLD_ID_RE = re.compile(r"^FV-AUXLD-\d+$")
FV_OSP_ID_RE = re.compile(r"^FV-OSP-\d+$")
FV_FC_ID_RE = re.compile(r"^FV-FC-\d+$")
FV_EMM_ID_RE = re.compile(r"^FV-EMM-\d+$")
FV_EMSH_ID_RE = re.compile(r"^FV-EMSH-\d+$")
FV_CPP_ID_RE = re.compile(r"^FV-CPP-\d+$")
FV_GRS_ID_RE = re.compile(r"^FV-GR-\d+$")
FV_TH_ID_RE = re.compile(r"^FV-TH-\d+$")
FV_WASP_ID_RE = re.compile(r"^FV-WASP-\d+$")
FV_ALS_ID_RE = re.compile(r"^FV-ALS-\d+$")
FV_DW_ID_RE = re.compile(r"^FV-DW-\d+$")
FV_AMMCELL_ID_RE = re.compile(r"^FV-AMMCELL-\d+$")


# =============================================================================
# Allowed values (currently minimal and would extend if more is needed)
# =============================================================================

# Fuels should match the ontology list.
# Started with the ones already seen in data; expand later if needed.
ALLOWED_FUELS: set[str] = {
    "HFO",
    "MGO",
    "MDO",
    "LNG",
    "H2",
    "NH3",
    "Methanol",
    "AMM",
    "BF",
}


# =============================================================================
# Report
# =============================================================================


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def ok(self) -> bool:
        return len(self.errors) == 0


# =============================================================================
# Helpers
# =============================================================================


def _is_missing_marker(v: Any) -> bool:
    # Erik said "-1 means missing"; JSON currently uses null a lot too.
    return v in (-1, -1.0) or (isinstance(v, str) and v.strip() in {"-1", "-1.0"})


def _expect_dict(report: ValidationReport, path: str, v: Any) -> bool:
    """Require v to be a JSON object (Python dict)."""
    if not isinstance(v, dict):
        report.errors.append(f"{path}: expected object")
        return False
    return True


def _expect_list(report: ValidationReport, path: str, v: Any) -> bool:
    """Require v to be a JSON array (Python list)."""
    if not isinstance(v, list):
        report.errors.append(f"{path}: expected list")
        return False
    return True


def _expect_str(report: ValidationReport, path: str, v: Any, allow_none: bool = False) -> None:
    """Require v to be a string (unless allow_none=True)."""
    if v is None and allow_none:
        return
    if not isinstance(v, str):
        report.errors.append(f"{path}: expected string")


def _expect_num(report: ValidationReport, path: str, v: Any, allow_none: bool = False) -> None:
    """
    Require v to be numeric.
    Allow None (null) if allow_none=True.
    Allow -1/-1.0 as "missing marker".
    """
    if v is None and allow_none:
        return
    if _is_missing_marker(v):
        return
    if not isinstance(v, (int, float)):
        report.errors.append(f"{path}: expected number")


def _expect_id(
    report: ValidationReport, path: str, v: Any, pat: re.Pattern[str], label: str
) -> None:
    """Require an ID string and check it matches the expected pattern."""
    if not isinstance(v, str) or not v.strip():
        report.errors.append(f"{path}: missing/empty {label}")
        return
    if not pat.match(v.strip()):
        report.errors.append(f"{path}: invalid {label} '{v}'")


def _normalize_fuels(v: Any) -> list[str]:
    """
    Fuels are usually a list: ["HFO", "MGO", ...]
    Sometimes they can be "", None, or a single string.
    This normalizes everything into a list[str].
    """
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v]
    if isinstance(v, str):
        return [v.strip()]
    return [str(v).strip()]


# =============================================================================
# Main validator
# =============================================================================


def validate_vessel_json(data: dict[str, Any]) -> ValidationReport:
    """
    Validate a single vessel JSON file.

    We validate:
      - required top-level keys: namespace + vessel object
      - ID formats
      - numeric fields are numeric/null/-1
      - relationships that matter for harmonisation:
          - main_engines[].gearbox_id must exist in gearboxes[].id
          - propellers[].gearbox_id must exist in gearboxes[].id
          - auxiliary_engines[].pms_id is checked ONLY if PMS objects exist in the file
      - fuels are from an allowed set (empty string fuel => warning)

    We DO NOT validate spreadsheet leftovers as hard errors:
      - gearboxes[].engine_id is redundant and not used (warning only)
      - auxiliary_do_mode like "[0, 1]" is likely "allowed values", not real data (warning only)
    """
    report = ValidationReport()

    _expect_str(report, "namespace", data.get("namespace"))

    vessel = data.get("vessel")
    if not _expect_dict(report, "vessel", vessel):
        return report

    _expect_id(report, "vessel.id", vessel.get("id"), VESSEL_ID_RE, "vessel id")
    _expect_str(report, "vessel.label", vessel.get("label"))
    _expect_str(report, "vessel.type", vessel.get("type"))

    # Use vessel.id to verify component vessel_id fields match.
    vessel_id = vessel.get("id") if isinstance(vessel.get("id"), str) else None

    # Optional vessel numeric fields (allow null OR -1)
    for k in [
        "displacement_max_mt",
        "draft_aft_max_m",
        "draft_for_max_m",
        "draft_mid_port_max_m",
        "draft_mid_stbd_max_m",
        "depth_of_water_max_m",
    ]:
        if k in vessel:
            _expect_num(report, f"vessel.{k}", vessel.get(k), allow_none=True)

    # Detect futuristic vessel (gensets present means futuristic)
    is_futuristic = bool(data.get("gensets"))

    # Lists (default to empty)
    main_engines = data.get("main_engines", [])
    auxiliary_engines = data.get("auxiliary_engines", [])
    propellers = data.get("propellers", [])
    gearboxes = data.get("gearboxes", [])
    pms = data.get("pms", [])
    boilers = data.get("boilers", [])

    # Futuristic vessels skip conventional propeller/PMS/boiler/gearbox validation
    # — those are validated in _validate_futuristic_components instead.
    conventional_lists = [
        ("main_engines", main_engines),
        ("auxiliary_engines", auxiliary_engines),
        ("gearboxes", gearboxes),
    ]
    if not is_futuristic:
        conventional_lists += [
            ("propellers", propellers),
            ("pms", pms),
            ("boilers", boilers),
        ]
    for name, arr in conventional_lists:
        _expect_list(report, name, arr)

    # Collect IDs used for reference checks
    # These sets let us verify "this thing references an existing object"
    gearbox_ids: set[str] = set()
    propeller_ids: set[str] = set()
    pms_ids: set[str] = set()

    def _collect_ids_inline(arr: Any, path: str, pat: re.Pattern[str], label: str) -> set[str]:
        """Collect IDs from list of objects and check duplicates."""
        ids: set[str] = set()
        if not isinstance(arr, list):
            return ids
        for i, obj in enumerate(arr):
            if not isinstance(obj, dict):
                report.errors.append(f"{path}[{i}]: expected object")
                continue
            oid = obj.get("id")
            _expect_id(report, f"{path}[{i}].id", oid, pat, label)
            if isinstance(oid, str):
                if oid in ids:
                    report.errors.append(f"{path}[{i}].id: duplicate id '{oid}'")
                ids.add(oid)
        return ids

    gearbox_ids = _collect_ids_inline(gearboxes, "gearboxes", GEARBOX_ID_RE, "gearbox id")
    if not is_futuristic:
        propeller_ids = _collect_ids_inline(
            propellers, "propellers", PROPELLER_ID_RE, "propeller id"
        )
        pms_ids = _collect_ids_inline(pms, "pms", PMS_ID_RE, "pms id")

    # If there are no PMS objects in this JSON, we can’t verify pms_id references.
    # We warn once instead of spamming one warning per auxiliary engine.
    warned_missing_pms_objects = False

    # Validate main engines (used relationship: engine -> gearbox)
    if isinstance(main_engines, list):
        for i, obj in enumerate(main_engines):
            path = f"main_engines[{i}]"
            if not isinstance(obj, dict):
                report.errors.append(f"{path}: expected object")
                continue

            _expect_id(report, f"{path}.id", obj.get("id"), ENGINE_ID_RE, "engine id")

            # vessel_id should match the top vessel.id
            if vessel_id and obj.get("vessel_id") is not None:
                if obj.get("vessel_id") != vessel_id:
                    report.errors.append(
                        f"{path}.vessel_id: '{obj.get('vessel_id')}' != vessel.id '{vessel_id}'"
                    )

            # gearbox_id matters because harmonisation uses it
            gb = obj.get("gearbox_id")
            if gb is not None:
                _expect_id(report, f"{path}.gearbox_id", gb, GEARBOX_ID_RE, "gearbox id")
                if isinstance(gb, str) and gb not in gearbox_ids:
                    report.errors.append(f"{path}.gearbox_id: references unknown gearbox '{gb}'")

            # fuels matter
            for f in _normalize_fuels(obj.get("fuels")):
                if f == "":
                    report.warnings.append(f"{path}.fuels: contains empty string fuel")
                elif f not in ALLOWED_FUELS:
                    report.errors.append(
                        f"{path}.fuels: unknown fuel '{f}' (allowed: {sorted(ALLOWED_FUELS)})"
                    )

            # numeric-ish fields (check all keys with unit suffixes)
            for k, v in obj.items():
                if k.endswith(("_kw", "_rpm", "_knm", "_kg_per_hr", "_c", "_hpa", "_mt", "_m")):
                    _expect_num(report, f"{path}.{k}", v, allow_none=True)

    # Validate auxiliary engines (used relationship: aux -> pms IF PMS objects exist)
    if isinstance(auxiliary_engines, list):
        for i, obj in enumerate(auxiliary_engines):
            path = f"auxiliary_engines[{i}]"
            if not isinstance(obj, dict):
                report.errors.append(f"{path}: expected object")
                continue

            _expect_id(report, f"{path}.id", obj.get("id"), ENGINE_ID_RE, "engine id")

            if vessel_id and obj.get("vessel_id") is not None:
                if obj.get("vessel_id") != vessel_id:
                    report.errors.append(
                        f"{path}.vessel_id: '{obj.get('vessel_id')}' != vessel.id '{vessel_id}'"
                    )

            pid = obj.get("pms_id")
            if pid is not None:
                _expect_id(report, f"{path}.pms_id", pid, PMS_ID_RE, "pms id")

                # Only enforce existence if PMS objects are present in this JSON file
                if pms_ids:
                    if isinstance(pid, str) and pid not in pms_ids:
                        report.errors.append(f"{path}.pms_id: references unknown PMS '{pid}'")
                else:
                    if not warned_missing_pms_objects:
                        report.warnings.append(
                            "pms: PMS objects not provided in this JSON, so pms_id references are not cross-checked"
                        )
                        warned_missing_pms_objects = True

            for f in _normalize_fuels(obj.get("fuels")):
                if f == "":
                    report.warnings.append(f"{path}.fuels: contains empty string fuel")
                elif f not in ALLOWED_FUELS:
                    report.errors.append(
                        f"{path}.fuels: unknown fuel '{f}' (allowed: {sorted(ALLOWED_FUELS)})"
                    )

            # "[0, 1]" probably means "allowed values"
            adm = obj.get("auxiliary_do_mode")
            if isinstance(adm, str) and adm.strip().replace(" ", "") in {"[0,1]", "[1,0]"}:
                report.warnings.append(
                    f"{path}.auxiliary_do_mode: looks like allowed-values '{adm}' (ignored)"
                )

            for k, v in obj.items():
                if k.endswith(("_kw", "_rpm", "_knm", "_kg_per_hr", "_c", "_hpa", "_mt", "_m")):
                    _expect_num(report, f"{path}.{k}", v, allow_none=True)

    # Validate propellers (used relationship: propeller -> gearbox)
    # Futuristic propellers use FV-CPP pattern and are validated in _validate_futuristic_components
    if not is_futuristic and isinstance(propellers, list):
        for i, obj in enumerate(propellers):
            path = f"propellers[{i}]"
            if not isinstance(obj, dict):
                report.errors.append(f"{path}: expected object")
                continue

            _expect_id(report, f"{path}.id", obj.get("id"), PROPELLER_ID_RE, "propeller id")

            if vessel_id and obj.get("vessel_id") is not None:
                if obj.get("vessel_id") != vessel_id:
                    report.errors.append(
                        f"{path}.vessel_id: '{obj.get('vessel_id')}' != vessel.id '{vessel_id}'"
                    )

            gb = obj.get("gearbox_id")
            if gb is not None:
                _expect_id(report, f"{path}.gearbox_id", gb, GEARBOX_ID_RE, "gearbox id")
                if isinstance(gb, str) and gb not in gearbox_ids:
                    report.errors.append(f"{path}.gearbox_id: references unknown gearbox '{gb}'")

            for k in [
                "diameter_mm",
                "blades",
                "pitch_diameter_ratio",
                "pitch_max_percentage",
                "expanded_area_ratio_percentage",
                "hub_ratio",
                "skew_angle_degree",
                "efficiency",
            ]:
                if k in obj:
                    _expect_num(report, f"{path}.{k}", obj.get(k), allow_none=True)

    # Validate gearboxes (engine_id backlink is redundant; warn only)
    # Futuristic vessels have no gearboxes
    if not is_futuristic and isinstance(gearboxes, list):
        for i, obj in enumerate(gearboxes):
            path = f"gearboxes[{i}]"
            if not isinstance(obj, dict):
                report.errors.append(f"{path}: expected object")
                continue

            _expect_id(report, f"{path}.id", obj.get("id"), GEARBOX_ID_RE, "gearbox id")

            if vessel_id and obj.get("vessel_id") is not None:
                if obj.get("vessel_id") != vessel_id:
                    report.errors.append(
                        f"{path}.vessel_id: '{obj.get('vessel_id')}' != vessel.id '{vessel_id}'"
                    )

            # Redundant backlink: not used by pipeline
            if obj.get("engine_id") is not None:
                report.warnings.append(f"{path}.engine_id: redundant field present (ignored)")

            # propeller_id is a real reference; keep strict
            prop = obj.get("propeller_id")
            if prop is not None:
                _expect_id(report, f"{path}.propeller_id", prop, PROPELLER_ID_RE, "propeller id")
                if isinstance(prop, str) and prop not in propeller_ids:
                    report.errors.append(
                        f"{path}.propeller_id: references unknown propeller '{prop}'"
                    )

    # Boilers (treat gently because current data has null vessel_id / empty fuels)
    # Futuristic vessels have no boilers
    if not is_futuristic and isinstance(boilers, list):
        for i, obj in enumerate(boilers):
            path = f"boilers[{i}]"
            if not isinstance(obj, dict):
                report.errors.append(f"{path}: expected object")
                continue

            _expect_id(report, f"{path}.id", obj.get("id"), BOILER_ID_RE, "boiler id")

            # Current JSON has vessel_id null for boilers; warn only
            if obj.get("vessel_id") is None:
                report.warnings.append(f"{path}.vessel_id: is null")

            for f in _normalize_fuels(obj.get("fuels")):
                if f == "":
                    report.warnings.append(f"{path}.fuels: contains empty string fuel")
                elif f not in ALLOWED_FUELS:
                    report.errors.append(
                        f"{path}.fuels: unknown fuel '{f}' (allowed: {sorted(ALLOWED_FUELS)})"
                    )

    # Futuristic vessel components (detected by presence of gensets)
    gensets = data.get("gensets", [])
    if gensets:
        _validate_futuristic_components(report, data, vessel_id)

    return report


# =============================================================================
# Futuristic vessel validation
# =============================================================================


def _validate_futuristic_components(
    report: ValidationReport, data: dict[str, Any], vessel_id: str | None
) -> None:
    """Validate futuristic vessel component data (gensets, ESS, SCR, etc.)."""

    gensets = data.get("gensets", [])
    ess = data.get("ess", [])
    dc_bus_converters = data.get("dc_bus_converters", [])
    scrs = data.get("scrs", [])
    pms = data.get("pms", [])
    auxiliary_loads = data.get("auxiliary_loads", [])
    shore_power = data.get("shore_power", [])
    frequency_converters = data.get("frequency_converters", [])
    electric_motors = data.get("electric_motors", [])
    electric_motor_shafts = data.get("electric_motor_shafts", [])
    gate_rudders = data.get("gate_rudders", [])
    thrusters = data.get("thrusters", [])
    wasps = data.get("wasps", [])
    als = data.get("als", [])
    dynamic_wings = data.get("dynamic_wings", [])
    ammonia_fuel_cells = data.get("ammonia_fuel_cells", [])

    # Collect IDs for referential integrity checks
    genset_ids = _collect_ids(report, gensets, "gensets", FV_GENSET_ID_RE, "genset id")
    ess_ids = _collect_ids(report, ess, "ess", FV_ESS_ID_RE, "ess id")
    dcb_ids = _collect_ids(report, dc_bus_converters, "dc_bus_converters", FV_DCB_ID_RE, "dcb id")
    scr_ids = _collect_ids(report, scrs, "scrs", FV_SCR_ID_RE, "scr id")
    pms_ids = _collect_ids(report, pms, "pms", FV_PMS_ID_RE, "pms id")
    _collect_ids(report, auxiliary_loads, "auxiliary_loads", FV_AUXLD_ID_RE, "auxld id")
    _collect_ids(report, shore_power, "shore_power", FV_OSP_ID_RE, "osp id")
    fc_ids = _collect_ids(
        report, frequency_converters, "frequency_converters", FV_FC_ID_RE, "fc id"
    )
    motor_ids = _collect_ids(report, electric_motors, "electric_motors", FV_EMM_ID_RE, "motor id")
    shaft_ids = _collect_ids(
        report, electric_motor_shafts, "electric_motor_shafts", FV_EMSH_ID_RE, "shaft id"
    )
    _collect_ids(report, gate_rudders, "gate_rudders", FV_GRS_ID_RE, "gate rudder id")
    _collect_ids(report, thrusters, "thrusters", FV_TH_ID_RE, "thruster id")
    _collect_ids(report, wasps, "wasps", FV_WASP_ID_RE, "wasp id")
    _collect_ids(report, als, "als", FV_ALS_ID_RE, "als id")
    _collect_ids(report, dynamic_wings, "dynamic_wings", FV_DW_ID_RE, "dynamic wing id")
    _collect_ids(
        report, ammonia_fuel_cells, "ammonia_fuel_cells", FV_AMMCELL_ID_RE, "ammonia cell id"
    )

    # Also validate futuristic propellers with FV-CPP pattern
    propellers = data.get("propellers", [])
    propeller_ids = _collect_ids(report, propellers, "propellers", FV_CPP_ID_RE, "propeller id")

    # Validate genset fields and references
    for i, obj in enumerate(_safe_list(gensets)):
        path = f"gensets[{i}]"
        _check_vessel_id(report, path, obj, vessel_id)
        _check_ref(report, f"{path}.pms_id", obj.get("pms_id"), pms_ids, "PMS")
        _check_ref(report, f"{path}.scr_id", obj.get("scr_id"), scr_ids, "SCR")
        _check_fuels(report, path, obj)
        _check_numeric_fields(report, path, obj)

    # Validate ESS references (ESS → DCB)
    for i, obj in enumerate(_safe_list(ess)):
        path = f"ess[{i}]"
        _check_vessel_id(report, path, obj, vessel_id)
        _check_ref(report, f"{path}.dcb_id", obj.get("dcb_id"), dcb_ids, "DC bus converter")

    # Validate DCB references (DCB → ESS, DCB → PMS)
    for i, obj in enumerate(_safe_list(dc_bus_converters)):
        path = f"dc_bus_converters[{i}]"
        _check_vessel_id(report, path, obj, vessel_id)
        _check_ref(report, f"{path}.ess_id", obj.get("ess_id"), ess_ids, "ESS")
        _check_ref(report, f"{path}.pms_id", obj.get("pms_id"), pms_ids, "PMS")

    # Validate SCR references (SCR → genset, SCR → PMS)
    for i, obj in enumerate(_safe_list(scrs)):
        path = f"scrs[{i}]"
        _check_vessel_id(report, path, obj, vessel_id)
        _check_ref(report, f"{path}.genset_id", obj.get("genset_id"), genset_ids, "genset")
        _check_ref(report, f"{path}.pms_id", obj.get("pms_id"), pms_ids, "PMS")

    # Validate FC references (FC → motor, FC → PMS)
    for i, obj in enumerate(_safe_list(frequency_converters)):
        path = f"frequency_converters[{i}]"
        _check_vessel_id(report, path, obj, vessel_id)
        _check_ref(report, f"{path}.motor_id", obj.get("motor_id"), motor_ids, "electric motor")
        _check_ref(report, f"{path}.pms_id", obj.get("pms_id"), pms_ids, "PMS")

    # Validate electric motor references (motor → FC, motor → shaft)
    for i, obj in enumerate(_safe_list(electric_motors)):
        path = f"electric_motors[{i}]"
        _check_vessel_id(report, path, obj, vessel_id)
        _check_ref(report, f"{path}.fc_id", obj.get("fc_id"), fc_ids, "frequency converter")
        _check_ref(report, f"{path}.shaft_id", obj.get("shaft_id"), shaft_ids, "shaft")

    # Validate electric motor shaft references (shaft → motor, shaft → propeller)
    for i, obj in enumerate(_safe_list(electric_motor_shafts)):
        path = f"electric_motor_shafts[{i}]"
        _check_vessel_id(report, path, obj, vessel_id)
        _check_ref(report, f"{path}.motor_id", obj.get("motor_id"), motor_ids, "electric motor")
        _check_ref(
            report, f"{path}.propeller_id", obj.get("propeller_id"), propeller_ids, "propeller"
        )

    # Validate components that reference PMS only
    for list_name, items in [
        ("auxiliary_loads", auxiliary_loads),
        ("shore_power", shore_power),
        ("gate_rudders", gate_rudders),
        ("thrusters", thrusters),
        ("wasps", wasps),
        ("als", als),
        ("dynamic_wings", dynamic_wings),
        ("ammonia_fuel_cells", ammonia_fuel_cells),
    ]:
        for i, obj in enumerate(_safe_list(items)):
            path = f"{list_name}[{i}]"
            _check_vessel_id(report, path, obj, vessel_id)
            _check_ref(report, f"{path}.pms_id", obj.get("pms_id"), pms_ids, "PMS")


def _safe_list(v: Any) -> list:
    """Return v if it's a list, else empty list."""
    return v if isinstance(v, list) else []


def _collect_ids(
    report: ValidationReport,
    arr: Any,
    path: str,
    pat: re.Pattern[str],
    label: str,
) -> set[str]:
    """Collect IDs from list of objects and check duplicates."""
    ids: set[str] = set()
    if not isinstance(arr, list):
        return ids
    for i, obj in enumerate(arr):
        if not isinstance(obj, dict):
            report.errors.append(f"{path}[{i}]: expected object")
            continue
        oid = obj.get("id")
        _expect_id(report, f"{path}[{i}].id", oid, pat, label)
        if isinstance(oid, str):
            if oid in ids:
                report.errors.append(f"{path}[{i}].id: duplicate id '{oid}'")
            ids.add(oid)
    return ids


def _check_vessel_id(report: ValidationReport, path: str, obj: dict, vessel_id: str | None) -> None:
    """Check component vessel_id matches the top-level vessel.id."""
    if vessel_id and obj.get("vessel_id") is not None:
        if obj.get("vessel_id") != vessel_id:
            report.errors.append(
                f"{path}.vessel_id: '{obj.get('vessel_id')}' != vessel.id '{vessel_id}'"
            )


def _check_ref(
    report: ValidationReport,
    path: str,
    ref_id: Any,
    valid_ids: set[str],
    label: str,
) -> None:
    """Check a reference ID exists in the valid set (if provided)."""
    if ref_id is None:
        return
    if not isinstance(ref_id, str) or not ref_id.strip():
        return
    if valid_ids and ref_id not in valid_ids:
        report.errors.append(f"{path}: references unknown {label} '{ref_id}'")


def _check_fuels(report: ValidationReport, path: str, obj: dict) -> None:
    """Validate fuel list entries."""
    for f in _normalize_fuels(obj.get("fuels")):
        if f == "":
            report.warnings.append(f"{path}.fuels: contains empty string fuel")
        elif f not in ALLOWED_FUELS:
            report.errors.append(
                f"{path}.fuels: unknown fuel '{f}' (allowed: {sorted(ALLOWED_FUELS)})"
            )


def _check_numeric_fields(report: ValidationReport, path: str, obj: dict) -> None:
    """Check all fields with unit suffixes are numeric."""
    for k, v in obj.items():
        if k.endswith(("_kw", "_rpm", "_knm", "_kg_per_hr", "_c", "_hpa", "_mt", "_m")):
            _expect_num(report, f"{path}.{k}", v, allow_none=True)
