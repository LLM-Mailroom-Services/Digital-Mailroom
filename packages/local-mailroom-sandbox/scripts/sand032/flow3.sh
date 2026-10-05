#!/usr/bin/env bash
# SAND-032 Stages 7–8 after the A-fleet sorter: B fleet (seqs32) then C fleet (seqs32 +
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
until grep -q '"stopped"' "$LOG/sand032-s6-sorter1000.times" 2>/dev/null; do sleep 10; done
echo "A fleet down after sorter; ledger \$$(spent)"; sleep 10
fleet() {  # $1 = first run (deploy); rest = "run cost" warm steps
  local first="$1"; shift
  gate 0.30 "$first" || return 1
  run "$first" deploy || { stopfleet; return 1; }
  for spec in "$@"; do set -- $spec; gate "$2" "$1" || break; sleep 5; run "$1" warm || break; done
  stopfleet
}
# Sorter reruns dropped: the vendored sorter reads whole docs (5.4k-token prompt + chunked long
# docs, p50 14k prompt tok) — ~$0.7/1000 docs; budget goes to the specialist hypotheses.
fleet sand032-s7-corr100-seqs32 "sand032-s7-insurance50-seqs32 0.12" "sand032-s7-corporate50-seqs32 0.12" \
      "sand032-s7-contracts50-seqs32 0.30" "sand032-s7-corr100-seqs32-c48 0.06" "sand032-s7-corr100-seqs32-c32 0.06"
sleep 10
fleet sand032-s8-corr100-bt16k "sand032-s8-contracts50-bt16k 0.30"
echo "FLOW3-DONE ledger \$$(spent) (delta from \$$BASE)"
