"""Low-level functions for creating vessel-related RDF triples."""

from datetime import UTC, datetime

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from twinship_harmonisation.constants import PAV, TWINSHIP, TWINSHIP_IND


def create_twinship_uri(entity_id: str, namespace: str) -> URIRef:
    """Create a TwinShip URI for an entity individual.

    Args:
        entity_id: Unique identifier for the entity.
        namespace: Namespace suffix (e.g., 'stena-tanker').

    Returns:
        URIRef for the entity.
    """
    base = Namespace(f"{TWINSHIP_IND}{namespace}/")
    return base[entity_id]


def get_twinship_type_uri(type_name: str) -> URIRef | None:
    """Map a type name to its TwinShip ontology class URI.

    Args:
        type_name: Type name from JSON (e.g., 'TwoStroke', 'CPP').

    Returns:
        URIRef for the class, or None if not recognized.
    """
    type_map = {
        # Vessel types
        "RoRo": TWINSHIP.RoRo,
        "RoPax": TWINSHIP.RoPax,
        "Tanker": TWINSHIP.Tanker,
        # Engine types
        "TwoStroke": TWINSHIP.TwoStroke,
        "FourStroke": TWINSHIP.FourStroke,
        "DieselEngine": TWINSHIP.DieselEngine,
        "MechanicalConfiguration": TWINSHIP.MechanicalConfiguration,
        # Futuristic engine/configuration types
        "GenSetSystem": TWINSHIP.GenSetSystem,
        "DieselElectricConfiguration": TWINSHIP.DieselElectricConfiguration,
        "AC": TWINSHIP.AC,
        "DC": TWINSHIP.DC,
        "ESD": TWINSHIP.ESD,
        # Propeller types
        "CPP": TWINSHIP.CPP,
        "FPP": TWINSHIP.FPP,
        # Gearbox types
        "DirectDrive": TWINSHIP.DirectDrive,
        "Reduction": TWINSHIP.Reduction,
        "SingleSpeed": TWINSHIP.SingleSpeed,
        "TISO": TWINSHIP.TISO,
        "PTO": TWINSHIP.PTO,
        # PMS
        "Pms": TWINSHIP.Pms,
        "PMS": TWINSHIP.Pms,
        # Emergency equipment
        "EmergencyEquipment": TWINSHIP.EmergencyEquipment,
        # Thrusters / Maneuvering
        "Maneuvering": TWINSHIP.Maneuvering,
        "BowThruster": TWINSHIP.BowThruster,
        "Bow": TWINSHIP.Bow,
        # Shaft generators
        "ShaftGeneratorSystem": TWINSHIP.ShaftGeneratorSystem,
        "RGShaftGenerator": TWINSHIP.RGShaftGenerator,
        # Boiler
        "Boiler": TWINSHIP.Boiler,
        # Futuristic component types
        "EnergyStorageSystem": TWINSHIP.EnergyStorageSystem,
        "BidirectionalConverterSystem": TWINSHIP.BidirectionalConverterSystem,
        "SCR": TWINSHIP.SCR,
        "EmissionReduction": TWINSHIP.SCR,
        "AUXLOAD": TWINSHIP.AUXLOAD,
        "ShipServices": TWINSHIP.ShipServices,
        "HotelLoad": TWINSHIP.HotelLoad,
        "OSP": TWINSHIP.OSP,
        "FrequencyConverterSystem": TWINSHIP.FrequencyConverterSystem,
        "ElectricMotorSystem": TWINSHIP.ElectricMotorSystem,
        "ElectricMotorShaft": TWINSHIP.ElectricMotorShaft,
        "GateRudder": TWINSHIP.GateRudder,
        "WindAssistedPropulsionSystem": TWINSHIP.WindAssistedPropulsionSystem,
        "SuctionSail": TWINSHIP.SuctionSail,
        "AirLubricationSystem": TWINSHIP.AirLubricationSystem,
        "DynamicWing": TWINSHIP.DynamicWing,
        "FuelCellSystem": TWINSHIP.FuelCellSystem,
    }
    return type_map.get(type_name)


def add_optional_double(
    g: Graph,
    subject: URIRef,
    predicate: URIRef,
    value: float | int | None,
) -> None:
    """Add an optional double-valued triple if value is not None."""
    if value is not None:
        g.add((subject, predicate, Literal(float(value), datatype=XSD.double)))


def add_optional_integer(
    g: Graph,
    subject: URIRef,
    predicate: URIRef,
    value: int | None,
) -> None:
    """Add an optional integer-valued triple if value is not None."""
    if value is not None:
        g.add((subject, predicate, Literal(int(value), datatype=XSD.integer)))


def add_optional_string(
    g: Graph,
    subject: URIRef,
    predicate: URIRef,
    value: str | None,
) -> None:
    """Add an optional string-valued triple if value is not None."""
    if value is not None and value.strip():
        g.add((subject, predicate, Literal(value, datatype=XSD.string)))


def create_twinship_vessel(
    namespace: str,
    vessel_id: str,
    label: str | None = None,
    vessel_type: str | None = None,
    displacement_max_mt: float | None = None,
    draft_aft_max_m: float | None = None,
    draft_for_max_m: float | None = None,
    draft_mid_port_max_m: float | None = None,
    draft_mid_stbd_max_m: float | None = None,
    depth_of_water_max_m: float | None = None,
) -> tuple[URIRef, Graph]:
    """Create TwinShip RDF triples for a vessel.

    Returns:
        Tuple of (vessel_uri, graph).
    """
    g = Graph()
    vessel_uri = create_twinship_uri(vessel_id, namespace)

    # Type assertions
    g.add((vessel_uri, RDF.type, TWINSHIP.VesselSystem))
    if vessel_type:
        type_uri = get_twinship_type_uri(vessel_type)
        if type_uri:
            g.add((vessel_uri, RDF.type, type_uri))

    # Label
    if label:
        g.add((vessel_uri, RDFS.label, Literal(label)))

    # Data properties
    add_optional_double(g, vessel_uri, TWINSHIP.twDisplacementMaxInMT, displacement_max_mt)
    add_optional_double(g, vessel_uri, TWINSHIP.twVesselDraftAftMaxInM, draft_aft_max_m)
    add_optional_double(g, vessel_uri, TWINSHIP.twVesselDraftForMaxInM, draft_for_max_m)
    add_optional_double(g, vessel_uri, TWINSHIP.twVesselDraftMidPortMaxInM, draft_mid_port_max_m)
    add_optional_double(g, vessel_uri, TWINSHIP.twVesselDraftMidStbdMaxInM, draft_mid_stbd_max_m)
    add_optional_double(g, vessel_uri, TWINSHIP.twVesselDepthOfWaterMaxInM, depth_of_water_max_m)

    return vessel_uri, g


def build_pav_provenance(
    subject: URIRef,
    created_by: str | None = None,
    derived_from: str | None = None,
    version: str | None = None,
) -> Graph:
    """Create PAV provenance triples for a subject.

    Args:
        subject: The URI to attach provenance metadata to.
        created_by: URI identifying the tool/agent that created the data.
        derived_from: URI identifying the source data.
        version: Version string for the pipeline/tool.

    Returns:
        Graph with PAV provenance triples.
    """
    g = Graph()
    g.add(
        (
            subject,
            PAV.createdOn,
            Literal(datetime.now(UTC).isoformat(), datatype=XSD.dateTime),
        )
    )
    if created_by:
        g.add((subject, PAV.createdBy, URIRef(created_by)))
    if derived_from:
        g.add((subject, PAV.derivedFrom, URIRef(derived_from)))
    if version:
        g.add((subject, PAV.version, Literal(version)))
    return g
