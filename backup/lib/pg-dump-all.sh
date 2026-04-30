#!/bin/bash
# shellcheck disable=SC2024
# (SC2024: redirects on `sudo -u postgres ... > file` happen in the calling
# shell, not under sudo. We run this script as root via /etc/cron.d/backup,
# so root's shell handles the redirect and has write access to $STAGING. The
# postgres process inherits the open FD. Correct as-written.)
#
# Dump every non-system PostgreSQL database to the staging directory.
#
# Per-DB exclusions:
#   - Any DB containing an `osm` schema gets that schema excluded (it's
#     huge derived data; handled separately via osm-checkpoint.sh + the
#     bootstrap PBF). Detection is dynamic — works for both prod
#     (`color_the_map`) and local dev (worktree DBs cloned from the OSM
#     template).
#
# Whole-DB exclusions (BACKUP_SKIP_DBS env var, comma-separated):
#   - Default: color-the-map-osm-template (a dev-only template DB used for
#     APFS-cloning into worktree DBs; ~125 GB; not present on prod).
#
# Postgres auth (PG_SUDO env var):
#   - Default: `sudo -u postgres` (matches prod's peer-auth setup).
#   - For local dev override with PG_SUDO="" (assumes the running user can
#     reach the cluster).
#
# Usage: pg-dump-all.sh <staging-dir>
# Output: <staging-dir>/postgres/<db>.dump and <db>.extensions.txt

set -euo pipefail

STAGING="${1:-/var/lib/backup-staging}/postgres"
SKIP_LIST=${BACKUP_SKIP_DBS:-color-the-map-osm-template}
PG_SUDO=${PG_SUDO-sudo -u postgres}

mkdir -p "$STAGING"

DBS=$($PG_SUDO psql -tAc "
    SELECT datname FROM pg_database
    WHERE datistemplate = false AND datname NOT IN ('postgres')
    ORDER BY datname;
")

if [ -z "$DBS" ]; then
    echo "No application databases found." >&2
    exit 1
fi

DUMPED=0
for DB in $DBS; do
    if [[ ",$SKIP_LIST," == *",$DB,"* ]]; then
        echo "  skip: $DB (in BACKUP_SKIP_DBS)"
        continue
    fi

    # Detect whether this DB has an osm schema (dynamic — works for
    # color_the_map on prod and color-the-map-<branch> worktree DBs locally).
    HAS_OSM=$($PG_SUDO psql -d "$DB" -tAc \
        "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'osm';")

    if [ -n "$HAS_OSM" ]; then
        echo "  dumping: $DB (excluding osm schema)"
        $PG_SUDO pg_dump --format=custom --exclude-schema=osm "$DB" \
            > "$STAGING/${DB}.dump"
    else
        echo "  dumping: $DB"
        $PG_SUDO pg_dump --format=custom "$DB" > "$STAGING/${DB}.dump"
    fi

    $PG_SUDO psql -d "$DB" -c "\dx" > "$STAGING/${DB}.extensions.txt" 2>&1

    DUMPED=$((DUMPED + 1))
done

echo "Postgres dumps complete: $DUMPED database(s)"
