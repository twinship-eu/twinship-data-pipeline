#!/usr/bin/env bash
# Replaces ontology/ and shacl/twinship/ with the model/ and shapes/ directories
# of one twinship-ontology git ref (preferably a release tag).
#
# Usage: scripts/sync_ontology.sh <tag-or-commit>      e.g. scripts/sync_ontology.sh v0.1.3
#
# Reads from a local twinship-ontology clone (default: sibling directory,
# override with TWINSHIP_ONTOLOGY_PATH). Only merged work is synced: the commit
# must be on origin/main or origin/develop of the clone. The files are taken from git at that
# commit, not from the clone's working tree. The full QUDT and IMO sources under
# model/external/ are left out; GraphDB only needs the simplified files.
# Pipeline-specific shapes in shacl/pipeline/ are not touched.
#
# The synced ref, commit and a SHA-256 checksum per copied file are recorded in
# ontology/VERSION; tests/test_ontology_copy.py fails if the copy is changed here.
# Change the ontology in its own repository, then sync.
set -euo pipefail

REF="${1:?usage: $0 <tag-or-commit>}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ONTOLOGY_PATH="${TWINSHIP_ONTOLOGY_PATH:-${REPO_ROOT}/../twinship-ontology}"
MODEL_TARGET="${REPO_ROOT}/ontology"
SHAPES_TARGET="${REPO_ROOT}/shacl/twinship"

git -C "${ONTOLOGY_PATH}" fetch --quiet --tags
COMMIT="$(git -C "${ONTOLOGY_PATH}" rev-parse --verify --quiet "${REF}^{commit}")" || {
    echo "Ref '${REF}' not found in ${ONTOLOGY_PATH}" >&2
    exit 1
}
BRANCHES="$(git -C "${ONTOLOGY_PATH}" branch -r --contains "${COMMIT}")"
if ! grep -qE '^[* ] origin/(main|develop)$' <<<"${BRANCHES}"; then
    echo "Commit ${COMMIT:0:7} is not on origin/main or origin/develop of ${ONTOLOGY_PATH}:" \
        "merge the change in twinship-ontology, fetch, then sync." >&2
    exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
    SHA256=(sha256sum)
else
    SHA256=(shasum -a 256)
fi

VERSION_TMP="$(mktemp)"
trap 'rm -f "${VERSION_TMP}"' EXIT

rm -rf "${MODEL_TARGET}" "${SHAPES_TARGET}"
mkdir -p "${MODEL_TARGET}" "${SHAPES_TARGET}"
git -C "${ONTOLOGY_PATH}" archive "${COMMIT}" model \
    ':(exclude)model/external/qudt' \
    ':(exclude)model/external/imo' \
    | tar -x -C "${MODEL_TARGET}" --strip-components=1
git -C "${ONTOLOGY_PATH}" archive "${COMMIT}" shapes \
    | tar -x -C "${SHAPES_TARGET}" --strip-components=1

{
    printf 'ref: %s\ncommit: %s\nfiles:\n' "${REF}" "${COMMIT}"
    cd "${REPO_ROOT}"
    find ontology shacl/twinship -type f ! -path ontology/VERSION -print0 \
        | LC_ALL=C sort -z \
        | xargs -0 "${SHA256[@]}"
} > "${VERSION_TMP}"
chmod 644 "${VERSION_TMP}"
mv "${VERSION_TMP}" "${MODEL_TARGET}/VERSION"

echo "Synced ontology/ and shacl/twinship/ to twinship-ontology ${REF} (${COMMIT});" \
    "commit them with ontology/VERSION"
