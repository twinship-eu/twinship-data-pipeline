"""High-level harmonisation functions for vessel data."""

import json
from pathlib import Path

from rdflib import Graph

from twinship_harmonisation.low_level import (
    add_direct_connection,
    add_fuel_consumption,
    create_auxiliary_engine,
    create_boiler,
    create_emergency_generator,
    create_gearbox,
    create_main_engine,
    create_pms,
    create_propeller,
    create_shaft_generator,
    create_thruster,
    create_vessel,
)
from twinship_harmonisation.utils import bind_namespaces


def harmonise_vessel_file(json_path: str | Path) -> Graph:
    """Harmonise vessel data from a JSON file into RDF triples.

    This is the main entry point for converting extracted vessel data
    into TwinShip-compliant RDF. It processes all components and their
    relationships.

    Args:
        json_path: Path to JSON file containing vessel data.

    Returns:
        RDFLib Graph with all vessel data and namespace bindings.

    The JSON file should have the structure:
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
    """
    with open(json_path) as f:
        data = json.load(f)

    return harmonise_vessel_data(data)


def harmonise_vessel_data(data: dict) -> Graph:
    """Harmonise vessel data dictionary into RDF triples.

    Args:
        data: Dictionary containing vessel data with namespace, operator,
              vessel, main_engines, auxiliary_engines, propellers,
              gearboxes, boilers, pms, emergency_generators, thrusters,
              and shaft_generators keys.

    Returns:
        RDFLib Graph with all vessel data and namespace bindings.
    """
    g = Graph()
    namespace = data["namespace"]

    # Track component URIs for relationship linking
    component_uris: dict[str, object] = {}

    # Create vessel
    vessel_data = data["vessel"]
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
    component_uris[vessel_data["id"]] = vessel_uri

    # Create main engines
    for engine in data.get("main_engines", []):
        engine_uri, engine_graph = create_main_engine(
            namespace=namespace,
            engine_id=engine["id"],
            vessel_uri=vessel_uri,
            label=engine.get("name"),
            types=engine.get("types"),
            shaft_torque_max_knm=engine.get("shaft_torque_max_knm"),
            shaft_speed_max_rpm=engine.get("shaft_speed_max_rpm"),
            shaft_power_max_kw=engine.get("shaft_power_max_kw"),
            flowrate_max_kg_per_hr=engine.get("flowrate_max_kg_per_hr"),
            fuel_flow_temp_max_c=engine.get("fuel_flow_temp_max_c"),
            inlet_air_pressure_max_hpa=engine.get("inlet_air_pressure_max_hpa"),
            inlet_air_temp_max_c=engine.get("inlet_air_temp_max_c"),
            me_cooling_water_temp_max_c=engine.get("me_cooling_water_temp_max_c"),
            lt_cooling_seawater_1_temp_max_c=engine.get("lt_cooling_seawater_1_temp_max_c"),
            lt_cooling_seawater_2_temp_max_c=engine.get("lt_cooling_seawater_2_temp_max_c"),
            scavenger_air_rec_temp_max_c=engine.get("scavenger_air_rec_temp_max_c"),
            common_do_mode=engine.get("common_do_mode"),
            common_fuel_mode=engine.get("common_fuel_mode"),
            fuel_consumption_total_mt=engine.get("fuel_consumption_total_mt"),
            power_propulsion_total_kw=engine.get("power_propulsion_total_kw"),
        )
        g += engine_graph
        component_uris[engine["id"]] = engine_uri

        # Add fuel consumption
        add_fuel_consumption(g, engine_uri, engine.get("fuels"))

    # Create auxiliary engines
    for engine in data.get("auxiliary_engines", []):
        engine_uri, engine_graph = create_auxiliary_engine(
            namespace=namespace,
            engine_id=engine["id"],
            vessel_uri=vessel_uri,
            label=engine.get("name"),
            types=engine.get("types"),
            diesel_engine_power_max_kw=engine.get("diesel_engine_power_max_kw"),
            diesel_engine_speed_rpm=engine.get("diesel_engine_speed_rpm"),
            generator_power_max_kw=engine.get("generator_power_max_kw"),
            generator_speed_rpm=engine.get("generator_speed_rpm"),
            auxiliary_do_mode=engine.get("auxiliary_do_mode"),
            fuel_rate_mass_net_kg_per_hr=engine.get("fuel_rate_mass_net_kg_per_hr"),
        )
        g += engine_graph
        component_uris[engine["id"]] = engine_uri

        # Add fuel consumption
        add_fuel_consumption(g, engine_uri, engine.get("fuels"))

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

    # =============================================================================
    # Add directlyConnectedTo relationships
    # =============================================================================

    # Engine -> Gearbox connections (from main_engines)
    for engine in data.get("main_engines", []):
        gearbox_id = engine.get("gearbox_id")
        if gearbox_id and gearbox_id in component_uris:
            add_direct_connection(
                g,
                component_uris[engine["id"]],
                component_uris[gearbox_id],
            )

    # Gearbox -> Propeller connections (from gearboxes)
    for gearbox in data.get("gearboxes", []):
        propeller_id = gearbox.get("propeller_id")
        if propeller_id and propeller_id in component_uris:
            add_direct_connection(
                g,
                component_uris[gearbox["id"]],
                component_uris[propeller_id],
            )

    # PMS connections - connect to auxiliary engines, emergency generators, thrusters, shaft generators
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

    return bind_namespaces(g)


def harmonise_all_vessels(data_dir: str | Path) -> Graph:
    """Harmonise all vessel JSON files in a directory.

    Args:
        data_dir: Directory containing vessel JSON files.

    Returns:
        Combined RDFLib Graph with all vessels.
    """
    g = Graph()
    data_path = Path(data_dir)

    for json_file in data_path.glob("*.json"):
        g += harmonise_vessel_file(json_file)

    return bind_namespaces(g)
