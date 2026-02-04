"""Low-level functions for fuel-related RDF triples."""

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import XSD

from twinship_harmonisation.constants import TWINSHIP


def get_fuel_uri(fuel_type: str) -> URIRef:
    """Get the URI for a standard fuel type.

    Args:
        fuel_type: Fuel type code ('HFO', 'MGO', or 'MDO').

    Returns:
        URIRef for the fuel individual.

    Raises:
        ValueError: If fuel_type is not recognized.
    """
    fuel_type = fuel_type.upper()
    if fuel_type not in ("HFO", "MGO", "MDO"):
        raise ValueError(f"Unknown fuel type: {fuel_type}. Must be HFO, MGO, or MDO.")
    return TWINSHIP[fuel_type]


def add_fuel_consumption(
    subject_uri: URIRef,
    fuel_uri: URIRef,
) -> Graph:
    """Add a fuel consumption relationship.

    Args:
        subject_uri: URI of the entity consuming fuel (engine, boiler, etc.).
        fuel_uri: URI of the fuel being consumed.

    Returns:
        Graph containing the consumption triple.
    """
    g = Graph()
    g.add((subject_uri, TWINSHIP.consume, fuel_uri))
    return g


def add_fuel_rate(
    subject_uri: URIRef,
    fuel_rate_kg_per_hr: float,
    property_uri: URIRef | None = None,
) -> Graph:
    """Add fuel consumption rate data.

    Args:
        subject_uri: URI of the entity.
        fuel_rate_kg_per_hr: Fuel rate in kg/hr.
        property_uri: Specific property to use (defaults to generic fuel rate).

    Returns:
        Graph containing the fuel rate triple.
    """
    g = Graph()
    if property_uri is None:
        property_uri = TWINSHIP.twAuxiliaryFuelRateMassNetKgPerHr
    g.add((subject_uri, property_uri, Literal(fuel_rate_kg_per_hr, datatype=XSD.double)))
    return g
