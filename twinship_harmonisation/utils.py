"""Utility functions for TwinShip harmonisation."""

import re

from rdflib import Graph

from twinship_harmonisation.constants import (
    IDO,
    PAV,
    QUDT,
    QUDT_QUANTITY_KIND,
    QUDT_UNIT,
    SOSA,
    SSN,
    TWINSHIP,
    TWINSHIP_IND,
)


def bind_namespaces(g: Graph) -> Graph:
    """Bind common namespace prefixes to a graph for readable serialization.

    Args:
        g: RDFLib Graph to bind namespaces to.

    Returns:
        The same graph with namespace bindings added.
    """
    g.bind("tws", TWINSHIP)
    g.bind("tws-ind", TWINSHIP_IND)
    g.bind("ido", IDO)
    g.bind("sosa", SOSA)
    g.bind("ssn", SSN)
    g.bind("qudt", QUDT)
    g.bind("unit", QUDT_UNIT)
    g.bind("quantitykind", QUDT_QUANTITY_KIND)
    g.bind("pav", PAV)
    return g


def sanitize_id(value: str) -> str:
    """Sanitize a string for use as a URI local name.

    Args:
        value: The string to sanitize.

    Returns:
        A sanitized string safe for use in URIs.
    """
    # Replace non-alphanumeric characters with underscores
    sanitized = re.sub(r"[^\w\-]", "_", str(value))
    # Remove leading digits
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized
