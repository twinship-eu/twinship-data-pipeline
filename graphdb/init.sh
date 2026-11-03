#!/bin/sh
# GraphDB initialisation script (runs once at startup before security is enabled).
#
# 1. Waits for GraphDB to become reachable
# 2. Creates the shared "twinship-ontology" repository with RDFS+ reasoning
# 3. Imports all ontology files from the server import directory
# 4. Waits for the import to finish
# 5. Enables GraphDB security
#
# If security is already enabled (an existing graphdb_home volume), the
# initialisation has run before and the script exits without changes.

set -e

GRAPHDB_URL="${GRAPHDB_URL:-http://graphdb:7200}"
ONTOLOGY_REPO="${ONTOLOGY_REPO:-twinship-ontology}"
ONTOLOGY_RULESET="${ONTOLOGY_RULESET:-rdfsplus-optimized}"
ONTOLOGY_CATALOG="${ONTOLOGY_CATALOG:-/scripts/catalog-v001.xml}"

# --- helpers ----------------------------------------------------------------

# Waits until GraphDB answers. Sets SECURED=true if it requires a login
# (401/403), i.e. security was enabled by an earlier run.
wait_for_graphdb() {
    echo "Waiting for GraphDB at ${GRAPHDB_URL}..."
    while true; do
        status=$(curl -s -o /dev/null -w '%{http_code}' "${GRAPHDB_URL}/rest/repositories" || true)
        case "$status" in
            200) SECURED=false; break ;;
            401|403) SECURED=true; break ;;
        esac
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

    # Every file mapped in the ontology catalog (same list as ontology_server_files()
    # in dagster_pipeline/assets/harmonisation.py)
    files=$(grep -o ' uri="[^"]*"' "${ONTOLOGY_CATALOG}" \
        | sed 's/ uri="\(.*\)"/"ontology\/\1"/' | sort -u | paste -sd, -)

    curl -sf -X POST "${GRAPHDB_URL}/rest/repositories/${ONTOLOGY_REPO}/import/server" \
        -H "Content-Type: application/json" \
        -d "{\"fileNames\": [${files}]}"

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
if [ "$SECURED" = "true" ]; then
    echo "GraphDB security is already enabled: initialisation ran before, nothing to do."
    echo "(The '${ONTOLOGY_REPO}' repository keeps its ontology; use 'docker compose down -v' for a fresh start.)"
    exit 0
fi
create_ontology_repo
import_ontology_files
wait_for_import
enable_security

echo "GraphDB initialisation complete."
