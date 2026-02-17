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
from typing import Any, dict, list, set

# =============================================================================
# ID patterns (based on current JSON files)
# =============================================================================

# Validate IDs with regex to catch typos like "STL-RP" or "STL--RP-1".
# These are "format checks" only.
VESSEL_ID_RE = re.compile(r"^[A-Z]{3}-[A-Z]{2,}-\d+$")                      # GRI-RR-1, STL-RP-1, STT-TK-1
ENGINE_ID_RE = re.compile(r"^[A-Z]{3}-(ME|AU)-\d+$")                        # STL-ME-1, STT-AU-4
GEARBOX_ID_RE = re.compile(r"^(DD|RG)-[A-Z]{3}-\d+$")                       # DD-GRI-1, RG-STL-2
PROPELLER_ID_RE = re.compile(r"^(CPP|FPP)-[A-Z]{3}-\d+$")                   # CPP-STL-1, FPP-STT-1
PMS_ID_RE = re.compile(r"^PMS-[A-Z]{3}-\d+$")                               # PMS-STL-1
BOILER_ID_RE = re.compile(r"^(BLR-[A-Z]{3}-\d+|CMP-BLR-[A-Z]{3}-\d+)$")     # BLR-STT-1, CMP-BLR-STT-1


# =============================================================================
# Allowed values (currently minimal and would extend if more is needed)
# =============================================================================

# Fuels should match the ontology list.
# Started with the ones already seen in data; expand later if needed.
ALLOWED_FUELS: set[str] = {
    "HFO", "MGO", "MDO",
    "LNG", "H2", "NH3", "Methanol",
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


def _expect_id(report: ValidationReport, path: str, v: Any, pat: re.Pattern[str], label: str) -> None:
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

    # Lists (default to empty)
    main_engines = data.get("main_engines", [])
    auxiliary_engines = data.get("auxiliary_engines", [])
    propellers = data.get("propellers", [])
    gearboxes = data.get("gearboxes", [])
    pms = data.get("pms", [])
    boilers = data.get("boilers", [])

    for name, arr in [
        ("main_engines", main_engines),
        ("auxiliary_engines", auxiliary_engines),
        ("propellers", propellers),
        ("gearboxes", gearboxes),
        ("pms", pms),
        ("boilers", boilers),
    ]:
        _expect_list(report, name, arr)

    # Collect IDs used for reference checks
    # These sets let us verify "this thing references an existing object"
    gearbox_ids: set[str] = set()
    propeller_ids: set[str] = set()
    pms_ids: set[str] = set()

    def _collect_ids(arr: Any, path: str, pat: re.Pattern[str], label: str) -> set[str]:
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

    gearbox_ids = _collect_ids(gearboxes, "gearboxes", GEARBOX_ID_RE, "gearbox id")
    propeller_ids = _collect_ids(propellers, "propellers", PROPELLER_ID_RE, "propeller id")
    pms_ids = _collect_ids(pms, "pms", PMS_ID_RE, "pms id")

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
                    report.errors.append(f"{path}.vessel_id: '{obj.get('vessel_id')}' != vessel.id '{vessel_id}'")

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
                    report.errors.append(f"{path}.fuels: unknown fuel '{f}' (allowed: {sorted(ALLOWED_FUELS)})")

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
                    report.errors.append(f"{path}.vessel_id: '{obj.get('vessel_id')}' != vessel.id '{vessel_id}'")

            pid = obj.get("pms_id")
            if pid is not None:
                _expect_id(report, f"{path}.pms_id", pid, PMS_ID_RE, "pms id")

                # Only enforce existence if PMS objects are present in this JSON file
                if pms_ids:
                    if isinstance(pid, str) and pid not in pms_ids:
                        report.errors.append(f"{path}.pms_id: references unknown PMS '{pid}'")
                else:
                    if not warned_missing_pms_objects:
                        report.warnings.append("pms: PMS objects not provided in this JSON, so pms_id references are not cross-checked")
                        warned_missing_pms_objects = True

            for f in _normalize_fuels(obj.get("fuels")):
                if f == "":
                    report.warnings.append(f"{path}.fuels: contains empty string fuel")
                elif f not in ALLOWED_FUELS:
                    report.errors.append(f"{path}.fuels: unknown fuel '{f}' (allowed: {sorted(ALLOWED_FUELS)})")

            # "[0, 1]" probably means "allowed values"
            adm = obj.get("auxiliary_do_mode")
            if isinstance(adm, str) and adm.strip().replace(" ", "") in {"[0,1]", "[1,0]"}:
                report.warnings.append(f"{path}.auxiliary_do_mode: looks like allowed-values '{adm}' (ignored)")

            for k, v in obj.items():
                if k.endswith(("_kw", "_rpm", "_knm", "_kg_per_hr", "_c", "_hpa", "_mt", "_m")):
                    _expect_num(report, f"{path}.{k}", v, allow_none=True)

    # Validate propellers (used relationship: propeller -> gearbox)
    if isinstance(propellers, list):
        for i, obj in enumerate(propellers):
            path = f"propellers[{i}]"
            if not isinstance(obj, dict):
                report.errors.append(f"{path}: expected object")
                continue

            _expect_id(report, f"{path}.id", obj.get("id"), PROPELLER_ID_RE, "propeller id")

            if vessel_id and obj.get("vessel_id") is not None:
                if obj.get("vessel_id") != vessel_id:
                    report.errors.append(f"{path}.vessel_id: '{obj.get('vessel_id')}' != vessel.id '{vessel_id}'")

            gb = obj.get("gearbox_id")
            if gb is not None:
                _expect_id(report, f"{path}.gearbox_id", gb, GEARBOX_ID_RE, "gearbox id")
                if isinstance(gb, str) and gb not in gearbox_ids:
                    report.errors.append(f"{path}.gearbox_id: references unknown gearbox '{gb}'")

            for k in [
                "diameter_mm", "blades", "pitch_diameter_ratio", "pitch_max_percentage",
                "expanded_area_ratio_percentage", "hub_ratio", "skew_angle_degree", "efficiency",
            ]:
                if k in obj:
                    _expect_num(report, f"{path}.{k}", obj.get(k), allow_none=True)

    # Validate gearboxes (engine_id backlink is redundant; warn only)
    if isinstance(gearboxes, list):
        for i, obj in enumerate(gearboxes):
            path = f"gearboxes[{i}]"
            if not isinstance(obj, dict):
                report.errors.append(f"{path}: expected object")
                continue

            _expect_id(report, f"{path}.id", obj.get("id"), GEARBOX_ID_RE, "gearbox id")

            if vessel_id and obj.get("vessel_id") is not None:
                if obj.get("vessel_id") != vessel_id:
                    report.errors.append(f"{path}.vessel_id: '{obj.get('vessel_id')}' != vessel.id '{vessel_id}'")

            # Redundant backlink: not used by pipeline
            if obj.get("engine_id") is not None:
                report.warnings.append(f"{path}.engine_id: redundant field present (ignored)")

            # propeller_id is a real reference; keep strict
            prop = obj.get("propeller_id")
            if prop is not None:
                _expect_id(report, f"{path}.propeller_id", prop, PROPELLER_ID_RE, "propeller id")
                if isinstance(prop, str) and prop not in propeller_ids:
                    report.errors.append(f"{path}.propeller_id: references unknown propeller '{prop}'")

    # Boilers (treat gently because current data has null vessel_id / empty fuels)
    if isinstance(boilers, list):
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
                    report.errors.append(f"{path}.fuels: unknown fuel '{f}' (allowed: {sorted(ALLOWED_FUELS)})")

    return report
