"""Mid-level functions for creating TwinShip electrical systems."""

from rdflib import Graph, URIRef

from twinship_harmonisation.low_level import (
    create_boiler,
    create_emergency_generator,
    create_pms,
    create_shaft_generator,
    create_thruster,
)


def create_twinship_electrical_system(
    data: dict,
    vessel_uri: URIRef,
    namespace: str,
) -> tuple[dict[str, URIRef], Graph]:
    """Create electrical system components.

    Includes: PMS, emergency generators, thrusters, shaft generators, and boilers.

    Args:
        data: Vessel data dictionary containing component lists.
        vessel_uri: URI of the parent vessel.
        namespace: Namespace for URI generation.

    Returns:
        Tuple of (component_uris dict, combined graph).
    """
    g = Graph()
    component_uris: dict[str, URIRef] = {}

    # Create PMS (Power Management Systems)
    for pms in data.get("pms", []):
        pms_uri, pms_graph = create_pms(
            namespace=namespace,
            pms_id=pms["id"],
            vessel_uri=vessel_uri,
            label=pms.get("name"),
            types=pms.get("types"),
        )
        g += pms_graph
        component_uris[pms["id"]] = pms_uri

    # Create emergency generators
    for eg in data.get("emergency_generators", []):
        eg_uri, eg_graph = create_emergency_generator(
            namespace=namespace,
            eg_id=eg["id"],
            vessel_uri=vessel_uri,
            label=eg.get("name"),
            types=eg.get("types"),
            power_max_kw=eg.get("power_max_kw"),
            speed_max_rpm=eg.get("speed_max_rpm"),
            do_mode=eg.get("do_mode"),
        )
        g += eg_graph
        component_uris[eg["id"]] = eg_uri

    # Create thrusters
    for thruster in data.get("thrusters", []):
        thruster_uri, thruster_graph = create_thruster(
            namespace=namespace,
            thruster_id=thruster["id"],
            vessel_uri=vessel_uri,
            label=thruster.get("name"),
            types=thruster.get("types"),
            power_max_kw=thruster.get("power_max_kw"),
            speed_max_rpm=thruster.get("speed_max_rpm"),
            is_bow=thruster.get("is_bow", True),
        )
        g += thruster_graph
        component_uris[thruster["id"]] = thruster_uri

    # Create shaft generators
    for sg in data.get("shaft_generators", []):
        sg_uri, sg_graph = create_shaft_generator(
            namespace=namespace,
            sg_id=sg["id"],
            vessel_uri=vessel_uri,
            label=sg.get("name"),
            types=sg.get("types"),
            power_max_kw=sg.get("power_max_kw"),
            speed_max_rpm=sg.get("speed_max_rpm"),
        )
        g += sg_graph
        component_uris[sg["id"]] = sg_uri

    # Create boilers
    for boiler in data.get("boilers", []):
        boiler_uri, boiler_graph = create_boiler(
            namespace=namespace,
            boiler_id=boiler["id"],
            vessel_uri=vessel_uri,
            label=boiler.get("name"),
            types=boiler.get("types"),
            power_max_kw=boiler.get("power_max_kw"),
            speed_max_rpm=boiler.get("speed_max_rpm"),
        )
        g += boiler_graph
        component_uris[boiler["id"]] = boiler_uri

    return component_uris, g
