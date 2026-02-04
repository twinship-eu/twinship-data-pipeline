"""Low-level functions for creating propeller-related RDF triples."""

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from twinship_harmonisation.constants import IDO, TWINSHIP
from twinship_harmonisation.low_level.vessel_functions import (
    add_optional_double,
    add_optional_integer,
    create_uri,
    get_type_uri,
)


def create_propeller(
    namespace: str,
    propeller_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    diameter_mm: float | None = None,
    blades: int | None = None,
    pitch_diameter_ratio: float | None = None,
    pitch_max_percentage: float | None = None,
    expanded_area_ratio_percentage: float | None = None,
    hub_ratio: float | None = None,
    skew_angle_degree: float | None = None,
    efficiency: float | None = None,
    rudder_angle_degree: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create RDF triples for a propeller system.

    Returns:
        Tuple of (propeller_uri, graph).
    """
    g = Graph()
    propeller_uri = create_uri(propeller_id, namespace)

    # Type assertions - only use specific subtypes from spreadsheet
    if types:
        for type_name in types:
            type_uri = get_type_uri(type_name)
            if type_uri:
                g.add((propeller_uri, RDF.type, type_uri))

    # Relationship to vessel (using IDO partOf)
    g.add((propeller_uri, IDO.partOf, vessel_uri))

    # Label
    if label:
        g.add((propeller_uri, RDFS.label, Literal(label)))

    # Data properties
    add_optional_double(g, propeller_uri, TWINSHIP.twPropellerDiameterMm, diameter_mm)
    add_optional_integer(g, propeller_uri, TWINSHIP.twPropellerBlades, blades)
    add_optional_double(
        g, propeller_uri, TWINSHIP.twPropellerPitchDiameterRatio, pitch_diameter_ratio
    )
    add_optional_double(
        g, propeller_uri, TWINSHIP.twPropellerPitchMaxInPercentage, pitch_max_percentage
    )
    add_optional_double(
        g,
        propeller_uri,
        TWINSHIP.twPropellerExpandedAreaRatioPercentage,
        expanded_area_ratio_percentage,
    )
    add_optional_double(g, propeller_uri, TWINSHIP.twPropellerHubRatio, hub_ratio)
    add_optional_double(g, propeller_uri, TWINSHIP.twPropellerSkewAngleDegree, skew_angle_degree)
    add_optional_double(g, propeller_uri, TWINSHIP.twPropellerEfficiency, efficiency)
    add_optional_double(g, propeller_uri, TWINSHIP.twRudderAngleDegree, rudder_angle_degree)

    return propeller_uri, g
