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
from twinship_harmonisation.high_level.futuristic_components import (
    twinship_als_graph,
    twinship_ammonia_fuel_cells_graph,
    twinship_auxiliary_loads_graph,
    twinship_bow_thrusters_graph,
    twinship_dc_bus_converters_graph,
    twinship_dynamic_wings_graph,
    twinship_electric_motor_shafts_graph,
    twinship_electric_motors_graph,
    twinship_ess_graph,
    twinship_frequency_converters_graph,
    twinship_gate_rudders_graph,
    twinship_gensets_graph,
    twinship_scrs_graph,
    twinship_shore_power_graph,
    twinship_wasps_graph,
)
from twinship_harmonisation.low_level import (
    build_twinship_connection,
    create_twinship_pms,
    create_twinship_uri,
    create_twinship_vessel,
)
from twinship_harmonisation.mid_level import (
    twinship_emergency_generators_graph,
    twinship_propellers_graph,
    twinship_provenance_graph,
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
    # Futuristic vessel components (all default to None for backwards compat)
    gensets: list[dict] | None = None,
    ess: list[dict] | None = None,
    dc_bus_converters: list[dict] | None = None,
    scrs: list[dict] | None = None,
    auxiliary_loads: list[dict] | None = None,
    shore_power: list[dict] | None = None,
    frequency_converters: list[dict] | None = None,
    electric_motors: list[dict] | None = None,
    electric_motor_shafts: list[dict] | None = None,
    gate_rudders: list[dict] | None = None,
    wasps: list[dict] | None = None,
    als: list[dict] | None = None,
    dynamic_wings: list[dict] | None = None,
    ammonia_fuel_cells: list[dict] | None = None,
    # PAV provenance metadata (optional)
    source_file: str | None = None,
    pipeline_version: str | None = None,
) -> Graph:
    """Harmonise vessel data into TwinShip RDF triples.

    This is the main entry point for converting extracted vessel data
    into TwinShip-compliant RDF. Parameter names match JSON keys so
    callers can unpack with ``harmonise_twinship_vessel(**data)``.

    Supports both conventional vessels (main_engines, gearboxes, etc.)
    and futuristic vessels (gensets, ess, electric_motors, etc.).
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

    # PAV provenance metadata
    g += twinship_provenance_graph(vessel_uri, source_file, pipeline_version)

    is_futuristic = bool(gensets)

    # Conventional component graphs
    g += twinship_main_engines_graph(namespace, vessel_uri, main_engines)
    g += twinship_auxiliary_engines_graph(namespace, vessel_uri, auxiliary_engines)
    g += twinship_gearboxes_graph(namespace, vessel_uri, gearboxes)
    g += twinship_propellers_graph(namespace, vessel_uri, propellers)
    g += twinship_shaft_generators_graph(namespace, vessel_uri, shaft_generators)
    g += twinship_boilers_graph(namespace, vessel_uri, boilers)
    g += twinship_emergency_generators_graph(namespace, vessel_uri, emergency_generators)

    if is_futuristic:
        # Futuristic: bow thrusters with connectedTo PMS
        g += twinship_bow_thrusters_graph(namespace, vessel_uri, thrusters)
    else:
        # Conventional: maneuvering thrusters with directlyConnectedTo PMS
        g += twinship_thrusters_graph(namespace, vessel_uri, thrusters)

    # Futuristic component graphs (all None for conventional vessels)
    g += twinship_gensets_graph(namespace, vessel_uri, gensets)
    g += twinship_ess_graph(namespace, vessel_uri, ess)
    g += twinship_dc_bus_converters_graph(namespace, vessel_uri, dc_bus_converters)
    g += twinship_scrs_graph(namespace, vessel_uri, scrs)
    g += twinship_auxiliary_loads_graph(namespace, vessel_uri, auxiliary_loads)
    g += twinship_shore_power_graph(namespace, vessel_uri, shore_power)
    g += twinship_frequency_converters_graph(namespace, vessel_uri, frequency_converters)
    g += twinship_electric_motors_graph(namespace, vessel_uri, electric_motors)
    g += twinship_electric_motor_shafts_graph(namespace, vessel_uri, electric_motor_shafts)
    g += twinship_gate_rudders_graph(namespace, vessel_uri, gate_rudders)
    g += twinship_wasps_graph(namespace, vessel_uri, wasps)
    g += twinship_als_graph(namespace, vessel_uri, als)
    g += twinship_dynamic_wings_graph(namespace, vessel_uri, dynamic_wings)
    g += twinship_ammonia_fuel_cells_graph(namespace, vessel_uri, ammonia_fuel_cells)

    # Futuristic propellers connect to PMS via connectedTo
    if is_futuristic:
        for prop in propellers or []:
            prop_pms_id = prop.get("pms_id")
            if prop_pms_id:
                g += build_twinship_connection(
                    create_twinship_uri(prop["id"], namespace),
                    create_twinship_uri(prop_pms_id, namespace),
                )

    # PMS connections: futuristic uses connectedTo, conventional uses directlyConnectedTo
    if gensets:
        # Futuristic PMS: connects to all component types via connectedTo
        g += _build_futuristic_pms_graph(
            namespace,
            vessel_uri,
            pms,
            gensets=gensets,
            dc_bus_converters=dc_bus_converters,
            scrs=scrs,
            auxiliary_loads=auxiliary_loads,
            shore_power=shore_power,
            frequency_converters=frequency_converters,
            gate_rudders=gate_rudders,
            thrusters=thrusters,
            wasps=wasps,
            als=als,
            dynamic_wings=dynamic_wings,
            ammonia_fuel_cells=ammonia_fuel_cells,
        )
    else:
        # Conventional PMS: connects via directlyConnectedTo
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


def _build_futuristic_pms_graph(
    namespace: str,
    vessel_uri,
    pms: list[dict] | None,
    *,
    gensets: list[dict] | None = None,
    dc_bus_converters: list[dict] | None = None,
    scrs: list[dict] | None = None,
    auxiliary_loads: list[dict] | None = None,
    shore_power: list[dict] | None = None,
    frequency_converters: list[dict] | None = None,
    gate_rudders: list[dict] | None = None,
    thrusters: list[dict] | None = None,
    wasps: list[dict] | None = None,
    als: list[dict] | None = None,
    dynamic_wings: list[dict] | None = None,
    ammonia_fuel_cells: list[dict] | None = None,
) -> Graph:
    """Build futuristic PMS graph with connectedTo relationships."""
    g = Graph()

    # Collect all component IDs that connect to PMS
    connected_ids: list[str] = []
    for component_list in [
        gensets,
        dc_bus_converters,
        scrs,
        auxiliary_loads,
        shore_power,
        frequency_converters,
        gate_rudders,
        thrusters,
        wasps,
        als,
        dynamic_wings,
        ammonia_fuel_cells,
    ]:
        for item in component_list or []:
            connected_ids.append(item["id"])

    for pms_dict in pms or []:
        pms_uri, pms_graph = create_twinship_pms(
            namespace=namespace,
            pms_id=pms_dict["id"],
            vessel_uri=vessel_uri,
            label=pms_dict.get("name"),
            types=pms_dict.get("types"),
        )
        g += pms_graph

        # Connect PMS to all futuristic components via connectedTo
        for component_id in connected_ids:
            g += build_twinship_connection(pms_uri, create_twinship_uri(component_id, namespace))

    return g


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
