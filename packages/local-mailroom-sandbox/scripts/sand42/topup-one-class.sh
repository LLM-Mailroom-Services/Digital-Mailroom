#!/usr/bin/env bash
# SAND-042 TARGETED TOP-UP — re-run ONE class in ONE cell.
#
# The repair path after a leg lands short: a capped merger, a run that errored out, or a
# class whose metrics were incomplete. It deliberately does NOT re-run the whole cell —
# `check_leg` in the campaign chain reports the failure, and this fixes exactly the run
# named, so a partial cell costs one class instead of a fleet.
#
#   ~/sand42-topup.sh merger 2l4-c8
#   ~/sand42-topup.sh contracts 1l4-c16
#
# Notes
#   * It archives the existing run dir first (the runner RESUMES by completed index and
#     would otherwise no-op), and the archive is left in place for recovery.
#   * It does NOT write the cell's fleet_window: a single-class boot is not the cell's
#     cold boot, and stamping one would misattribute ready_ts.
#   * It takes the fleet size from the config (deploy-env), so 1xL4 and 2xL4 cells both work.
set -euo pipefail
CLASS="${1:?usage: sand42-topup.sh <correspondence|insurance-claims|corporate-records|contracts|merger> <cell>}"
CELL="${2:?usage: sand42-topup.sh <class> <cell>  e.g. merger 2l4-c8}"
case "$CLASS" in
  correspondence|insurance-claims|corporate-records|contracts|merger) ;;
  *) echo "unknown class '$CLASS' (correspondence|insurance-claims|corporate-records|contracts|merger)" >&2; exit 2 ;;
esac
cd /Users/luciusjmorningstar/Downloads/local-mailroom-sandbox
# shellcheck disable=SC1091
source .venv/bin/activate
.venv/bin/python -c "import modal" || { echo "[topup] modal missing from .venv"; exit 3; }

PROFILE=exios66
export SANDBOX_MODAL_PROFILE_TRACK_A="$PROFILE"
modal profile activate "$PROFILE" >/dev/null
[ "$(modal profile current)" = "$PROFILE" ] || { echo "[topup] activate $PROFILE first"; exit 3; }
export SANDBOX_PROFILE=modal-vllm PHOENIX_TRACING=disabled OPENROUTER_API_KEY=""

RID="sand42-50-$CLASS-specialist-awq-$CELL"
CFG="config/runs/$RID.yaml"
[ -f "$CFG" ] || { echo "[topup] missing $CFG"; exit 2; }

if pgrep -f "sand42-1l4-c8-rerun.sh|sand42-1l4-c16-rerun.sh|sand42-2l4-rerun.sh|sand42-rerun-chain.sh|parallel-fleets.sh" >/dev/null; then
  echo "[topup] REFUSING: a SAND-042 campaign/fleet is running — one app name at a time" >&2
  exit 3
fi

ARCH="data/runtime/superseded-topup-$CLASS-$CELL-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$ARCH"
if [ -e "data/runtime/runs/$RID" ]; then
  n=$(wc -l < "data/runtime/runs/$RID/items.jsonl" 2>/dev/null | tr -d ' ' || echo 0)
  mv "data/runtime/runs/$RID" "$ARCH/" && echo "[topup] archived $RID (it held ${n:-0} items)"
fi

set -a; eval "$(sandbox run deploy-env --config "$CFG")"; set +a
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"
export VLLM_API_KEY="$MODAL_VLLM_API_TOKEN"
sandbox run benchmark-check --config "$CFG" --modal-profile "$PROFILE"

echo "[topup] $(date '+%F %H:%M:%S') deploy ($RID)"
modal deploy deploy/modal_vllm.py --strategy recreate
export VLLM_BASE_URL="https://${PROFILE}--sandbox-vllm-serve.modal.run/v1"
sandbox cutover --profile modal-vllm
trap './deploy/teardown_vllm.sh </dev/null || true' EXIT
for i in $(seq 1 80); do
  sandbox health --profile modal-vllm >/dev/null 2>&1 && break
  [ "$i" = 80 ] && { echo "[topup] endpoint never came up"; exit 4; }
  echo "[topup] booting ($((i*15))s)…"; sleep 15
done
sandbox health --profile modal-vllm

# Mid-run sampling, same mechanism the chain/runbook uses, pointed at this one config.
PTR="$HOME/.sand42-$CELL-active-cfg"
echo "$CFG" > "$PTR"
while :; do
  c="$(cat "$PTR" 2>/dev/null || true)"
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
sandbox run card --runbook "sand42-$CELL" || true
sandbox run card --runbook sand42
n=$(wc -l < "data/runtime/runs/$RID/items.jsonl" 2>/dev/null | tr -d ' ' || echo 0)
echo "[topup] DONE $RID — ${n:-0}/50 items $(date '+%F %H:%M:%S')"
[ "${n:-0}" -ge 50 ] || { echo "[topup] WARN $RID still short (${n:-0}/50)" >&2; exit 5; }
