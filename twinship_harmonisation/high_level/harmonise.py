"""High-level TwinShip harmonisation functions.

This module provides the main entry points for data scientists to convert
vessel data into TwinShip-compliant RDF graphs. Parameter names match JSON
keys so callers can unpack with **data.
"""

import json
from pathlib import Path

from rdflib import Graph

from twinship_harmonisation.high_level.components import (
    twinship_auxiliary_engines_graph,
    twinship_boilers_graph,
    twinship_gearboxes_graph,
    twinship_main_engines_graph,
    twinship_pms_graph,
)
from twinship_harmonisation.low_level import create_twinship_vessel
from twinship_harmonisation.mid_level import (
    twinship_emergency_generators_graph,
    twinship_propellers_graph,
    twinship_shaft_generators_graph,
    twinship_thrusters_graph,
)
from twinship_harmonisation.utils import bind_namespaces


def harmonise_twinship_vessel(
    *,
    namespace: str,
    vessel: dict,
    main_engines: list[dict] | None = None,
    auxiliary_engines: list[dict] | None = None,
    gearboxes: list[dict] | None = None,
    propellers: list[dict] | None = None,
    pms: list[dict] | None = None,
    emergency_generators: list[dict] | None = None,
    thrusters: list[dict] | None = None,
    shaft_generators: list[dict] | None = None,
    boilers: list[dict] | None = None,
) -> Graph:
    """Harmonise vessel data into TwinShip RDF triples.

    This is the main entry point for converting extracted vessel data
    into TwinShip-compliant RDF. Parameter names match JSON keys so
    callers can unpack with ``harmonise_twinship_vessel(**data)``.

    Args:
        namespace: Namespace for URI generation (e.g. "grimaldi").
        vessel: Vessel metadata dict with keys: id, label, type, etc.
        main_engines: List of main engine dicts.
        auxiliary_engines: List of auxiliary engine dicts.
        gearboxes: List of gearbox dicts.
        propellers: List of propeller dicts.
        pms: List of PMS dicts.
        emergency_generators: List of emergency generator dicts.
        thrusters: List of thruster dicts.
        shaft_generators: List of shaft generator dicts.
        boilers: List of boiler dicts.

    Returns:
        RDFLib Graph with all vessel data and namespace bindings.
    """
    vessel_uri, g = create_twinship_vessel(
        namespace=namespace,
        vessel_id=vessel["id"],
        label=vessel.get("label"),
        vessel_type=vessel.get("type"),
        displacement_max_mt=vessel.get("displacement_max_mt"),
        draft_aft_max_m=vessel.get("draft_aft_max_m"),
        draft_for_max_m=vessel.get("draft_for_max_m"),
        draft_mid_port_max_m=vessel.get("draft_mid_port_max_m"),
        draft_mid_stbd_max_m=vessel.get("draft_mid_stbd_max_m"),
        depth_of_water_max_m=vessel.get("depth_of_water_max_m"),
    )

    # Build graphs for each component type and combine
    g += twinship_main_engines_graph(namespace, vessel_uri, main_engines)
    g += twinship_auxiliary_engines_graph(namespace, vessel_uri, auxiliary_engines)
    g += twinship_gearboxes_graph(namespace, vessel_uri, gearboxes)
    g += twinship_propellers_graph(namespace, vessel_uri, propellers)
    g += twinship_thrusters_graph(namespace, vessel_uri, thrusters)
    g += twinship_shaft_generators_graph(namespace, vessel_uri, shaft_generators)
    g += twinship_boilers_graph(namespace, vessel_uri, boilers)
    g += twinship_emergency_generators_graph(namespace, vessel_uri, emergency_generators)
    g += twinship_pms_graph(
        namespace,
        vessel_uri,
        pms,
        auxiliary_engine_ids=[e["id"] for e in auxiliary_engines or []],
        emergency_generator_ids=[e["id"] for e in emergency_generators or []],
        thruster_ids=[t["id"] for t in thrusters or []],
        shaft_generator_ids=[s["id"] for s in shaft_generators or []],
    )

    return bind_namespaces(g)


def harmonise_twinship_vessel_file(json_path: str | Path) -> Graph:
    """Harmonise vessel data from a JSON file into TwinShip RDF triples.

    Args:
        json_path: Path to JSON file containing vessel data.

    Returns:
        RDFLib Graph with all vessel data and namespace bindings.
    """
    with open(json_path) as f:
        data = json.load(f)

    return harmonise_twinship_vessel(**data)


def harmonise_all_twinship_vessels(data_dir: str | Path) -> Graph:
    """Harmonise all vessel JSON files in a directory.

    Args:
        data_dir: Directory containing vessel JSON files.

    Returns:
        Combined RDFLib Graph with all vessels.
    """
    g = Graph()
    data_path = Path(data_dir)

    for json_file in data_path.glob("*.json"):
        g += harmonise_twinship_vessel_file(json_file)

    return bind_namespaces(g)
