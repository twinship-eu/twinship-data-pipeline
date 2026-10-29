"""Low-level functions for creating futuristic vessel component RDF triples.

Each function returns (URIRef, Graph) following the same pattern as
create_twinship_main_engine etc.
"""

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from twinship_harmonisation.constants import IDO, TWINSHIP
from twinship_harmonisation.low_level.vessel_functions import (
    add_optional_code,
    add_optional_double,
    create_twinship_uri,
    get_twinship_type_uri,
)


def _add_types(g: Graph, uri: URIRef, primary_type: URIRef, types: list[str] | None) -> None:
    """Add the primary RDF type and any additional types from the types list."""
    g.add((uri, RDF.type, primary_type))
    for type_name in types or []:
        type_uri = get_twinship_type_uri(type_name)
        if type_uri:
            g.add((uri, RDF.type, type_uri))


def create_twinship_genset(
    namespace: str,
    genset_id: str,
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
    fuel_consumption_total_mt: float | None = None,
    power_propulsion_total_kw: float | None = None,
    common_fuel_mode: int | None = None,
    generator_voltage_v: float | None = None,
    electrical_efficiency_percentage: float | None = None,
    generator_frequency: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for a generator set (diesel-electric)."""
    g = Graph()
    uri = create_twinship_uri(genset_id, namespace)

    _add_types(g, uri, TWINSHIP.GenSetSystem, types)
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    # Same engine properties as main engine
    add_optional_double(g, uri, TWINSHIP.twShaftTorqueMaxInKnm, shaft_torque_max_knm)
    add_optional_double(g, uri, TWINSHIP.twShaftSpeedMaxInRevPerMin, shaft_speed_max_rpm)
    add_optional_double(g, uri, TWINSHIP.twShaftPowerMaxInKW, shaft_power_max_kw)
    add_optional_double(g, uri, TWINSHIP.twFlowrateMaxInKgPerHr, flowrate_max_kg_per_hr)
    add_optional_double(g, uri, TWINSHIP.twFuelFlowTemperatureMaxInDegC, fuel_flow_temp_max_c)
    add_optional_double(g, uri, TWINSHIP.twInletAirPressureMaxInHPa, inlet_air_pressure_max_hpa)
    add_optional_double(g, uri, TWINSHIP.twInletAirTemperatureMaxInDegC, inlet_air_temp_max_c)
    add_optional_double(
        g, uri, TWINSHIP.twMeCoolingWaterTemperatureMaxInDegC, me_cooling_water_temp_max_c
    )
    add_optional_double(
        g, uri, TWINSHIP.twLtCoolingSeawater1TemperatureMaxInDegC, lt_cooling_seawater_1_temp_max_c
    )
    add_optional_double(
        g, uri, TWINSHIP.twLtCoolingSeawater2TemperatureMaxInDegC, lt_cooling_seawater_2_temp_max_c
    )
    add_optional_double(
        g, uri, TWINSHIP.twScavengerAirRecTemperatureMaxInDegC, scavenger_air_rec_temp_max_c
    )
    add_optional_double(g, uri, TWINSHIP.twFuelConsumptionTotalInMT, fuel_consumption_total_mt)
    add_optional_double(g, uri, TWINSHIP.twPowerPropulsionTotalInKw, power_propulsion_total_kw)

    add_optional_code(g, uri, TWINSHIP.twCommonFuelMode, common_fuel_mode)

    # Generator-specific properties
    add_optional_double(g, uri, TWINSHIP.twGeneratorVoltageInV, generator_voltage_v)
    add_optional_double(
        g, uri, TWINSHIP.twElectricalEfficiencyPercentage, electrical_efficiency_percentage
    )
    add_optional_double(g, uri, TWINSHIP.twGeneratorFrequency, generator_frequency)

    return uri, g


def create_twinship_ess(
    namespace: str,
    ess_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    capacity_mwh: float | None = None,
    weight_kg: float | None = None,
    depth_of_discharge_percentage: float | None = None,
    cycle_life: int | None = None,
    volume_m3: float | None = None,
    c_rate: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for an energy storage system."""
    g = Graph()
    uri = create_twinship_uri(ess_id, namespace)

    _add_types(g, uri, TWINSHIP.EnergyStorageSystem, types)
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    add_optional_double(g, uri, TWINSHIP.twESSCapacityInMWh, capacity_mwh)
    add_optional_double(g, uri, TWINSHIP.twESSWeightInKg, weight_kg)
    add_optional_double(
        g, uri, TWINSHIP.twESSDepthOfDischargePercentage, depth_of_discharge_percentage
    )
    if cycle_life is not None:
        g.add((uri, TWINSHIP.twESSCycleLife, Literal(int(cycle_life), datatype=XSD.integer)))
    add_optional_double(g, uri, TWINSHIP.twESSVolumeInM3, volume_m3)
    add_optional_double(g, uri, TWINSHIP.twESSCRate, c_rate)

    return uri, g


def create_twinship_dc_bus_converter(
    namespace: str,
    dcb_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    nominal_voltage: float | None = None,
    max_voltage: float | None = None,
    min_voltage: float | None = None,
    max_current: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for a bidirectional DC bus converter."""
    g = Graph()
    uri = create_twinship_uri(dcb_id, namespace)

    _add_types(g, uri, TWINSHIP.BidirectionalConverterSystem, types)
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    add_optional_double(g, uri, TWINSHIP.twDCBNominalVoltage, nominal_voltage)
    add_optional_double(g, uri, TWINSHIP.twDCBMaxVoltage, max_voltage)
    add_optional_double(g, uri, TWINSHIP.twDCBMinVoltage, min_voltage)
    add_optional_double(g, uri, TWINSHIP.twDCBMaxCurrent, max_current)

    return uri, g


def create_twinship_scr(
    namespace: str,
    scr_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    no_reduction_efficiency: float | None = None,
    exhaust_gas_flowrate_kg_per_hr: float | None = None,
    op_temp_centigrade: float | None = None,
    catalyst_volume_m3: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for a selective catalytic reduction system."""
    g = Graph()
    uri = create_twinship_uri(scr_id, namespace)

    _add_types(g, uri, TWINSHIP.SCR, types)
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    add_optional_double(g, uri, TWINSHIP.twSCRNOReductionEfficiency, no_reduction_efficiency)
    add_optional_double(
        g, uri, TWINSHIP.twSCRExhaustGasFlowrateInKgPerHr, exhaust_gas_flowrate_kg_per_hr
    )
    add_optional_double(g, uri, TWINSHIP.twSCROpTempCentigrade, op_temp_centigrade)
    add_optional_double(g, uri, TWINSHIP.twSCRCatalystVolumeInM3, catalyst_volume_m3)

    return uri, g


def create_twinship_auxiliary_load(
    namespace: str,
    auxld_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    ship_services_power_kw: float | None = None,
    hotel_load_power_kw: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for an auxiliary load (ship services + hotel)."""
    g = Graph()
    uri = create_twinship_uri(auxld_id, namespace)

    _add_types(g, uri, TWINSHIP.AUXLOAD, types)
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    add_optional_double(g, uri, TWINSHIP.twAUXLDShipServicesPowerInKW, ship_services_power_kw)
    add_optional_double(g, uri, TWINSHIP.twAUXLDHotelLoadPowerInKW, hotel_load_power_kw)

    return uri, g


def create_twinship_shore_power(
    namespace: str,
    osp_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    power_kwh: float | None = None,
    time_hours: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for an on-shore power connection."""
    g = Graph()
    uri = create_twinship_uri(osp_id, namespace)

    _add_types(g, uri, TWINSHIP.OSP, types)
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    add_optional_double(g, uri, TWINSHIP.twOSPPowerInKWh, power_kwh)
    add_optional_double(g, uri, TWINSHIP.twOSPTimeInHours, time_hours)

    return uri, g


def create_twinship_frequency_converter(
    namespace: str,
    fc_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    power_mwh: float | None = None,
    voltage_volts: float | None = None,
    frequency_hz: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for a frequency converter."""
    g = Graph()
    uri = create_twinship_uri(fc_id, namespace)

    _add_types(g, uri, TWINSHIP.FrequencyConverterSystem, types)
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    add_optional_double(g, uri, TWINSHIP.twEMPowerInMWh, power_mwh)
    add_optional_double(g, uri, TWINSHIP.twFCVoltageInVolts, voltage_volts)
    add_optional_double(g, uri, TWINSHIP.twFCFrequencyInHz, frequency_hz)

    return uri, g


def create_twinship_electric_motor(
    namespace: str,
    motor_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    power_mwh: float | None = None,
    voltage_volts: float | None = None,
    frequency_hz: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for an electric motor."""
    g = Graph()
    uri = create_twinship_uri(motor_id, namespace)

    _add_types(g, uri, TWINSHIP.ElectricMotorSystem, types)
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    add_optional_double(g, uri, TWINSHIP.twEMPowerInMWh, power_mwh)
    add_optional_double(g, uri, TWINSHIP.twFCVoltageInVolts, voltage_volts)
    add_optional_double(g, uri, TWINSHIP.twFCFrequencyInHz, frequency_hz)

    return uri, g


def create_twinship_electric_motor_shaft(
    namespace: str,
    shaft_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    speed_rpm: float | None = None,
    torque_kn: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for an electric motor shaft."""
    g = Graph()
    uri = create_twinship_uri(shaft_id, namespace)

    g.add((uri, RDF.type, TWINSHIP.ElectricMotorShaft))
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    add_optional_double(g, uri, TWINSHIP.twEMSHSpeedInRevPerMin, speed_rpm)
    add_optional_double(g, uri, TWINSHIP.twEMSHTorqueInKN, torque_kn)

    return uri, g


def create_twinship_gate_rudder(
    namespace: str,
    gr_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    power_kw: float | None = None,
    power_reduction_efficiency_percentage: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for a gate rudder."""
    g = Graph()
    uri = create_twinship_uri(gr_id, namespace)

    _add_types(g, uri, TWINSHIP.GateRudder, types)
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    add_optional_double(g, uri, TWINSHIP.twGRSPowerInKW, power_kw)
    add_optional_double(
        g,
        uri,
        TWINSHIP.twGRSPowerReductionEfficiencyPercentage,
        power_reduction_efficiency_percentage,
    )

    return uri, g


def create_twinship_bow_thruster(
    namespace: str,
    thruster_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    power_kw: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for a bow thruster."""
    g = Graph()
    uri = create_twinship_uri(thruster_id, namespace)

    _add_types(g, uri, TWINSHIP.BowThruster, types)
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    add_optional_double(g, uri, TWINSHIP.twBowThrusterPowerMaxInKW, power_kw)

    return uri, g


def create_twinship_wasp(
    namespace: str,
    wasp_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    power_kw: float | None = None,
    power_reduction_efficiency_percentage: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for a wind-assisted propulsion system."""
    g = Graph()
    uri = create_twinship_uri(wasp_id, namespace)

    _add_types(g, uri, TWINSHIP.WindAssistedPropulsionSystem, types)
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    add_optional_double(g, uri, TWINSHIP.twWASPPowerInKW, power_kw)
    add_optional_double(
        g,
        uri,
        TWINSHIP.twWASPPowerReductionEfficiencyPercentage,
        power_reduction_efficiency_percentage,
    )

    return uri, g


def create_twinship_als(
    namespace: str,
    als_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    power_kw: float | None = None,
    power_reduction_efficiency_percentage: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for an air lubrication system."""
    g = Graph()
    uri = create_twinship_uri(als_id, namespace)

    _add_types(g, uri, TWINSHIP.AirLubricationSystem, types)
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    add_optional_double(g, uri, TWINSHIP.twALSPowerInKW, power_kw)
    add_optional_double(
        g,
        uri,
        TWINSHIP.twALSPowerReductionEfficiencyPercentage,
        power_reduction_efficiency_percentage,
    )

    return uri, g


def create_twinship_dynamic_wing(
    namespace: str,
    dw_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    power_kw: float | None = None,
    power_reduction_efficiency_percentage: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for a dynamic wing."""
    g = Graph()
    uri = create_twinship_uri(dw_id, namespace)

    _add_types(g, uri, TWINSHIP.DynamicWing, types)
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    add_optional_double(g, uri, TWINSHIP.twDWPowerInKW, power_kw)
    add_optional_double(
        g,
        uri,
        TWINSHIP.twDWPowerReductionEfficiencyPercentage,
        power_reduction_efficiency_percentage,
    )

    return uri, g


def create_twinship_ammonia_fuel_cell(
    namespace: str,
    ammcell_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    power_capacity_kwh: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for an ammonia fuel cell."""
    g = Graph()
    uri = create_twinship_uri(ammcell_id, namespace)

    _add_types(g, uri, TWINSHIP.FuelCellSystem, types)
    g.add((uri, IDO.partOf, vessel_uri))
    if label:
        g.add((uri, RDFS.label, Literal(label)))

    add_optional_double(g, uri, TWINSHIP.twAMMCELLPowerCapacityInKWh, power_capacity_kwh)
    # Fuel cell consumes ammonia
    g.add((uri, TWINSHIP.consume, TWINSHIP.AMM))

    return uri, g
