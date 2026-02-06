"""High-level TwinShip harmonisation functions.

This module provides the main entry points for data scientists to convert
vessel data into TwinShip-compliant RDF graphs. Parameter names match JSON
keys so callers can unpack with **data.
"""

import json
from pathlib import Path

from rdflib import Graph

from twinship_harmonisation.low_level import create_twinship_vessel
from twinship_harmonisation.mid_level import (
    add_twinship_auxiliary_engine,
    add_twinship_boiler,
    add_twinship_emergency_generator,
    add_twinship_gearbox,
    add_twinship_main_engine,
    add_twinship_pms,
    add_twinship_propeller,
    add_twinship_shaft_generator,
    add_twinship_thruster,
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
    g = Graph()

    # --- Vessel ---
    vessel_uri, vessel_graph = create_twinship_vessel(
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
    g += vessel_graph

    # --- Engines ---
    for engine in main_engines or []:
        add_twinship_main_engine(
            g, namespace=namespace, vessel_uri=vessel_uri, **engine
        )

    for engine in auxiliary_engines or []:
        add_twinship_auxiliary_engine(
            g, namespace=namespace, vessel_uri=vessel_uri, **engine
        )

    # --- Propulsion ---
    for gearbox in gearboxes or []:
        add_twinship_gearbox(
            g, namespace=namespace, vessel_uri=vessel_uri, **gearbox
        )

    for propeller in propellers or []:
        add_twinship_propeller(
            g, namespace=namespace, vessel_uri=vessel_uri, **propeller
        )

    # --- Power Management System ---
    # Collect component IDs so each PMS can establish connections to them
    auxiliary_engine_ids = [
        auxiliary_engine["id"] for auxiliary_engine in auxiliary_engines or []
    ]
    emergency_generator_ids = [
        emergency_generator["id"]
        for emergency_generator in emergency_generators or []
    ]
    thruster_ids = [thruster["id"] for thruster in thrusters or []]
    shaft_generator_ids = [
        shaft_generator["id"] for shaft_generator in shaft_generators or []
    ]

    for power_management_system in pms or []:
        add_twinship_pms(
            g,
            namespace=namespace,
            vessel_uri=vessel_uri,
            auxiliary_engine_ids=auxiliary_engine_ids,
            emergency_generator_ids=emergency_generator_ids,
            thruster_ids=thruster_ids,
            shaft_generator_ids=shaft_generator_ids,
            **power_management_system,
        )

    # --- Other electrical components ---
    for emergency_generator in emergency_generators or []:
        add_twinship_emergency_generator(
            g, namespace=namespace, vessel_uri=vessel_uri, **emergency_generator
        )

    for thruster in thrusters or []:
        add_twinship_thruster(
            g, namespace=namespace, vessel_uri=vessel_uri, **thruster
        )

    for shaft_generator in shaft_generators or []:
        add_twinship_shaft_generator(
            g, namespace=namespace, vessel_uri=vessel_uri, **shaft_generator
        )

    for boiler in boilers or []:
        add_twinship_boiler(
            g, namespace=namespace, vessel_uri=vessel_uri, **boiler
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