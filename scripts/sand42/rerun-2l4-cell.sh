#!/usr/bin/env bash
# SAND-042 2xL4 RE-RUN - one cell, given as $1.
#
# Why: the audit of every required metric shows ALL FIVE 2l4-c16 runs lack the MID-RUN
# KV/queue sample — the cell ran before `scrape-metrics --label mid` existed, and the
# before/after pair brackets each run at its DRAINED EDGES, where kv_cache_usage_perc
# gauges a pre-allocated cache with no live sequences and reads 0 by construction. The
# verbatim /metrics and the memory-bandwidth families are already complete for this cell;
# the mid-run sample is the only thing this leg adds.
#
# 2×L4 (min=max containers 2 from the config), one warm fleet, five specialists chained,
# teardown after the fifth, and a proper fleet window (deploy -> ready -> teardown) so the
# cold-boot row is measured rather than reasoned.
#
#   ~/sand42-2l4-rerun.sh <cell> 2>&1 | tee ~/sand42-$CELL.log
#
# Run ONLY when no other SAND-042 fleet holds the app name.
set -euo pipefail
CELL="${1:?usage: sand42-2l4-rerun.sh <cell>  e.g. 2l4-c8}"
FOLDER="${CELL/l4/L4}"
cd /Users/luciusjmorningstar/Downloads/local-mailroom-sandbox
# shellcheck disable=SC1091
source .venv/bin/activate
.venv/bin/python -c "import modal" || { echo "[$CELL] modal missing from .venv — uv sync --extra deploy"; exit 3; }

PROFILE=exios66
export SANDBOX_MODAL_PROFILE_TRACK_A="$PROFILE"
modal profile activate "$PROFILE"
[ "$(modal profile current)" = "$PROFILE" ] || { echo "[$CELL] activate $PROFILE first"; exit 3; }
export SANDBOX_PROFILE=modal-vllm PHOENIX_TRACING=disabled OPENROUTER_API_KEY=""

# Duplicate guard, aligned with the campaign's own gate (SAND-048 finding): only the
# coverage-ledger verdict decides "finished" — and only when it ran successfully.
# rc=0  → ALL CAPTURES: finished work, refuse the re-run.
# rc=1  → gaps: repair path, archive and re-run.
# rc>=2 → the arbiter itself failed (crash/env/renamed ARGUMENT): refuse WITHOUT touching
#         the stores — archiving on a broken arbiter is how finished cells get destroyed.
GUARD_OUT=$( .venv/bin/python scripts/sand42/coverage-ledger.py "$CELL" 2>&1 )
GUARD_RC=$?
if [ "$GUARD_RC" -eq 0 ]; then
  echo "[$CELL] REFUSING: coverage-ledger verdict is ALL CAPTURES — this cell is finished."
  echo "[$CELL] Re-running would duplicate finished work. Repair path: scripts/sand42/topup-one-class.sh <class> <cell>"
  exit 7
elif [ "$GUARD_RC" -ne 1 ]; then
  echo "[$CELL] REFUSING: coverage-ledger FAILED (rc=$GUARD_RC) — cannot prove this cell is finished OR incomplete."
  echo "[$CELL] Stores left untouched. Fix the ledger, then re-invoke." | tee -a "$HOME/sand42-alerts.log" >&2
  exit 9
fi
echo "[$CELL] duplicate guard: coverage-ledger found gaps (re-run proceeds):"
echo "$GUARD_OUT" | grep -E "^  - |GAPS" | head -18 | sed 's/^/  [guard] /'

# Archive the mid-run-less runs: the re-run must be genuine (the runner resumes by
# completed index and would otherwise no-op), and the old runs stay recoverable.
ARCH="data/runtime/superseded-$CELL-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$ARCH"
for r in correspondence-specialist insurance-claims-specialist corporate-records-specialist contracts-specialist merger-specialist; do
  d="data/runtime/runs/sand42-50-$r-awq-$CELL"
  [ -e "$d" ] && mv "$d" "$ARCH/" && echo "[$CELL] archived $(basename "$d")"
done
mv reports/SAND42/$FOLDER/fleet_window.json "$ARCH/$FOLDER.fleet_window.json" 2>/dev/null || true

CFGS=(
  config/runs/sand42-50-correspondence-specialist-awq-$CELL.yaml
  config/runs/sand42-50-insurance-claims-specialist-awq-$CELL.yaml
  config/runs/sand42-50-corporate-records-specialist-awq-$CELL.yaml
  config/runs/sand42-50-contracts-specialist-awq-$CELL.yaml
  config/runs/sand42-50-merger-specialist-awq-$CELL.yaml
)

set -a; eval "$(sandbox run deploy-env --config "${CFGS[0]}")"; set +a
[ "${MODAL_VLLM_MAX_CONTAINERS:-1}" = 2 ] || { echo "[$CELL] expected 2 containers, got ${MODAL_VLLM_MAX_CONTAINERS:-1}"; exit 3; }
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"
export VLLM_API_KEY="$MODAL_VLLM_API_TOKEN"
sandbox run benchmark-check --config "${CFGS[0]}" --modal-profile "$PROFILE"

DEPLOY_TS=$(date +%s)
echo "[$CELL] $(date '+%F %H:%M:%S') deploy (2×L4)"
modal deploy deploy/modal_vllm.py --strategy recreate
export VLLM_BASE_URL="https://${PROFILE}--sandbox-vllm-serve.modal.run/v1"
sandbox cutover --profile modal-vllm
trap './deploy/teardown_vllm.sh </dev/null || true' EXIT
for i in $(seq 1 80); do
  sandbox health --profile modal-vllm >/dev/null 2>&1 && break
  [ "$i" = 80 ] && { echo "[$CELL] endpoint never came up"; sandbox health --profile modal-vllm; exit 4; }
  echo "[$CELL] booting ($((i*15))s)…"; sleep 15
done
sandbox health --profile modal-vllm
READY_TS=$(date +%s)

# SAND-047: the MID-RUN sample. Through the CLI's own scrape path on purpose: that also
# preserves the verbatim exporter text (~120 families) at the mid point and appends every
# sample to vllm_metrics_mid.series.jsonl, so the card reports the run's MAXIMUM rather
# than whichever probe ran last. The config pointer follows the ACTIVE run, because a
# scrape files its output under the run dir of the config it is given.
MIDRUN_INTERVAL="${MIDRUN_INTERVAL:-10}"
MIDRUN_CFG_FILE="$HOME/.sand42-$CELL-active-cfg"
echo "${CFGS[0]}" > "$MIDRUN_CFG_FILE"
while :; do
  cfg="$(cat "$MIDRUN_CFG_FILE" 2>/dev/null || true)"
  [ -n "$cfg" ] && sandbox run scrape-metrics --config "$cfg" --label mid || true
  sleep "$MIDRUN_INTERVAL"
done >> "$HOME/sand42-$CELL-midrun.log" 2>&1 &
MIDRUN_PID=$!
# One trap, both duties: a bare `trap … EXIT` here would REPLACE the teardown trap set
# above and leave a failed run's two GPUs warm and billing.
trap 'kill "$MIDRUN_PID" 2>/dev/null || true; ./deploy/teardown_vllm.sh </dev/null || true' EXIT

for cfg in "${CFGS[@]}"; do
  echo "[$CELL] $(date '+%H:%M:%S') ===== start $(basename "$cfg")"
  sandbox run preflight --config "$cfg" --live --force
  sandbox run scrape-metrics --config "$cfg" --label before
  echo "$cfg" > "$MIDRUN_CFG_FILE"
  sandbox run start --config "$cfg" --job-mode endpoint
  sandbox run scrape-metrics --config "$cfg" --label after
  .venv/bin/python scripts/sand42/midrun_kv.py fold --cell $CELL >/dev/null 2>&1 || true
  sandbox run card --config "$cfg"
  echo "[$CELL] $(date '+%H:%M:%S') ===== done $(basename "$cfg")"
done
kill "$MIDRUN_PID" 2>/dev/null || true

./deploy/teardown_vllm.sh </dev/null
trap - EXIT
TEARDOWN_TS=$(date +%s)
.venv/bin/python - "$DEPLOY_TS" "$READY_TS" "$TEARDOWN_TS" "$CELL" "$FOLDER" <<'PY'
import json, sys
CELL, FOLDER = sys.argv[4], sys.argv[5]
d, r, t = map(float, sys.argv[1:4])
p = f"reports/SAND42/{FOLDER}/fleet_window.json"
json.dump({"cell": CELL, "deploy_ts": d, "ready_ts": r, "gpu": "L4", "replicas": 2,
           "source": "wall clock (deploy → ready → teardown)", "teardown_ts": t},
          open(p, "w"), indent=2)
print("[$CELL] wrote", p, "cold_boot", round(r - d, 1), "s")
PY
sandbox run card --runbook sand42-$CELL

# ── SAND-050: coverage gate, THEN the master report ───────────────────────────
# The master report is the campaign's deliverable, so a leg has to earn its way in: verify
# every designed capture is on disk and no document errored, and only then let these numbers
# into the master. A non-compliant leg leaves the master as it stood, says so in the alerts
# log, and exits non-zero. Repair path: scripts/sand42/topup-one-class.sh <class> <cell>.
echo "[$CELL] coverage gate $(date '+%F %H:%M:%S')"
if .venv/bin/python scripts/sand42/coverage-ledger.py "$CELL" 2>&1 | tee -a "$HOME/sand42-alerts.log"; then
  echo "[$CELL] coverage gate PASSED — populating the master report with this leg's numbers"
  sandbox run card --runbook sand42
  echo "[$CELL] RE-RUN COMPLETE $(date '+%F %H:%M:%S') (compliant, master repopulated)"
else
  echo "[$CELL] coverage gate FAILED — master report NOT repopulated (this leg stays out of it);" \
       "repair with scripts/sand42/topup-one-class.sh" | tee -a "$HOME/sand42-alerts.log" >&2
  echo "[$CELL] RE-RUN COMPLETE $(date '+%F %H:%M:%S') (NON-COMPLIANT, master untouched)"
  exit 9
fi
