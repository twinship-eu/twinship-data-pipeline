"""Low-level functions for creating engine-related RDF triples."""

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from twinship_harmonisation.constants import TWINSHIP, TWINSHIP_IND
from twinship_harmonisation.utils import sanitize_id


def create_engine_uri(engine_id: str, namespace: str | None = None) -> URIRef:
    """Create a URI for an engine individual.

    Args:
        engine_id: Unique identifier for the engine.
        namespace: Optional namespace suffix (e.g., 'stena-tanker').

    Returns:
        URIRef for the engine.
    """
    if namespace:
        base = Namespace(f"{TWINSHIP_IND}{namespace}/")
    else:
        base = TWINSHIP_IND
    return base[sanitize_id(engine_id)]


def create_main_engine(
    engine_uri: URIRef,
    vessel_uri: URIRef | None = None,
    label: str | None = None,
    power_max_kw: float | None = None,
    shaft_power_max_kw: float | None = None,
    shaft_speed_max_rpm: float | None = None,
    shaft_torque_max_knm: float | None = None,
    is_two_stroke: bool = False,
    is_four_stroke: bool = False,
) -> Graph:
    """Create RDF triples for a main engine system.

    Args:
        engine_uri: URI for the engine individual.
        vessel_uri: Optional URI of the vessel this engine belongs to.
        label: Optional human-readable label.
        power_max_kw: Maximum engine power in kW.
        shaft_power_max_kw: Maximum shaft power in kW.
        shaft_speed_max_rpm: Maximum shaft speed in RPM.
        shaft_torque_max_knm: Maximum shaft torque in kNm.
        is_two_stroke: Whether this is a two-stroke engine.
        is_four_stroke: Whether this is a four-stroke engine.

    Returns:
        Graph containing the engine triples.
    """
    g = Graph()

    # Type assertions
    g.add((engine_uri, RDF.type, TWINSHIP.MainEngineSystem))
    if is_two_stroke:
        g.add((engine_uri, RDF.type, TWINSHIP.TwoStroke))
    if is_four_stroke:
        g.add((engine_uri, RDF.type, TWINSHIP.FourStroke))

    # Relationship to vessel
    if vessel_uri:
        g.add((engine_uri, TWINSHIP.componentOf, vessel_uri))
        g.add((vessel_uri, TWINSHIP.hasComponent, engine_uri))

    # Label
    if label:
        g.add((engine_uri, RDFS.label, Literal(label)))

    # Data properties
    if power_max_kw is not None:
        g.add(
            (
                engine_uri,
                TWINSHIP.twPowerMaxInKW,
                Literal(power_max_kw, datatype=XSD.double),
            )
        )

    if shaft_power_max_kw is not None:
        g.add(
            (
                engine_uri,
                TWINSHIP.twShaftPowerMaxInKW,
                Literal(shaft_power_max_kw, datatype=XSD.double),
            )
        )

    if shaft_speed_max_rpm is not None:
        g.add(
            (
                engine_uri,
                TWINSHIP.twShaftSpeedMaxInRevPerMin,
                Literal(shaft_speed_max_rpm, datatype=XSD.double),
            )
        )

    if shaft_torque_max_knm is not None:
        g.add(
            (
                engine_uri,
                TWINSHIP.twShaftTorqueMaxInKnm,
                Literal(shaft_torque_max_knm, datatype=XSD.double),
            )
        )

    return g


def create_auxiliary_engine(
    engine_uri: URIRef,
    vessel_uri: URIRef | None = None,
    label: str | None = None,
    power_max_kw: float | None = None,
    speed_rpm: float | None = None,
    is_diesel: bool = True,
) -> Graph:
    """Create RDF triples for an auxiliary engine system.

    Args:
        engine_uri: URI for the engine individual.
        vessel_uri: Optional URI of the vessel this engine belongs to.
        label: Optional human-readable label.
        power_max_kw: Maximum engine power in kW.
        speed_rpm: Engine speed in RPM.
        is_diesel: Whether this is a diesel engine (default True).

    Returns:
        Graph containing the engine triples.
    """
    g = Graph()

    # Type assertions
    g.add((engine_uri, RDF.type, TWINSHIP.AuxiliaryEngineSystem))
    if is_diesel:
        g.add((engine_uri, RDF.type, TWINSHIP.DieselEngine))

    # Relationship to vessel
    if vessel_uri:
        g.add((engine_uri, TWINSHIP.componentOf, vessel_uri))
        g.add((vessel_uri, TWINSHIP.hasComponent, engine_uri))

    # Label
    if label:
        g.add((engine_uri, RDFS.label, Literal(label)))

    # Data properties
    if power_max_kw is not None:
        g.add(
            (
                engine_uri,
                TWINSHIP.twDieselEnginePowerMaxInKW,
                Literal(power_max_kw, datatype=XSD.double),
            )
        )

    if speed_rpm is not None:
        g.add(
            (
                engine_uri,
                TWINSHIP.twDieselEngineSpeedInRevPerMin,
                Literal(speed_rpm, datatype=XSD.double),
            )
        )

    return g
