#!/usr/bin/env bash
# SAND-042 1l4-c16 RE-RUN.
#
# Why: the completion-watch's own gap list reports 10 runs with NO verbatim vLLM
# /metrics text — five 1l4-c8 AND five 1l4-c16 — because those runs were scraped
# before the exporter-preservation commit, so their ~112 dropped families are gone
# and only a re-run recovers them. 1l4-c16 keeps its GPU memory-bandwidth family (its
# sampler already read utilization.memory); the verbatim exporter output is what this
# leg exists for.
#
# The draw and posture are unchanged, so the cell stays paired. Also records a proper
# fleet window (deploy -> ready -> teardown) so the cold-boot row is measured.
# The NOISE FLOOR does NOT ride this boot: it mirrors the 1l4-c8 correspondence/C8
# condition specifically and rides that leg instead.
#
#   ~/sand42-1l4-c16-rerun.sh 2>&1 | tee ~/sand42-1l4-c16.log
#
# Run ONLY after the 1l4-c8 leg has torn its fleet down (one Modal app name).
set -euo pipefail
cd /Users/luciusjmorningstar/Downloads/local-mailroom-sandbox
# shellcheck disable=SC1091
source .venv/bin/activate
.venv/bin/python -c "import modal" || { echo "[1l4-c16] modal missing from .venv — uv sync --extra deploy"; exit 3; }

PROFILE=exios66
export SANDBOX_MODAL_PROFILE_TRACK_A="$PROFILE"
modal profile activate "$PROFILE"
[ "$(modal profile current)" = "$PROFILE" ] || { echo "[1l4-c16] activate $PROFILE first"; exit 3; }
export SANDBOX_PROFILE=modal-vllm PHOENIX_TRACING=disabled OPENROUTER_API_KEY=""

# Archive the metrics-less runs so the re-run is genuine (the runner resumes by
# completed index and would otherwise no-op).
ARCH="data/runtime/superseded-1l4-c16-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$ARCH"
for r in correspondence-specialist insurance-claims-specialist corporate-records-specialist contracts-specialist merger-specialist; do
  d="data/runtime/runs/sand42-50-$r-awq-1l4-c16"
  [ -e "$d" ] && mv "$d" "$ARCH/" && echo "[1l4-c16] archived $(basename "$d")"
done
mv reports/SAND42/1L4-c16/fleet_window.json "$ARCH/1L4-C16.fleet_window.json" 2>/dev/null || true

CFGS=(
  config/runs/sand42-50-correspondence-specialist-awq-1l4-c16.yaml
  config/runs/sand42-50-insurance-claims-specialist-awq-1l4-c16.yaml
  config/runs/sand42-50-corporate-records-specialist-awq-1l4-c16.yaml
  config/runs/sand42-50-contracts-specialist-awq-1l4-c16.yaml
  config/runs/sand42-50-merger-specialist-awq-1l4-c16.yaml
)

set -a; eval "$(sandbox run deploy-env --config "${CFGS[0]}")"; set +a
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"
export VLLM_API_KEY="$MODAL_VLLM_API_TOKEN"
sandbox run benchmark-check --config "${CFGS[0]}" --modal-profile "$PROFILE"

DEPLOY_TS=$(date +%s)
echo "[1l4-c16] $(date '+%F %H:%M:%S') deploy"
modal deploy deploy/modal_vllm.py --strategy recreate
export VLLM_BASE_URL="https://${PROFILE}--sandbox-vllm-serve.modal.run/v1"
sandbox cutover --profile modal-vllm
trap './deploy/teardown_vllm.sh </dev/null || true' EXIT
for i in $(seq 1 80); do
  sandbox health --profile modal-vllm >/dev/null 2>&1 && break
  [ "$i" = 80 ] && { echo "[1l4-c16] endpoint never came up"; sandbox health --profile modal-vllm; exit 4; }
  echo "[1l4-c16] booting ($((i*15))s)…"; sleep 15
done
sandbox health --profile modal-vllm
READY_TS=$(date +%s)

# SAND-047: MID-RUN /metrics sample, every $MIDRUN_INTERVAL seconds, via the CLI's own
# scrape path — the before/after pair brackets each run at its drained edges, where
# kv_cache_usage_perc reads 0 by construction. Going through `scrape-metrics` also
# preserves the VERBATIM exporter text (~120 families) at the mid point and appends every
# sample to vllm_metrics_mid.series.jsonl, so the card reports the run's maximum rather
# than whichever probe ran last. The config pointer follows the ACTIVE run, because a
# scrape files its output under the run dir of the config it is given.
MIDRUN_INTERVAL="${MIDRUN_INTERVAL:-10}"
MIDRUN_CFG_FILE="$HOME/.sand42-1l4-c16-active-cfg"
echo "${CFGS[0]}" > "$MIDRUN_CFG_FILE"
while :; do
  cfg="$(cat "$MIDRUN_CFG_FILE" 2>/dev/null || true)"
  [ -n "$cfg" ] && sandbox run scrape-metrics --config "$cfg" --label mid || true
  sleep "$MIDRUN_INTERVAL"
done >> "$HOME/sand42-1l4-c16-midrun.log" 2>&1 &
MIDRUN_PID=$!
# One trap, both duties: a bare `trap … EXIT` here would REPLACE the teardown trap set
# above and leave a failed run's fleet warm and billing.
trap 'kill "$MIDRUN_PID" 2>/dev/null || true; ./deploy/teardown_vllm.sh </dev/null || true' EXIT

for cfg in "${CFGS[@]}"; do
  echo "[1l4-c16] $(date '+%H:%M:%S') ===== start $(basename "$cfg")"
  sandbox run preflight --config "$cfg" --live --force
  sandbox run scrape-metrics --config "$cfg" --label before
  echo "$cfg" > "$HOME/.sand42-1l4-c16-active-cfg"   # point the mid loop at THIS run
  sandbox run start --config "$cfg" --job-mode endpoint
  sandbox run scrape-metrics --config "$cfg" --label after
  .venv/bin/python scripts/sand42/midrun_kv.py fold --cell 1l4-c16 >/dev/null 2>&1 || true
  sandbox run card --config "$cfg"
  echo "[1l4-c16] $(date '+%H:%M:%S') ===== done $(basename "$cfg")"
done
kill "$MIDRUN_PID" 2>/dev/null || true
.venv/bin/python scripts/sand42/midrun_kv.py fold --cell 1l4-c16 || true

./deploy/teardown_vllm.sh </dev/null
trap - EXIT
TEARDOWN_TS=$(date +%s)
.venv/bin/python - "$DEPLOY_TS" "$READY_TS" "$TEARDOWN_TS" <<'PY'
import json, sys
d, r, t = map(float, sys.argv[1:4])
p = "reports/SAND42/1L4-c16/fleet_window.json"
json.dump({"cell": "1l4-c16", "deploy_ts": d, "ready_ts": r, "gpu": "L4", "replicas": 1,
           "source": "wall clock (deploy → ready → teardown)", "teardown_ts": t},
          open(p, "w"), indent=2)
print("[1l4-c16] wrote", p, "cold_boot", round(r - d, 1), "s")
PY
sandbox run card --runbook sand42-1l4-c16

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
