"""Low-level functions for creating TwinShip connection relationships."""

from rdflib import Graph, URIRef

from twinship_harmonisation.constants import IDO


def build_twinship_connection(
    subject_uri: URIRef,
    object_uri: URIRef,
) -> Graph:
    """Build a graph with a connectedTo relationship between two components.

    This is a symmetric relationship for general (non-physical) connections,
    e.g. electrical connections via PMS.

    Args:
        subject_uri: First component URI.
        object_uri: Second component URI.

    Returns:
        Graph containing bidirectional connection triples.
    """
    g = Graph()
    g.add((subject_uri, IDO.connectedTo, object_uri))
    g.add((object_uri, IDO.connectedTo, subject_uri))
    return g


def build_twinship_direct_connection(
    subject_uri: URIRef,
    object_uri: URIRef,
) -> Graph:
    """Build a graph with a directlyConnectedTo relationship between two components.

    This is a symmetric relationship, so both directions are added.

    Args:
        subject_uri: First component URI.
        object_uri: Second component URI.

    Returns:
        Graph containing bidirectional connection triples.
    """
    g = Graph()
    g.add((subject_uri, IDO.directlyConnectedTo, object_uri))
    g.add((object_uri, IDO.directlyConnectedTo, subject_uri))
    return g
