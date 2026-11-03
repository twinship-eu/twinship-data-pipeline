"""Low-level functions for creating engine-related TwinShip RDF triples."""

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from twinship_harmonisation.constants import IDO, TWINSHIP
from twinship_harmonisation.low_level.vessel_functions import (
    add_optional_code,
    add_optional_double,
    create_twinship_uri,
    get_twinship_type_uri,
)


def create_twinship_main_engine(
    namespace: str,
    engine_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
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
    common_do_mode: int | None = None,
    common_fuel_mode: int | None = None,
    fuel_consumption_total_mt: float | None = None,
    power_propulsion_total_kw: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for a main engine system.

    Returns:
        Tuple of (engine_uri, graph).
    """
    g = Graph()
    engine_uri = create_twinship_uri(engine_id, namespace)

    # Type assertions
    g.add((engine_uri, RDF.type, TWINSHIP.MainEngineSystem))
    if types:
        for type_name in types:
            type_uri = get_twinship_type_uri(type_name)
            if type_uri:
                g.add((engine_uri, RDF.type, type_uri))

    # Relationship to vessel (using IDO partOf)
    g.add((engine_uri, IDO.partOf, vessel_uri))

    # Label
    if label:
        g.add((engine_uri, RDFS.label, Literal(label)))

    # Data properties
    add_optional_double(g, engine_uri, TWINSHIP.twShaftTorqueMaxInKnm, shaft_torque_max_knm)
    add_optional_double(g, engine_uri, TWINSHIP.twShaftSpeedMaxInRevPerMin, shaft_speed_max_rpm)
    add_optional_double(g, engine_uri, TWINSHIP.twShaftPowerMaxInKW, shaft_power_max_kw)
    add_optional_double(g, engine_uri, TWINSHIP.twFlowrateMaxInKgPerHr, flowrate_max_kg_per_hr)
    add_optional_double(
        g, engine_uri, TWINSHIP.twFuelFlowTemperatureMaxInDegC, fuel_flow_temp_max_c
    )
    add_optional_double(
        g, engine_uri, TWINSHIP.twInletAirPressureMaxInHPa, inlet_air_pressure_max_hpa
    )
    add_optional_double(
        g, engine_uri, TWINSHIP.twInletAirTemperatureMaxInDegC, inlet_air_temp_max_c
    )
    add_optional_double(
        g, engine_uri, TWINSHIP.twMeCoolingWaterTemperatureMaxInDegC, me_cooling_water_temp_max_c
    )
    add_optional_double(
        g,
        engine_uri,
        TWINSHIP.twLtCoolingSeawater1TemperatureMaxInDegC,
        lt_cooling_seawater_1_temp_max_c,
    )
    add_optional_double(
        g,
        engine_uri,
        TWINSHIP.twLtCoolingSeawater2TemperatureMaxInDegC,
        lt_cooling_seawater_2_temp_max_c,
    )
    add_optional_double(
        g, engine_uri, TWINSHIP.twScavengerAirRecTemperatureMaxInDegC, scavenger_air_rec_temp_max_c
    )
    add_optional_code(g, engine_uri, TWINSHIP.twCommonDOMode, common_do_mode)
    add_optional_code(g, engine_uri, TWINSHIP.twCommonFuelMode, common_fuel_mode)

    add_optional_double(
        g, engine_uri, TWINSHIP.twFuelConsumptionTotalInMT, fuel_consumption_total_mt
    )
    add_optional_double(
        g, engine_uri, TWINSHIP.twPowerPropulsionTotalInKw, power_propulsion_total_kw
    )

    return engine_uri, g


def create_twinship_auxiliary_engine(
    namespace: str,
    engine_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    diesel_engine_power_max_kw: float | None = None,
    diesel_engine_speed_rpm: float | None = None,
    generator_power_max_kw: float | None = None,
    generator_speed_rpm: float | None = None,
    auxiliary_do_mode: str | None = None,
    fuel_rate_mass_net_kg_per_hr: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for an auxiliary engine system.

    Returns:
        Tuple of (engine_uri, graph).
    """
    g = Graph()
    engine_uri = create_twinship_uri(engine_id, namespace)

    # Type assertions
    g.add((engine_uri, RDF.type, TWINSHIP.AuxiliaryEngineSystem))
    if types:
        for type_name in types:
            type_uri = get_twinship_type_uri(type_name)
            if type_uri:
                g.add((engine_uri, RDF.type, type_uri))

    # Relationship to vessel (using IDO partOf)
    g.add((engine_uri, IDO.partOf, vessel_uri))

    # Label
    if label:
        g.add((engine_uri, RDFS.label, Literal(label)))

    # Data properties
    add_optional_double(
        g, engine_uri, TWINSHIP.twDieselEnginePowerMaxInKW, diesel_engine_power_max_kw
    )
    add_optional_double(
        g, engine_uri, TWINSHIP.twDieselEngineSpeedInRevPerMin, diesel_engine_speed_rpm
    )
    add_optional_double(g, engine_uri, TWINSHIP.twGeneratorPowerMaxInKW, generator_power_max_kw)
    add_optional_double(g, engine_uri, TWINSHIP.twGeneratorSpeedInRevPerMin, generator_speed_rpm)
    add_optional_double(
        g, engine_uri, TWINSHIP.twAuxiliaryFuelRateMassNetKgPerHr, fuel_rate_mass_net_kg_per_hr
    )

    add_optional_code(g, engine_uri, TWINSHIP.twAuxiliaryDOMode, auxiliary_do_mode)

    return engine_uri, g
