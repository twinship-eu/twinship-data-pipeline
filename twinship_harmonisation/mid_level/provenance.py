"""Mid-level functions for TwinShip provenance metadata."""

from rdflib import Graph, URIRef

from twinship_harmonisation.low_level import build_pav_provenance

TWINSHIP_PIPELINE_URI = "https://twin-ship.eu/tools/twinship-data-pipeline"


def twinship_provenance_graph(
    subject: URIRef,
    source_file: str | None = None,
    version: str | None = None,
) -> Graph:
    """Build TwinShip provenance graph for a subject.

    Attaches PAV metadata identifying the TwinShip data pipeline
    as the creator, with optional source file and version.

    Args:
        subject: The URI to attach provenance metadata to.
        source_file: URI identifying the source data file.
        version: Version string for the pipeline.

    Returns:
        Graph with PAV provenance triples.
    """
    return build_pav_provenance(
        subject,
        created_by=TWINSHIP_PIPELINE_URI,
        derived_from=source_file,
        version=version,
    )
