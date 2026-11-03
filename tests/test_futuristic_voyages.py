"""Tests for the futuristic vessel voyage patch (dagster_pipeline/assets/futuristic_voyages.py)."""

from datetime import timedelta
from pathlib import Path

import pytest
from rdflib import RDF, Graph, Namespace, URIRef

from dagster_pipeline.assets.futuristic_voyages import (
    COLUMNS,
    PORTS,
    VOYAGE_START,
    build_voyage_graph,
    interpolate,
    read_records,
    record_time,
    split_crossings,
)
from twinship_harmonisation.constants import TWINSHIP

REPO_ROOT = Path(__file__).resolve().parents[1]
VOYAGE_FILE = REPO_ROOT / "data" / "RoRo Futuristic Vessel Voyages.dat"
# Reference output of the twinship-futuristic-vessel generator, if checked out next to this repo
REFERENCE_TTL = REPO_ROOT.parent / "twinship-futuristic-vessel" / "output" / "voyages.ttl"
REFERENCE_NS = "https://twin-ship.eu/examples/futuristic-vessel#"
PIPELINE_NS = "https://twin-ship.eu/individuals/futuristic-vessel/"
VESSEL = URIRef(PIPELINE_NS + "FV-RR-1")


def _rec(i, direction, dist_trav, dist_rem, **values):
    rec = dict.fromkeys(COLUMNS, 0.0)
    rec.update(i=i, dir=direction, dist_trav=dist_trav, dist_rem=dist_rem, vs_sog=18.0)
    rec.update(values)
    return rec


# Two complete crossings (Rotterdam -> Immingham, back) and an unfinished third one
RECORDS = [
    _rec(1, 1, 0, 36),
    _rec(2, 1, 18, 18),
    _rec(3, 1, 36, 0),
    _rec(4, 2, 0, 36),
    _rec(5, 2, 18, 18),
    _rec(6, 2, 36, 0),
    _rec(7, 1, 0, 36),
]


def test_split_crossings():
    crossings, leftover = split_crossings(RECORDS)
    assert [(c.departure.code, c.arrival.code) for c in crossings] == [
        ("NLRTM", "GBIMM"),
        ("GBIMM", "NLRTM"),
    ]
    assert [len(c.records) for c in crossings] == [3, 3]
    assert crossings[0].total_nm == 36
    assert [r["i"] for r in leftover] == [7]


def test_split_crossings_rejects_record_before_departure():
    with pytest.raises(ValueError, match="precedes the first departure"):
        split_crossings([_rec(1, 1, 18, 18)])


def test_record_time_uses_three_hour_steps():
    assert record_time(1) == VOYAGE_START
    assert record_time(3) == VOYAGE_START + timedelta(hours=6)


def test_interpolate_endpoints_and_midpoint():
    dep, arr = PORTS["NLRTM"], PORTS["GBIMM"]
    assert interpolate(dep, arr, 0) == (dep.lat, dep.lon)
    assert interpolate(dep, arr, 1) == pytest.approx((arr.lat, arr.lon))
    assert interpolate(dep, arr, 0.5) == pytest.approx(
        ((dep.lat + arr.lat) / 2, (dep.lon + arr.lon) / 2)
    )


def test_build_voyage_graph_structure():
    g, warnings = build_voyage_graph(RECORDS)
    voyages = set(g.subjects(RDF.type, TWINSHIP.Voyage))
    assert len(voyages) == 2
    assert set(g.objects(VESSEL, TWINSHIP.hasVoyage)) == voyages
    assert len(set(g.subjects(RDF.type, TWINSHIP.VoyageLeg))) == 4  # 2 legs per crossing
    assert len(set(g.subjects(RDF.type, TWINSHIP.WayPoint))) == 6
    assert len(set(g.subjects(RDF.type, TWINSHIP.Port))) == 2
    assert any("unfinished trailing crossing" in w for w in warnings)
    assert all(str(s).startswith(PIPELINE_NS) for s in g.subjects())


def test_voyage_terms_exist_in_ontology():
    """Every TwinShip class and property the voyage graph uses is declared in ontology/."""
    ontology = Graph()
    for path in (REPO_ROOT / "ontology").rglob("*.ttl"):
        ontology.parse(path, format="turtle")
    g, _ = build_voyage_graph(RECORDS)
    tws = Namespace(str(TWINSHIP))
    used = {p for p in g.predicates() if str(p).startswith(tws)}
    used |= {o for o in g.objects(None, RDF.type) if str(o).startswith(tws)}
    missing = sorted(str(t) for t in used if (t, RDF.type, None) not in ontology)
    assert not missing, f"Not declared in the ontology: {missing}"


@pytest.mark.skipif(
    not (VOYAGE_FILE.exists() and REFERENCE_TTL.exists()),
    reason="Needs the voyage file and twinship-futuristic-vessel/output/voyages.ttl",
)
def test_matches_futuristic_vessel_generator():
    """Same triples as the original generator, after mapping its IRIs to the pipeline's."""
    g, _ = build_voyage_graph(read_records(VOYAGE_FILE))

    def remap(term):
        if isinstance(term, URIRef) and str(term).startswith(REFERENCE_NS):
            return URIRef(PIPELINE_NS + str(term)[len(REFERENCE_NS) :])
        return term

    reference = {tuple(remap(t) for t in triple) for triple in Graph().parse(REFERENCE_TTL)}
    ours = set(g)
    assert ours == reference, (
        f"{len(ours - reference)} triples only in pipeline, "
        f"{len(reference - ours)} only in reference"
    )
