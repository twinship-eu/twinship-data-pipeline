"""Tests for the futuristic vessel's operational modes (data/RoRo Futuristic Vessel Operational Modes.ttl)."""

from pathlib import Path

import pytest
from rdflib import RDF, RDFS, Graph, URIRef
from rdflib.namespace import SKOS

from dagster_pipeline.assets.harmonisation import FUTURISTIC_OPERATIONAL_MODES
from dagster_pipeline.futuristic_extraction import extract_futuristic_vessel, load_futuristic_sheets
from dagster_pipeline.resources import ShaclValidator, ontology_individuals
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

    assert (count("EngineMode"), count("EngineSpeedBin")) == (8, 0)
    assert (count("DraftMode"), count("TrimMode")) == (3, 2)
    assert count("VesselSpeedBin") == 4


def test_speed_bins_use_sog_and_rising_reference_speeds(modes):
    """Each speed bin has exactly one speed reference, SOG; reference speeds rise with the bin."""
    bins = sorted(modes.subjects(RDF.type, TWINSHIP.VesselSpeedBin))
    assert all(list(modes.objects(b, TWINSHIP.hasSpeedReference)) == [TWINSHIP.SOG] for b in bins)
    speeds = [modes.value(b, TWINSHIP.twSpeedValueInKnots).toPython() for b in bins]
    assert speeds == sorted(set(speeds)) and len(speeds) == 4


def test_draft_ranges_are_contiguous(modes):
    """Draft modes in order: each upper bound is the next mode's lower bound."""
    modes_in_order = sorted(
        modes.subjects(RDF.type, TWINSHIP.DraftMode),
        key=lambda m: modes.value(m, TWINSHIP.twDraftModeReferenceDraftInM).toPython(),
    )
    uppers = [modes.value(m, TWINSHIP.twDraftModeUpperBoundInM) for m in modes_in_order[:-1]]
    lowers = [modes.value(m, TWINSHIP.twDraftModeLowerBoundInM) for m in modes_in_order[1:]]
    assert uppers == lowers and None not in uppers


def test_speed_bins_are_contiguous(modes):
    """Speed bins in order: each upper bound is the next bin's lower bound, from 0 kn."""
    bins = sorted(
        modes.subjects(RDF.type, TWINSHIP.VesselSpeedBin),
        key=lambda b: modes.value(b, TWINSHIP.twSpeedValueInKnots).toPython(),
    )
    lowers = [modes.value(b, TWINSHIP.twSpeedBinLowerBoundInKnots) for b in bins]
    uppers = [modes.value(b, TWINSHIP.twSpeedBinUpperBoundInKnots) for b in bins]
    assert None not in lowers + uppers
    assert lowers[0].toPython() == 0 and uppers[:-1] == lowers[1:]
    for b in bins:
        lo, hi, ref = (
            modes.value(b, TWINSHIP[p]).toPython()
            for p in (
                "twSpeedBinLowerBoundInKnots",
                "twSpeedBinUpperBoundInKnots",
                "twSpeedValueInKnots",
            )
        )
        assert lo <= ref < hi, f"Reference speed {ref} outside its bin [{lo}, {hi})"


def test_trim_modes_are_contiguous(modes):
    """Bow trim's upper bound is even keel's lower bound; both are open at their outer end."""
    by_name = {
        str(modes.value(m, SKOS.altLabel)): m for m in modes.subjects(RDF.type, TWINSHIP.TrimMode)
    }
    bow, even = by_name["Bow trim"], by_name["Even keel"]
    assert modes.value(bow, TWINSHIP.twTrimModeUpperBoundInM) == modes.value(
        even, TWINSHIP.twTrimModeLowerBoundInM
    )
    assert modes.value(bow, TWINSHIP.twTrimModeLowerBoundInM) is None
    assert modes.value(bow, TWINSHIP.twTrimModeUpperBoundInM).toPython() < 0
    assert modes.value(even, TWINSHIP.twTrimModeUpperBoundInM) is None
    assert modes.value(even, TWINSHIP.twTrimModeLowerBoundInM).toPython() <= 0


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


def test_validator_gets_ontology_individuals_only():
    """The validator sees the ontology's individuals (types and labels), not its classes."""
    g = ontology_individuals(REPO_ROOT / "ontology")
    assert (TWINSHIP.SOG, RDF.type, TWINSHIP.SpeedReference) in g
    assert (TWINSHIP.BF, RDFS.label, None) in g
    assert (TWINSHIP.VesselSpeedBin, None, None) not in g


def test_validator_fails_without_ontology_modules(tmp_path):
    """A missing ontology copy is an error, not an empty graph (e.g. in a Docker image)."""
    with pytest.raises(FileNotFoundError):
        ontology_individuals(tmp_path)
