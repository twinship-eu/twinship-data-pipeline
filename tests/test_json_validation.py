from __future__ import annotations

import json

import pytest

from dagster_pipeline.utils import vessel_data_dir
from dagster_pipeline.validation.json_validation import validate_vessel_json


def test_all_json_files_validate_ok():
    # Extracted vessel JSON lives in the vessel data folder;
    # other JSON there (e.g. configuration) has no "namespace" key and is skipped.
    vessels = [
        (p, data)
        for p in sorted(vessel_data_dir().glob("*.json"))
        if "namespace" in (data := json.loads(p.read_text(encoding="utf-8")))
    ]
    if not vessels:
        pytest.skip(f"No vessel JSON files in {vessel_data_dir()}")
    for p, data in vessels:
        report = validate_vessel_json(data)
        assert report.ok(), f"{p} failed with errors: {report.errors}"
