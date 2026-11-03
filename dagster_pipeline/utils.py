"""General utility functions for the TwinShip pipeline."""

import os
from pathlib import Path
from typing import Any

import pandas as pd


def vessel_data_dir() -> Path:
    """Folder to read vessel input files from.

    TWINSHIP_VESSEL_DATA_DIR (absolute, or relative to the working directory),
    or data/ when the variable is unset or empty.
    """
    return Path(os.environ.get("TWINSHIP_VESSEL_DATA_DIR") or "data")


# Known operator mappings: prefix -> namespace
# Should ideally be updated when new operators are added to the dataset.
KNOWN_OPERATORS = {
    "GRI": "grimaldi-roro",
    "STL": "stena-ropax",
    "STT": "stena-tanker",
    "FV": "futuristic-vessel",
}


# The source spreadsheets mark unknown values with -1. TwinShip omits unknown
# values instead (no triple), so -1 is read as empty.
SOURCE_UNKNOWN_MARKERS = {"-1", "-1.0"}


def clean_value(val) -> Any:
    """Normalize Excel empty values (NaN, None) and the -1 unknown marker to None for JSON."""
    if pd.isna(val) or (isinstance(val, float) and val != val):
        return None
    if str(val).strip() in SOURCE_UNKNOWN_MARKERS:
        return None
    return val


def extract_operator_prefix(entity_id: str) -> str | None:
    """Extract the operator prefix (GRI, STL, STT) from an entity ID.

    Searches all segments of the ID to handle various formats:
    GRI-ME-1, CPP-GRI-1, CMP-BLR-STT-1
    """
    if pd.isna(entity_id):
        return None
    for part in str(entity_id).split("-"):
        if part.upper() in KNOWN_OPERATORS:
            return part.upper()
    return None


def parse_bracket_list(value: str | None) -> list[str]:
    """Parse '[HFO, MGO, MDO]' -> ['HFO', 'MGO', 'MDO']."""
    if not value or pd.isna(value):
        return []
    cleaned = str(value).replace("[", "").replace("]", "")
    return [part.strip() for part in cleaned.split(",") if part.strip()]


def parse_types(type_string: str | None) -> list[str]:
    """Parse '[tws:FourStroke, tws:DieselEngine]' -> ['FourStroke', 'DieselEngine'].

    Handles both 'tws:X' and 'tws: X' (with space after colon).
    """
    result = []
    for t in parse_bracket_list(type_string):
        if t.startswith("tws:"):
            result.append(t[4:].strip())
        else:
            result.append(t)
    return result


def prefix_to_namespace(prefix: str) -> str:
    """Convert operator prefix to namespace (GRI -> grimaldi-roro)."""
    return KNOWN_OPERATORS.get(prefix.upper(), prefix.lower())
