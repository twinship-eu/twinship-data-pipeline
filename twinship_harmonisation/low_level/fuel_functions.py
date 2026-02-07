"""Low-level functions for creating fuel-related TwinShip RDF triples."""

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from twinship_harmonisation.constants import TWINSHIP


def get_twinship_fuel_uri(fuel_type: str) -> URIRef | None:
    """Get the TwinShip URI for a standard fuel type.

    Args:
        fuel_type: Fuel type code ('HFO', 'MGO', or 'MDO').

    Returns:
        URIRef for the fuel individual, or None if not recognized.
    """
    fuel_type = fuel_type.upper().strip()
    fuel_map = {
        "HFO": TWINSHIP.HFO,
        "MGO": TWINSHIP.MGO,
        "MDO": TWINSHIP.MDO,
    }
    return fuel_map.get(fuel_type)


def build_twinship_fuel_consumption(
    subject_uri: URIRef,
    fuels: list[str] | None,
) -> Graph:
    """Build a graph of TwinShip fuel consumption relationships.

    Args:
        subject_uri: URI of the entity consuming fuel.
        fuels: List of fuel type codes.

    Returns:
        Graph containing fuel consumption triples.
    """
    g = Graph()
    if not fuels:
        return g

    for fuel_type in fuels:
        fuel_uri = get_twinship_fuel_uri(fuel_type)
        if fuel_uri:
            g.add((fuel_uri, RDF.type, TWINSHIP.Fuel))
            g.add((fuel_uri, RDFS.label, Literal(fuel_type)))
            g.add((subject_uri, TWINSHIP.consume, fuel_uri))

    return g
