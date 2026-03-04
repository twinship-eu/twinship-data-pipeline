#!/bin/sh
# GraphDB initialisation script (runs once at startup before security is enabled).
#
# 1. Waits for GraphDB to become reachable
# 2. Creates the shared "twinship-ontology" repository with RDFS+ reasoning
# 3. Imports all ontology files from the server import directory
# 4. Waits for the import to finish
# 5. Enables GraphDB security

set -e

GRAPHDB_URL="${GRAPHDB_URL:-http://graphdb:7200}"
ONTOLOGY_REPO="${ONTOLOGY_REPO:-twinship-ontology}"
ONTOLOGY_RULESET="${ONTOLOGY_RULESET:-rdfsplus-optimized}"

# --- helpers ----------------------------------------------------------------

wait_for_graphdb() {
    echo "Waiting for GraphDB at ${GRAPHDB_URL}..."
    until curl -sf "${GRAPHDB_URL}/rest/repositories" > /dev/null 2>&1; do
        sleep 2
    done
    echo "GraphDB is ready."
}

repo_exists() {
    status=$(curl -s -o /dev/null -w '%{http_code}' "${GRAPHDB_URL}/rest/repositories/${1}")
    [ "$status" = "200" ]
}

create_ontology_repo() {
    if repo_exists "${ONTOLOGY_REPO}"; then
        echo "Repository '${ONTOLOGY_REPO}' already exists, skipping creation."
        return 0
    fi

    echo "Creating repository '${ONTOLOGY_REPO}' (ruleset: ${ONTOLOGY_RULESET})..."

    # Write the repo config to a temp file
    cat > /tmp/ontology-repo-config.ttl <<REPOEOF
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.
@prefix rep: <http://www.openrdf.org/config/repository#>.
@prefix sr: <http://www.openrdf.org/config/repository/sail#>.
@prefix sail: <http://www.openrdf.org/config/sail#>.
@prefix graphdb: <http://www.ontotext.com/config/graphdb#>.

[] a rep:Repository ;
    rep:repositoryID "${ONTOLOGY_REPO}" ;
    rdfs:label "TwinShip Ontology" ;
    rep:repositoryImpl [
        rep:repositoryType "graphdb:SailRepository" ;
        sr:sailImpl [
            sail:sailType "graphdb:Sail" ;
            graphdb:ruleset "${ONTOLOGY_RULESET}" ;
            graphdb:check-for-inconsistencies "false" ;
            graphdb:disable-sameAs "true" ;
            graphdb:enable-context-index "true"
        ]
    ].
REPOEOF

    curl -sf -X POST "${GRAPHDB_URL}/rest/repositories" \
        -F "config=@/tmp/ontology-repo-config.ttl;type=text/turtle"

    echo "Repository '${ONTOLOGY_REPO}' created."
}

import_ontology_files() {
    echo "Importing ontology files into '${ONTOLOGY_REPO}'..."

    curl -sf -X POST "${GRAPHDB_URL}/rest/repositories/${ONTOLOGY_REPO}/import/server" \
        -H "Content-Type: application/json" \
        -d '{
            "fileNames": [
                "ontology/external/IDO_20240503.ttl",
                "ontology/external/PAV-simplified.ttl",
                "ontology/external/SCHEMA_QUDT-simplified.ttl",
                "ontology/vocabularies/VOCAB_QUDT-QUANTITY-KINDS-simplified.ttl",
                "ontology/vocabularies/VOCAB_QUDT_UNIT2-simplified.ttl",
                "ontology/external/vesselai/vesselAI_ontology_v2.owl",
                "ontology/external/vesselai/modules/main.ttl",
                "ontology/external/vesselai/modules/contextualInformation.ttl",
                "ontology/external/vesselai/modules/events.ttl",
                "ontology/external/vesselai/modules/trajectories_module.ttl",
                "ontology/external/vesselai/modules/vesselCharacteristics.ttl",
                "ontology/twinship-base.ttl",
                "ontology/modules/vessel.ttl",
                "ontology/modules/weatherconditions.ttl",
                "ontology/modules/draft_time_mode.ttl",
                "ontology/twinship-core.ttl"
            ]
        }'

    echo "Import request submitted."
}

wait_for_import() {
    echo "Waiting for ontology import to complete..."
    # Poll the import status — an active import shows status "IMPORTING"
    while true; do
        status=$(curl -sf "${GRAPHDB_URL}/rest/repositories/${ONTOLOGY_REPO}/import/server" 2>/dev/null || echo "[]")
        # If no files are in IMPORTING/PENDING state, we're done
        if echo "$status" | grep -q '"IMPORTING"\|"PENDING"'; then
            sleep 2
        else
            break
        fi
    done

    # Report triple count
    count=$(curl -sf "${GRAPHDB_URL}/repositories/${ONTOLOGY_REPO}/size" 2>/dev/null || echo "unknown")
    echo "Ontology import complete. Triple count: ${count}"
}

enable_security() {
    echo "Enabling GraphDB security..."
    curl -sf -X POST -H 'Content-Type: application/json' -d 'true' \
        "${GRAPHDB_URL}/rest/security"
    echo "Security enabled."
}

# --- main -------------------------------------------------------------------

wait_for_graphdb
create_ontology_repo
import_ontology_files
wait_for_import
enable_security

echo "GraphDB initialisation complete."
