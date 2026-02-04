"""Low-level functions for creating connection relationships."""

from rdflib import Graph, URIRef

from twinship_harmonisation.constants import IDO


def add_direct_connection(
    g: Graph,
    subject_uri: URIRef,
    object_uri: URIRef,
) -> None:
    """Add a directlyConnectedTo relationship between two components.

    This is a symmetric relationship, so we add both directions.

    Args:
        g: Graph to add triples to.
        subject_uri: First component URI.
        object_uri: Second component URI.
    """
    g.add((subject_uri, IDO.directlyConnectedTo, object_uri))
    g.add((object_uri, IDO.directlyConnectedTo, subject_uri))
