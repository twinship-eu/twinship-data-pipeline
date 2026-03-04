"""Mid-level functions for creating futuristic vessel component graphs.

Each function builds a graph for a single component including its connections.
Parameter names match JSON keys so callers can unpack with **kwargs.
"""

from rdflib import Graph, URIRef

from twinship_harmonisation.low_level import (
    build_twinship_connection,
    build_twinship_direct_connection,
    build_twinship_fuel_consumption,
    create_twinship_als,
    create_twinship_ammonia_fuel_cell,
    create_twinship_auxiliary_load,
    create_twinship_bow_thruster,
    create_twinship_dc_bus_converter,
    create_twinship_dynamic_wing,
    create_twinship_electric_motor,
    create_twinship_electric_motor_shaft,
    create_twinship_frequency_converter,
    create_twinship_gate_rudder,
    create_twinship_genset,
    create_twinship_scr,
    create_twinship_shore_power,
    create_twinship_uri,
    create_twinship_wasp,
)
from twinship_harmonisation.low_level.futuristic_functions import create_twinship_ess


def build_twinship_genset(
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
    fuel_consumption_total_mt: float | None = None,
    power_propulsion_total_kw: float | None = None,
    common_fuel_mode: int | None = None,
    generator_voltage_v: float | None = None,
    electrical_efficiency_percentage: float | None = None,
    generator_frequency: float | None = None,
    fuels: list[str] | None = None,
    pms_id: str | None = None,
    scr_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single genset with connections and fuel consumption."""
    uri, g = create_twinship_genset(
        namespace=namespace,
        genset_id=id,
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
        fuel_consumption_total_mt=fuel_consumption_total_mt,
        power_propulsion_total_kw=power_propulsion_total_kw,
        common_fuel_mode=common_fuel_mode,
        generator_voltage_v=generator_voltage_v,
        electrical_efficiency_percentage=electrical_efficiency_percentage,
        generator_frequency=generator_frequency,
    )

    g += build_twinship_fuel_consumption(uri, fuels)

    # Genset connects to PMS and SCR via connectedTo
    if pms_id:
        g += build_twinship_connection(uri, create_twinship_uri(pms_id, namespace))
    if scr_id:
        g += build_twinship_connection(uri, create_twinship_uri(scr_id, namespace))

    return g


def build_twinship_ess(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    capacity_mwh: float | None = None,
    weight_kg: float | None = None,
    depth_of_discharge_percentage: float | None = None,
    cycle_life: int | None = None,
    volume_m3: float | None = None,
    c_rate: float | None = None,
    dcb_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single energy storage system."""
    uri, g = create_twinship_ess(
        namespace=namespace,
        ess_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        capacity_mwh=capacity_mwh,
        weight_kg=weight_kg,
        depth_of_discharge_percentage=depth_of_discharge_percentage,
        cycle_life=cycle_life,
        volume_m3=volume_m3,
        c_rate=c_rate,
    )

    if dcb_id:
        g += build_twinship_connection(uri, create_twinship_uri(dcb_id, namespace))

    return g


def build_twinship_dc_bus_converter(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    nominal_voltage: float | None = None,
    max_voltage: float | None = None,
    min_voltage: float | None = None,
    max_current: float | None = None,
    ess_id: str | None = None,
    pms_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single DC bus bidirectional converter."""
    uri, g = create_twinship_dc_bus_converter(
        namespace=namespace,
        dcb_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        nominal_voltage=nominal_voltage,
        max_voltage=max_voltage,
        min_voltage=min_voltage,
        max_current=max_current,
    )

    if ess_id:
        g += build_twinship_connection(uri, create_twinship_uri(ess_id, namespace))
    if pms_id:
        g += build_twinship_connection(uri, create_twinship_uri(pms_id, namespace))

    return g


def build_twinship_scr(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    no_reduction_efficiency: float | None = None,
    exhaust_gas_flowrate_kg_per_hr: float | None = None,
    op_temp_centigrade: float | None = None,
    catalyst_volume_m3: float | None = None,
    genset_id: str | None = None,
    pms_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single SCR system."""
    uri, g = create_twinship_scr(
        namespace=namespace,
        scr_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        no_reduction_efficiency=no_reduction_efficiency,
        exhaust_gas_flowrate_kg_per_hr=exhaust_gas_flowrate_kg_per_hr,
        op_temp_centigrade=op_temp_centigrade,
        catalyst_volume_m3=catalyst_volume_m3,
    )

    if genset_id:
        g += build_twinship_connection(uri, create_twinship_uri(genset_id, namespace))
    if pms_id:
        g += build_twinship_connection(uri, create_twinship_uri(pms_id, namespace))

    return g


def build_twinship_auxiliary_load(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    ship_services_power_kw: float | None = None,
    hotel_load_power_kw: float | None = None,
    pms_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single auxiliary load."""
    uri, g = create_twinship_auxiliary_load(
        namespace=namespace,
        auxld_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        ship_services_power_kw=ship_services_power_kw,
        hotel_load_power_kw=hotel_load_power_kw,
    )

    if pms_id:
        g += build_twinship_connection(uri, create_twinship_uri(pms_id, namespace))

    return g


def build_twinship_shore_power(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    power_kwh: float | None = None,
    time_hours: float | None = None,
    pms_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single shore power connection."""
    uri, g = create_twinship_shore_power(
        namespace=namespace,
        osp_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        power_kwh=power_kwh,
        time_hours=time_hours,
    )

    if pms_id:
        g += build_twinship_connection(uri, create_twinship_uri(pms_id, namespace))

    return g


def build_twinship_frequency_converter(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    power_mwh: float | None = None,
    voltage_volts: float | None = None,
    frequency_hz: float | None = None,
    motor_id: str | None = None,
    pms_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single frequency converter."""
    uri, g = create_twinship_frequency_converter(
        namespace=namespace,
        fc_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        power_mwh=power_mwh,
        voltage_volts=voltage_volts,
        frequency_hz=frequency_hz,
    )

    if pms_id:
        g += build_twinship_connection(uri, create_twinship_uri(pms_id, namespace))
    if motor_id:
        g += build_twinship_connection(uri, create_twinship_uri(motor_id, namespace))

    return g


def build_twinship_electric_motor(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    power_mwh: float | None = None,
    voltage_volts: float | None = None,
    frequency_hz: float | None = None,
    fc_id: str | None = None,
    shaft_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single electric motor."""
    uri, g = create_twinship_electric_motor(
        namespace=namespace,
        motor_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        power_mwh=power_mwh,
        voltage_volts=voltage_volts,
        frequency_hz=frequency_hz,
    )

    # Motor connects to FC via connectedTo, to shaft via directlyConnectedTo
    if fc_id:
        g += build_twinship_connection(uri, create_twinship_uri(fc_id, namespace))
    if shaft_id:
        g += build_twinship_direct_connection(uri, create_twinship_uri(shaft_id, namespace))

    return g


def build_twinship_electric_motor_shaft(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    speed_rpm: float | None = None,
    torque_kn: float | None = None,
    motor_id: str | None = None,
    propeller_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single electric motor shaft."""
    uri, g = create_twinship_electric_motor_shaft(
        namespace=namespace,
        shaft_id=id,
        vessel_uri=vessel_uri,
        label=name,
        speed_rpm=speed_rpm,
        torque_kn=torque_kn,
    )

    # Shaft connects directly to motor and propeller
    if motor_id:
        g += build_twinship_direct_connection(uri, create_twinship_uri(motor_id, namespace))
    if propeller_id:
        g += build_twinship_direct_connection(uri, create_twinship_uri(propeller_id, namespace))

    return g


def build_twinship_gate_rudder(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    power_kw: float | None = None,
    power_reduction_efficiency_percentage: float | None = None,
    pms_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single gate rudder."""
    uri, g = create_twinship_gate_rudder(
        namespace=namespace,
        gr_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        power_kw=power_kw,
        power_reduction_efficiency_percentage=power_reduction_efficiency_percentage,
    )

    if pms_id:
        g += build_twinship_connection(uri, create_twinship_uri(pms_id, namespace))

    return g


def build_twinship_bow_thruster(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    power_kw: float | None = None,
    pms_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single bow thruster."""
    uri, g = create_twinship_bow_thruster(
        namespace=namespace,
        thruster_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        power_kw=power_kw,
    )

    if pms_id:
        g += build_twinship_connection(uri, create_twinship_uri(pms_id, namespace))

    return g


def build_twinship_wasp(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    power_kw: float | None = None,
    power_reduction_efficiency_percentage: float | None = None,
    pms_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single wind-assisted propulsion system."""
    uri, g = create_twinship_wasp(
        namespace=namespace,
        wasp_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        power_kw=power_kw,
        power_reduction_efficiency_percentage=power_reduction_efficiency_percentage,
    )

    if pms_id:
        g += build_twinship_connection(uri, create_twinship_uri(pms_id, namespace))

    return g


def build_twinship_als(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    power_kw: float | None = None,
    power_reduction_efficiency_percentage: float | None = None,
    pms_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single air lubrication system."""
    uri, g = create_twinship_als(
        namespace=namespace,
        als_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        power_kw=power_kw,
        power_reduction_efficiency_percentage=power_reduction_efficiency_percentage,
    )

    if pms_id:
        g += build_twinship_connection(uri, create_twinship_uri(pms_id, namespace))

    return g


def build_twinship_dynamic_wing(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    power_kw: float | None = None,
    power_reduction_efficiency_percentage: float | None = None,
    pms_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single dynamic wing."""
    uri, g = create_twinship_dynamic_wing(
        namespace=namespace,
        dw_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        power_kw=power_kw,
        power_reduction_efficiency_percentage=power_reduction_efficiency_percentage,
    )

    if pms_id:
        g += build_twinship_connection(uri, create_twinship_uri(pms_id, namespace))

    return g


def build_twinship_ammonia_fuel_cell(
    *,
    namespace: str,
    vessel_uri: URIRef,
    id: str,
    name: str | None = None,
    types: list[str] | None = None,
    power_capacity_kwh: float | None = None,
    pms_id: str | None = None,
    vessel_id: str | None = None,
) -> Graph:
    """Build a graph for a single ammonia fuel cell."""
    uri, g = create_twinship_ammonia_fuel_cell(
        namespace=namespace,
        ammcell_id=id,
        vessel_uri=vessel_uri,
        label=name,
        types=types,
        power_capacity_kwh=power_capacity_kwh,
    )

    if pms_id:
        g += build_twinship_connection(uri, create_twinship_uri(pms_id, namespace))

    return g
