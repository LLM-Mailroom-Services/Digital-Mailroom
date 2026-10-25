#!/usr/bin/env bash
# Publish the wiki/ directory to the GitHub wiki.
# Mirrors docs/ (edit both in the same change; AGENTS.md documents the
# release process that requires this after every pushed major/minor release).
set -euo pipefail

cd "$(dirname "$0")"

REPO_URL="$(git -C .. remote get-url origin | sed 's|\.git$||')"

if [[ "$REPO_URL" != *github.com/* ]]; then
  echo "error: origin is not a GitHub repo (got: $REPO_URL)" >&2
  exit 1
fi

WIKI_URL="${REPO_URL%.git}.wiki.git"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "pushing wiki/ -> $WIKI_URL"
git clone --quiet "$WIKI_URL" "$TMP/wiki" || {
  echo "error: failed to clone wiki (does $REPO_URL/wiki exist?)" >&2
  exit 1
}

rsync -a --delete ./ "$TMP/wiki/"

(
  cd "$TMP/wiki"
  git add -A
  if git diff --cached --quiet; then
    echo "no wiki changes"
    exit 0
  fi
  git commit -m "Sync wiki from docs/ ($(date +%Y-%m-%d))"
  git push --quiet
)

echo "wiki published"
