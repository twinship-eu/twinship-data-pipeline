"""General utility functions for the TwinShip pipeline."""

from typing import Any

import pandas as pd

# Known operator mappings: prefix -> (namespace, display_name)
# Should ideally be updated when new operators are added to the dataset.
KNOWN_OPERATORS = {
    "GRI": ("grimaldi", "Grimaldi"),
    "STL": ("stena-scandinavica", "Stena Line"),
    "STT": ("stena-tanker", "Stena Tanker"),
}


def clean_value(val) -> Any:
    """Normalize Excel empty values (NaN, None) to None for JSON."""
    if pd.isna(val) or (isinstance(val, float) and val != val):
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


def parse_types(type_string: str | None) -> list[str]:
    """Parse '[tws:FourStroke, tws:DieselEngine]' -> ['FourStroke', 'DieselEngine']."""
    if not type_string or pd.isna(type_string):
        return []
    cleaned = str(type_string).replace("[", "").replace("]", "")
    return [
        part.strip()[4:] if part.strip().startswith("tws:") else part.strip()
        for part in cleaned.split(",")
        if part.strip()
    ]


def prefix_to_namespace(prefix: str) -> str:
    """Convert operator prefix to namespace (GRI -> grimaldi)."""
    return KNOWN_OPERATORS.get(prefix.upper(), (prefix.lower(),))[0]


def prefix_to_name(prefix: str) -> str:
    """Convert operator prefix to display name (GRI -> Grimaldi)."""
    return KNOWN_OPERATORS.get(prefix.upper(), (None, prefix.title()))[1]
