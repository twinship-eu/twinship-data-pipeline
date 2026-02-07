"""High-level graph builders for each TwinShip component type.

Each function takes a list of component dicts and returns a single
combined Graph for that component type.
"""

from rdflib import Graph, URIRef

from twinship_harmonisation.mid_level import (
    build_twinship_auxiliary_engine,
    build_twinship_boiler,
    build_twinship_gearbox,
    build_twinship_main_engine,
    build_twinship_pms,
)


def twinship_main_engines_graph(
    namespace: str,
    vessel_uri: URIRef,
    main_engines: list[dict] | None,
) -> Graph:
    """Build a combined graph for all main engines."""
    g = Graph()
    for engine in main_engines or []:
        g += build_twinship_main_engine(
            namespace=namespace, vessel_uri=vessel_uri, **engine
        )
    return g


def twinship_auxiliary_engines_graph(
    namespace: str,
    vessel_uri: URIRef,
    auxiliary_engines: list[dict] | None,
) -> Graph:
    """Build a combined graph for all auxiliary engines."""
    g = Graph()
    for engine in auxiliary_engines or []:
        g += build_twinship_auxiliary_engine(
            namespace=namespace, vessel_uri=vessel_uri, **engine
        )
    return g


def twinship_gearboxes_graph(
    namespace: str,
    vessel_uri: URIRef,
    gearboxes: list[dict] | None,
) -> Graph:
    """Build a combined graph for all gearboxes."""
    g = Graph()
    for gearbox in gearboxes or []:
        g += build_twinship_gearbox(
            namespace=namespace, vessel_uri=vessel_uri, **gearbox
        )
    return g


def twinship_pms_graph(
    namespace: str,
    vessel_uri: URIRef,
    pms: list[dict] | None,
    auxiliary_engine_ids: list[str],
    emergency_generator_ids: list[str],
    thruster_ids: list[str],
    shaft_generator_ids: list[str],
) -> Graph:
    """Build a combined graph for all power management systems."""
    g = Graph()
    for power_management_system in pms or []:
        g += build_twinship_pms(
            namespace=namespace,
            vessel_uri=vessel_uri,
            auxiliary_engine_ids=auxiliary_engine_ids,
            emergency_generator_ids=emergency_generator_ids,
            thruster_ids=thruster_ids,
            shaft_generator_ids=shaft_generator_ids,
            **power_management_system,
        )
    return g


def twinship_boilers_graph(
    namespace: str,
    vessel_uri: URIRef,
    boilers: list[dict] | None,
) -> Graph:
    """Build a combined graph for all boilers."""
    g = Graph()
    for boiler in boilers or []:
        g += build_twinship_boiler(namespace=namespace, vessel_uri=vessel_uri, **boiler)
    return g
