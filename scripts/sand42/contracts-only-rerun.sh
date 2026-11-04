#!/usr/bin/env bash
# SAND-042 contracts-only re-run for ONE cell, on the corrected ground-truth draw.
#
# Why: the first grid drew 5 contracts of 50 whose `cuad_clause_labels` is an empty object
# — no CUAD annotations — so the contracts clause column could only ever be computed on 45
# documents (44 where an arm also hit a LengthFinishReasonError). The strata request 26
# subclasses with 1-3 each, and the under-annotated ones (Supply 18/47, Consulting 11/38,
# IP 17/35) supplied the unscoreable five. The five cell configs now set
# `dataset.require_task_gt: true`, which drops those documents BEFORE the draw; every
# subclass's annotated supply still covers its requested count, so the strata block is
# unchanged and the new draw is 50/50 annotated with all 26 subclasses intact.
#
# Because the draw changed on 11 of 50 documents, EVERY cell's contracts run must be redone
# or the pairing mixes two draws. Three cells are re-run in full by the other legs; this
# script tops up the remaining cell's contracts alone.
#
# It does NOT write the cell's fleet_window: a contracts-only boot is not the cell's cold
# boot, and stamping one would misattribute ready_ts.
#
#   ~/sand42-contracts-rerun.sh 2l4-c8
set -euo pipefail
CELL="${1:?usage: sand42-contracts-rerun.sh <cell>  e.g. 2l4-c8}"
cd /Users/luciusjmorningstar/Downloads/local-mailroom-sandbox
# shellcheck disable=SC1091
source .venv/bin/activate
.venv/bin/python -c "import modal" || { echo "[$CELL] modal missing from .venv"; exit 3; }

PROFILE=exios66
export SANDBOX_MODAL_PROFILE_TRACK_A="$PROFILE"
modal profile activate "$PROFILE" >/dev/null
[ "$(modal profile current)" = "$PROFILE" ] || { echo "[$CELL] activate $PROFILE first"; exit 3; }
export SANDBOX_PROFILE=modal-vllm PHOENIX_TRACING=disabled OPENROUTER_API_KEY=""

RID="sand42-50-contracts-specialist-awq-$CELL"
CFG="config/runs/$RID.yaml"
[ -f "$CFG" ] || { echo "[$CELL] missing $CFG"; exit 2; }

# Only this class: the other four keep their existing (still-valid) runs.
ARCH="data/runtime/superseded-contracts-$CELL-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$ARCH"
[ -e "data/runtime/runs/$RID" ] && mv "data/runtime/runs/$RID" "$ARCH/" && echo "[$CELL] archived $RID"

set -a; eval "$(sandbox run deploy-env --config "$CFG")"; set +a
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"
export VLLM_API_KEY="$MODAL_VLLM_API_TOKEN"
sandbox run benchmark-check --config "$CFG" --modal-profile "$PROFILE"

echo "[$CELL] $(date '+%F %H:%M:%S') deploy"
modal deploy deploy/modal_vllm.py --strategy recreate
export VLLM_BASE_URL="https://${PROFILE}--sandbox-vllm-serve.modal.run/v1"
sandbox cutover --profile modal-vllm
trap './deploy/teardown_vllm.sh </dev/null || true' EXIT
for i in $(seq 1 80); do
  sandbox health --profile modal-vllm >/dev/null 2>&1 && break
  [ "$i" = 80 ] && { echo "[$CELL] endpoint never came up"; exit 4; }
  echo "[$CELL] booting ($((i*15))s)…"; sleep 15
done
sandbox health --profile modal-vllm

CFG_PTR="$HOME/.sand42-$CELL-active-cfg"
echo "$CFG" > "$CFG_PTR"
while :; do
  c="$(cat "$CFG_PTR" 2>/dev/null || true)"
  [ -n "$c" ] && sandbox run scrape-metrics --config "$c" --label mid || true
  sleep "${MIDRUN_INTERVAL:-30}"
done >> "$HOME/sand42-$CELL-midrun.log" 2>&1 &
MIDRUN_PID=$!
trap 'kill "$MIDRUN_PID" 2>/dev/null || true; ./deploy/teardown_vllm.sh </dev/null || true' EXIT

sandbox run preflight --config "$CFG" --live --force
sandbox run scrape-metrics --config "$CFG" --label before
sandbox run start --config "$CFG" --job-mode endpoint
sandbox run scrape-metrics --config "$CFG" --label after
.venv/bin/python scripts/sand42/midrun_kv.py fold --cell "$CELL" >/dev/null 2>&1 || true
sandbox run card --config "$CFG"
kill "$MIDRUN_PID" 2>/dev/null || true

./deploy/teardown_vllm.sh </dev/null
trap - EXIT
sandbox run card --runbook "sand42-$CELL"
sandbox run card --runbook sand42
echo "[$CELL] CONTRACTS RE-RUN COMPLETE $(date '+%F %H:%M:%S')"
