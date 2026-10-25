#!/usr/bin/env bash
# SAND-042 — the queued rerun chain, gated on the C32 publish.
#
# Runs the two remaining reruns back to back on ONE 1xL4 app name (so two fleets can
# never bill at once), then records the one capture that is not automatic: the metered
# cost (`sandbox run card --record-metered`). Everything else is captured by the run
# itself — see the audit in the log header below.
#
# ORDER
#   gate     the C32 reports are published (sentinel: ~/.sand42-c32-published). The
#            sentinel exists because the master spans all five cells: starting a rerun
#            before the C32 publish would rebuild the same report files underneath it.
#   leg 1    1l4-c8 rerun + the NOISE FLOOR riding its boot (5+1 configs, ~101 min)
#   leg 2    1l4-c16 rerun (5 configs, ~95 min)
#   record   metered/billed from `modal billing summary`
#
# PER-RUN CAPTURE (audited against the completion-watch's gap list — this is the list
# the reruns must leave nothing missing from):
#   vLLM /metrics      before + after, verbatim per replica (~120 families)  scrape-metrics
#   vLLM mid-run       KV/queue/prefix cache, sampled every 30 s              midrun_kv sample
#   container GPU      nvidia-smi util/mem/temp/power/BANDWIDTH/clocks        deploy sampler
#   run store          items, dataset, spec+prompt locks, cold_boot, events   runner
#   fleet window       deploy -> ready -> teardown (+ ready_ts for cold boot) this script
#   cards              per-run + dated report + serving export                run card --config
#   study reports      cell cards + comparison + noise floor + master+figures run card --runbook sand42
#   cost               metered/billed (MANUAL — recorded at the end)           --record-metered
#
#   bash ~/sand42-rerun-chain.sh 2>&1 | tee ~/sand42-rerun-chain.log
set -uo pipefail
cd /Users/luciusjmorningstar/Downloads/local-mailroom-sandbox
SENT="$HOME/.sand42-c32-published"

echo "[chain] $(date '+%F %H:%M:%S') waiting for the C32 publish sentinel ($SENT)"
while [ ! -f "$SENT" ]; do sleep 30; done
echo "[chain] C32 published — starting the rerun legs"

if pgrep -f "scripts/sand42/parallel-fleets.sh|sand42-1l4-c8-rerun.sh|sand42-1l4-c16-rerun.sh" >/dev/null; then
  echo "[chain] REFUSING: another SAND-042 fleet process is running" >&2
  exit 3
fi

# Armed HERE, not before: the watcher waits for the legs, then enforces the winddown,
# refreshes all 25 per-run cards, rebuilds the master and prints the gap list.
nohup bash scripts/sand42/completion-watch.sh --timeout-min 600 > "$HOME/sand42-rerun-watch.log" 2>&1 &
echo "[chain] completion-watch armed (pid $!)"


# Loud per-leg completeness check: a run that lands short (capped merger, dead endpoint,
# missing mid-run sample) is reported the moment its leg ends, not at the end of the
# campaign — otherwise a partial cell silently burns the leg's spend.
check_leg() {
  local cell="$1" rid n short=0
  for f in config/runs/sand42-*-awq-"$cell".yaml; do
    rid="$(basename "$f" .yaml)"
    n="$(wc -l < "data/runtime/runs/$rid/items.jsonl" 2>/dev/null | tr -d ' ' || true)"
    [ -z "$n" ] && n=0
    if [ "$n" -lt 50 ] || [ ! -s "data/runtime/runs/$rid/vllm_metrics_after.txt" ]; then
      echo "[chain] WARN $rid landed SHORT: items=$n/50 after-scrape=$([ -s "data/runtime/runs/$rid/vllm_metrics_after.txt" ] && echo yes || echo NO)"
      short=$((short+1))
    fi
  done
  [ "$short" = 0 ] && echo "[chain] $cell complete: 5/5 runs at 50 items with scrape + card"
}

set -a
bash "$HOME/sand42-1l4-c8-rerun.sh" 2>&1 | tee "$HOME/sand42-1l4-c8.log"
check_leg 1l4-c8
bash "$HOME/sand42-1l4-c16-rerun.sh" 2>&1 | tee "$HOME/sand42-1l4-c16.log"
check_leg 1l4-c16
# Leg 3: 2l4-c16 — the additional re-run for the mid-run KV column. The other two 2×L4
# cells (2l4-c8, 2l4-c32) would be needed for a COMPLETE mid-run matrix; see the
# completeness note in this script's header.
bash "$HOME/sand42-2l4-rerun.sh" 2l4-c16 2>&1 | tee "$HOME/sand42-2l4-c16.log"
check_leg 2l4-c16
# Legs 4-5: contracts-only, on the corrected ground-truth draw. The other four classes
# in these cells are still valid; only contracts changed draw (11 of 50 documents).
bash "$HOME/sand42-2l4-rerun.sh" 2l4-c8 2>&1 | tee "$HOME/sand42-2l4-c8.log"
check_leg 2l4-c8
bash "$HOME/sand42-2l4-rerun.sh" 2l4-c32 2>&1 | tee "$HOME/sand42-2l4-c32.log"
check_leg 2l4-c32
set +a

# The one capture that is not automatic. Cumulative, so one recording covers both legs.
M=$(modal billing summary 2>&1 | awk '/Metered Cost/{print $3; exit}')
B=$(modal billing summary 2>&1 | awk '/Billed Cost/{print $3; exit}' | tr -d '$')
if [ -n "${M:-}" ]; then
  .venv/bin/sandbox run card --record-metered SAND-42 "$M" "${B:-0}"
  echo "[chain] metered recorded: $M / billed ${B:-0}"
else
  echo "[chain] WARN could not read the billing summary — record the metered cost by hand" >&2
fi

echo "[chain] $(date '+%F %H:%M:%S') legs done — the watcher rebuilds + verifies next"
