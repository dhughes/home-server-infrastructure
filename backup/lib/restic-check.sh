#!/bin/bash
# Weekly restic integrity check (metadata only — fast).
#
# `restic check` verifies all data structures are intact. It does NOT
# re-decrypt blob contents (that would be `restic check --read-data`,
# expensive — hours on a non-trivial repo). The cheap metadata check
# catches almost all real-world corruption.
#
# Pings a SEPARATE healthchecks check than the nightly backup (so we can
# track them independently). The URL goes in /root/.healthchecks-url-restic-check.
# If that file doesn't exist, the script still runs but skips the pings
# (graceful degradation — the ntfy on failure is the load-bearing alert).

set -euo pipefail

REPO=/mnt/backup/restic-repo
PASS=/root/.restic-password
HC_URL_FILE=/root/.healthchecks-url-restic-check
NOTIFY="$(dirname "$(readlink -f "$0")")/notify.sh"

HC=""
if [ -f "$HC_URL_FILE" ]; then
    HC=$(cat "$HC_URL_FILE")
fi

# /start ping for duration tracking
if [ -n "$HC" ]; then
    curl -fsS -m 10 --retry 3 "${HC}/start" > /dev/null || true
fi

if restic check --repo "$REPO" --password-file "$PASS"; then
    echo "Restic repo integrity check passed."
    if [ -n "$HC" ]; then
        curl -fsS -m 10 --retry 3 "$HC" > /dev/null || true
    fi
else
    EXIT=$?
    "$NOTIFY" 5 "Restic CHECK FAILED (exit $EXIT)" \
        "Repo integrity check failed. Run \`sudo restic check --repo $REPO --password-file $PASS\` manually for details. Snapshots may be unrecoverable until this is fixed."
    if [ -n "$HC" ]; then
        curl -fsS -m 10 --retry 3 --data-binary "Restic check failed with exit $EXIT" "${HC}/fail" > /dev/null || true
    fi
    exit "$EXIT"
fi
