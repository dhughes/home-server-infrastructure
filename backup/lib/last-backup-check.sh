#!/bin/bash
# Alert (via ntfy) if no successful backup has occurred in the last 36 hours.
# Catches the case where the script is failing in some way that bypasses the
# healthchecks watchdog (e.g., succeeding-but-not-actually-backing-anything).

set -euo pipefail

TS_FILE=${TS_FILE:-/mnt/backup/last-backup-timestamp}
THRESHOLD_SECONDS=${THRESHOLD_SECONDS:-129600}  # 36 hours
NOTIFY="$(dirname "$(readlink -f "$0")")/notify.sh"

if [ ! -f "$TS_FILE" ]; then
    "$NOTIFY" 5 "Backup timestamp missing" "$TS_FILE does not exist. The backup may never have run, or the file was deleted."
    exit 1
fi

NOW=$(date +%s)
LAST=$(cat "$TS_FILE")
AGE=$((NOW - LAST))

if [ "$AGE" -gt "$THRESHOLD_SECONDS" ]; then
    HOURS=$((AGE / 3600))
    "$NOTIFY" 5 \
        "Backup is stale (${HOURS}h old)" \
        "Last successful backup was ${HOURS}h ago. Check /var/log/backup/run.log."
fi
