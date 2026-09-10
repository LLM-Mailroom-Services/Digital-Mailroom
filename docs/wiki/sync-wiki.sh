#!/usr/bin/env bash
# Sync docs/wiki/ -> https://github.com/LLM-Mailroom-Services/Digital-Mailroom/wiki (DMR-002).
# Same pattern as packages/llm-entity-extraction/docs/wiki/sync-wiki.sh:
# the wiki source is version-controlled HERE; the GitHub wiki is a mirror.
#
# Usage:
#   ./docs/wiki/sync-wiki.sh           # clone-or-pull the wiki repo, copy pages, commit + push
#   ./docs/wiki/sync-wiki.sh --check   # verify the wiki is current (no writes)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WIKI_URL="https://github.com/LLM-Mailroom-Services/Digital-Mailroom.wiki.git"
WIKI_TMP="${WIKI_TMP:-/tmp/digital-mailroom-wiki}"
SRC="$REPO_ROOT/docs/wiki"

cd "$SRC"

if [[ "${1:-}" == "--check" ]]; then
    # every tracked wiki page must be identical to the live wiki clone
    rm -rf "$WIKI_TMP"
    git clone --quiet "$WIKI_URL" "$WIKI_TMP" 2>/dev/null || {
        echo "wiki repo unreachable or uninitialized"; exit 1; }
    rc=0
    for f in *.md _Sidebar.md; do
        [[ -f "$SRC/$f" ]] || continue
        if ! diff -q "$SRC/$f" "$WIKI_TMP/$f" >/dev/null 2>&1; then
            echo "DRIFT: $f differs from the live wiki"; rc=1
        fi
    done
    [[ $rc -eq 0 ]] && echo "wiki in sync with docs/wiki/"
    exit $rc
fi

if [[ -d "$WIKI_TMP/.git" && -n "$(git -C "$WIKI_TMP" remote get-url origin 2>/dev/null || true)" ]] \
    && git -C "$WIKI_TMP" rev-parse --verify -q origin/master >/dev/null; then
    git -C "$WIKI_TMP" pull --ff-only --quiet origin master
else
    rm -rf "$WIKI_TMP"
    git clone --quiet "$WIKI_URL" "$WIKI_TMP"
fi

copied=0
for f in *.md _Sidebar.md; do
    [[ -f "$SRC/$f" ]] || continue
    cp "$SRC/$f" "$WIKI_TMP/$f"
    copied=$((copied + 1))
done

cd "$WIKI_TMP"
if [[ -n "$(git status --porcelain)" ]]; then
    git add -A
    git commit -q -m "${WIKI_CARD:-docs}: sync wiki from Digital-Mailroom docs/wiki/ ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
    git push --quiet origin master
    echo "pushed $copied page(s) to the wiki"
else
    echo "wiki already up to date ($copied page(s) identical)"
fi
