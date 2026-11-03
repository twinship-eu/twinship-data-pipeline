"""Tests for the ontology import list derived from ontology/catalog-v001.xml."""

import json
import subprocess
from pathlib import Path

from dagster_pipeline.assets.harmonisation import ONTOLOGY_CATALOG, ontology_server_files

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_import_files_exist():
    files = ontology_server_files()
    assert "ontology/twinship-core.ttl" in files
    for f in files:
        assert (REPO_ROOT / f).is_file(), f"{f} listed in catalog but missing"


def test_core_modules_listed():
    files = ontology_server_files()
    for module in (REPO_ROOT / "ontology" / "modules").glob("*.ttl"):
        assert f"ontology/modules/{module.name}" in files


def test_init_script_uses_same_list():
    """graphdb/init.sh builds the same list with grep/sed; run that pipeline here."""
    script = (REPO_ROOT / "graphdb" / "init.sh").read_text(encoding="utf-8")
    start = script.index("files=$(")
    end = script.index("paste -sd, -)", start) + len("paste -sd, -)")
    cmd = f'ONTOLOGY_CATALOG="{ONTOLOGY_CATALOG}"\n{script[start:end]}\necho "[$files]"'
    out = subprocess.run(["sh", "-c", cmd], capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == ontology_server_files()
