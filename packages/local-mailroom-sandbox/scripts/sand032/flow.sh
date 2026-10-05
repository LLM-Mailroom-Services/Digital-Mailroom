#!/usr/bin/env bash
# SAND-032 warm flow: ONE cold boot of the frozen production config, then every
# run back-to-back on the warm fleet; scale 1→2 replicas IN PLACE; stop once.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
PY="${SANDBOX_PY:-$ROOT/../local-mailroom-sandbox/.venv/bin/python}"
RT="$ROOT/data/runtime/sand032"; LOG="$RT/logs"
spent() { python3 -c 'import json;print(json.load(open("data/runtime/sand032/spend.json"))["spent_usd"])'; }
step() { echo "=== $1 (spent \$$(python3 scripts/sand032/spend.py write >/dev/null; spent)) ==="; }
run() { scripts/sand032/run_one.sh "config/runs/$1.yaml" "$2" ${3:-} 2>&1 | tail -2; }
gate() {  # projected total must stay <= $4.50 (spec §Stage 3)
  local proj; proj=$(python3 -c "print(round($(spent) + $1, 4))")
  if python3 -c "import sys; sys.exit(0 if $proj > 4.50 else 1)"; then
    echo "BUDGET GATE: projected \$$proj > \$4.50 — skipping $2"; return 1; fi
  echo "budget gate ok: projected \$$proj ≤ \$4.50 for $2"; return 0
}

step "sand032-l5-graphs — FIRST COLD BOOT (frozen config: marlin + thinking-off + fp8 KV + seqs16 + CUDA graphs)"
run sand032-l5-graphs deploy || exit 1
sleep 10
step "sand032-s2a-corr100-1rep — warm, same container"
run sand032-s2a-corr100-1rep warm || exit 1
sleep 10

step "scale 1→2 replicas in place"
date +%s > "$LOG/scale_start"
scripts/sand032/scale.py 2 fleet-2xL4 || { modal app stop sandbox-vllm-sand032 -y; exit 1; }
export VLLM_API_KEY="$(cat "$RT/api_token")" VLLM_BASE_URL="$(cat "$RT/base_url")"
for i in $(seq 1 60); do
  cov=$(PYTHONPATH=src "$PY" -c "from mailroom_sandbox.job.vllm_metrics import scrape; import os; print(scrape(os.environ['VLLM_BASE_URL'], os.environ['VLLM_API_KEY'], attempts=8, expected=2)['coverage'])" 2>/dev/null)
  echo "  second replica: $cov"
  [ "$cov" = "replicas observed: 2 of 2" ] && break
  sleep 15
done
date +%s > "$LOG/scale_ready"
[ "$cov" = "replicas observed: 2 of 2" ] || echo "WARNING: second replica not observed — continuing (coverage reported honestly)"

step "sand032-s2b-corr100-2rep — warm 2×L4"
run sand032-s2b-corr100-2rep warm || exit 1
sleep 10
for spec in "sand032-s3-corr50 0.10" "sand032-s3-insurance50 0.35" "sand032-s3-corporate50 0.55" \
            "sand032-s3-merger50 0.60" "sand032-s3-contracts50 1.00" "sand032-s3-corr50-repeat 0.10"; do
  set -- $spec
  gate "$2" "$1" || continue
  step "$1 — warm 2×L4"
  run "$1" warm || exit 1
  sleep 10
done
step "teardown 2×L4 fleet"
modal app stop sandbox-vllm-sand032 -y 2>&1 | tail -1
python3 scripts/sand032/spend.py close fleet-2xL4 >/dev/null
echo '"stopped": '"$(date +%s)"',' >> "$LOG/sand032-s3-corr50-repeat.times"
python3 scripts/sand032/spend.py write >/dev/null
echo "FLEET-STOPPED spent \$$(spent)"
sleep 10
if gate 0.12 sand032-s4-corr20-bf16; then
  step "sand032-s4-corr20-bf16 — bf16 quality arm (different model = its own boot)"
  run sand032-s4-corr20-bf16 deploy stop
fi
echo WARM-FLOW-DONE
