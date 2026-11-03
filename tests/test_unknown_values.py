"""Tests that unknown values are omitted rather than written as -1."""

import math

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import XSD

from dagster_pipeline.utils import clean_value
from twinship_harmonisation.constants import TWINSHIP
from twinship_harmonisation.low_level.vessel_functions import add_optional_code

SUBJECT = URIRef("https://twin-ship.eu/individuals/test/ME-1")


@pytest.mark.parametrize("val", [None, math.nan, -1, -1.0, "-1", " -1.0 "])
def test_clean_value_unknown_is_none(val):
    assert clean_value(val) is None


@pytest.mark.parametrize("val", [0, 1, 0.0, -2, -0.5, "HFO"])
def test_clean_value_keeps_values(val):
    assert clean_value(val) == val


@pytest.mark.parametrize("val,expected", [(0, 0), (1, 1), ("1", 1), (1.0, 1)])
def test_add_optional_code_adds_integer(val, expected):
    g = Graph()
    add_optional_code(g, SUBJECT, TWINSHIP.twCommonDOMode, val)
    assert list(g.objects(SUBJECT, TWINSHIP.twCommonDOMode)) == [
        Literal(expected, datatype=XSD.integer)
    ]


@pytest.mark.parametrize("val", [None, "[0,1]", "[0, 1]", "BINARY"])
def test_add_optional_code_omits_non_values(val):
    g = Graph()
    add_optional_code(g, SUBJECT, TWINSHIP.twCommonDOMode, val)
    assert len(g) == 0
