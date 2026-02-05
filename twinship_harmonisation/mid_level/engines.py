"""Mid-level functions for creating TwinShip engine systems."""

from rdflib import Graph, URIRef

from twinship_harmonisation.low_level import (
    add_fuel_consumption,
    create_auxiliary_engine,
    create_main_engine,
)


def create_twinship_main_engines(
    data: dict,
    vessel_uri: URIRef,
    namespace: str,
) -> tuple[dict[str, URIRef], Graph]:
    """Create all main engines for a TwinShip vessel.

    Args:
        data: Vessel data dictionary containing 'main_engines' list.
        vessel_uri: URI of the parent vessel.
        namespace: Namespace for URI generation.

    Returns:
        Tuple of (component_uris dict, combined graph).
    """
    g = Graph()
    component_uris: dict[str, URIRef] = {}

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

        # Add fuel consumption relationships
        add_fuel_consumption(g, engine_uri, engine.get("fuels"))

    return component_uris, g


def create_twinship_auxiliary_engines(
    data: dict,
    vessel_uri: URIRef,
    namespace: str,
) -> tuple[dict[str, URIRef], Graph]:
    """Create all auxiliary engines for a TwinShip vessel.

    Args:
        data: Vessel data dictionary containing 'auxiliary_engines' list.
        vessel_uri: URI of the parent vessel.
        namespace: Namespace for URI generation.

    Returns:
        Tuple of (component_uris dict, combined graph).
    """
    g = Graph()
    component_uris: dict[str, URIRef] = {}

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

        # Add fuel consumption relationships
        add_fuel_consumption(g, engine_uri, engine.get("fuels"))

    return component_uris, g
