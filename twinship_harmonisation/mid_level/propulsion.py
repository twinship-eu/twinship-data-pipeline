"""Mid-level functions for creating TwinShip propulsion systems.

Each function handles a single propulsion component and adds it to the
graph in place. Parameter names match JSON keys so callers can unpack
with **gearbox or **propeller.
"""

from rdflib import Graph, URIRef

from twinship_harmonisation.low_level import (
    add_twinship_direct_connection,
    create_twinship_gearbox,
    create_twinship_propeller,
    create_twinship_uri,
)


def add_twinship_gearbox(
    g: Graph,
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
) -> None:
    """Create a single gearbox and add it to the graph.

    Also adds gearbox -> propeller connection when propeller_id is present.

    Args:
        g: Graph to add triples to (modified in place).
        namespace: Namespace for URI generation.
        vessel_uri: URI of the parent vessel.
        id: Gearbox identifier (maps to gearbox_id in low-level function).
        name: Human-readable label.
        types: RDF type names to add (e.g. ["Reduction"]).
        propeller_id: If set, creates gearbox -> propeller connection.
        vessel_id: Accepted from JSON for **kwargs compatibility, unused.
        engine_id: Accepted from JSON for **kwargs compatibility, unused.
    """
    # Create the gearbox triples (type assertions, data properties, partOf)
    gearbox_uri, gearbox_graph = create_twinship_gearbox(
        namespace=namespace,
        gearbox_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        ratio=ratio,
        efficiency=efficiency,
        shaft_generator=shaft_generator,
    )
    g += gearbox_graph

    # Connect gearbox to its propeller if specified
    if propeller_id:
        add_twinship_direct_connection(
            g, gearbox_uri, create_twinship_uri(propeller_id, namespace)
        )


def add_twinship_propeller(
    g: Graph,
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
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
    vessel_id: str | None = None,
    gearbox_id: str | None = None,
) -> None:
    """Create a single propeller and add it to the graph.

    Args:
        g: Graph to add triples to (modified in place).
        namespace: Namespace for URI generation.
        vessel_uri: URI of the parent vessel.
        id: Propeller identifier (maps to propeller_id in low-level function).
        name: Human-readable label.
        types: RDF type names to add (e.g. ["CPP"]).
        vessel_id: Accepted from JSON for **kwargs compatibility, unused.
        gearbox_id: Accepted from JSON for **kwargs compatibility, unused.
    """
    # Create the propeller triples (type assertions, data properties, partOf)
    _propeller_uri, propeller_graph = create_twinship_propeller(
        namespace=namespace,
        propeller_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        diameter_mm=diameter_mm,
        blades=blades,
        pitch_diameter_ratio=pitch_diameter_ratio,
        pitch_max_percentage=pitch_max_percentage,
        expanded_area_ratio_percentage=expanded_area_ratio_percentage,
        hub_ratio=hub_ratio,
        skew_angle_degree=skew_angle_degree,
        efficiency=efficiency,
        rudder_angle_degree=rudder_angle_degree,
    )
    g += propeller_graph
