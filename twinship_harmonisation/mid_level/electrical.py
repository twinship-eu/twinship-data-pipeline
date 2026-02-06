"""Mid-level functions for creating TwinShip electrical systems.

Each function handles a single electrical component and adds it to the
graph in place. Parameter names match JSON keys so callers can unpack
with **kwargs.
"""

from rdflib import Graph, URIRef

from twinship_harmonisation.low_level import (
    add_twinship_direct_connection,
    add_twinship_fuel_consumption,
    create_twinship_boiler,
    create_twinship_emergency_generator,
    create_twinship_pms,
    create_twinship_shaft_generator,
    create_twinship_thruster,
    create_twinship_uri,
)


def add_twinship_pms(
    g: Graph,
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
) -> None:
    """Create a single PMS and connect all listed components to it.

    The orchestrator collects component IDs from the vessel data and passes
    them here so the PMS can establish directlyConnectedTo relationships.

    Args:
        g: Graph to add triples to (modified in place).
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
    """
    # Create the PMS triples (type assertions, partOf)
    pms_uri, pms_graph = create_twinship_pms(
        namespace=namespace,
        pms_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
    )
    g += pms_graph

    # Connect auxiliary engines to PMS (bidirectional directlyConnectedTo)
    for auxiliary_engine_id in auxiliary_engine_ids or []:
        add_twinship_direct_connection(
            g, create_twinship_uri(auxiliary_engine_id, namespace), pms_uri
        )

    # Connect emergency generators to PMS
    for emergency_generator_id in emergency_generator_ids or []:
        add_twinship_direct_connection(
            g, create_twinship_uri(emergency_generator_id, namespace), pms_uri
        )

    # Connect thrusters to PMS
    for thruster_id in thruster_ids or []:
        add_twinship_direct_connection(
            g, create_twinship_uri(thruster_id, namespace), pms_uri
        )

    # Connect shaft generators to PMS
    for shaft_generator_id in shaft_generator_ids or []:
        add_twinship_direct_connection(
            g, create_twinship_uri(shaft_generator_id, namespace), pms_uri
        )


def add_twinship_emergency_generator(
    g: Graph,
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    power_max_kw: float | None = None,
    speed_max_rpm: float | None = None,
    do_mode: str | None = None,
    vessel_id: str | None = None,
) -> None:
    """Create a single emergency generator and add it to the graph.

    Args:
        g: Graph to add triples to (modified in place).
        namespace: Namespace for URI generation.
        vessel_uri: URI of the parent vessel.
        id: Emergency generator identifier.
        name: Human-readable label.
        types: RDF type names to add.
        vessel_id: Accepted from JSON for **kwargs compatibility, unused.
    """
    _emergency_generator_uri, emergency_generator_graph = (
        create_twinship_emergency_generator(
            namespace=namespace,
            emergency_generator_id=id,
            vessel_uri=vessel_uri,
            label=name,
            types=types,
            power_max_kw=power_max_kw,
            speed_max_rpm=speed_max_rpm,
            do_mode=do_mode,
        )
    )
    g += emergency_generator_graph


def add_twinship_thruster(
    g: Graph,
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    power_max_kw: float | None = None,
    speed_max_rpm: float | None = None,
    is_bow: bool = True,
    vessel_id: str | None = None,
) -> None:
    """Create a single thruster and add it to the graph.

    Args:
        g: Graph to add triples to (modified in place).
        namespace: Namespace for URI generation.
        vessel_uri: URI of the parent vessel.
        id: Thruster identifier.
        name: Human-readable label.
        types: RDF type names to add.
        vessel_id: Accepted from JSON for **kwargs compatibility, unused.
    """
    _thruster_uri, thruster_graph = create_twinship_thruster(
        namespace=namespace,
        thruster_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        power_max_kw=power_max_kw,
        speed_max_rpm=speed_max_rpm,
        is_bow=is_bow,
    )
    g += thruster_graph


def add_twinship_shaft_generator(
    g: Graph,
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    power_max_kw: float | None = None,
    speed_max_rpm: float | None = None,
    vessel_id: str | None = None,
) -> None:
    """Create a single shaft generator and add it to the graph.

    Args:
        g: Graph to add triples to (modified in place).
        namespace: Namespace for URI generation.
        vessel_uri: URI of the parent vessel.
        id: Shaft generator identifier.
        name: Human-readable label.
        types: RDF type names to add.
        vessel_id: Accepted from JSON for **kwargs compatibility, unused.
    """
    _shaft_generator_uri, shaft_generator_graph = create_twinship_shaft_generator(
        namespace=namespace,
        shaft_generator_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        power_max_kw=power_max_kw,
        speed_max_rpm=speed_max_rpm,
    )
    g += shaft_generator_graph


def add_twinship_boiler(
    g: Graph,
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
) -> None:
    """Create a single boiler and add it to the graph.

    Also adds fuel consumption triples.

    Args:
        g: Graph to add triples to (modified in place).
        namespace: Namespace for URI generation.
        vessel_uri: URI of the parent vessel.
        id: Boiler identifier.
        name: Human-readable label.
        types: RDF type names to add.
        fuels: Fuel type names for consumption triples.
        vessel_id: Accepted from JSON for **kwargs compatibility, unused.
    """
    # Create the boiler triples
    boiler_uri, boiler_graph = create_twinship_boiler(
        namespace=namespace,
        boiler_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        power_max_kw=power_max_kw,
        speed_max_rpm=speed_max_rpm,
    )
    g += boiler_graph

    # Add fuel consumption relationships
    add_twinship_fuel_consumption(g, boiler_uri, fuels)
