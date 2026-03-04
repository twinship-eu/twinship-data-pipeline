"""Tests for futuristic vessel harmonisation."""

from pathlib import Path

import pytest
from rdflib import RDF, RDFS, Literal

from twinship_harmonisation.constants import IDO, TWINSHIP
from twinship_harmonisation.high_level import harmonise_twinship_vessel
from twinship_harmonisation.low_level import (
    build_twinship_connection,
    create_twinship_uri,
)
from twinship_harmonisation.low_level.fuel_functions import get_twinship_fuel_uri
from twinship_harmonisation.low_level.futuristic_functions import (
    create_twinship_ammonia_fuel_cell,
    create_twinship_ess,
    create_twinship_genset,
)

# =============================================================================
# Low-level tests
# =============================================================================


class TestFuturisticCreateFunctions:
    def test_create_genset(self):
        vessel_uri = create_twinship_uri("FV-RR-1", "test")
        uri, g = create_twinship_genset(
            namespace="test",
            genset_id="FV-GS-1",
            vessel_uri=vessel_uri,
            label="GenSet 1",
            types=["FourStroke", "DieselElectricConfiguration", "AC"],
            shaft_power_max_kw=5000.0,
            generator_voltage_v=6600.0,
        )

        assert (uri, RDF.type, TWINSHIP.GenSetSystem) in g
        assert (uri, RDF.type, TWINSHIP.FourStroke) in g
        assert (uri, RDF.type, TWINSHIP.DieselElectricConfiguration) in g
        assert (uri, RDF.type, TWINSHIP.AC) in g
        assert (uri, IDO.partOf, vessel_uri) in g
        assert (uri, RDFS.label, Literal("GenSet 1")) in g

    def test_create_ess(self):
        vessel_uri = create_twinship_uri("FV-RR-1", "test")
        uri, g = create_twinship_ess(
            namespace="test",
            ess_id="FV-ESS-1",
            vessel_uri=vessel_uri,
            label="ESS 1",
            types=["ESD"],
            cycle_life=5000,
        )

        assert (uri, RDF.type, TWINSHIP.EnergyStorageSystem) in g
        assert (uri, RDF.type, TWINSHIP.ESD) in g
        assert (uri, IDO.partOf, vessel_uri) in g
        # cycle_life is integer, not double
        from rdflib.namespace import XSD

        assert (uri, TWINSHIP.twESSCycleLife, Literal(5000, datatype=XSD.integer)) in g

    def test_create_ammonia_fuel_cell(self):
        vessel_uri = create_twinship_uri("FV-RR-1", "test")
        uri, g = create_twinship_ammonia_fuel_cell(
            namespace="test",
            ammcell_id="FV-AMMCELL-1",
            vessel_uri=vessel_uri,
            label="AmmCell 1",
            types=["FuelCellSystem"],
        )

        assert (uri, RDF.type, TWINSHIP.FuelCellSystem) in g
        assert (uri, IDO.partOf, vessel_uri) in g
        # Auto-consumes ammonia
        assert (uri, TWINSHIP.consume, TWINSHIP.AMM) in g


class TestFuturisticFuels:
    def test_amm_fuel_uri(self):
        assert get_twinship_fuel_uri("AMM") == TWINSHIP.AMM

    def test_bf_fuel_uri(self):
        assert get_twinship_fuel_uri("BF") == TWINSHIP.BF


class TestConnectionPredicates:
    def test_connected_to_is_symmetric(self):
        a = create_twinship_uri("A", "test")
        b = create_twinship_uri("B", "test")
        g = build_twinship_connection(a, b)

        assert (a, IDO.connectedTo, b) in g
        assert (b, IDO.connectedTo, a) in g


# =============================================================================
# High-level integration tests
# =============================================================================


class TestFuturisticHarmonisation:
    @pytest.fixture()
    def fv_graph(self):
        """Build a complete futuristic vessel graph."""
        data = {
            "namespace": "test-fv",
            "vessel": {"id": "FV-RR-1", "label": "Test FV", "type": "RoRo"},
            "main_engines": [],
            "auxiliary_engines": [],
            "gearboxes": [],
            "boilers": [],
            "propellers": [
                {"id": "FV-CPP-1", "name": "CPP 1", "types": ["CPP"], "pms_id": "FV-PMS-1"},
            ],
            "gensets": [
                {
                    "id": "FV-GS-1",
                    "name": "GenSet 1",
                    "types": ["FourStroke", "DieselElectricConfiguration", "AC"],
                    "fuels": ["AMM", "BF"],
                    "pms_id": "FV-PMS-1",
                    "scr_id": "FV-SCR-1",
                },
            ],
            "ess": [
                {"id": "FV-ESS-1", "name": "ESS 1", "types": ["ESD"], "dcb_id": "FV-DCB-1"},
            ],
            "dc_bus_converters": [
                {
                    "id": "FV-DCB-1",
                    "name": "DCB 1",
                    "types": ["DC"],
                    "ess_id": "FV-ESS-1",
                    "pms_id": "FV-PMS-1",
                },
            ],
            "scrs": [
                {
                    "id": "FV-SCR-1",
                    "name": "SCR 1",
                    "types": ["EmissionReduction"],
                    "genset_id": "FV-GS-1",
                    "pms_id": "FV-PMS-1",
                },
            ],
            "pms": [{"id": "FV-PMS-1", "name": "PMS 1", "types": ["PMS"]}],
            "auxiliary_loads": [
                {
                    "id": "FV-AUXLD-1",
                    "name": "AuxLoad 1",
                    "types": ["AUXLOAD"],
                    "pms_id": "FV-PMS-1",
                },
            ],
            "shore_power": [
                {"id": "FV-OSP-1", "name": "OSP 1", "types": ["OSP"], "pms_id": "FV-PMS-1"},
            ],
            "frequency_converters": [
                {
                    "id": "FV-FC-1",
                    "name": "FC 1",
                    "types": ["FrequencyConverterSystem"],
                    "motor_id": "FV-EMM-1",
                    "pms_id": "FV-PMS-1",
                },
            ],
            "electric_motors": [
                {
                    "id": "FV-EMM-1",
                    "name": "Motor 1",
                    "types": ["ElectricMotorSystem"],
                    "fc_id": "FV-FC-1",
                    "shaft_id": "FV-EMSH-1",
                },
            ],
            "electric_motor_shafts": [
                {
                    "id": "FV-EMSH-1",
                    "name": "Shaft 1",
                    "motor_id": "FV-EMM-1",
                    "propeller_id": "FV-CPP-1",
                },
            ],
            "gate_rudders": [
                {"id": "FV-GRS-1", "name": "GRS 1", "types": ["GateRudder"], "pms_id": "FV-PMS-1"},
            ],
            "thrusters": [
                {
                    "id": "FV-TH-1",
                    "name": "Thruster 1",
                    "types": ["BowThruster", "Bow"],
                    "pms_id": "FV-PMS-1",
                },
            ],
            "wasps": [
                {
                    "id": "FV-WASP-1",
                    "name": "WASP 1",
                    "types": ["WindAssistedPropulsionSystem"],
                    "pms_id": "FV-PMS-1",
                },
            ],
            "als": [
                {
                    "id": "FV-ALS-1",
                    "name": "ALS 1",
                    "types": ["AirLubricationSystem"],
                    "pms_id": "FV-PMS-1",
                },
            ],
            "dynamic_wings": [
                {"id": "FV-DW-1", "name": "DW 1", "types": ["DynamicWing"], "pms_id": "FV-PMS-1"},
            ],
            "ammonia_fuel_cells": [
                {
                    "id": "FV-AMMCELL-1",
                    "name": "AmmCell 1",
                    "types": ["FuelCellSystem"],
                    "pms_id": "FV-PMS-1",
                },
            ],
        }
        return harmonise_twinship_vessel(**data)

    def test_vessel_created(self, fv_graph):
        vessel_uri = create_twinship_uri("FV-RR-1", "test-fv")
        assert (vessel_uri, RDF.type, TWINSHIP.VesselSystem) in fv_graph
        assert (vessel_uri, RDF.type, TWINSHIP.RoRo) in fv_graph

    def test_genset_type_and_partof(self, fv_graph):
        gs = create_twinship_uri("FV-GS-1", "test-fv")
        vessel = create_twinship_uri("FV-RR-1", "test-fv")
        assert (gs, RDF.type, TWINSHIP.GenSetSystem) in fv_graph
        assert (gs, IDO.partOf, vessel) in fv_graph

    def test_genset_fuel_consumption(self, fv_graph):
        gs = create_twinship_uri("FV-GS-1", "test-fv")
        assert (gs, TWINSHIP.consume, TWINSHIP.AMM) in fv_graph
        assert (gs, TWINSHIP.consume, TWINSHIP.BF) in fv_graph

    def test_genset_pms_connection(self, fv_graph):
        """Genset uses connectedTo PMS (not directlyConnectedTo)."""
        gs = create_twinship_uri("FV-GS-1", "test-fv")
        pms = create_twinship_uri("FV-PMS-1", "test-fv")
        assert (gs, IDO.connectedTo, pms) in fv_graph
        assert (pms, IDO.connectedTo, gs) in fv_graph

    def test_genset_scr_connection(self, fv_graph):
        gs = create_twinship_uri("FV-GS-1", "test-fv")
        scr = create_twinship_uri("FV-SCR-1", "test-fv")
        assert (gs, IDO.connectedTo, scr) in fv_graph
        assert (scr, IDO.connectedTo, gs) in fv_graph

    def test_motor_shaft_direct_connection(self, fv_graph):
        """Motor ↔ shaft uses directlyConnectedTo."""
        motor = create_twinship_uri("FV-EMM-1", "test-fv")
        shaft = create_twinship_uri("FV-EMSH-1", "test-fv")
        assert (motor, IDO.directlyConnectedTo, shaft) in fv_graph
        assert (shaft, IDO.directlyConnectedTo, motor) in fv_graph

    def test_shaft_propeller_direct_connection(self, fv_graph):
        """Shaft ↔ propeller uses directlyConnectedTo."""
        shaft = create_twinship_uri("FV-EMSH-1", "test-fv")
        prop = create_twinship_uri("FV-CPP-1", "test-fv")
        assert (shaft, IDO.directlyConnectedTo, prop) in fv_graph
        assert (prop, IDO.directlyConnectedTo, shaft) in fv_graph

    def test_fc_motor_connection(self, fv_graph):
        """FC ↔ motor uses connectedTo."""
        fc = create_twinship_uri("FV-FC-1", "test-fv")
        motor = create_twinship_uri("FV-EMM-1", "test-fv")
        assert (fc, IDO.connectedTo, motor) in fv_graph
        assert (motor, IDO.connectedTo, fc) in fv_graph

    def test_propeller_pms_connection(self, fv_graph):
        """Propeller ↔ PMS uses connectedTo for futuristic vessels."""
        prop = create_twinship_uri("FV-CPP-1", "test-fv")
        pms = create_twinship_uri("FV-PMS-1", "test-fv")
        assert (prop, IDO.connectedTo, pms) in fv_graph
        assert (pms, IDO.connectedTo, prop) in fv_graph

    def test_ess_dcb_connection(self, fv_graph):
        ess = create_twinship_uri("FV-ESS-1", "test-fv")
        dcb = create_twinship_uri("FV-DCB-1", "test-fv")
        assert (ess, IDO.connectedTo, dcb) in fv_graph
        assert (dcb, IDO.connectedTo, ess) in fv_graph

    def test_ammonia_fuel_cell_consumes_amm(self, fv_graph):
        cell = create_twinship_uri("FV-AMMCELL-1", "test-fv")
        assert (cell, TWINSHIP.consume, TWINSHIP.AMM) in fv_graph

    def test_bow_thruster_type(self, fv_graph):
        th = create_twinship_uri("FV-TH-1", "test-fv")
        assert (th, RDF.type, TWINSHIP.BowThruster) in fv_graph

    def test_triple_count(self, fv_graph):
        """Minimal futuristic vessel should produce a reasonable number of triples."""
        assert len(fv_graph) > 50


class TestFuturisticShaclValidation:
    """Test that harmonised futuristic vessel passes SHACL validation."""

    def test_shacl_passes(self):
        from dagster_pipeline.resources import ShaclValidator

        data = {
            "namespace": "shacl-test",
            "vessel": {"id": "FV-RR-1", "label": "SHACL Test", "type": "RoRo"},
            "main_engines": [],
            "auxiliary_engines": [],
            "gearboxes": [],
            "boilers": [],
            "propellers": [
                {"id": "FV-CPP-1", "types": ["CPP"], "pms_id": "FV-PMS-1"},
            ],
            "gensets": [
                {
                    "id": "FV-GS-1",
                    "types": ["FourStroke", "DieselElectricConfiguration"],
                    "fuels": ["AMM"],
                    "pms_id": "FV-PMS-1",
                    "scr_id": "FV-SCR-1",
                },
            ],
            "scrs": [
                {
                    "id": "FV-SCR-1",
                    "types": ["EmissionReduction"],
                    "genset_id": "FV-GS-1",
                    "pms_id": "FV-PMS-1",
                },
            ],
            "pms": [{"id": "FV-PMS-1", "types": ["PMS"]}],
            "frequency_converters": [
                {
                    "id": "FV-FC-1",
                    "types": ["FrequencyConverterSystem"],
                    "motor_id": "FV-EMM-1",
                    "pms_id": "FV-PMS-1",
                },
            ],
            "electric_motors": [
                {
                    "id": "FV-EMM-1",
                    "types": ["ElectricMotorSystem"],
                    "fc_id": "FV-FC-1",
                    "shaft_id": "FV-EMSH-1",
                },
            ],
            "electric_motor_shafts": [
                {"id": "FV-EMSH-1", "motor_id": "FV-EMM-1", "propeller_id": "FV-CPP-1"},
            ],
            "thrusters": [
                {"id": "FV-TH-1", "types": ["BowThruster", "Bow"], "pms_id": "FV-PMS-1"},
            ],
            "ammonia_fuel_cells": [
                {"id": "FV-AMMCELL-1", "types": ["FuelCellSystem"], "pms_id": "FV-PMS-1"},
            ],
        }
        g = harmonise_twinship_vessel(**data)

        validator = ShaclValidator()
        conforms, report = validator.validate(g, Path("shacl/"))
        assert conforms, f"SHACL validation failed:\n{report}"


class TestFullExtractionHarmonisation:
    """Integration test: extract from real spreadsheet and harmonise."""

    @pytest.fixture(scope="class")
    def full_graph(self):
        from dagster_pipeline.futuristic_extraction import (
            extract_futuristic_vessel,
            load_futuristic_sheets,
        )

        spreadsheet = Path("data/RoRo Futuristic Vessel KG Working File.xlsx")
        if not spreadsheet.exists():
            pytest.skip("Futuristic spreadsheet not available")

        sheets = load_futuristic_sheets(str(spreadsheet))
        data = extract_futuristic_vessel(sheets, "FV", "futuristic-vessel")
        return harmonise_twinship_vessel(**data)

    def test_produces_triples(self, full_graph):
        assert len(full_graph) > 100

    def test_shacl_validates(self, full_graph):
        from dagster_pipeline.resources import ShaclValidator

        validator = ShaclValidator()
        conforms, report = validator.validate(full_graph, Path("shacl/"))
        assert conforms, f"SHACL validation failed:\n{report}"
