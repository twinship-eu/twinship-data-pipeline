"""High-level graph builders for futuristic vessel component types.

Each function takes a list of component dicts and returns a single
combined Graph for that component type.
"""

from rdflib import Graph, URIRef

from twinship_harmonisation.mid_level.futuristic import (
    build_twinship_als,
    build_twinship_ammonia_fuel_cell,
    build_twinship_auxiliary_load,
    build_twinship_bow_thruster,
    build_twinship_dc_bus_converter,
    build_twinship_dynamic_wing,
    build_twinship_electric_motor,
    build_twinship_electric_motor_shaft,
    build_twinship_frequency_converter,
    build_twinship_gate_rudder,
    build_twinship_genset,
    build_twinship_scr,
    build_twinship_shore_power,
    build_twinship_wasp,
)


def twinship_gensets_graph(namespace: str, vessel_uri: URIRef, gensets: list[dict] | None) -> Graph:
    g = Graph()
    for genset in gensets or []:
        g += build_twinship_genset(namespace=namespace, vessel_uri=vessel_uri, **genset)
    return g


def twinship_ess_graph(namespace: str, vessel_uri: URIRef, ess: list[dict] | None) -> Graph:
    from twinship_harmonisation.mid_level.futuristic import build_twinship_ess

    g = Graph()
    for item in ess or []:
        g += build_twinship_ess(namespace=namespace, vessel_uri=vessel_uri, **item)
    return g


def twinship_dc_bus_converters_graph(
    namespace: str, vessel_uri: URIRef, dc_bus_converters: list[dict] | None
) -> Graph:
    g = Graph()
    for dcb in dc_bus_converters or []:
        g += build_twinship_dc_bus_converter(namespace=namespace, vessel_uri=vessel_uri, **dcb)
    return g


def twinship_scrs_graph(namespace: str, vessel_uri: URIRef, scrs: list[dict] | None) -> Graph:
    g = Graph()
    for scr in scrs or []:
        g += build_twinship_scr(namespace=namespace, vessel_uri=vessel_uri, **scr)
    return g


def twinship_auxiliary_loads_graph(
    namespace: str, vessel_uri: URIRef, auxiliary_loads: list[dict] | None
) -> Graph:
    g = Graph()
    for load in auxiliary_loads or []:
        g += build_twinship_auxiliary_load(namespace=namespace, vessel_uri=vessel_uri, **load)
    return g


def twinship_shore_power_graph(
    namespace: str, vessel_uri: URIRef, shore_power: list[dict] | None
) -> Graph:
    g = Graph()
    for sp in shore_power or []:
        g += build_twinship_shore_power(namespace=namespace, vessel_uri=vessel_uri, **sp)
    return g


def twinship_frequency_converters_graph(
    namespace: str, vessel_uri: URIRef, frequency_converters: list[dict] | None
) -> Graph:
    g = Graph()
    for fc in frequency_converters or []:
        g += build_twinship_frequency_converter(namespace=namespace, vessel_uri=vessel_uri, **fc)
    return g


def twinship_electric_motors_graph(
    namespace: str, vessel_uri: URIRef, electric_motors: list[dict] | None
) -> Graph:
    g = Graph()
    for motor in electric_motors or []:
        g += build_twinship_electric_motor(namespace=namespace, vessel_uri=vessel_uri, **motor)
    return g


def twinship_electric_motor_shafts_graph(
    namespace: str, vessel_uri: URIRef, electric_motor_shafts: list[dict] | None
) -> Graph:
    g = Graph()
    for shaft in electric_motor_shafts or []:
        g += build_twinship_electric_motor_shaft(
            namespace=namespace, vessel_uri=vessel_uri, **shaft
        )
    return g


def twinship_gate_rudders_graph(
    namespace: str, vessel_uri: URIRef, gate_rudders: list[dict] | None
) -> Graph:
    g = Graph()
    for gr in gate_rudders or []:
        g += build_twinship_gate_rudder(namespace=namespace, vessel_uri=vessel_uri, **gr)
    return g


def twinship_bow_thrusters_graph(
    namespace: str, vessel_uri: URIRef, thrusters: list[dict] | None
) -> Graph:
    g = Graph()
    for thruster in thrusters or []:
        g += build_twinship_bow_thruster(namespace=namespace, vessel_uri=vessel_uri, **thruster)
    return g


def twinship_wasps_graph(namespace: str, vessel_uri: URIRef, wasps: list[dict] | None) -> Graph:
    g = Graph()
    for wasp in wasps or []:
        g += build_twinship_wasp(namespace=namespace, vessel_uri=vessel_uri, **wasp)
    return g


def twinship_als_graph(namespace: str, vessel_uri: URIRef, als: list[dict] | None) -> Graph:
    g = Graph()
    for item in als or []:
        g += build_twinship_als(namespace=namespace, vessel_uri=vessel_uri, **item)
    return g


def twinship_dynamic_wings_graph(
    namespace: str, vessel_uri: URIRef, dynamic_wings: list[dict] | None
) -> Graph:
    g = Graph()
    for dw in dynamic_wings or []:
        g += build_twinship_dynamic_wing(namespace=namespace, vessel_uri=vessel_uri, **dw)
    return g


def twinship_ammonia_fuel_cells_graph(
    namespace: str, vessel_uri: URIRef, ammonia_fuel_cells: list[dict] | None
) -> Graph:
    g = Graph()
    for cell in ammonia_fuel_cells or []:
        g += build_twinship_ammonia_fuel_cell(namespace=namespace, vessel_uri=vessel_uri, **cell)
    return g
