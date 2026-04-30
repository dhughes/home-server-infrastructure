#!/bin/bash
# shellcheck disable=SC2024
# (SC2024: redirect on `sudo -u postgres psql ... > file` runs in the calling
# shell. We run as root via cron, so root's shell handles the redirect and
# has write access to $STAGING. Correct as-written.)
#
# Save the OSM replication state from osm.osm2pgsql_properties.
#
# This is the bookmark needed to resume incremental replication after
# restoring OSM data from the bootstrap PBF in /mnt/backup/osm-bootstrap/.
#
# Dumps the entire properties table as CSV (with header) so we don't need
# to track column names — everything restic needs at recovery time is here.
#
# Usage: osm-checkpoint.sh <staging-dir>
# Output: <staging-dir>/osm/osm2pgsql_properties.csv

set -euo pipefail

STAGING="${1:-/var/lib/backup-staging}/osm"
DB=${OSM_DB:-color_the_map}

mkdir -p "$STAGING"

# Use \COPY with CSV HEADER so the dump is structure-agnostic and parseable.
sudo -u postgres psql -d "$DB" -c \
    "\COPY osm.osm2pgsql_properties TO STDOUT WITH CSV HEADER" \
    > "$STAGING/osm2pgsql_properties.csv"

if [ ! -s "$STAGING/osm2pgsql_properties.csv" ]; then
    echo "WARNING: osm2pgsql_properties.csv is empty (table missing or no rows?)" >&2
    exit 1
fi

LINES=$(wc -l < "$STAGING/osm2pgsql_properties.csv")
echo "OSM checkpoint saved: $((LINES - 1)) rows"
