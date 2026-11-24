"""Dagster resources for TwinShip pipeline."""

from pathlib import Path

from dagster import ConfigurableResource
from pyshacl import validate
from rdflib import OWL, RDF, RDFS, Graph

from dagster_pipeline.resources.graphdb import GraphDBClient, graphdb_client
from dagster_pipeline.resources.keycloak import KeycloakTokenProvider, keycloak_token_provider


def ontology_individuals(ontology_path: Path) -> Graph:
    """Types and labels of the ontology's named individuals (e.g. tws:SOG, the fuels).

    Data refers to these individuals without repeating them; the validator needs their
    types for sh:class checks, and the fuel shape needs their labels. Only these triples
    are used, not the whole ontology: RDFS inference over the full ontology is slow and
    adds supertypes to the data.
    """
    ontology = Graph()
    if ontology_path.is_dir():
        for ttl_file in sorted(ontology_path.rglob("*.ttl")):
            ontology.parse(str(ttl_file), format="turtle")
    individuals = Graph()
    for individual in ontology.subjects(RDF.type, OWL.NamedIndividual):
        for prop in (RDF.type, RDFS.label):
            for value in ontology.objects(individual, prop):
                individuals.add((individual, prop, value))
    return individuals


class ShaclValidator(ConfigurableResource):
    """Resource for SHACL validation of RDF graphs."""

    ontology_path: str = "ontology/"

    def validate(self, data_graph: Graph, shapes_path: Path) -> tuple[bool, str]:
        """Validate an RDF graph against SHACL shapes.

        The types and labels of the ontology's named individuals (from ontology_path)
        are added as ont_graph, so data can refer to tws:SOG and the like without
        repeating them.

        Args:
            data_graph: The RDF graph to validate.
            shapes_path: Path to a SHACL shapes file or directory of .ttl files
                (subdirectories included).

        Returns:
            Tuple of (conforms, report_text).
        """
        shapes_graph = Graph()
        shapes_path = Path(str(shapes_path))

        if shapes_path.is_dir():
            for ttl_file in sorted(shapes_path.rglob("*.ttl")):
                shapes_graph.parse(str(ttl_file), format="turtle")
        else:
            shapes_graph.parse(str(shapes_path), format="turtle")

        conforms, results_graph, results_text = validate(
            data_graph,
            shacl_graph=shapes_graph,
            ont_graph=ontology_individuals(Path(self.ontology_path)),
            inference="rdfs",
            abort_on_first=False,
        )

        return conforms, results_text


# Default resource instance
shacl_validator = ShaclValidator()

__all__ = [
    "GraphDBClient",
    "KeycloakTokenProvider",
    "ShaclValidator",
    "graphdb_client",
    "keycloak_token_provider",
    "shacl_validator",
]
