#!/usr/bin/env bash
# SAND-032 Stage 10: eval-environment v2 prompts, 1×L4 c8, n=75 (corr, insurance, corporate); $1 real left: B fleet (seqs32) then C fleet (seqs32 +
# max_num_batched_tokens 16384 + gpu_mem 0.93), each warm across its runs, value-ordered so
# the budget gate drops the least valuable last. Gate: ledger delta from BASE ≤ LIMIT
# (hard account limit $2.80; ledger under-counts real billing).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
LOG="$ROOT/data/runtime/sand032/logs"; BASE="${SAND032_BASE:-1.2119}"; LIMIT="${SAND032_DELTA_LIMIT:-1.50}"
spent() { python3 scripts/sand032/spend.py write >/dev/null 2>&1; python3 -c 'import json;print(json.load(open("data/runtime/sand032/spend.json"))["spent_usd"])'; }
gate() { local d; d=$(python3 -c "print(round($(spent) - $BASE + $1, 4))")
  if python3 -c "import sys; sys.exit(0 if $d > $LIMIT else 1)"; then echo "BUDGET GATE: projected delta \$$d > \$$LIMIT — skip $2"; return 1; fi
  echo "gate ok: projected delta \$$d for $2"; }
stopfleet() { modal app stop sandbox-vllm-sand032 -y 2>&1 | tail -1
  python3 scripts/sand032/spend.py close "$(python3 -c 'import json;d=json.load(open("data/runtime/sand032/fleets.json"));o=[k for k,v in d.items() if not v.get("stop_ts")];print(o[-1] if o else "")')" >/dev/null 2>&1; }
run() { echo "=== $1 ($2) ledger \$$(spent) ==="; scripts/sand032/run_one.sh "config/runs/$1.yaml" $2 2>&1 | tail -2; }
fleet() {
  local first="$1"; shift
  gate 0.12 "$first" || return 1
  run "$first" deploy || { stopfleet; return 1; }
  for spec in "$@"; do set -- $spec; gate "$2" "$1" || break; sleep 5; run "$1" warm || break; done
  stopfleet
}
fleet sand032-s10-corr75-v2 "sand032-s10-insurance75-v2 0.08" "sand032-s10-corporate75-v2 0.08"
echo "FLOW5-DONE ledger \$$(spent) (delta from \$$BASE)"
