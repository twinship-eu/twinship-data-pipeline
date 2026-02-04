"""Low-level functions for creating gearbox-related RDF triples."""

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from twinship_harmonisation.constants import IDO, TWINSHIP
from twinship_harmonisation.low_level.vessel_functions import (
    add_optional_double,
    add_optional_string,
    create_uri,
    get_type_uri,
)


def create_gearbox(
    namespace: str,
    gearbox_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    ratio: str | None = None,
    efficiency: float | None = None,
    shaft_generator: str | None = None,
) -> tuple[URIRef, Graph]:
    """Create RDF triples for a gearbox system.

    Returns:
        Tuple of (gearbox_uri, graph).
    """
    g = Graph()
    gearbox_uri = create_uri(gearbox_id, namespace)

    # Type assertions - only use specific subtypes from spreadsheet
    if types:
        for type_name in types:
            type_uri = get_type_uri(type_name)
            if type_uri:
                g.add((gearbox_uri, RDF.type, type_uri))

    # Relationship to vessel (using IDO partOf)
    g.add((gearbox_uri, IDO.partOf, vessel_uri))

    # Label
    if label:
        g.add((gearbox_uri, RDFS.label, Literal(label)))

    # Data properties
    add_optional_string(g, gearbox_uri, TWINSHIP.twGearboxRatio, ratio)
    add_optional_double(g, gearbox_uri, TWINSHIP.twGearboxEfficiency, efficiency)

    # Shaft generator is YES/NO, convert to 1/0
    if shaft_generator:
        value = 1 if shaft_generator.upper() == "YES" else 0
        g.add((gearbox_uri, TWINSHIP.twGearboxShaftGenerator, Literal(value, datatype=XSD.integer)))

    return gearbox_uri, g
