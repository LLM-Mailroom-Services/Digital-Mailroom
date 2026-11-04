#!/usr/bin/env bash
# SAND-042 parallel fleet launch — two cells at once, COLLISION-FREE.
#
# Each cell gets its own Modal app (so its own URL and its own cache Volumes):
#   - app name  -> from the cell's config `engine.modal.app` (deploy-env renders
#                  MODAL_VLLM_APP_NAME; benchmark-check enforces the match), and
#   - the HF / vLLM cache Volumes are app-scoped (deploy/modal_vllm.py), so two
#     concurrent fleets never write the same cache.
# The in-container GPU telemetry Volume stays SHARED: its files are namespaced
# per cell by MODAL_VLLM_TELEMETRY_LABEL, so that is not a collision.
#
# Preconditions: the default `sandbox-vllm` app is free (or you have given it
# another name) — the two fleets here use NON-default app names so they can even
# overlap a running `sandbox-vllm` campaign.
#
# Usage:
#   ~/sand42-parallel.sh                       # print the plan only
#   ~/sand42-parallel.sh --go                  # deploy both fleets and run
#   ~/sand42-parallel.sh --go 2l4-c8 sandbox-vllm-a 2l4-c16 sandbox-vllm-b
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
source .venv/bin/activate

PROFILE=exios66
GO=0
ARGS=()
for a in "$@"; do
  if [ "$a" = "--go" ]; then GO=1; else ARGS+=("$a"); fi
done
CELL_A=${ARGS[0]:-2l4-c8};   APP_A=${ARGS[1]:-sandbox-vllm-a}
CELL_B=${ARGS[2]:-2l4-c16};  APP_B=${ARGS[3]:-sandbox-vllm-b}
SINGLE=0
if [ "$CELL_B" = "-" ]; then SINGLE=1; fi   # one fleet only (overlap a running campaign)
[ "$SINGLE" = 1 ] || [ "$APP_A" != "$APP_B" ] || { echo "app names must differ"; exit 2; }

GEN=data/runtime/parallel-configs   # gitignored scratch; derived, not committed

echo "=== PLAN ==="
echo "  fleet A: cell $CELL_A on app $APP_A  (caches: $APP_A-scoped)"
if [ "$SINGLE" = 1 ]; then echo "  fleet B: (none — single fleet)"; else
echo "  fleet B: cell $CELL_B on app $APP_B  (caches: $APP_B-scoped)"; fi
if [ "$SINGLE" = 1 ]; then echo "  telemetry: shared volume, label sand42-$CELL_A"
else echo "  telemetry: shared volume, labels sand42-$CELL_A / sand42-$CELL_B"; fi
echo "  generated configs: $GEN/<app>/<run>.yaml"
[ "$GO" = 1 ] || { echo "(dry run — re-run with --go)"; exit 0; }

modal profile activate "$PROFILE" >/dev/null
[ "$(modal profile current)" = "$PROFILE" ] || { echo "activate $PROFILE first"; exit 3; }

# Materialize this fleet's configs: the app is the ONLY field that differs per
# fleet, so patch it and leave the run_id (and therefore the report path) intact.
materialize() {  # $1=cell  $2=app
  local cell="$1" app="$2" src out
  mkdir -p "$GEN/$app"
  for src in config/runs/sand42-50-*-awq-"$cell".yaml; do
    out="$GEN/$app/$(basename "$src")"
    .venv/bin/python - "$src" "$out" "$app" <<'PY'
import re, sys
src, out, app = sys.argv[1:4]
text = open(src, encoding="utf-8").read()
text, n = re.subn(r"(?m)^(\s*app:\s*).*$", lambda m: m.group(1) + app, text, count=1)
assert n == 1, f"no app: line in {src}"
open(out, "w", encoding="utf-8").write(text)
PY
  done
}

run_fleet() {  # $1=cell  $2=app
  local cell="$1" app="$2"
  local folder="${cell/l4/L4}" log="$HOME/sand42-$cell.log"
  local cfgs=() f r rid
  materialize "$cell" "$app"
  # Driver order (sand42.sh run_cell), NOT `ls` order: run order shapes prefix-cache
  # warmup and cold-boot attribution, so reordering would make this cell incomparable
  # with the 1xL4 cells that ran correspondence-first.
  local order=(correspondence-specialist insurance-claims-specialist corporate-records-specialist contracts-specialist merger-specialist)
  for r in "${order[@]}"; do
    f="$GEN/$app/sand42-50-$r-awq-$cell.yaml"
    [ -f "$f" ] || { echo "[$app] missing config $f"; return 5; }
    # Refuse a store that already has results: `run start` RESUMES (runner
    # resume_cursor), so re-running a store another fleet/app already wrote would
    # silently mix items from two Modal apps inside one run_id.
    rid="$(basename "$f" .yaml)"
    if [ -s "data/runtime/runs/$rid/items.jsonl" ]; then
      echo "[$app] REFUSING: $rid already has items.jsonl — a re-run would resume/mix stores"
      return 5
    fi
    cfgs+=("$f")
  done

  {
    echo "[$app] $(date '+%F %H:%M:%S') fleet start ($cell)"
    # Per-fleet env from the config: MODAL_VLLM_APP_NAME (the app), telemetry
    # label, container knobs. Scoped to this subshell, so the other fleet's env
    # is untouched (benchmark-check enforces the match — no drift).
    set -a; eval "$(sandbox run deploy-env --config "${cfgs[0]}")"; set +a
    export MODAL_VLLM_APP="$app"                    # teardown_vllm.sh targets this app
    export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"
    export VLLM_API_KEY="$MODAL_VLLM_API_TOKEN"
    export SANDBOX_PROFILE=modal-vllm PHOENIX_TRACING=disabled OPENROUTER_API_KEY=""

    echo "[$app] $(date '+%H:%M:%S') benchmark-check"
    sandbox run benchmark-check --config "${cfgs[0]}" --modal-profile "$PROFILE"

    # Pre-warm THIS fleet's own HF cache. download_model is the CPU image (no GPU
    # billed); the app-scoped volume keeps it out of the other fleet's cache.
    echo "[$app] $(date '+%H:%M:%S') pre-warm weights"
    modal run deploy/modal_vllm.py::download_model

    local deploy_ts ready_ts teardown_ts
    deploy_ts=$(date +%s)
    echo "[$app] $(date '+%H:%M:%S') deploy"
    modal deploy deploy/modal_vllm.py --strategy recreate

    export VLLM_BASE_URL="https://${PROFILE}--${app}-serve.modal.run/v1"
    for i in $(seq 1 80); do
      sandbox health --profile modal-vllm >/dev/null 2>&1 && break
      [ "$i" = 80 ] && { echo "[$app] endpoint never came up"; return 4; }
      echo "[$app] booting ($((i*15))s)…"; sleep 15
    done
    ready_ts=$(date +%s)
    sandbox health --profile modal-vllm

    for cfg in "${cfgs[@]}"; do
      echo "[$app] $(date '+%H:%M:%S') === $(basename "$cfg")"
      sandbox run preflight --config "$cfg" --live --force
      sandbox run scrape-metrics --config "$cfg" --label before
      sandbox run start --config "$cfg" --job-mode endpoint
      sandbox run scrape-metrics --config "$cfg" --label after
      sandbox run card --config "$cfg"
    done

    # Non-fatal: a teardown verification failure must not abort the subshell before
    # the fleet window and the cell card are written (the driver orders this the
    # same way). The verification failure is still loud in the log.
    ./deploy/teardown_vllm.sh "$app" </dev/null \
        || echo "[$app] WARN teardown verification failed — check for a warm container"
    teardown_ts=$(date +%s)
    .venv/bin/python - "$folder" "$deploy_ts" "$ready_ts" "$teardown_ts" "$cell" "${MODAL_VLLM_MAX_CONTAINERS:-1}" <<'PY'
import json, sys
folder, deploy, ready, teardown, cell, replicas = sys.argv[1:7]
path = f"reports/SAND42/{folder}/fleet_window.json"
json.dump({"cell": cell, "deploy_ts": float(deploy), "ready_ts": float(ready), "gpu": "L4",
           "replicas": int(replicas), "source": "wall clock (deploy → teardown)",
           "teardown_ts": float(teardown)}, open(path, "w"), indent=2)
print("wrote", path)
PY
    sandbox run card --runbook "sand42-$cell"
    echo "[$app] $(date '+%F %H:%M:%S') fleet done ($cell)"
  } >>"$log" 2>&1
}

# Run the fleets concurrently; each has its own env, app and caches.
rc=0
if [ "$SINGLE" = 1 ]; then
  run_fleet "$CELL_A" "$APP_A" || { echo "fleet ($CELL_A) failed — see ~/sand42-$CELL_A.log"; rc=1; }
else
  run_fleet "$CELL_A" "$APP_A" & PID_A=$!
  run_fleet "$CELL_B" "$APP_B" & PID_B=$!
  wait "$PID_A" || { echo "fleet A ($CELL_A) failed — see ~/sand42-$CELL_A.log"; rc=1; }
  wait "$PID_B" || { echo "fleet B ($CELL_B) failed — see ~/sand42-$CELL_B.log"; rc=1; }
fi

echo "[parallel] $(date '+%F %H:%M:%S') rebuild master across all cells"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
.venv/bin/sandbox run card --runbook sand42 || rc=1
echo "[parallel] $(date '+%F %H:%M:%S') DONE (rc=$rc) — logs: ~/sand42-$CELL_A.log ~/sand42-$CELL_B.log"
exit "$rc"
