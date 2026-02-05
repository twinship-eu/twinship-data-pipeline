"""High-level TwinShip harmonisation functions.

This module provides the main entry points for data scientists to convert
vessel data into TwinShip-compliant RDF graphs.
"""

import json
from pathlib import Path

from rdflib import Graph

from twinship_harmonisation.low_level import create_vessel
from twinship_harmonisation.mid_level import (
    connect_twinship_components,
    create_twinship_auxiliary_engines,
    create_twinship_electrical_system,
    create_twinship_main_engines,
    create_twinship_propulsion_system,
)
from twinship_harmonisation.utils import bind_namespaces


def harmonise_twinship_vessel(data: dict) -> Graph:
    """Harmonise vessel data dictionary into TwinShip RDF triples.

    This is the main entry point for converting extracted vessel data
    into TwinShip-compliant RDF.

    Args:
        data: Dictionary containing vessel data with structure:
            {
                "namespace": "grimaldi",
                "operator": "Grimaldi",
                "vessel": {"id": "...", "label": "...", "type": "...", ...},
                "main_engines": [...],
                "auxiliary_engines": [...],
                "propellers": [...],
                "gearboxes": [...],
                "boilers": [...],
                "pms": [...],
                "emergency_generators": [...],
                "thrusters": [...],
                "shaft_generators": [...]
            }

    Returns:
        RDFLib Graph with all vessel data and namespace bindings.
    """
    g = Graph()
    namespace = data["namespace"]
    vessel_data = data["vessel"]
    components: dict[str, object] = {}

    # Create vessel
    vessel_uri, vessel_graph = create_vessel(
        namespace=namespace,
        vessel_id=vessel_data["id"],
        label=vessel_data.get("label"),
        vessel_type=vessel_data.get("type"),
        displacement_max_mt=vessel_data.get("displacement_max_mt"),
        draft_aft_max_m=vessel_data.get("draft_aft_max_m"),
        draft_for_max_m=vessel_data.get("draft_for_max_m"),
        draft_mid_port_max_m=vessel_data.get("draft_mid_port_max_m"),
        draft_mid_stbd_max_m=vessel_data.get("draft_mid_stbd_max_m"),
        depth_of_water_max_m=vessel_data.get("depth_of_water_max_m"),
    )
    g += vessel_graph
    components[vessel_data["id"]] = vessel_uri

    # Create main engines
    engine_uris, engine_graph = create_twinship_main_engines(data, vessel_uri, namespace)
    g += engine_graph
    components.update(engine_uris)

    # Create auxiliary engines
    aux_uris, aux_graph = create_twinship_auxiliary_engines(data, vessel_uri, namespace)
    g += aux_graph
    components.update(aux_uris)

    # Create propulsion system (gearboxes, propellers)
    prop_uris, prop_graph = create_twinship_propulsion_system(data, vessel_uri, namespace)
    g += prop_graph
    components.update(prop_uris)

    # Create electrical system (PMS, emergency generators, thrusters, shaft generators, boilers)
    elec_uris, elec_graph = create_twinship_electrical_system(data, vessel_uri, namespace)
    g += elec_graph
    components.update(elec_uris)

    # Connect components
    g += connect_twinship_components(data, components)

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

    return harmonise_twinship_vessel(data)


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


# Backwards compatibility aliases
harmonise_vessel_data = harmonise_twinship_vessel
harmonise_vessel_file = harmonise_twinship_vessel_file
harmonise_all_vessels = harmonise_all_twinship_vessels
