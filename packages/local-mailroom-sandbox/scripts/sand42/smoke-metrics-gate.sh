#!/usr/bin/env bash
# SAND-042 metric-capture smoke gate.
#
# Spends ~$0.05-0.15 on one 1xL4 cold boot to prove, BEFORE the live reruns, that every
# capture actually lands and is reported — the lesson of the KV column: the family was
# "captured" all along and still reported 0, because nothing sampled it mid-run.
#
# It is a VALIDATION, not a cell: the run is the catalog's `sand42-smoke` check leg, which
# is excluded from the condition cards and the comparison. The gate hashes the master
# report/card and the cell cards before and after and FAILS if any of them changed, so a
# smoke can never quietly append itself to the study.
#
#   bash scripts/sand42/smoke-metrics-gate.sh
#
# Checks, per the artifact contract the reruns must satisfy:
#   vLLM /metrics      before + after + MID, verbatim .txt per replica (~120 families)
#   mid series         vllm_metrics_mid.series.jsonl (what the card's max is computed from)
#   container GPU      nvidia-smi series (util/mem/temp/power/BANDWIDTH/clocks) + window
#   run store          items.jsonl rows, spec+prompt locks, cold_boot
#   card               the mid-run rows carry a VALUE, not "—"
#   isolation          master report/card + cell cards byte-identical
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
REPO="$PWD"
# shellcheck disable=SC1091
source .venv/bin/activate
.venv/bin/python -c "import modal" || { echo "FAIL: modal missing from .venv — uv sync --extra deploy" >&2; exit 3; }
RUN_ID="sand42-check-5-corporate-records-awq-1l4-c8"
CFG="config/runs/$RUN_ID.yaml"
DEST="data/runtime/runs/$RUN_ID"
PROFILE="${SANDBOX_MODAL_PROFILE_TRACK_A:-exios66}"
MASTER="reports/SAND42/SAND42-MASTER-REPORT.md"
MASTER_CARD="reports/SAND42/SAND42-MASTER-SCORE-COST-CARD.md"

sha() { [ -f "$1" ] && shasum -a 256 "$1" | awk '{print $1}' || echo "absent"; }
# CELL-level cards only: the smoke legitimately writes its OWN per-run card, so folding
# every *.card.json into this hash made the isolation check fail for doing its job.
cell_cards_hash() {
  find reports/SAND42 -name 'SAND42-*-SCORE-COST-CARD.*' -exec shasum -a 256 {} \; 2>/dev/null \
    | sort | shasum -a 256
}
BEFORE_HASHES="$(sha "$MASTER") $(sha "$MASTER_CARD") $(sha reports/SAND42/SAND42-CELL-COMPARISON.md)"
BEFORE_CARDS="$(cell_cards_hash)"

echo "== SAND-042 metric-capture smoke gate =="
echo "   run $RUN_ID  (excluded from the cell cards by design)"
[ -f "$CFG" ] || { echo "FAIL: missing $CFG" >&2; exit 2; }

# one Modal app name at a time
if pgrep -f "scripts/sand42/parallel-fleets.sh|sand42-1l4-c8-rerun.sh|sand42-1l4-c16-rerun.sh" >/dev/null; then
  echo "FAIL: a SAND-042 fleet is running — stop it before the smoke" >&2; exit 3
fi

modal profile activate "$PROFILE" >/dev/null 2>&1
export SANDBOX_PROFILE=modal-vllm PHOENIX_TRACING=disabled OPENROUTER_API_KEY=""

# The runner RESUMES by completed index, so a check run left over from the last pre-spend
# smoke would no-op — and the mid checks would then fail on stale artifacts, blaming the
# capture for what is really a stale store.
if [ -s "$DEST/items.jsonl" ]; then
  ARCH="data/runtime/superseded-$RUN_ID-$(date +%Y%m%d-%H%M%S)"
  mv "$DEST" "$ARCH" && echo "   archived the previous check run → $ARCH"
fi

set -a; eval "$(sandbox run deploy-env --config "$CFG")"; set +a
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"
export VLLM_API_KEY="$MODAL_VLLM_API_TOKEN"

DEPLOY_TS=$(date +%s)
modal deploy deploy/modal_vllm.py --strategy recreate >/dev/null
export VLLM_BASE_URL="https://${PROFILE}--sandbox-vllm-serve.modal.run/v1"
sandbox cutover --profile modal-vllm >/dev/null
trap './deploy/teardown_vllm.sh </dev/null || true' EXIT
for i in $(seq 1 80); do
  sandbox health --profile modal-vllm >/dev/null 2>&1 && break
  [ "$i" = 80 ] && { echo "FAIL: endpoint never came up" >&2; exit 4; }
  sleep 15
done
READY_TS=$(date +%s)
echo "   cold boot $((READY_TS - DEPLOY_TS))s"

# The mid loop the runbook emits — 5 s here because the smoke is only 5 documents.
export MIDRUN_INTERVAL=5
while :; do
  [ -n "$(cat "$HOME/.sand42-smoke-active-cfg" 2>/dev/null || true)" ] && \
    sandbox run scrape-metrics --config "$(cat "$HOME/.sand42-smoke-active-cfg")" --label mid \
      >> "$HOME/sand42-smoke-midrun.log" 2>&1 || true
  sleep "$MIDRUN_INTERVAL"
done &
MID_PID=$!
trap 'kill "$MID_PID" 2>/dev/null || true; ./deploy/teardown_vllm.sh </dev/null || true' EXIT

sandbox run preflight --config "$CFG" --live --force >/dev/null
sandbox run scrape-metrics --config "$CFG" --label before >/dev/null
echo "$CFG" > "$HOME/.sand42-smoke-active-cfg"
sandbox run start --config "$CFG" --job-mode endpoint
sandbox run scrape-metrics --config "$CFG" --label after >/dev/null
kill "$MID_PID" 2>/dev/null || true
sandbox run card --config "$CFG"

./deploy/teardown_vllm.sh </dev/null
trap - EXIT
AFTER_HASHES="$(sha "$MASTER") $(sha "$MASTER_CARD") $(sha reports/SAND42/SAND42-CELL-COMPARISON.md)"
AFTER_CARDS="$(cell_cards_hash)"

echo
echo "== validation =="
FAIL=0
chk() {  # $1=label  $2=0/1 pass
  if [ "$2" = 1 ]; then printf '   PASS  %s\n' "$1"; else printf '   FAIL  %s\n' "$1"; FAIL=1; fi
}
has() { [ -s "$DEST/$1" ] && echo 1 || echo 0; }

chk "$RUN_ID items.jsonl has rows"           "$([ "$(wc -l < "$DEST/items.jsonl" 2>/dev/null || echo 0)" -gt 0 ] && echo 1 || echo 0)"
chk "vLLM /metrics before .json + .txt"      "$([ "$(has vllm_metrics_before.json)" = 1 ] && [ "$(has vllm_metrics_before.txt)" = 1 ] && echo 1 || echo 0)"
chk "vLLM /metrics after .json + .txt"       "$([ "$(has vllm_metrics_after.json)" = 1 ] && [ "$(has vllm_metrics_after.txt)" = 1 ] && echo 1 || echo 0)"
chk "vLLM /metrics MID .json + .txt (new)"   "$([ "$(has vllm_metrics_mid.json)" = 1 ] && [ "$(has vllm_metrics_mid.txt)" = 1 ] && echo 1 || echo 0)"
chk "mid SERIES jsonl (the card's max)"      "$(has vllm_metrics_mid.series.jsonl)"
chk "container telemetry window"             "$(has container_telemetry_window.json)"
chk "container telemetry (incl. mid)"        "$([ "$(has container_telemetry_after.json)" = 1 ] && [ "$(has container_telemetry_mid.json)" = 1 ] && echo 1 || echo 0)"
chk "spec + prompt locks, cold_boot"         "$([ "$(has spec.lock.json)" = 1 ] && [ "$(has prompt.lock.json)" = 1 ] && echo 1 || echo 0)"
chk "verbatim mid text carries vllm families" "$(grep -c '^vllm:' "$DEST/vllm_metrics_mid.txt" 2>/dev/null | awk '{print ($1>50)?1:0}')"
chk "BANDWIDTH family present (utilization.memory)" "$(grep -q 'memory_bandwidth\|utilization_memory' "$DEST/container_telemetry_after.json" && echo 1 || echo 0)"

# The mid-run rows render on the CELL card, and the smoke must not touch a cell card — so
# validate the DATA PATH (the per-run card's engine_telemetry, which the cell card reads)
# and the RENDERER (pure functions, no file writes) rather than grepping a report.
CARD_JSON="reports/SAND42/1L4-c8/corporate_records/${RUN_ID}.card.json"
chk "per-run card written" "$([ -s "$CARD_JSON" ] && echo 1 || echo 0)"
chk "engine_telemetry.midrun present" "$(.venv/bin/python -c "
import json,sys
d=json.load(open('$CARD_JSON'))
print(1 if (d.get('engine_telemetry') or {}).get('midrun') else 0)" 2>/dev/null || echo 0)"
RENDER=$(.venv/bin/python - "$CARD_JSON" <<'PY' 2>/dev/null || echo "—|—"
import json, pathlib, sys
sys.path.insert(0, "src")
from mailroom_sandbox.job import sand42_cards as c
data = json.loads(pathlib.Path(sys.argv[1]).read_text())
r = {"engine_telemetry": data.get("engine_telemetry") or {}}
print(f"{c._midrun_kv_text(r)}|{c._midrun_queue_text(r)}")
PY
)
KV="${RENDER%%|*}"; QD="${RENDER##*|}"
chk "renderer: mid-run KV has a value (${KV})" "$([ "${KV}" != "—" ] && echo 1 || echo 0)"
chk "renderer: mid-run queue has a value (${QD})" "$([ "${QD}" != "—" ] && echo 1 || echo 0)"

chk "master report UNCHANGED (smoke not appended)" "$([ "$BEFORE_HASHES" = "$AFTER_HASHES" ] && echo 1 || echo 0)"
chk "cell cards UNCHANGED"                         "$([ "$BEFORE_CARDS" = "$AFTER_CARDS" ] && echo 1 || echo 0)"

echo
if [ "$FAIL" = 0 ]; then
  echo "SMOKE GATE: PASS — the corrected captures land and report. Safe to launch the live reruns."
else
  echo "SMOKE GATE: FAIL — fix before spending on the reruns." >&2
fi
exit "$FAIL"
