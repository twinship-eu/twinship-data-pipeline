"""Tests for the futuristic vessel's operational modes (data/RoRo Futuristic Vessel Operational Modes.ttl)."""

from pathlib import Path

import pytest
from rdflib import RDF, Graph, URIRef

from dagster_pipeline.assets.harmonisation import FUTURISTIC_OPERATIONAL_MODES
from dagster_pipeline.futuristic_extraction import extract_futuristic_vessel, load_futuristic_sheets
from dagster_pipeline.resources import ShaclValidator
from twinship_harmonisation.constants import TWINSHIP, TWINSHIP_IND
from twinship_harmonisation.high_level import harmonise_twinship_vessel

REPO_ROOT = Path(__file__).resolve().parents[1]
SPREADSHEET = REPO_ROOT / "data" / "RoRo Futuristic Vessel KG Working File.xlsx"
VESSEL_NS = f"{TWINSHIP_IND}futuristic-vessel/"


@pytest.fixture(scope="module")
def modes() -> Graph:
    return Graph().parse(REPO_ROOT / FUTURISTIC_OPERATIONAL_MODES, format="turtle")


@pytest.fixture(scope="module")
def components() -> Graph:
    if not SPREADSHEET.exists():
        pytest.skip("Futuristic spreadsheet not available")
    sheets = load_futuristic_sheets(str(SPREADSHEET))
    return harmonise_twinship_vessel(**extract_futuristic_vessel(sheets, "FV", "futuristic-vessel"))


def test_counts(modes):
    def count(cls):
        return len(set(modes.subjects(RDF.type, TWINSHIP[cls])))

    assert (count("EngineMode"), count("EngineSpeedBin")) == (8, 4)
    assert (count("DraftMode"), count("TrimMode")) == (3, 3)


def test_uses_pipeline_iris(modes):
    """All named individuals are in the pipeline's namespace for the futuristic vessel.

    Blank nodes (the owl:AllDifferent statements and their lists) are allowed.
    """
    iris = {str(s) for s in modes.subjects() if isinstance(s, URIRef)}
    assert iris and all(i.startswith(VESSEL_NS) for i in iris)


def test_engine_modes_attach_to_existing_gensets(modes, components):
    gensets = set(components.subjects(RDF.type, TWINSHIP.GenSetSystem))
    owners = set(modes.subjects(TWINSHIP.hasEngineMode, None))
    assert owners and owners <= gensets, f"Not gensets in the pipeline graph: {owners - gensets}"


def test_terms_exist_in_ontology(modes):
    ontology = Graph()
    for path in (REPO_ROOT / "ontology").rglob("*.ttl"):
        ontology.parse(path, format="turtle")
    used = {p for p in modes.predicates() if str(p).startswith(str(TWINSHIP))}
    used |= {o for o in modes.objects(None, RDF.type) if str(o).startswith(str(TWINSHIP))}
    missing = sorted(str(t) for t in used if (t, RDF.type, None) not in ontology)
    assert not missing, f"Not declared in the ontology: {missing}"


def test_components_with_modes_pass_shacl(modes, components):
    conforms, report = ShaclValidator().validate(components + modes, REPO_ROOT / "shacl")
    assert conforms, f"SHACL validation failed:\n{report}"
