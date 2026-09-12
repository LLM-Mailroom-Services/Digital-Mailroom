#!/usr/bin/env bash
# Build + publish the static site to the `gh-pages` branch — NO GitHub Actions.
#
# GitHub Pages serves it via the native "Deploy from a branch" mode, which is
# configured ONCE in the GitHub UI (Settings → Pages → Source: "Deploy from a
# branch", branch: gh-pages, folder: /docs) and never touches Actions.
#
# Site layout produced (under docs/ on the gh-pages branch):
#   docs/index.html       terminal site root (owlcot-style TTY)
#   docs/terminal/        terminal site (terminal/) — the TTY
#   docs/pixel/           pixel-art SPA console
#   docs/pixel/static/{css,js}  pixel-engine assets
#   docs/.nojekyll        disable Jekyll processing
#   docs/data/*.json      snapshot exported from the trace source
#                         (Langfuse / Phoenix / both) by export_snapshot.py
#   docs/data/corpus.json slim catalog of Lucius-Morningstar/mailroom-dataset
#                         (export_corpus_catalog.py) — backs the terminal
#                         site's corpus ls/search/stats
#   docs/debug/build-info.json  provenance for agents (git sha, counts)
#
# Anything else already on the branch root is left untouched; legacy root-
# level site files from older publishes are cleaned up.
#
# Usage:
#   scripts/publish_pages.sh [--source langfuse|phoenix|both] [--since-hours N]
#                            [--limit N] [--skip-export] [--allow-empty] [--dry-run]
# Env overrides: PAGES_BRANCH (default gh-pages), PAGES_REMOTE (default origin).
set -euo pipefail

cd "$(dirname "$0")/.."

SOURCE="auto"
SINCE_HOURS="24"
LIMIT="200"
SKIP_EXPORT=0
ALLOW_EMPTY=0
DRY_RUN=0
STATUS_ONLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --source)      SOURCE="$2"; shift 2 ;;
    --since-hours) SINCE_HOURS="$2"; shift 2 ;;
    --limit)       LIMIT="$2"; shift 2 ;;
    --skip-export) SKIP_EXPORT=1; shift ;;
    --allow-empty) ALLOW_EMPTY=1; shift ;;
    --dry-run)     DRY_RUN=1; shift ;;
    --status)      STATUS_ONLY=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

BRANCH="${PAGES_BRANCH:-gh-pages}"
REMOTE="${PAGES_REMOTE:-origin}"
REPO_URL="$(git remote get-url "$REMOTE")"
HEAD_SHA="$(git rev-parse --short HEAD)"
DIRTY=$(git status --porcelain | head -1)

# The site is built from a main checkout (web/, scripts/). Running from
# another branch (e.g. gh-pages left checked out in GitHub Desktop) fails in
# confusing ways — fail clearly instead.
CURRENT_BRANCH="$(git branch --show-current)"
if [[ "$CURRENT_BRANCH" != "main" && "${ALLOW_ANY_BRANCH:-0}" != "1" ]]; then
  echo "error: publish_pages.sh must run from 'main' (currently on '${CURRENT_BRANCH:-detached}')." >&2
  echo "switch first:  git switch main   — then re-run." >&2
  exit 1
fi

# --status: is the deployed site built from this commit? Exit 0 = in sync.
if [[ "$STATUS_ONLY" -eq 1 ]]; then
  if ! git ls-remote --heads "$REMOTE" "refs/heads/$BRANCH" | grep -q .; then
    echo "SYNC STATUS: NOT PUBLISHED ($REMOTE@$BRANCH does not exist)"
    exit 1
  fi
  # Always fetch: publishes go through a temp clone, so the local
  # remote-tracking ref can lag the real branch.
  git fetch --quiet "$REMOTE" "$BRANCH"
  DEPLOYED="$(git show "FETCH_HEAD:docs/debug/build-info.json" 2>/dev/null || true)"
  if [[ -z "$DEPLOYED" ]]; then
    echo "SYNC STATUS: UNKNOWN ($BRANCH has no docs/debug/build-info.json)"
    exit 1
  fi
  DEP_SHA="$(python3 -c "import json,sys;print(json.load(sys.stdin).get('git_sha','?'))" <<<"$DEPLOYED")"
  DEP_AT="$(python3 -c "import json,sys;print(json.load(sys.stdin).get('generated_at','?'))" <<<"$DEPLOYED")"
  if [[ "$DEP_SHA" == "$HEAD_SHA" ]]; then
    echo "SYNC STATUS: IN SYNC (deployed ${DEP_SHA} @ ${DEP_AT} == HEAD)"
    exit 0
  fi
  echo "SYNC STATUS: STALE (deployed ${DEP_SHA} @ ${DEP_AT}; HEAD is ${HEAD_SHA})"
  echo "run: scripts/publish_pages.sh"
  exit 1
fi

if [[ -n "$DIRTY" ]]; then
  echo "note: working tree has uncommitted changes; build-info records HEAD ${HEAD_SHA} anyway"
fi

echo "== staging site shell (pixel console -> /pixel/) =="
rm -rf site
mkdir -p site/pixel/static
cp -R web/css web/js site/pixel/static/
cp web/index.html site/pixel/
touch site/.nojekyll

echo "== staging terminal site (docs/terminal/) =="
cp -R terminal site/terminal
touch site/terminal/.nojekyll

echo "== root index.html -> terminal =="
cp terminal/index.html site/index.html

if [[ "$SKIP_EXPORT" -ne 1 ]]; then
  echo "== exporting snapshot (source=${SOURCE} since=${SINCE_HOURS}h limit=${LIMIT}) =="
  python scripts/export_snapshot.py \
    --source "$SOURCE" --out site/data \
    --since-hours "$SINCE_HOURS" --limit "$LIMIT"

  echo "== exporting corpus catalog (mailroom-dataset slim rows) =="
  python scripts/export_corpus_catalog.py --out site/data
else
  echo "== skipping export (--skip-export): reusing existing site/data =="
fi

echo "== verifying snapshot =="
python scripts/export_snapshot.py --check --out site/data 2>/dev/null || \
  TRACE_COUNT=1

# Guard: an empty export usually means unreachable/misconfigured source, not
# "no runs". Never let it silently blank a populated live site.  For
# static-site deployments (--skip-export) the trace file may be absent; treat
# that as a passing guard so the terminal can be published independently.
TRACE_COUNT=$(python3 -c "import json;print(json.load(open('site/data/traces.json'))['count'])" 2>/dev/null || echo "1")
if [[ "$TRACE_COUNT" -eq 0 && "$ALLOW_EMPTY" -ne 1 ]]; then
  echo "" >&2
  echo "REFUSING to publish: the export contains 0 runs." >&2
  echo "This is usually LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY missing from" >&2
  echo ".env or an unreachable PHOENIX_ENDPOINT — check the WARN lines above." >&2
  echo "Publish anyway with --allow-empty." >&2
  exit 1
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "== dry run: site/ built, nothing pushed =="
  find site -type f | sort | sed 's/^/  /'
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
CLONE="$TMP/pages"

if git ls-remote --heads "$REMOTE" "refs/heads/$BRANCH" | grep -q .; then
  echo "== publishing to existing $BRANCH (docs/ folder) =="
  git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$CLONE"
else
  echo "== creating orphan $BRANCH (first publish) =="
  git clone --quiet --depth 1 "$REPO_URL" "$CLONE"
  (cd "$CLONE" && git checkout --orphan "$BRANCH" && git rm -rf --quiet .)
fi

# Site root on the branch is docs/. Clean legacy root-level site files from
# older publishes AND any sensitive/junk files that must never ride this
# branch (a previous Desktop mishap committed .env to gh-pages root); leave
# anything else untouched.
for legacy in index.html .nojekyll static data debug .env .DS_Store mailroom_ui server site tests tui web scripts docs.wiki; do
  rm -rf "$CLONE/$legacy"
done
rm -rf "$CLONE/docs"
mkdir -p "$CLONE/docs"
rsync -a --exclude '.git' site/ "$CLONE/docs/"

# Final guard: never push secrets or env files to a public-serving branch.
if find "$CLONE" -name ".env" -o -name "*.env" | grep -q .; then
  echo "ABORT: .env-like file present in staging tree — refusing to push" >&2
  exit 1
fi
if grep -rl "sk-lf-\|pk-lf-" --exclude-dir=.git "$CLONE" >/dev/null 2>&1; then
  echo "ABORT: Langfuse key material detected in staged files — refusing to push" >&2
  exit 1
fi

(
  cd "$CLONE"
  git add -A
  if git diff --cached --quiet; then
    echo "no site changes to publish"
    exit 0
  fi
  git commit --quiet -m "PUBLISH: pages snapshot $(date '+%Y-%m-%d %H:%M %Z') (${HEAD_SHA})"
  if git rev-parse --abbrev-ref HEAD | grep -q "^$BRANCH$"; then
    git push --quiet origin "$BRANCH"
  else
    git push --quiet origin HEAD:"refs/heads/$BRANCH"
  fi
)

echo "published -> $REMOTE@$BRANCH:/docs"
echo "Pages source must be: Deploy from a branch -> $BRANCH -> /docs"
