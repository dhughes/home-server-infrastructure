#!/bin/bash
# Alert (via ntfy) if /mnt/backup is over the threshold % full.
# Idempotent: emits at most one ntfy per cron run regardless of severity.

set -euo pipefail

THRESHOLD=${THRESHOLD:-80}
MOUNT=${MOUNT:-/mnt/backup}
NOTIFY="$(dirname "$(readlink -f "$0")")/notify.sh"

if ! mountpoint -q "$MOUNT"; then
    "$NOTIFY" 5 "Backup drive not mounted" "$MOUNT is not currently mounted. Backups will fail."
    exit 1
fi

USE=$(df --output=pcent "$MOUNT" | tail -1 | tr -dc '0-9')
FREE=$(df -h "$MOUNT" | tail -1 | awk '{print $4}')

if [ "$USE" -gt "$THRESHOLD" ]; then
    "$NOTIFY" 4 \
        "Backup disk ${USE}% full" \
        "${MOUNT} has ${FREE} free. Consider tightening retention (restic forget) or removing older OSM bootstrap PBFs."
fi
