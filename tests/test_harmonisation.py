"""Tests for the harmonisation library."""

from rdflib import RDF, RDFS, Literal

from twinship_harmonisation.constants import TWINSHIP
from twinship_harmonisation.high_level import harmonise_vessel_data
from twinship_harmonisation.low_level import (
    create_auxiliary_engine,
    create_engine_uri,
    create_main_engine,
    create_vessel,
    create_vessel_uri,
    get_fuel_uri,
)


def test_create_vessel_uri():
    """Test vessel URI creation."""
    uri = create_vessel_uri("IMO-1234567", "test-vessel")
    assert str(uri) == "https://twin-ship.eu/individuals/test-vessel/IMO-1234567"


def test_create_vessel():
    """Test vessel triple creation."""
    uri = create_vessel_uri("IMO-1234567", "test")
    g = create_vessel(
        uri,
        vessel_type=TWINSHIP.RoPax,
        label="Test Vessel",
        displacement_max_mt=10000.0,
    )

    assert (uri, RDF.type, TWINSHIP.VesselSystem) in g
    assert (uri, RDF.type, TWINSHIP.RoPax) in g
    assert (uri, RDFS.label, Literal("Test Vessel")) in g


def test_create_main_engine():
    """Test main engine triple creation."""
    vessel_uri = create_vessel_uri("IMO-1234567", "test")
    engine_uri = create_engine_uri("ME-1", "test")

    g = create_main_engine(
        engine_uri,
        vessel_uri=vessel_uri,
        label="Main Engine 1",
        power_max_kw=12000.0,
        is_two_stroke=True,
    )

    assert (engine_uri, RDF.type, TWINSHIP.MainEngineSystem) in g
    assert (engine_uri, RDF.type, TWINSHIP.TwoStroke) in g
    assert (engine_uri, TWINSHIP.componentOf, vessel_uri) in g
    assert (vessel_uri, TWINSHIP.hasComponent, engine_uri) in g


def test_create_auxiliary_engine():
    """Test auxiliary engine triple creation."""
    vessel_uri = create_vessel_uri("IMO-1234567", "test")
    engine_uri = create_engine_uri("AE-1", "test")

    g = create_auxiliary_engine(
        engine_uri,
        vessel_uri=vessel_uri,
        label="Auxiliary Engine 1",
        power_max_kw=2000.0,
    )

    assert (engine_uri, RDF.type, TWINSHIP.AuxiliaryEngineSystem) in g
    assert (engine_uri, RDF.type, TWINSHIP.DieselEngine) in g


def test_get_fuel_uri():
    """Test fuel URI retrieval."""
    assert get_fuel_uri("HFO") == TWINSHIP.HFO
    assert get_fuel_uri("mgo") == TWINSHIP.MGO
    assert get_fuel_uri("MDO") == TWINSHIP.MDO


def test_harmonise_vessel_data():
    """Test high-level harmonisation function."""
    g = harmonise_vessel_data(
        vessel_id="IMO-1234567",
        namespace="test",
        vessel_label="Test Vessel",
        vessel_type="RoPax",
        main_engines=[
            {
                "id": "ME-1",
                "label": "Main Engine 1",
                "power_max_kw": 12000,
                "fuels": ["HFO", "MGO"],
            }
        ],
        auxiliary_engines=[
            {
                "id": "AE-1",
                "label": "Auxiliary Engine 1",
                "power_max_kw": 2000,
                "fuels": ["MGO"],
            }
        ],
    )

    # Should have vessel, main engine, auxiliary engine, and fuel relationships
    assert len(g) > 10

    # Check vessel exists
    vessel_uri = create_vessel_uri("IMO-1234567", "test")
    assert (vessel_uri, RDF.type, TWINSHIP.VesselSystem) in g

    # Check fuel consumption relationship exists
    engine_uri = create_engine_uri("ME-1", "test")
    assert (engine_uri, TWINSHIP.consume, TWINSHIP.HFO) in g
