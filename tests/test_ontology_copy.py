"""The ontology copy must match the twinship-ontology commit pinned in ontology/VERSION.

ontology/ and shacl/twinship/ are written by scripts/sync_ontology.sh, which records a
SHA-256 checksum per file. Change the ontology in its own repository, then sync.
"""

import hashlib
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = REPO_ROOT / "ontology" / "VERSION"
COPIED_DIRS = ("ontology", "shacl/twinship")
IGNORED_NAMES = {".DS_Store"}


def _read_version():
    text = VERSION_FILE.read_text(encoding="utf-8")
    commit = re.search(r"^commit: ([0-9a-f]{40})$", text, re.M)
    assert commit, "ontology/VERSION has no commit line; run scripts/sync_ontology.sh"
    files = {}
    for line in text.split("files:\n", 1)[1].splitlines() if "files:\n" in text else []:
        digest, path = line.split(maxsplit=1)
        files[path] = digest
    assert files, "ontology/VERSION has no checksums; run scripts/sync_ontology.sh"
    return commit.group(1), files


def _copied_files():
    found = {}
    for folder in COPIED_DIRS:
        for path in (REPO_ROOT / folder).rglob("*"):
            if path.is_file() and path.name not in IGNORED_NAMES and path != VERSION_FILE:
                rel = path.relative_to(REPO_ROOT).as_posix()
                found[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def test_ontology_copy_matches_pinned_commit():
    commit, expected = _read_version()
    actual = _copied_files()
    problems = [f"missing: {p}" for p in sorted(expected.keys() - actual.keys())]
    problems += [f"not in the ontology: {p}" for p in sorted(actual.keys() - expected.keys())]
    problems += [
        f"changed here: {p}"
        for p in sorted(expected.keys() & actual.keys())
        if expected[p] != actual[p]
    ]
    assert not problems, (
        f"The ontology copy differs from twinship-ontology {commit[:7]}:\n  "
        + "\n  ".join(problems)
        + "\nChange the ontology in twinship-ontology, then run scripts/sync_ontology.sh."
    )
