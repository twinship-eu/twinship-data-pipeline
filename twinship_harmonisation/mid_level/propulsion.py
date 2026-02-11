"""Mid-level functions for creating TwinShip propulsion systems.

Each function builds a graph for propulsion components and returns it.
Parameter names match JSON keys so callers can unpack with **kwargs.
"""

from rdflib import Graph, URIRef

from twinship_harmonisation.low_level import (
    build_twinship_direct_connection,
    create_twinship_gearbox,
    create_twinship_propeller,
    create_twinship_uri,
)


def build_twinship_gearbox(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    ratio: str | None = None,
    efficiency: float | None = None,
    shaft_generator: str | None = None,
    propeller_id: str | None = None,
    vessel_id: str | None = None,
    engine_id: str | None = None,
) -> Graph:
    """Build a graph for a single gearbox.

    Also includes gearbox -> propeller connection when propeller_id is present.

    Args:
        namespace: Namespace for URI generation.
        vessel_uri: URI of the parent vessel.
        id: Gearbox identifier (maps to gearbox_id in low-level function).
        name: Human-readable label.
        types: RDF type names to add (e.g. ["Reduction"]).
        propeller_id: If set, creates gearbox -> propeller connection.
        vessel_id: Accepted from JSON for **kwargs compatibility, unused.
        engine_id: Accepted from JSON for **kwargs compatibility, unused.

    Returns:
        Graph containing all triples for this gearbox.
    """
    # Create the gearbox triples (type assertions, data properties, partOf)
    gearbox_uri, g = create_twinship_gearbox(
        namespace=namespace,
        gearbox_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        ratio=ratio,
        efficiency=efficiency,
        shaft_generator=shaft_generator,
    )

    # Connect gearbox to its propeller if specified
    if propeller_id:
        g += build_twinship_direct_connection(
            gearbox_uri, create_twinship_uri(propeller_id, namespace)
        )

    return g


def twinship_propellers_graph(
    namespace: str,
    vessel_uri: URIRef,
    propellers: list[dict] | None,
) -> Graph:
    """Build a combined graph for all propellers."""
    g = Graph()
    for propeller in propellers or []:
        _uri, propeller_graph = create_twinship_propeller(
            namespace=namespace,
            propeller_id=propeller["id"],
            vessel_uri=vessel_uri,
            label=propeller.get("name"),
            types=propeller.get("types"),
            diameter_mm=propeller.get("diameter_mm"),
            blades=propeller.get("blades"),
            pitch_diameter_ratio=propeller.get("pitch_diameter_ratio"),
            pitch_max_percentage=propeller.get("pitch_max_percentage"),
            expanded_area_ratio_percentage=propeller.get("expanded_area_ratio_percentage"),
            hub_ratio=propeller.get("hub_ratio"),
            skew_angle_degree=propeller.get("skew_angle_degree"),
            efficiency=propeller.get("efficiency"),
            rudder_angle_degree=propeller.get("rudder_angle_degree"),
        )
        g += propeller_graph
    return g
