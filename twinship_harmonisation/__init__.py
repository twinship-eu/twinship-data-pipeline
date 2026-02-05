"""TwinShip Harmonisation Library.

A Python library for converting maritime vessel data into RDF triples
that conform to the TwinShip ontology.

Main entry points for data scientists:
    - harmonise_twinship_vessel(data) - Convert vessel dict to RDF graph
    - harmonise_twinship_vessel_file(path) - Convert vessel JSON file to RDF graph
    - harmonise_all_twinship_vessels(dir) - Convert all vessel files in directory
"""

from twinship_harmonisation.constants import (
    QUDT,
    QUDT_UNIT,
    SOSA,
    TWINSHIP,
    TWINSHIP_IND,
)
from twinship_harmonisation.high_level import (
    harmonise_all_twinship_vessels,
    harmonise_all_vessels,
    harmonise_twinship_vessel,
    harmonise_twinship_vessel_file,
    harmonise_vessel_data,
    harmonise_vessel_file,
)
from twinship_harmonisation.utils import bind_namespaces

__all__ = [
    # Namespaces
    "TWINSHIP",
    "TWINSHIP_IND",
    "SOSA",
    "QUDT",
    "QUDT_UNIT",
    # Utilities
    "bind_namespaces",
    # Main entry points (recommended)
    "harmonise_twinship_vessel",
    "harmonise_twinship_vessel_file",
    "harmonise_all_twinship_vessels",
    # Backwards compatibility aliases
    "harmonise_vessel_file",
    "harmonise_vessel_data",
    "harmonise_all_vessels",
]
