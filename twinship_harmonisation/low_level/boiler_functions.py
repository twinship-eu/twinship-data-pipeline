"""Low-level functions for creating boiler-related TwinShip RDF triples."""

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from twinship_harmonisation.constants import IDO, TWINSHIP
from twinship_harmonisation.low_level.vessel_functions import (
    add_optional_double,
    create_twinship_uri,
    get_twinship_type_uri,
)


def create_twinship_boiler(
    namespace: str,
    boiler_id: str,
    vessel_uri: URIRef | None = None,
    label: str | None = None,
    types: list[str] | None = None,
    power_max_kw: float | None = None,
    speed_max_rpm: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for a boiler system.

    Returns:
        Tuple of (boiler_uri, graph).
    """
    g = Graph()
    boiler_uri = create_twinship_uri(boiler_id, namespace)

    # Type assertions
    g.add((boiler_uri, RDF.type, TWINSHIP.Boiler))
    if types:
        for type_name in types:
            type_uri = get_twinship_type_uri(type_name)
            if type_uri and type_uri != TWINSHIP.Boiler:  # Avoid duplicate
                g.add((boiler_uri, RDF.type, type_uri))

    # Relationship to vessel (if provided, using IDO partOf)
    if vessel_uri:
        g.add((boiler_uri, IDO.partOf, vessel_uri))

    # Label
    if label:
        g.add((boiler_uri, RDFS.label, Literal(label)))

    # Data properties
    add_optional_double(g, boiler_uri, TWINSHIP.twBoilerPowerMaxInKW, power_max_kw)
    add_optional_double(g, boiler_uri, TWINSHIP.twBoilerSpeedMaxInRevPerMin, speed_max_rpm)

    return boiler_uri, g
