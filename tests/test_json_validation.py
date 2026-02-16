from __future__ import annotations

import json
from pathlib import Path

from dagster_pipeline.validation.json_validation import validate_vessel_json


def test_all_json_files_validate_ok():
    for p in Path("data").glob("*.json"):
        data = json.loads(p.read_text())
        report = validate_vessel_json(data)
        assert report.ok(), f"{p} failed with errors: {report.errors}"