#!/usr/bin/env bash
# Vercel Ignored Build Step (monorepo): exit 0 → skip deploy, exit 1 → build.
# Only board-site/ changes should consume the digital-mailroom Vercel budget.
set -uo pipefail

repo_root="${VERCEL_GIT_REPO_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$repo_root" || exit 1

prev="${VERCEL_GIT_PREVIOUS_SHA:-}"
curr="${VERCEL_GIT_COMMIT_SHA:-}"

if [[ -n "$prev" && -n "$curr" ]]; then
  git diff --quiet "$prev" "$curr" -- board-site/
else
  git diff --quiet HEAD^ HEAD -- board-site/
fi
