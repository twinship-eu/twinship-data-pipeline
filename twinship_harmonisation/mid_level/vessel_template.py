"""Mid-level templates for vessel data patterns."""

from rdflib import Graph, URIRef

from twinship_harmonisation.constants import TWINSHIP
from twinship_harmonisation.low_level.engine_functions import (
    create_auxiliary_engine,
    create_engine_uri,
    create_main_engine,
)
from twinship_harmonisation.low_level.fuel_functions import add_fuel_consumption, get_fuel_uri
from twinship_harmonisation.low_level.vessel_functions import create_vessel, create_vessel_uri


def create_vessel_with_engines(
    vessel_id: str,
    namespace: str,
    vessel_label: str | None = None,
    vessel_type: str | None = None,
    main_engines: list[dict] | None = None,
    auxiliary_engines: list[dict] | None = None,
) -> tuple[URIRef, Graph]:
    """Create a vessel with its engine systems.

    Args:
        vessel_id: Unique vessel identifier.
        namespace: Namespace for the vessel (e.g., 'stena-tanker').
        vessel_label: Human-readable vessel name.
        vessel_type: Vessel type ('RoPax', 'RoRo', 'Tanker').
        main_engines: List of main engine specifications.
        auxiliary_engines: List of auxiliary engine specifications.

    Returns:
        Tuple of (vessel_uri, graph) containing all triples.

    Example:
        >>> uri, g = create_vessel_with_engines(
        ...     vessel_id="IMO-1234567",
        ...     namespace="my-vessel",
        ...     vessel_label="MV Example",
        ...     vessel_type="RoPax",
        ...     main_engines=[{
        ...         "id": "ME-1",
        ...         "label": "Main Engine 1",
        ...         "power_max_kw": 12000,
        ...         "fuels": ["HFO", "MGO"],
        ...     }],
        ... )
    """
    g = Graph()

    # Create vessel
    vessel_uri = create_vessel_uri(vessel_id, namespace)
    vessel_type_uri = _get_vessel_type_uri(vessel_type) if vessel_type else None
    g += create_vessel(vessel_uri, vessel_type=vessel_type_uri, label=vessel_label)

    # Create main engines
    if main_engines:
        for engine_spec in main_engines:
            engine_uri = create_engine_uri(engine_spec["id"], namespace)
            g += create_main_engine(
                engine_uri=engine_uri,
                vessel_uri=vessel_uri,
                label=engine_spec.get("label"),
                power_max_kw=engine_spec.get("power_max_kw"),
                shaft_power_max_kw=engine_spec.get("shaft_power_max_kw"),
                shaft_speed_max_rpm=engine_spec.get("shaft_speed_max_rpm"),
                shaft_torque_max_knm=engine_spec.get("shaft_torque_max_knm"),
                is_two_stroke=engine_spec.get("is_two_stroke", False),
                is_four_stroke=engine_spec.get("is_four_stroke", False),
            )
            # Add fuel consumption relationships
            for fuel_type in engine_spec.get("fuels", []):
                g += add_fuel_consumption(engine_uri, get_fuel_uri(fuel_type))

    # Create auxiliary engines
    if auxiliary_engines:
        for engine_spec in auxiliary_engines:
            engine_uri = create_engine_uri(engine_spec["id"], namespace)
            g += create_auxiliary_engine(
                engine_uri=engine_uri,
                vessel_uri=vessel_uri,
                label=engine_spec.get("label"),
                power_max_kw=engine_spec.get("power_max_kw"),
                speed_rpm=engine_spec.get("speed_rpm"),
                is_diesel=engine_spec.get("is_diesel", True),
            )
            # Add fuel consumption relationships
            for fuel_type in engine_spec.get("fuels", []):
                g += add_fuel_consumption(engine_uri, get_fuel_uri(fuel_type))

    return vessel_uri, g


def _get_vessel_type_uri(vessel_type: str) -> URIRef:
    """Map vessel type string to ontology class URI."""
    types = {
        "RoPax": TWINSHIP.RoPax,
        "RoRo": TWINSHIP.RoRo,
        "Tanker": TWINSHIP.Tanker,
    }
    if vessel_type not in types:
        raise ValueError(f"Unknown vessel type: {vessel_type}. Must be one of {list(types.keys())}")
    return types[vessel_type]
