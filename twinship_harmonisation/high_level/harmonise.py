"""High-level harmonisation functions for vessel data."""

import json
from pathlib import Path

from rdflib import Graph

from twinship_harmonisation.mid_level.vessel_template import create_vessel_with_engines
from twinship_harmonisation.utils import bind_namespaces


def harmonise_vessel_data(
    vessel_id: str,
    namespace: str,
    vessel_label: str | None = None,
    vessel_type: str | None = None,
    main_engines: list[dict] | None = None,
    auxiliary_engines: list[dict] | None = None,
) -> Graph:
    """Harmonise vessel data into RDF triples.

    This is the main entry point for converting vessel data
    into TwinShip-compliant RDF.

    Args:
        vessel_id: Unique vessel identifier.
        namespace: Namespace for the vessel individuals.
        vessel_label: Human-readable vessel name.
        vessel_type: Vessel type ('RoPax', 'RoRo', 'Tanker').
        main_engines: List of main engine specifications.
        auxiliary_engines: List of auxiliary engine specifications.

    Returns:
        RDFLib Graph with namespace bindings applied.

    Example:
        >>> g = harmonise_vessel_data(
        ...     vessel_id="IMO-1234567",
        ...     namespace="my-vessel",
        ...     vessel_label="MV Example",
        ...     vessel_type="RoPax",
        ...     main_engines=[{"id": "ME-1", "power_max_kw": 12000}],
        ... )
        >>> print(g.serialize(format="turtle"))
    """
    _, g = create_vessel_with_engines(
        vessel_id=vessel_id,
        namespace=namespace,
        vessel_label=vessel_label,
        vessel_type=vessel_type,
        main_engines=main_engines,
        auxiliary_engines=auxiliary_engines,
    )
    return bind_namespaces(g)


def harmonise_vessel_json(json_path: str | Path) -> Graph:
    """Harmonise vessel data from a JSON file.

    Args:
        json_path: Path to JSON file containing vessel data.

    Returns:
        RDFLib Graph with all vessel data.

    The JSON file should have the structure:
    {
        "vessel_id": "IMO-1234567",
        "namespace": "my-vessel",
        "vessel_label": "MV Example",
        "vessel_type": "RoPax",
        "main_engines": [...],
        "auxiliary_engines": [...]
    }
    """
    with open(json_path) as f:
        data = json.load(f)

    return harmonise_vessel_data(
        vessel_id=data["vessel_id"],
        namespace=data["namespace"],
        vessel_label=data.get("vessel_label"),
        vessel_type=data.get("vessel_type"),
        main_engines=data.get("main_engines"),
        auxiliary_engines=data.get("auxiliary_engines"),
    )
