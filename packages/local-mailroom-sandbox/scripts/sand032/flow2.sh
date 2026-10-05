#!/usr/bin/env bash
# SAND-032 Stage 6+7: A fleet (frozen seqs16) sorter1000 → stop; B fleet (seqs32, c64)
# corr100 / insurance50 / corporate50 / sorter1000 → stop. Hard account limit $2.80:
# every step is gated on ledger delta since start ≤ $LIMIT (ledger under-counts billing).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
LOG="$ROOT/data/runtime/sand032/logs"; LIMIT="${SAND032_DELTA_LIMIT:-1.20}"
spent() { python3 scripts/sand032/spend.py write >/dev/null 2>&1; python3 -c 'import json;print(json.load(open("data/runtime/sand032/spend.json"))["spent_usd"])'; }
BASE=$(spent); echo "baseline ledger \$$BASE; delta limit \$$LIMIT"
gate() {  # $1 = projected cost of next step
  local d; d=$(python3 -c "print(round($(spent) - $BASE + $1, 4))")
  if python3 -c "import sys; sys.exit(0 if $d > $LIMIT else 1)"; then echo "BUDGET GATE: projected delta \$$d > \$$LIMIT — skip $2"; return 1; fi
  echo "gate ok: projected delta \$$d for $2"; }
watchdog() {  # stop the app if the first ≥8 finished items are all errors
  python3 - "$1" <<'PY' &
import json, os, subprocess, sys, time
p = f"data/runtime/runs/{sys.argv[1]}/items.jsonl"
while True:
    time.sleep(10)
    if not os.path.exists(p): continue
    rows = [json.loads(l) for l in open(p) if l.strip()]
    if len(rows) >= 8 and not any(r.get("ok") for r in rows):
        print(f"WATCHDOG: {sys.argv[1]} first {len(rows)} items all errors — stopping app", flush=True)
        subprocess.run(["modal", "app", "stop", "sandbox-vllm-sand032", "-y"]); sys.exit(0)
    if len(rows) >= 8: sys.exit(0)
PY
}
run() { echo "=== $1 ($2) ledger \$$(spent) ==="; watchdog "$1"; scripts/sand032/run_one.sh "config/runs/$1.yaml" $2 2>&1 | tail -2; }
# A fleet — frozen seqs16, c32
gate 0.40 sand032-s6-sorter1000 && run sand032-s6-sorter1000 "deploy stop"
sleep 15
# B fleet — seqs32, c64
if gate 0.20 sand032-s7-corr100-seqs32; then
  run sand032-s7-corr100-seqs32 deploy || { modal app stop sandbox-vllm-sand032 -y; exit 1; }
  for spec in "sand032-s7-insurance50-seqs32 0.10" "sand032-s7-corporate50-seqs32 0.10" "sand032-s7-sorter1000-seqs32 0.25"; do
    set -- $spec; gate "$2" "$1" || break; sleep 5; run "$1" warm || break
  done
  modal app stop sandbox-vllm-sand032 -y 2>&1 | tail -1
  python3 scripts/sand032/spend.py close "$(python3 -c 'import json;d=json.load(open("data/runtime/sand032/fleets.json"));o=[k for k,v in d.items() if not v.get("stop_ts")];print(o[-1] if o else "")')" >/dev/null 2>&1
fi
echo "FLOW2-DONE ledger \$$(spent) (delta from \$$BASE)"
