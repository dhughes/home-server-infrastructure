#!/bin/bash
# Send a push notification via ntfy.sh.
#
# Usage: notify.sh <priority> <title> <body>
#   priority: 1 (min) | 3 (default) | 4 (high) | 5 (max — bypasses Do Not Disturb)
#
# Reads the topic name from /root/.ntfy-topic by default.
# For local testing, override via env var: NTFY_TOPIC=foo ./notify.sh ...

set -euo pipefail

PRIO=${1:-3}
TITLE=${2:-Home server}
BODY=${3:-(no body)}

NTFY_TOPIC=${NTFY_TOPIC:-$(cat /root/.ntfy-topic)}

curl -fsS -m 10 --retry 3 \
    -H "Title: $TITLE" \
    -H "Priority: $PRIO" \
    -H "Tags: backup" \
    -d "$BODY" \
    "ntfy.sh/$NTFY_TOPIC" > /dev/null
