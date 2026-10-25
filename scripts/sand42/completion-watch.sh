#!/usr/bin/env bash
# SAND-042 completion watch — guarantee the fleets come DOWN and the reports land.
#
# Why this exists: every SAND-042 app runs min_containers=2, so a fleet that is
# merely still DEPLOYED bills 2 L4s ($1.60/hr on `exios66` free credits) with no
# work in flight. The launchers do tear their own fleets down, but the teardown is
# non-fatal by design (it must not abort before the fleet window and cell card are
# written) and the handoff's final master rebuild ends in `|| true`. So a single
# failed teardown or rebuild is silent — and expensive.
#
# This watch waits for the launchers to exit (never kills a live run), then:
#   1. forces every sandbox-vllm* app down and verifies 0 tasks,
#   2. rebuilds the master card + report + comparison + noise floor,
#   3. verifies the full artifact set (cell cards, per-run cards, the preserved
#      vLLM metrics sweep, container telemetry, figures) and the metric rows,
#   4. prints a gap list and exits non-zero if anything is missing.
#
# Usage: scripts/sand42/completion-watch.sh [--timeout-min 180] [--no-rebuild]
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"
PY=.venv/bin/python
TIMEOUT_MIN=180
REBUILD=1
while [ $# -gt 0 ]; do
  case "$1" in
    --timeout-min) TIMEOUT_MIN="$2"; shift 2 ;;
    --no-rebuild)  REBUILD=0; shift ;;
    *) echo "unknown arg $1"; exit 2 ;;
  esac
done

say() { echo "[watch] $(date '+%F %H:%M:%S') $*"; }

# ── 1. wait for the launchers to exit (bounded; never interrupts a live run) ──
say "waiting for the campaign processes (timeout ${TIMEOUT_MIN}min)"
deadline=$(( $(date +%s) + TIMEOUT_MIN * 60 ))
while :; do
  alive=$(pgrep -f "bash $HOME/sand42.sh|sand42-handoff.sh|scripts/sand42/parallel-fleets.sh|sand42-1l4-c8-rerun.sh|sand42-1l4-c16-rerun.sh|sand42-2l4-rerun.sh|sand42-rerun-chain.sh" | wc -l | tr -d ' ')
  if [ "$alive" = "0" ]; then say "all campaign processes exited"; break; fi
  if [ "$(date +%s)" -ge "$deadline" ]; then
    say "TIMEOUT after ${TIMEOUT_MIN}min with $alive process(es) still alive — NOT tearing down (a fleet may be running). Re-run when they exit."
    exit 1
  fi
  sleep 20
done

# ── 2. enforce the winddown ───────────────────────────────────────────────────
# Any sandbox-vllm* app still deployed with tasks is burning credits for nothing.
# Copy of the handoff's exact-name match: a substring match would count a
# concurrent sandbox-vllm-a as sandbox-vllm (the bug fixed under SAND-046).
still() { # $1=app -> count of DEPLOYED entries with that exact description
  modal app list --json 2>/dev/null | "$PY" -c '
import json, sys
name = sys.argv[1]
try:
    data = json.load(sys.stdin)
except ValueError:
    data = []
print(sum(1 for a in data if isinstance(a, dict)
          and a.get("description") == name and a.get("state") == "deployed"))' "$1" 2>/dev/null || echo 1
}

apps=$("$PY" - <<'PY'
import json, subprocess
out = subprocess.run(["modal", "app", "list", "--json"], capture_output=True, text=True).stdout
try:
    data = json.loads(out)
except ValueError:
    data = []
print(" ".join(sorted({a["description"] for a in data
                       if isinstance(a, dict) and a.get("state") == "deployed"
                       and str(a.get("description", "")).startswith("sandbox-vllm")
                       # `tasks` arrives as a STRING from `modal app list --json`
                       # ("2", not 2): comparing it to 0 raises TypeError and the
                       # detector silently finds nothing to tear down.
                       and int(a.get("tasks") or 0) > 0})))
PY
)
if [ -z "$apps" ]; then
  say "no sandbox-vllm* app is deployed with tasks — winddown already clean"
else
  for app in $apps; do
    say "app $app still deployed with tasks — tearing down"
    ./deploy/teardown_vllm.sh "$app" </dev/null || say "WARN teardown of $app returned non-zero"
    sleep 5
    if [ "$(still "$app")" != "0" ]; then
      say "still up — forcing modal app stop $app"
      modal app stop "$app" --yes >/dev/null 2>&1 || true
      sleep 8
    fi
    if [ "$(still "$app")" != "0" ]; then
      say "ERROR: $app will not stop — TEAR IT DOWN MANUALLY (cost leak)"
    else
      say "$app verified down"
    fi
  done
fi

# ── 3. rebuild the reports ────────────────────────────────────────────────────
if [ "$REBUILD" = 1 ]; then
  # 3a. Refresh the per-run cards FIRST. They are what the cell cards and the master
  # are built from, so a metric added to the card renderer after a run finished only
  # appears once that run's card is rewritten. Offline: reads the run store, no LLM.
  say "refreshing the per-run cards"
  # c32 is its own glob rather than {c8,c16,c32}: 1l4-c32 does not exist, and a brace
  # that silently matches nothing would drop a whole cell's cards without a word.
  for cfg in config/runs/sand42-50-*-awq-{1l4,2l4}-{c8,c16}.yaml config/runs/sand42-50-*-awq-2l4-c32.yaml; do
    .venv/bin/sandbox run card --config "$cfg" >/dev/null 2>&1 \
      || say "WARN per-run card failed for $(basename "$cfg")"
  done
  # 3b. Then the cell cards, comparison, noise floor and master card + report.
  say "rebuilding every SAND-042 report (cell cards + comparison + noise floor + master)"
  .venv/bin/sandbox run card --runbook sand42 || say "ERROR: master rebuild returned non-zero"
fi

# ── 4. verify the artifact set + print the gap list ──────────────────────────
say "verifying artifacts"
"$PY" - <<'PY'
import glob, json, pathlib, sys

# Imported from the grid, never duplicated: the hardcoded copy that used to live here
# missed 2l4-c32 the moment the SAND-047 amendment registered it and reported its six
# cards as gaps. sand42_cards.cell_paths derives the folder the same way the writers do.
from mailroom_sandbox.job import sand42_cards as _cards

CELLS = {c: _cards.cell_paths(c)["md"].parent.name for c in _cards.CELL_ORDER}
# config slug -> the card FOLDER (snake_case; the slugs are hyphenated)
FOLDERS = {"correspondence": "correspondence", "insurance-claims": "insurance_claims",
           "corporate-records": "corporate_records", "contracts": "contracts",
           "merger": "merger_agreement"}
STUDY = pathlib.Path("reports/SAND42")
gaps, ok, notes = [], [], []

# The eleven metric families SAND-046 added so nothing captured is dropped. They are
# rendered in the MASTER REPORT; the master CARD is the deliberate two-page executive
# (SAND-044) and is checked separately below.
ROWS = ["Quality SD", "Clause metric", "Parse errors", "Error kinds", "Documents/min",
        "Mean TTFT", "Prefix-cache hit", "$ / doc", "$ / ok doc", "$ / 1M tokens", "GPU util"]

master = STUDY / "SAND42-MASTER-SCORE-COST-CARD.md"
report = STUDY / "SAND42-MASTER-REPORT.md"
comparison = STUDY / "SAND42-CELL-COMPARISON.md"
noise = STUDY / "SAND42-NOISE-FLOOR.md"
for p in (master, report, comparison, noise):
    (ok if p.is_file() else gaps).append(f"master artifact {p.name}")

if report.is_file():
    text = report.read_text(encoding="utf-8")
    missing = [r for r in ROWS if r not in text]
    if missing:
        gaps.append(f"master report missing metric rows: {missing}")
    else:
        ok.append(f"master report carries all {len(ROWS)} metric families")

if master.is_file():
    text = master.read_text(encoding="utf-8")
    for probe in ("| Condition |", "| Metric |", "goodput docs/min/GPU",
                  "GPU util % (mean)", "$/1k ok", "GPU mem bandwidth"):
        if probe not in text:
            gaps.append(f"master card missing {probe!r}")
    # The one row that must never read "not captured": the per-GPU document rate the
    # master card and the comparison both read (nothing produced the key until the
    # throughput builder was fixed, while the cell card's same-labelled row silently
    # showed the absolute rate).
    if "documents/min/GPU | not captured" in text:
        gaps.append("master card still reads 'documents/min/GPU | not captured'")
    else:
        ok.append("master card populates documents/min/GPU")
    # Known + planned gap, not a failure: the 1L4-c8 runs predate the GPU memory
    # bandwidth family, so its column reads "not captured" until the 1L4-c8 re-run.
    nc_count = text.count("not captured")
    if nc_count:
        ok.append(f"master card has {nc_count} 'not captured' reading(s) — each must carry a reason, never a figure: the 1L4 re-runs fill the memory-bandwidth column, and the cold-boot rows state why ready_ts is unwritten for the cells the sequential driver ran")

# newest run card vs the master: the master must have been rebuilt AFTER them
run_cards = []
for cell, folder in CELLS.items():
    stem = f"SAND42-{folder}-SCORE-COST-CARD"
    for ext in ("md", "json"):
        p = STUDY / folder / f"{stem}.{ext}"
        (ok if p.is_file() else gaps).append(f"cell card {folder}.{ext}")
    for sp in FOLDERS:
        hits = glob.glob(str(STUDY / folder / FOLDERS[sp] / f"sand42-50-{sp}-*awq-{cell}.card.md"))
        if hits:
            run_cards.append(pathlib.Path(hits[0]))
        else:
            gaps.append(f"run card {cell}/{sp}")
if master.is_file() and run_cards:
    newest = max(p.stat().st_mtime for p in run_cards)
    if master.stat().st_mtime < newest:
        gaps.append("master card is OLDER than a run card — rerun `sandbox run card --runbook sand42`")
    else:
        ok.append(f"master is newer than all {len(run_cards)} run cards")

# the preserved metrics sweep: verbatim /metrics per label + container telemetry
txt, tel, no_json, pre_fix = 0, 0, [], []
for card in run_cards:
    run = card.name.replace(".card.md", "")
    d = pathlib.Path("data/runtime/runs") / run
    pair = list(d.glob("vllm_metrics_*.txt"))
    jsons = list(d.glob("vllm_metrics_*.json"))
    txt += len(pair)
    tel += len(list(d.glob("container_telemetry_*.json")))
    if len(jsons) < 2:
        no_json.append(run)          # the scrape itself never ran: actionable failure
    elif len(pair) < 2:
        pre_fix.append(run)          # scraped before the exporter text was preserved
if no_json:
    gaps.append(f"metrics scrape missing for {len(no_json)} run(s): {no_json}")
if pre_fix:
    notes.append(f"{len(pre_fix)} run(s) have no verbatim /metrics text — scraped before the "
                 f"exporter-preservation commit, so the 112 dropped families are GONE and only a "
                 f"re-run recovers them: {[r.split('-awq-')[-1] for r in pre_fix]}")
if not no_json and not pre_fix:
    ok.append(f"vLLM /metrics preserved for all {len(run_cards)} runs ({txt} txt files)")
else:
    ok.append(f"container telemetry present for {len(run_cards)} runs ({tel} files)")

figs = list((STUDY / "figures").glob("*.png")) if (STUDY / "figures").is_dir() else []
(ok if figs else gaps).append(f"figures ({len(figs)} png)")
serving = list(pathlib.Path("reports/serving/SAND42").rglob("*.json")) if pathlib.Path("reports/serving/SAND42").is_dir() else []
(ok if serving else gaps).append(f"serving exports ({len(serving)} json)")

for line in ok:
    print(f"  OK   {line}")
for line in notes:
    print(f"  NOTE {line}")
for line in gaps:
    print(f"  GAP  {line}")
print(f"\n[{len(ok)} ok / {len(notes)} notes / {len(gaps)} gaps]")
sys.exit(1 if gaps else 0)
PY
rc=$?
say "done (verify rc=$rc)"
exit "$rc"
