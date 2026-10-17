#!/usr/bin/env bash
# SAND-054: the campaign pager — the notification path.
#
# Waits on the sitter's sentinel and exits the instant it appears, which is what raises the
# operator notification. It removes the sentinel before exiting, so the next trouble pages
# again without anyone re-arming anything — the reason this exists instead of a watcher that
# exits on its first alert and then watches nothing.
#
# It also exits when the campaign is over, so the operator learns the legs are gone rather
# than the pager sitting silently forever.
#
#   bash scripts/sand42/campaign-pager.sh
set -uo pipefail
SENT="$HOME/.sand42-page-me"
LEGS='sand42-rerun-chain\.sh|sand42-1l4-c8-rerun\.sh|sand42-1l4-c16-rerun\.sh|sand42-2l4-rerun\.sh'
GAP="${1:-5}"

while :; do
  if [ -s "$SENT" ]; then
    echo "[pager $(date '+%H:%M:%S')] TROUBLE — the campaign sitter flagged:"
    cat "$SENT"
    rm -f "$SENT"
    exit 3
  fi
  if ! pgrep -f "$LEGS" >/dev/null 2>&1; then
    echo "[pager $(date '+%H:%M:%S')] campaign finished — no legs running"
    exit 0
  fi
  sleep "$GAP"
done
