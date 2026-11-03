#!/usr/bin/env bash
# Renders twinship-realm.json from its template by substituting secret
# placeholders with values from the container's environment (populated from
# the project's .env file via docker-compose), then hands off to the normal
# Keycloak startup command.
#
# Keycloak's --import-realm does not expand ${env.VAR} placeholders inside
# realm JSON files, so secrets are substituted here before the file is read.
set -euo pipefail

TEMPLATE=/opt/keycloak/render/twinship-realm.json.template
IMPORT_DIR=/opt/keycloak/data/import
mkdir -p "$IMPORT_DIR"

# Escape a raw value for safe embedding as a JSON string, then for safe use
# as a sed replacement (sed treats \ and & specially in replacement text).
json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}
sed_escape_replacement() {
  printf '%s' "$1" | sed -e 's/[\&]/\\&/g'
}
safe() { sed_escape_replacement "$(json_escape "$1")"; }

# Use a control character as the sed delimiter so secret values containing
# "/", "|", etc. can't collide with it.
D=$'\x01'
sed \
  -e "s${D}__DAGSTER_CLIENT_SECRET__${D}$(safe "$KEYCLOAK_CLIENT_SECRET")${D}g" \
  -e "s${D}__GRIMALDI_RORO_PASSWORD__${D}$(safe "$KEYCLOAK_GRIMALDI_RORO_PASSWORD")${D}g" \
  -e "s${D}__STENA_ROPAX_PASSWORD__${D}$(safe "$KEYCLOAK_STENA_ROPAX_PASSWORD")${D}g" \
  -e "s${D}__STENA_TANKER_PASSWORD__${D}$(safe "$KEYCLOAK_STENA_TANKER_PASSWORD")${D}g" \
  -e "s${D}__FUTURISTIC_VESSEL_PASSWORD__${D}$(safe "$KEYCLOAK_FUTURISTIC_VESSEL_PASSWORD")${D}g" \
  -e "s${D}__DEVELOPER_PASSWORD__${D}$(safe "$KEYCLOAK_DEVELOPER_PASSWORD")${D}g" \
  "$TEMPLATE" > "$IMPORT_DIR/twinship-realm.json"

exec /opt/keycloak/bin/kc.sh "$@"
