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


def add_twinship_fuel_consumption(
    g: Graph,
    subject_uri: URIRef,
    fuels: list[str] | None,
) -> None:
    """Add TwinShip fuel consumption relationships to a graph.

    Args:
        g: Graph to add triples to.
        subject_uri: URI of the entity consuming fuel.
        fuels: List of fuel type codes.
    """
    if not fuels:
        return

    for fuel_type in fuels:
        fuel_uri = get_twinship_fuel_uri(fuel_type)
        if fuel_uri:
            g.add((fuel_uri, RDF.type, TWINSHIP.Fuel))
            g.add((fuel_uri, RDFS.label, Literal(fuel_type)))
            g.add((subject_uri, TWINSHIP.consume, fuel_uri))
