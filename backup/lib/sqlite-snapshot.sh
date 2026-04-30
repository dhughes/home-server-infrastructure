#!/bin/bash
# Snapshot every SQLite database under /home/dhughes/apps using
# `sqlite3 .backup`, which is online-safe (doesn't require stopping the app).
#
# Search depth is bounded to keep it from descending into venv/node_modules
# or going arbitrarily deep into test directories.
#
# Usage: sqlite-snapshot.sh <staging-dir>
# Output: <staging-dir>/sqlite/<rel-path-under-apps>

set -euo pipefail

STAGING="${1:-/var/lib/backup-staging}/sqlite"
APPS_ROOT=${APPS_ROOT:-/home/dhughes/apps}

mkdir -p "$STAGING"

COUNT=0
while IFS= read -r DB; do
    REL=$(realpath --relative-to="$APPS_ROOT" "$DB")
    DEST="$STAGING/$REL"
    mkdir -p "$(dirname "$DEST")"

    echo "  snapshotting: $REL"
    sqlite3 "$DB" ".backup '$DEST'"
    COUNT=$((COUNT + 1))
done < <(find "$APPS_ROOT" -maxdepth 3 \
    \( -name node_modules -o -name venv -o -name .venv -o -name __pycache__ -o -name .git \) -prune \
    -o -type f \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \) -print)

echo "SQLite snapshots complete: $COUNT database(s)"
