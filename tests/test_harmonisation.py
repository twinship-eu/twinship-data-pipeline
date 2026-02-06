"""Tests for the harmonisation library."""

from rdflib import RDF, RDFS, Literal

from twinship_harmonisation.constants import IDO, TWINSHIP
from twinship_harmonisation.high_level import harmonise_twinship_vessel
from twinship_harmonisation.low_level import (
    add_twinship_fuel_consumption,
    create_twinship_auxiliary_engine,
    create_twinship_main_engine,
    create_twinship_uri,
    create_twinship_vessel,
    get_twinship_fuel_uri,
)


def test_create_uri():
    """Test URI creation."""
    uri = create_twinship_uri("IMO-1234567", "test-vessel")
    assert str(uri) == "https://twin-ship.eu/individuals/test-vessel/IMO-1234567"


def test_create_vessel():
    """Test vessel triple creation."""
    vessel_uri, g = create_twinship_vessel(
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
    vessel_uri = create_twinship_uri("IMO-1234567", "test")

    engine_uri, g = create_twinship_main_engine(
        namespace="test",
        engine_id="ME-1",
        vessel_uri=vessel_uri,
        label="Main Engine 1",
        types=["TwoStroke"],
        shaft_power_max_kw=12000.0,
    )

    assert (engine_uri, RDF.type, TWINSHIP.MainEngineSystem) in g
    assert (engine_uri, RDF.type, TWINSHIP.TwoStroke) in g
    assert (engine_uri, IDO.partOf, vessel_uri) in g


def test_create_auxiliary_engine():
    """Test auxiliary engine triple creation."""
    vessel_uri = create_twinship_uri("IMO-1234567", "test")

    engine_uri, g = create_twinship_auxiliary_engine(
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
    assert get_twinship_fuel_uri("HFO") == TWINSHIP.HFO
    assert get_twinship_fuel_uri("mgo") == TWINSHIP.MGO
    assert get_twinship_fuel_uri("MDO") == TWINSHIP.MDO
    assert get_twinship_fuel_uri("unknown") is None


def test_add_fuel_consumption():
    """Test fuel consumption triple creation."""
    from rdflib import Graph

    g = Graph()
    engine_uri = create_twinship_uri("ME-1", "test")
    add_twinship_fuel_consumption(g, engine_uri, ["HFO", "MGO"])

    assert (engine_uri, TWINSHIP.consume, TWINSHIP.HFO) in g
    assert (engine_uri, TWINSHIP.consume, TWINSHIP.MGO) in g


def test_harmonise_twinship_vessel():
    """Test high-level harmonisation function."""
    data = {
        "namespace": "test",
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
    g = harmonise_twinship_vessel(**data)

    # Should have vessel, main engine, auxiliary engine, and fuel relationships
    assert len(g) > 10

    # Check vessel exists
    vessel_uri = create_twinship_uri("IMO-1234567", "test")
    assert (vessel_uri, RDF.type, TWINSHIP.VesselSystem) in g

    # Check fuel consumption relationship exists
    engine_uri = create_twinship_uri("ME-1", "test")
    assert (engine_uri, TWINSHIP.consume, TWINSHIP.HFO) in g


def test_connections():
    """Test that directlyConnectedTo triples are produced for linked components."""
    data = {
        "namespace": "test",
        "vessel": {
            "id": "IMO-9999999",
            "label": "Connection Test Vessel",
            "type": "RoPax",
        },
        "main_engines": [
            {
                "id": "ME-1",
                "name": "Main Engine 1",
                "types": ["TwoStroke"],
                "gearbox_id": "GB-1",
            },
        ],
        "auxiliary_engines": [
            {"id": "AE-1", "name": "Aux Engine 1", "types": ["FourStroke"]},
        ],
        "gearboxes": [
            {
                "id": "GB-1",
                "name": "Gearbox 1",
                "types": ["Reduction"],
                "propeller_id": "PROP-1",
            },
        ],
        "propellers": [
            {"id": "PROP-1", "name": "Propeller 1", "types": ["CPP"]},
        ],
        "pms": [
            {"id": "PMS-1", "name": "PMS 1", "types": ["Pms"]},
        ],
        "emergency_generators": [
            {"id": "EG-1", "name": "Emergency Gen 1", "types": ["EmergencyEquipment"]},
        ],
        "thrusters": [
            {"id": "THR-1", "name": "Thruster 1", "types": ["Maneuvering"]},
        ],
        "shaft_generators": [
            {"id": "SG-1", "name": "Shaft Gen 1", "types": ["ShaftGeneratorSystem"]},
        ],
        "boilers": [],
    }
    g = harmonise_twinship_vessel(**data)

    main_engine_uri = create_twinship_uri("ME-1", "test")
    gearbox_uri = create_twinship_uri("GB-1", "test")
    propeller_uri = create_twinship_uri("PROP-1", "test")
    pms_uri = create_twinship_uri("PMS-1", "test")
    auxiliary_engine_uri = create_twinship_uri("AE-1", "test")
    emergency_generator_uri = create_twinship_uri("EG-1", "test")
    thruster_uri = create_twinship_uri("THR-1", "test")
    shaft_generator_uri = create_twinship_uri("SG-1", "test")

    # Engine -> Gearbox (both directions)
    assert (main_engine_uri, IDO.directlyConnectedTo, gearbox_uri) in g
    assert (gearbox_uri, IDO.directlyConnectedTo, main_engine_uri) in g

    # Gearbox -> Propeller (both directions)
    assert (gearbox_uri, IDO.directlyConnectedTo, propeller_uri) in g
    assert (propeller_uri, IDO.directlyConnectedTo, gearbox_uri) in g

    # PMS connections (both directions)
    assert (auxiliary_engine_uri, IDO.directlyConnectedTo, pms_uri) in g
    assert (pms_uri, IDO.directlyConnectedTo, auxiliary_engine_uri) in g

    assert (emergency_generator_uri, IDO.directlyConnectedTo, pms_uri) in g
    assert (pms_uri, IDO.directlyConnectedTo, emergency_generator_uri) in g

    assert (thruster_uri, IDO.directlyConnectedTo, pms_uri) in g
    assert (pms_uri, IDO.directlyConnectedTo, thruster_uri) in g

    assert (shaft_generator_uri, IDO.directlyConnectedTo, pms_uri) in g
    assert (pms_uri, IDO.directlyConnectedTo, shaft_generator_uri) in g
