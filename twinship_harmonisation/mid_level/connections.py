"""Mid-level functions for connecting TwinShip components."""

from rdflib import Graph, URIRef

from twinship_harmonisation.low_level import add_direct_connection


def connect_twinship_components(
    data: dict,
    component_uris: dict[str, URIRef],
) -> Graph:
    """Create all directlyConnectedTo relationships between components.

    Handles:
    - Main engine -> Gearbox connections
    - Gearbox -> Propeller connections
    - PMS connections to auxiliary engines, emergency generators,
      thrusters, and shaft generators

    Args:
        data: Vessel data dictionary containing component lists with relationship IDs.
        component_uris: Mapping of component IDs to their URIs.

    Returns:
        Graph containing all connection triples.
    """
    g = Graph()

    # Main Engine -> Gearbox connections
    for engine in data.get("main_engines", []):
        gearbox_id = engine.get("gearbox_id")
        if gearbox_id and engine["id"] in component_uris and gearbox_id in component_uris:
            add_direct_connection(g, component_uris[engine["id"]], component_uris[gearbox_id])

    # Gearbox -> Propeller connections
    for gearbox in data.get("gearboxes", []):
        propeller_id = gearbox.get("propeller_id")
        if propeller_id and gearbox["id"] in component_uris and propeller_id in component_uris:
            add_direct_connection(g, component_uris[gearbox["id"]], component_uris[propeller_id])

    # PMS connections
    for pms in data.get("pms", []):
        pms_id = pms["id"]
        if pms_id not in component_uris:
            continue
        pms_uri = component_uris[pms_id]

        # Connect auxiliary engines to PMS
        for aux_engine in data.get("auxiliary_engines", []):
            if aux_engine["id"] in component_uris:
                add_direct_connection(g, component_uris[aux_engine["id"]], pms_uri)

        # Connect emergency generators to PMS
        for eg in data.get("emergency_generators", []):
            if eg["id"] in component_uris:
                add_direct_connection(g, component_uris[eg["id"]], pms_uri)

        # Connect thrusters to PMS
        for thruster in data.get("thrusters", []):
            if thruster["id"] in component_uris:
                add_direct_connection(g, component_uris[thruster["id"]], pms_uri)

        # Connect shaft generators to PMS
        for sg in data.get("shaft_generators", []):
            if sg["id"] in component_uris:
                add_direct_connection(g, component_uris[sg["id"]], pms_uri)

    return g
