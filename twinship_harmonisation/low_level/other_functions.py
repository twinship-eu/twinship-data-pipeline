"""Low-level functions for creating TwinShip RDF triples for other components.

Includes: PMS, Emergency Generators, Thrusters, Shaft Generators.
"""

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS

from twinship_harmonisation.constants import IDO, TWINSHIP
from twinship_harmonisation.low_level.vessel_functions import (
    add_optional_code,
    add_optional_double,
    create_twinship_uri,
    get_twinship_type_uri,
)


def create_twinship_pms(
    namespace: str,
    pms_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for a Power Management System.

    Returns:
        Tuple of (pms_uri, graph).
    """
    g = Graph()
    pms_uri = create_twinship_uri(pms_id, namespace)

    # Type assertions
    g.add((pms_uri, RDF.type, TWINSHIP.Pms))
    if types:
        for type_name in types:
            type_uri = get_twinship_type_uri(type_name)
            if type_uri and type_uri != TWINSHIP.Pms:
                g.add((pms_uri, RDF.type, type_uri))

    # Relationship to vessel
    g.add((pms_uri, IDO.partOf, vessel_uri))

    # Label
    if label:
        g.add((pms_uri, RDFS.label, Literal(label)))

    return pms_uri, g


def create_twinship_emergency_generator(
    namespace: str,
    emergency_generator_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    power_max_kw: float | None = None,
    speed_max_rpm: float | None = None,
    do_mode: int | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for an Emergency Generator.

    Returns:
        Tuple of (emergency_generator_uri, graph).
    """
    g = Graph()
    emergency_generator_uri = create_twinship_uri(emergency_generator_id, namespace)

    # Type assertions - EmergencyEquipment and DieselEngine
    g.add((emergency_generator_uri, RDF.type, TWINSHIP.EmergencyEquipment))
    g.add((emergency_generator_uri, RDF.type, TWINSHIP.DieselEngine))
    if types:
        for type_name in types:
            type_uri = get_twinship_type_uri(type_name)
            if type_uri:
                g.add((emergency_generator_uri, RDF.type, type_uri))

    # Relationship to vessel
    g.add((emergency_generator_uri, IDO.partOf, vessel_uri))

    # Label
    if label:
        g.add((emergency_generator_uri, RDFS.label, Literal(label)))

    # Data properties
    add_optional_double(
        g, emergency_generator_uri, TWINSHIP.twEmergencyDieselGeneratorPowerMaxInKW, power_max_kw
    )
    add_optional_double(
        g,
        emergency_generator_uri,
        TWINSHIP.twEmergencyDieselGeneratorSpeedMaxInRevPerMin,
        speed_max_rpm,
    )
    add_optional_code(
        g, emergency_generator_uri, TWINSHIP.twEmergencyDieselGeneratorEmergencyDOMode, do_mode
    )

    return emergency_generator_uri, g


def create_twinship_thruster(
    namespace: str,
    thruster_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    power_max_kw: float | None = None,
    speed_max_rpm: float | None = None,
    is_bow: bool = True,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for a Thruster (bow or stern).

    Returns:
        Tuple of (thruster_uri, graph).
    """
    g = Graph()
    thruster_uri = create_twinship_uri(thruster_id, namespace)

    # Type assertions
    g.add((thruster_uri, RDF.type, TWINSHIP.Maneuvering))
    if types:
        for type_name in types:
            type_uri = get_twinship_type_uri(type_name)
            if type_uri and type_uri != TWINSHIP.Maneuvering:
                g.add((thruster_uri, RDF.type, type_uri))

    # Relationship to vessel
    g.add((thruster_uri, IDO.partOf, vessel_uri))

    # Label
    if label:
        g.add((thruster_uri, RDFS.label, Literal(label)))

    # Data properties - use bow or stern property depending on thruster type
    if is_bow:
        add_optional_double(g, thruster_uri, TWINSHIP.twBowThrusterPowerMaxInKW, power_max_kw)
        add_optional_double(
            g, thruster_uri, TWINSHIP.twBowThrusterSpeedMaxInRevPerMin, speed_max_rpm
        )
    else:
        add_optional_double(g, thruster_uri, TWINSHIP.twSternThrusterPowerMaxInKW, power_max_kw)
        add_optional_double(
            g, thruster_uri, TWINSHIP.twSternThrusterSpeedMaxInRevPerMin, speed_max_rpm
        )

    return thruster_uri, g


def create_twinship_shaft_generator(
    namespace: str,
    shaft_generator_id: str,
    vessel_uri: URIRef,
    label: str | None = None,
    types: list[str] | None = None,
    power_max_kw: float | None = None,
    speed_max_rpm: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for a Shaft Generator.

    Returns:
        Tuple of (shaft_generator_uri, graph).
    """
    g = Graph()
    shaft_generator_uri = create_twinship_uri(shaft_generator_id, namespace)

    # Type assertions
    g.add((shaft_generator_uri, RDF.type, TWINSHIP.ShaftGeneratorSystem))
    if types:
        for type_name in types:
            type_uri = get_twinship_type_uri(type_name)
            if type_uri:
                g.add((shaft_generator_uri, RDF.type, type_uri))

    # Relationship to vessel
    g.add((shaft_generator_uri, IDO.partOf, vessel_uri))

    # Label
    if label:
        g.add((shaft_generator_uri, RDFS.label, Literal(label)))

    # Data properties
    add_optional_double(g, shaft_generator_uri, TWINSHIP.twShaftGeneratorPowerMaxInKW, power_max_kw)
    add_optional_double(
        g, shaft_generator_uri, TWINSHIP.twShaftGeneratorSpeedMaxInRevPerMin, speed_max_rpm
    )

    return shaft_generator_uri, g
