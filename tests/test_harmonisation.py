"""Tests for the harmonisation library."""

from rdflib import RDF, RDFS, Literal

from twinship_harmonisation.constants import TWINSHIP
from twinship_harmonisation.high_level import harmonise_vessel_data
from twinship_harmonisation.low_level import (
    add_fuel_consumption,
    create_auxiliary_engine,
    create_main_engine,
    create_uri,
    create_vessel,
    get_fuel_uri,
)


def test_create_uri():
    """Test URI creation."""
    uri = create_uri("IMO-1234567", "test-vessel")
    assert str(uri) == "https://twin-ship.eu/individuals/test-vessel/IMO-1234567"


def test_create_vessel():
    """Test vessel triple creation."""
    vessel_uri, g = create_vessel(
        namespace="test",
        vessel_id="IMO-1234567",
        vessel_type="RoPax",
        label="Test Vessel",
        displacement_max_mt=10000.0,
    )

    assert str(vessel_uri) == "https://twin-ship.eu/individuals/test/IMO-1234567"
    assert (vessel_uri, RDF.type, TWINSHIP.VesselSystem) in g
    assert (vessel_uri, RDF.type, TWINSHIP.RoPax) in g
    assert (vessel_uri, RDFS.label, Literal("Test Vessel")) in g


def test_create_main_engine():
    """Test main engine triple creation."""
    vessel_uri = create_uri("IMO-1234567", "test")

    engine_uri, g = create_main_engine(
        namespace="test",
        engine_id="ME-1",
        vessel_uri=vessel_uri,
        label="Main Engine 1",
        types=["TwoStroke"],
        shaft_power_max_kw=12000.0,
    )

    assert (engine_uri, RDF.type, TWINSHIP.MainEngineSystem) in g
    assert (engine_uri, RDF.type, TWINSHIP.TwoStroke) in g
    assert (engine_uri, TWINSHIP.componentOf, vessel_uri) in g
    assert (vessel_uri, TWINSHIP.hasComponent, engine_uri) in g


def test_create_auxiliary_engine():
    """Test auxiliary engine triple creation."""
    vessel_uri = create_uri("IMO-1234567", "test")

    engine_uri, g = create_auxiliary_engine(
        namespace="test",
        engine_id="AE-1",
        vessel_uri=vessel_uri,
        label="Auxiliary Engine 1",
        types=["FourStroke", "DieselEngine"],
        generator_power_max_kw=2000.0,
    )

    assert (engine_uri, RDF.type, TWINSHIP.AuxiliaryEngineSystem) in g
    assert (engine_uri, RDF.type, TWINSHIP.DieselEngine) in g
    assert (engine_uri, RDF.type, TWINSHIP.FourStroke) in g


def test_get_fuel_uri():
    """Test fuel URI retrieval."""
    assert get_fuel_uri("HFO") == TWINSHIP.HFO
    assert get_fuel_uri("mgo") == TWINSHIP.MGO
    assert get_fuel_uri("MDO") == TWINSHIP.MDO
    assert get_fuel_uri("unknown") is None


def test_add_fuel_consumption():
    """Test fuel consumption triple creation."""
    from rdflib import Graph

    g = Graph()
    engine_uri = create_uri("ME-1", "test")
    add_fuel_consumption(g, engine_uri, ["HFO", "MGO"])

    assert (engine_uri, TWINSHIP.consume, TWINSHIP.HFO) in g
    assert (engine_uri, TWINSHIP.consume, TWINSHIP.MGO) in g


def test_harmonise_vessel_data():
    """Test high-level harmonisation function."""
    data = {
        "namespace": "test",
        "operator": "Test Operator",
        "vessel": {
            "id": "IMO-1234567",
            "label": "Test Vessel",
            "type": "RoPax",
            "displacement_max_mt": 10000.0,
        },
        "main_engines": [
            {
                "id": "ME-1",
                "name": "Main Engine 1",
                "types": ["TwoStroke"],
                "shaft_power_max_kw": 12000,
                "fuels": ["HFO", "MGO"],
            }
        ],
        "auxiliary_engines": [
            {
                "id": "AE-1",
                "name": "Auxiliary Engine 1",
                "types": ["FourStroke", "DieselEngine"],
                "generator_power_max_kw": 2000,
                "fuels": ["MGO"],
            }
        ],
        "propellers": [],
        "gearboxes": [],
        "boilers": [],
    }
    g = harmonise_vessel_data(data)

    # Should have vessel, main engine, auxiliary engine, and fuel relationships
    assert len(g) > 10

    # Check vessel exists
    vessel_uri = create_uri("IMO-1234567", "test")
    assert (vessel_uri, RDF.type, TWINSHIP.VesselSystem) in g

    # Check fuel consumption relationship exists
    engine_uri = create_uri("ME-1", "test")
    assert (engine_uri, TWINSHIP.consume, TWINSHIP.HFO) in g
