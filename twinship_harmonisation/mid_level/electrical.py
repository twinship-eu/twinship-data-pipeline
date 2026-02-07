"""Mid-level functions for creating TwinShip electrical systems.

Each function builds a graph for electrical components and returns it.
Parameter names match JSON keys so callers can unpack with **kwargs.
"""

from rdflib import Graph, URIRef

from twinship_harmonisation.low_level import (
    build_twinship_direct_connection,
    build_twinship_fuel_consumption,
    create_twinship_boiler,
    create_twinship_emergency_generator,
    create_twinship_pms,
    create_twinship_shaft_generator,
    create_twinship_thruster,
    create_twinship_uri,
)


def build_twinship_pms(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    auxiliary_engine_ids: list[str] | None = None,
    emergency_generator_ids: list[str] | None = None,
    thruster_ids: list[str] | None = None,
    shaft_generator_ids: list[str] | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single PMS with connections to all listed components.

    The orchestrator collects component IDs from the vessel data and passes
    them here so the PMS can establish directlyConnectedTo relationships.

    Args:
        namespace: Namespace for URI generation.
        vessel_uri: URI of the parent vessel.
        id: PMS identifier (maps to pms_id in low-level function).
        name: Human-readable label.
        types: RDF type names to add.
        auxiliary_engine_ids: IDs of auxiliary engines to connect to this PMS.
        emergency_generator_ids: IDs of emergency generators to connect.
        thruster_ids: IDs of thrusters to connect.
        shaft_generator_ids: IDs of shaft generators to connect.
        vessel_id: Accepted from JSON for **kwargs compatibility, unused.

    Returns:
        Graph containing all triples for this PMS and its connections.
    """
    # Create the PMS triples (type assertions, partOf)
    pms_uri, g = create_twinship_pms(
        namespace=namespace,
        pms_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
    )

    # Connect auxiliary engines to PMS (bidirectional directlyConnectedTo)
    for auxiliary_engine_id in auxiliary_engine_ids or []:
        g += build_twinship_direct_connection(
            create_twinship_uri(auxiliary_engine_id, namespace), pms_uri
        )

    # Connect emergency generators to PMS
    for emergency_generator_id in emergency_generator_ids or []:
        g += build_twinship_direct_connection(
            create_twinship_uri(emergency_generator_id, namespace), pms_uri
        )

    # Connect thrusters to PMS
    for thruster_id in thruster_ids or []:
        g += build_twinship_direct_connection(
            create_twinship_uri(thruster_id, namespace), pms_uri
        )

    # Connect shaft generators to PMS
    for shaft_generator_id in shaft_generator_ids or []:
        g += build_twinship_direct_connection(
            create_twinship_uri(shaft_generator_id, namespace), pms_uri
        )

    return g


def twinship_emergency_generators_graph(
    namespace: str,
    vessel_uri: URIRef,
    emergency_generators: list[dict] | None,
) -> Graph:
    """Build a combined graph for all emergency generators."""
    g = Graph()
    for eg in emergency_generators or []:
        _uri, eg_graph = create_twinship_emergency_generator(
            namespace=namespace,
            emergency_generator_id=eg["id"],
            vessel_uri=vessel_uri,
            label=eg.get("name"),
            types=eg.get("types"),
            power_max_kw=eg.get("power_max_kw"),
            speed_max_rpm=eg.get("speed_max_rpm"),
            do_mode=eg.get("do_mode"),
        )
        g += eg_graph
    return g


def twinship_thrusters_graph(
    namespace: str,
    vessel_uri: URIRef,
    thrusters: list[dict] | None,
) -> Graph:
    """Build a combined graph for all thrusters."""
    g = Graph()
    for thruster in thrusters or []:
        _uri, thruster_graph = create_twinship_thruster(
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
    return g


def twinship_shaft_generators_graph(
    namespace: str,
    vessel_uri: URIRef,
    shaft_generators: list[dict] | None,
) -> Graph:
    """Build a combined graph for all shaft generators."""
    g = Graph()
    for sg in shaft_generators or []:
        _uri, sg_graph = create_twinship_shaft_generator(
            namespace=namespace,
            shaft_generator_id=sg["id"],
            vessel_uri=vessel_uri,
            label=sg.get("name"),
            types=sg.get("types"),
            power_max_kw=sg.get("power_max_kw"),
            speed_max_rpm=sg.get("speed_max_rpm"),
        )
        g += sg_graph
    return g


def build_twinship_boiler(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    power_max_kw: float | None = None,
    speed_max_rpm: float | None = None,
    fuels: list[str] | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single boiler.

    Also includes fuel consumption triples.

    Args:
        namespace: Namespace for URI generation.
        vessel_uri: URI of the parent vessel.
        id: Boiler identifier.
        name: Human-readable label.
        types: RDF type names to add.
        fuels: Fuel type names for consumption triples.
        vessel_id: Accepted from JSON for **kwargs compatibility, unused.

    Returns:
        Graph containing all triples for this boiler.
    """
    # Create the boiler triples
    boiler_uri, g = create_twinship_boiler(
        namespace=namespace,
        boiler_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        power_max_kw=power_max_kw,
        speed_max_rpm=speed_max_rpm,
    )

    # Add fuel consumption relationships
    g += build_twinship_fuel_consumption(boiler_uri, fuels)

    return g
