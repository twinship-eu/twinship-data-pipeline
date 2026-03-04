"""Tests for futuristic vessel spreadsheet extraction."""

from pathlib import Path

import pytest

from dagster_pipeline.futuristic_extraction import (
    discover_futuristic_vessels,
    extract_futuristic_vessel,
    load_futuristic_sheets,
)

SPREADSHEET_PATH = Path("data/RoRo Futuristic Vessel KG Working File.xlsx")
pytestmark = pytest.mark.skipif(
    not SPREADSHEET_PATH.exists(), reason="Futuristic spreadsheet not available"
)


@pytest.fixture(scope="module")
def fv_sheets():
    return load_futuristic_sheets(str(SPREADSHEET_PATH))


@pytest.fixture(scope="module")
def fv_data(fv_sheets):
    return extract_futuristic_vessel(fv_sheets, "FV", "futuristic-vessel")


class TestLoadSheets:
    def test_loads_expected_sheets(self, fv_sheets):
        assert "Genset" in fv_sheets
        assert "ESS" in fv_sheets
        assert "SCR" in fv_sheets
        assert "PMS" in fv_sheets
        assert "EM" in fv_sheets
        assert "CPP" in fv_sheets

    def test_sheet_has_rows(self, fv_sheets):
        for name, df in fv_sheets.items():
            assert len(df) > 0, f"Sheet {name} has no data rows"


class TestDiscoverVessels:
    def test_discovers_futuristic_vessel(self, fv_sheets):
        vessels = discover_futuristic_vessels(fv_sheets)
        assert "futuristic-vessel" in vessels
        assert vessels["futuristic-vessel"]["prefix"] == "FV"

    def test_returns_empty_for_empty_sheets(self):
        assert discover_futuristic_vessels({}) == {}


class TestExtraction:
    def test_has_required_keys(self, fv_data):
        required = [
            "namespace",
            "vessel",
            "gensets",
            "ess",
            "dc_bus_converters",
            "scrs",
            "pms",
            "propellers",
            "frequency_converters",
            "electric_motors",
            "electric_motor_shafts",
            "gate_rudders",
            "thrusters",
            "wasps",
            "als",
            "dynamic_wings",
            "ammonia_fuel_cells",
        ]
        for key in required:
            assert key in fv_data, f"Missing key: {key}"

    def test_namespace(self, fv_data):
        assert fv_data["namespace"] == "futuristic-vessel"

    def test_vessel_synthesised(self, fv_data):
        vessel = fv_data["vessel"]
        assert vessel["id"] == "FV-RR-1"
        assert vessel["type"] == "RoRo"

    def test_gensets_extracted(self, fv_data):
        gensets = fv_data["gensets"]
        assert len(gensets) >= 1
        gs = gensets[0]
        assert gs["id"].startswith("FV-GN-")
        assert "fuels" in gs
        assert "pms_id" in gs
        assert "scr_id" in gs

    def test_ess_extracted(self, fv_data):
        ess = fv_data["ess"]
        assert len(ess) >= 1
        assert ess[0]["id"].startswith("FV-ESS-")
        assert "dcb_id" in ess[0]

    def test_dcb_extracted(self, fv_data):
        dcbs = fv_data["dc_bus_converters"]
        assert len(dcbs) >= 1
        assert dcbs[0]["id"].startswith("FV-DCB-")
        assert "ess_id" in dcbs[0]
        assert "pms_id" in dcbs[0]

    def test_scrs_extracted(self, fv_data):
        scrs = fv_data["scrs"]
        assert len(scrs) >= 1
        assert scrs[0]["id"].startswith("FV-SCR-")
        assert "genset_id" in scrs[0]

    def test_pms_extracted(self, fv_data):
        pms = fv_data["pms"]
        assert len(pms) >= 1
        assert pms[0]["id"].startswith("FV-PMS-")

    def test_propellers_extracted(self, fv_data):
        props = fv_data["propellers"]
        assert len(props) >= 1
        assert props[0]["id"].startswith("FV-CPP-")

    def test_em_sheet_routing(self, fv_data):
        """The EM sheet splits into FC, EMM, and EMSH by ID prefix."""
        assert len(fv_data["frequency_converters"]) >= 1
        assert len(fv_data["electric_motors"]) >= 1
        assert len(fv_data["electric_motor_shafts"]) >= 1

        assert fv_data["frequency_converters"][0]["id"].startswith("FV-FC-")
        assert fv_data["electric_motors"][0]["id"].startswith("FV-EMM-")
        assert fv_data["electric_motor_shafts"][0]["id"].startswith("FV-EMSH-")

    def test_efficiency_systems_extracted(self, fv_data):
        for key in ["gate_rudders", "thrusters", "wasps", "als", "dynamic_wings"]:
            assert len(fv_data[key]) >= 1, f"{key} should have at least one entry"

    def test_ammonia_fuel_cells_extracted(self, fv_data):
        cells = fv_data["ammonia_fuel_cells"]
        assert len(cells) >= 1
        assert cells[0]["id"].startswith("FV-AMMCELL-")

    def test_conventional_components_empty(self, fv_data):
        """Futuristic vessels should have empty conventional component lists."""
        assert fv_data["main_engines"] == []
        assert fv_data["auxiliary_engines"] == []
        assert fv_data["gearboxes"] == []
        assert fv_data["boilers"] == []

    def test_referential_integrity_genset_scr(self, fv_data):
        """Each genset's scr_id should reference an existing SCR."""
        scr_ids = {s["id"] for s in fv_data["scrs"]}
        for gs in fv_data["gensets"]:
            if gs.get("scr_id"):
                assert gs["scr_id"] in scr_ids, f"Genset {gs['id']} references unknown SCR"

    def test_referential_integrity_motor_shaft(self, fv_data):
        """Each motor's shaft_id should reference an existing shaft."""
        shaft_ids = {s["id"] for s in fv_data["electric_motor_shafts"]}
        for motor in fv_data["electric_motors"]:
            if motor.get("shaft_id"):
                assert motor["shaft_id"] in shaft_ids, (
                    f"Motor {motor['id']} references unknown shaft"
                )
