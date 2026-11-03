#!/usr/bin/env bash
# Replaces ontology/ and shacl/twinship/ with the model/ and shapes/ directories
# of one twinship-ontology git ref (preferably a release tag).
#
# Usage: scripts/sync_ontology.sh <tag-or-commit>      e.g. scripts/sync_ontology.sh v0.1.2
#
# Reads from a local twinship-ontology clone (default: sibling directory,
# override with TWINSHIP_ONTOLOGY_PATH). The full QUDT and IMO sources under
# model/external/ are left out; GraphDB only needs the simplified files.
# Pipeline-specific shapes in shacl/pipeline/ are not touched.
# The synced ref and commit are recorded in ontology/VERSION.
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

rm -rf "${MODEL_TARGET}" "${SHAPES_TARGET}"
mkdir -p "${MODEL_TARGET}" "${SHAPES_TARGET}"
git -C "${ONTOLOGY_PATH}" archive "${COMMIT}" model \
    ':(exclude)model/external/qudt' \
    ':(exclude)model/external/imo' \
    | tar -x -C "${MODEL_TARGET}" --strip-components=1
git -C "${ONTOLOGY_PATH}" archive "${COMMIT}" shapes \
    | tar -x -C "${SHAPES_TARGET}" --strip-components=1

printf 'ref: %s\ncommit: %s\n' "${REF}" "${COMMIT}" > "${MODEL_TARGET}/VERSION"
echo "Synced ontology/ and shacl/twinship/ to twinship-ontology ${REF} (${COMMIT})"
