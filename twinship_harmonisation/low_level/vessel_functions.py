"""Low-level functions for creating vessel-related RDF triples."""

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS, XSD

from twinship_harmonisation.constants import TWINSHIP, TWINSHIP_IND
from twinship_harmonisation.utils import sanitize_id


def create_vessel_uri(vessel_id: str, namespace: str | None = None) -> URIRef:
    """Create a URI for a vessel individual.

    Args:
        vessel_id: Unique identifier for the vessel (e.g., IMO number).
        namespace: Optional namespace suffix (e.g., 'stena-tanker').

    Returns:
        URIRef for the vessel.
    """
    if namespace:
        base = Namespace(f"{TWINSHIP_IND}{namespace}/")
    else:
        base = TWINSHIP_IND
    return base[sanitize_id(vessel_id)]


def create_vessel(
    vessel_uri: URIRef,
    vessel_type: URIRef | None = None,
    label: str | None = None,
    displacement_max_mt: float | None = None,
    power_propulsion_total_kw: float | None = None,
) -> Graph:
    """Create RDF triples for a vessel.

    Args:
        vessel_uri: URI for the vessel individual.
        vessel_type: Optional vessel type class (e.g., TWINSHIP.RoPax).
        label: Optional human-readable label.
        displacement_max_mt: Maximum displacement in metric tons.
        power_propulsion_total_kw: Total propulsion power in kW.

    Returns:
        Graph containing the vessel triples.
    """
    g = Graph()

    # Type assertions
    g.add((vessel_uri, RDF.type, TWINSHIP.VesselSystem))
    if vessel_type:
        g.add((vessel_uri, RDF.type, vessel_type))

    # Label
    if label:
        g.add((vessel_uri, RDFS.label, Literal(label)))

    # Data properties
    if displacement_max_mt is not None:
        g.add(
            (
                vessel_uri,
                TWINSHIP.twDisplacementMaxInMT,
                Literal(displacement_max_mt, datatype=XSD.double),
            )
        )

    if power_propulsion_total_kw is not None:
        g.add(
            (
                vessel_uri,
                TWINSHIP.twPowerPropulsionTotalInKw,
                Literal(power_propulsion_total_kw, datatype=XSD.double),
            )
        )

    return g
