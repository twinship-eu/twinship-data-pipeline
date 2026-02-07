"""Mid-level functions for creating TwinShip engine systems.

Each function builds a graph for a single engine and returns it.
Parameter names match JSON keys so callers can unpack with **engine.
"""

from rdflib import Graph, URIRef

from twinship_harmonisation.low_level import (
    build_twinship_direct_connection,
    build_twinship_fuel_consumption,
    create_twinship_auxiliary_engine,
    create_twinship_main_engine,
    create_twinship_uri,
)


def build_twinship_main_engine(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    shaft_torque_max_knm: float | None = None,
    shaft_speed_max_rpm: float | None = None,
    shaft_power_max_kw: float | None = None,
    flowrate_max_kg_per_hr: float | None = None,
    fuel_flow_temp_max_c: float | None = None,
    inlet_air_pressure_max_hpa: float | None = None,
    inlet_air_temp_max_c: float | None = None,
    me_cooling_water_temp_max_c: float | None = None,
    lt_cooling_seawater_1_temp_max_c: float | None = None,
    lt_cooling_seawater_2_temp_max_c: float | None = None,
    scavenger_air_rec_temp_max_c: float | None = None,
    common_do_mode: str | None = None,
    common_fuel_mode: str | None = None,
    fuel_consumption_total_mt: float | None = None,
    power_propulsion_total_kw: float | None = None,
    fuels: list[str] | None = None,
    gearbox_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single main engine.

    Also includes fuel consumption triples and an engine -> gearbox connection
    when gearbox_id is present.

    Args:
        namespace: Namespace for URI generation.
        vessel_uri: URI of the parent vessel.
        id: Engine identifier (maps to engine_id in low-level function).
        name: Human-readable label.
        types: RDF type names to add (e.g. ["TwoStroke"]).
        fuels: Fuel type names for consumption triples (e.g. ["HFO", "MGO"]).
        gearbox_id: If set, creates engine -> gearbox connection.
        vessel_id: Accepted from JSON for **kwargs compatibility, unused.

    Returns:
        Graph containing all triples for this main engine.
    """
    # Create the main engine triples (type assertions, data properties, partOf)
    engine_uri, g = create_twinship_main_engine(
        namespace=namespace,
        engine_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        shaft_torque_max_knm=shaft_torque_max_knm,
        shaft_speed_max_rpm=shaft_speed_max_rpm,
        shaft_power_max_kw=shaft_power_max_kw,
        flowrate_max_kg_per_hr=flowrate_max_kg_per_hr,
        fuel_flow_temp_max_c=fuel_flow_temp_max_c,
        inlet_air_pressure_max_hpa=inlet_air_pressure_max_hpa,
        inlet_air_temp_max_c=inlet_air_temp_max_c,
        me_cooling_water_temp_max_c=me_cooling_water_temp_max_c,
        lt_cooling_seawater_1_temp_max_c=lt_cooling_seawater_1_temp_max_c,
        lt_cooling_seawater_2_temp_max_c=lt_cooling_seawater_2_temp_max_c,
        scavenger_air_rec_temp_max_c=scavenger_air_rec_temp_max_c,
        common_do_mode=common_do_mode,
        common_fuel_mode=common_fuel_mode,
        fuel_consumption_total_mt=fuel_consumption_total_mt,
        power_propulsion_total_kw=power_propulsion_total_kw,
    )

    # Add fuel consumption relationships (e.g. engine twinship:consume twinship:HFO)
    g += build_twinship_fuel_consumption(engine_uri, fuels)

    # Connect engine to its gearbox if specified
    if gearbox_id:
        g += build_twinship_direct_connection(
            engine_uri, create_twinship_uri(gearbox_id, namespace)
        )

    return g


def build_twinship_auxiliary_engine(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    diesel_engine_power_max_kw: float | None = None,
    diesel_engine_speed_rpm: float | None = None,
    generator_power_max_kw: float | None = None,
    generator_speed_rpm: float | None = None,
    auxiliary_do_mode: str | None = None,
    fuel_rate_mass_net_kg_per_hr: float | None = None,
    fuels: list[str] | None = None,
    vessel_id: str | None = None,
    pms_id: str | None = None,
) -> Graph:
    """Build a graph for a single auxiliary engine.

    Also includes fuel consumption triples.

    Args:
        namespace: Namespace for URI generation.
        vessel_uri: URI of the parent vessel.
        id: Engine identifier (maps to engine_id in low-level function).
        name: Human-readable label.
        types: RDF type names to add (e.g. ["FourStroke", "DieselEngine"]).
        fuels: Fuel type names for consumption triples.
        vessel_id: Accepted from JSON for **kwargs compatibility, unused.
        pms_id: Accepted from JSON for **kwargs compatibility, unused.

    Returns:
        Graph containing all triples for this auxiliary engine.
    """
    # Create the auxiliary engine triples
    engine_uri, g = create_twinship_auxiliary_engine(
        namespace=namespace,
        engine_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        diesel_engine_power_max_kw=diesel_engine_power_max_kw,
        diesel_engine_speed_rpm=diesel_engine_speed_rpm,
        generator_power_max_kw=generator_power_max_kw,
        generator_speed_rpm=generator_speed_rpm,
        auxiliary_do_mode=auxiliary_do_mode,
        fuel_rate_mass_net_kg_per_hr=fuel_rate_mass_net_kg_per_hr,
    )

    # Add fuel consumption relationships
    g += build_twinship_fuel_consumption(engine_uri, fuels)

    return g
