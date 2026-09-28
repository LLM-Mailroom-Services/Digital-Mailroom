#!/usr/bin/env bash
# Vercel Ignored Build Step (monorepo, Root Directory = board-site/).
# Exit 0 → skip deploy; exit 1 → build. See board-site/vercel.json.
set -eo pipefail

find_git_root() {
  local dir="${1:-$PWD}"
  while [[ "$dir" != "/" ]]; do
    if [[ -d "$dir/.git" ]]; then
      printf '%s' "$dir"
      return 0
    fi
    dir=$(dirname "$dir")
  done
  return 1
}

root="$(find_git_root "$PWD" || true)"
if [[ -z "$root" ]]; then
  exit 0
fi
cd "$root"

diff_board_site() {
  local base="$1" head="$2"
  git diff --name-only "$base" "$head" -- board-site/
}

prev="${VERCEL_GIT_PREVIOUS_SHA:-}"
curr="${VERCEL_GIT_COMMIT_SHA:-}"

if [[ -n "$prev" && -n "$curr" ]]; then
  mapfile -t changed < <(diff_board_site "$prev" "$curr")
elif git rev-parse --verify HEAD^ >/dev/null 2>&1; then
  mapfile -t changed < <(diff_board_site HEAD^ HEAD)
else
  git fetch --depth=1 origin main 2>/dev/null || true
  if git rev-parse --verify origin/main >/dev/null 2>&1; then
    base=$(git merge-base HEAD origin/main 2>/dev/null || echo origin/main)
    mapfile -t changed < <(diff_board_site "$base" HEAD)
  else
    exit 0
  fi
fi

if ((${#changed[@]} == 0)); then
  exit 0
fi

infra_only=1
for path in "${changed[@]}"; do
  case "$path" in
    board-site/vercel.json | board-site/scripts/ignore-build.sh) ;;
    *) infra_only=0; break ;;
  esac
done
if ((infra_only)); then
  exit 0
fi

exit 1
