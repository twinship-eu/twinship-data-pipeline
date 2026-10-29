"""Dagster resources for TwinShip pipeline."""

from pathlib import Path

from dagster import ConfigurableResource
from pyshacl import validate
from rdflib import Graph

from dagster_pipeline.resources.graphdb import GraphDBClient, graphdb_client
from dagster_pipeline.resources.keycloak import KeycloakTokenProvider, keycloak_token_provider


class ShaclValidator(ConfigurableResource):
    """Resource for SHACL validation of RDF graphs."""

    def validate(self, data_graph: Graph, shapes_path: Path) -> tuple[bool, str]:
        """Validate an RDF graph against SHACL shapes.

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
