"""Mid-level functions for creating TwinShip propulsion systems."""

from rdflib import Graph, URIRef

from twinship_harmonisation.low_level import (
    create_gearbox,
    create_propeller,
)


def create_twinship_propulsion_system(
    data: dict,
    vessel_uri: URIRef,
    namespace: str,
) -> tuple[dict[str, URIRef], Graph]:
    """Create propulsion system components (gearboxes and propellers).

    Args:
        data: Vessel data dictionary containing 'gearboxes' and 'propellers' lists.
        vessel_uri: URI of the parent vessel.
        namespace: Namespace for URI generation.

    Returns:
        Tuple of (component_uris dict, combined graph).
    """
    g = Graph()
    component_uris: dict[str, URIRef] = {}

    # Create gearboxes
    for gearbox in data.get("gearboxes", []):
        gearbox_uri, gearbox_graph = create_gearbox(
            namespace=namespace,
            gearbox_id=gearbox["id"],
            vessel_uri=vessel_uri,
            label=gearbox.get("name"),
            types=gearbox.get("types"),
            ratio=gearbox.get("ratio"),
            efficiency=gearbox.get("efficiency"),
            shaft_generator=gearbox.get("shaft_generator"),
        )
        g += gearbox_graph
        component_uris[gearbox["id"]] = gearbox_uri

    # Create propellers
    for propeller in data.get("propellers", []):
        propeller_uri, propeller_graph = create_propeller(
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
        component_uris[propeller["id"]] = propeller_uri

    return component_uris, g
