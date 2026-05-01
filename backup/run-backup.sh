#!/bin/bash
# Nightly backup orchestrator. Runs as root via /etc/cron.d/backup at 1:15 AM.
#
# Phases:
#   0. Sentinel check (abort fast if /mnt/backup not mounted)
#   1. Prepare staging dir
#   2. Postgres dumps
#   3. SQLite snapshots
#   4. OSM checkpoint
#   5. System metadata
#   6. Restic backup
#   7. Retention (forget + prune)
#   8. Update on-drive RESTORE notes + last-backup timestamp
#   9. Cleanup
#
# Notification model:
#   - On any phase failure: ntfy push (priority 5) + healthchecks /fail ping
#     with log tail, then non-zero exit.
#   - On success: optional low-priority ntfy + healthchecks success ping.
#
# We deliberately do NOT use `set -e` so we can handle errors explicitly
# and report them with context. Each phase's failure path runs `fail`.

set -uo pipefail

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"
STAGING=/var/lib/backup-staging
RESTIC_REPO=/mnt/backup/restic-repo
RESTIC_PASS=/root/.restic-password
EXCLUDES="$SCRIPT_DIR/exclude-list.txt"
RESTORE_MD="$SCRIPT_DIR/RESTORE.md"
LOG_FILE=/var/log/backup/run.log

APP_ROOT="${APP_ROOT:-/home/dhughes/apps}"
INFRASTRUCTURE_ROOT="${INFRASTRUCTURE_ROOT:-/home/dhughes/infrastructure}"

NOTIFY="$LIB_DIR/notify.sh"
HC_URL_FILE=/root/.healthchecks-url

HC=""
if [ -f "$HC_URL_FILE" ]; then
    HC=$(cat "$HC_URL_FILE")
fi

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
log() {
    echo "[$(date -Iseconds)] $*"
}

hc_ping() {
    # $1 = endpoint suffix ("", "/start", "/fail")
    # $2 = optional body
    if [ -z "$HC" ]; then return 0; fi
    if [ -n "${2:-}" ]; then
        curl -fsS -m 10 --retry 3 --data-binary "$2" "${HC}${1}" > /dev/null || true
    else
        curl -fsS -m 10 --retry 3 "${HC}${1}" > /dev/null || true
    fi
}

fail() {
    # $1 = phase name, $2 = exit code
    local PHASE="$1"
    local EXIT="$2"
    local TAIL
    TAIL=$(tail -30 "$LOG_FILE" 2>/dev/null || echo '(no log available)')

    log "FATAL: $PHASE failed with exit $EXIT"
    "$NOTIFY" 5 "BACKUP FAILED: $PHASE (exit $EXIT)" "$TAIL" || true
    hc_ping "/fail" "$PHASE failed with exit $EXIT"
    exit "$EXIT"
}

# Run a phase command and abort with proper error context on failure.
# Captures the actual exit code (the `if !` pattern reports 0 incorrectly
# because the `!` inverts the pipeline status before $? is evaluated).
# Usage: run_phase "<phase description>" <command> [args...]
run_phase() {
    local PHASE="$1"
    shift
    "$@"
    local EXIT=$?
    if [ $EXIT -ne 0 ]; then
        fail "$PHASE" "$EXIT"
    fi
}

# ----------------------------------------------------------------------------
# Phase 0: Sentinel check
# ----------------------------------------------------------------------------
log "==== Backup run starting ===="
hc_ping "/start"

if ! mountpoint -q /mnt/backup; then
    fail "Phase 0 (sentinel): /mnt/backup is not mounted" 1
fi
if [ ! -f /mnt/backup/.mounted ]; then
    fail "Phase 0 (sentinel): /mnt/backup/.mounted file missing" 1
fi
log "Phase 0: sentinel check passed"

# ----------------------------------------------------------------------------
# Phase 1: Prepare staging dir
# ----------------------------------------------------------------------------
log "Phase 1: preparing staging directory"
rm -rf "$STAGING"
mkdir -p "$STAGING"
chmod 0700 "$STAGING"

# ----------------------------------------------------------------------------
# Phase 2: Postgres dumps
# ----------------------------------------------------------------------------
log "Phase 2: Postgres dumps"
run_phase "Phase 2 (Postgres dumps)" "$LIB_DIR/pg-dump-all.sh" "$STAGING"

# ----------------------------------------------------------------------------
# Phase 3: SQLite snapshots
# ----------------------------------------------------------------------------
log "Phase 3: SQLite snapshots"
run_phase "Phase 3 (SQLite snapshots)" "$LIB_DIR/sqlite-snapshot.sh" "$STAGING"

# ----------------------------------------------------------------------------
# Phase 4: OSM data (replication checkpoint + app-tables dump)
# ----------------------------------------------------------------------------
log "Phase 4: OSM (checkpoint + tables dump)"
run_phase "Phase 4 (OSM checkpoint)" "$LIB_DIR/osm-checkpoint.sh" "$STAGING"
run_phase "Phase 4 (OSM tables dump)" "$LIB_DIR/osm-tables-dump.sh" "$STAGING"

# ----------------------------------------------------------------------------
# Phase 5: System metadata
# ----------------------------------------------------------------------------
log "Phase 5: System metadata"
mkdir -p "$STAGING/metadata"
apt-mark showmanual > "$STAGING/metadata/installed-packages.txt"
crontab -l -u dhughes > "$STAGING/metadata/crontab-dhughes.txt" 2>/dev/null || true
crontab -l > "$STAGING/metadata/crontab-root.txt" 2>/dev/null || true
ls /etc/systemd/system/ > "$STAGING/metadata/systemd-units.txt"
ls /etc/cron.d/ > "$STAGING/metadata/cron-d-listing.txt" 2>/dev/null || true

# ----------------------------------------------------------------------------
# Phase 6: Restic backup
# ----------------------------------------------------------------------------
log "Phase 6: Restic backup"
run_phase "Phase 6 (Restic backup)" \
    restic backup \
    --repo "$RESTIC_REPO" \
    --password-file "$RESTIC_PASS" \
    --tag nightly \
    --exclude-file "$EXCLUDES" \
    --exclude-caches \
    "$STAGING" \
    "$APP_ROOT" \
    "$INFRASTRUCTURE_ROOT" \
    /etc/ssh \
    /etc/ddclient.conf \
    /etc/crypttab \
    /etc/fstab \
    /etc/cron.d \
    /etc/logrotate.d \
    /root/backup-disk.key \
    /home/dhughes/.ssh/authorized_keys

# ----------------------------------------------------------------------------
# Phase 7: Retention
# ----------------------------------------------------------------------------
log "Phase 7: Retention (forget + prune)"
run_phase "Phase 7 (Retention)" \
    restic forget \
    --repo "$RESTIC_REPO" \
    --password-file "$RESTIC_PASS" \
    --keep-daily 14 \
    --keep-weekly 8 \
    --keep-monthly 12 \
    --prune

# ----------------------------------------------------------------------------
# Phase 8: Update on-drive RESTORE notes + timestamp
# ----------------------------------------------------------------------------
log "Phase 8: Updating on-drive RESTORE notes + timestamp"
if [ -f "$RESTORE_MD" ]; then
    cp "$RESTORE_MD" /mnt/backup/RESTORE.md
fi
date +%s > /mnt/backup/last-backup-timestamp

# ----------------------------------------------------------------------------
# Phase 9: Cleanup
# ----------------------------------------------------------------------------
log "Phase 9: Cleanup"
rm -rf "$STAGING"

# ----------------------------------------------------------------------------
# Success
# ----------------------------------------------------------------------------
REPO_SIZE=$(du -sh "$RESTIC_REPO" 2>/dev/null | cut -f1 || echo "?")
log "==== Backup completed successfully (repo size: $REPO_SIZE) ===="
hc_ping ""
"$NOTIFY" 2 "Backup OK" "$(date -Iminutes), repo size $REPO_SIZE" || true
