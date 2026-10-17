#!/usr/bin/env bash
# SAND-054: the campaign babysitter — sits, and pages on anything unexpected.
#
# Paging model. In this harness only a TOP-LEVEL background command notifies the operator when
# it exits, so a long-lived sitter cannot page by exiting (it must keep sitting) and a pager
# that exits stops watching. So they are split:
#   * this sitter never exits early; when it finds trouble it appends to a sentinel file;
#   * `campaign-pager.sh` waits on that sentinel and exits the moment it appears — which is
#     what raises the notification — then removes it, so the next trouble pages again.
# That makes paging repeatable: no re-arming, no dead watcher after the first alert.
#
#   bash scripts/sand42/campaign-sitter.sh [cadence_seconds]
set -uo pipefail
cd /Users/luciusjmorningstar/Downloads/local-mailroom-sandbox
GAP="${1:-45}"
STALL_MIN="${STALL_MIN:-15}"
BEAT_EVERY="${BEAT_EVERY:-300}"
IDLE_PAGE_MIN="${IDLE_PAGE_MIN:-8}"
DISK_MIN_KB="${DISK_MIN_KB:-2097152}"        # 2 GiB
LOG="$HOME/sand42-sitter.log"
ALERTS="$HOME/sand42-alerts.log"
SENT="$HOME/.sand42-page-me"
LEGS='sand42-rerun-chain\.sh|sand42-1l4-c8-rerun\.sh|sand42-1l4-c16-rerun\.sh|sand42-2l4-rerun\.sh'
CELLS=(1l4-c8 1l4-c16 2l4-c16 2l4-c8 2l4-c32)

say() { echo "[sitter $(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
# Appends to the sentinel rather than overwriting: two conditions firing before the pager reads
# must both survive, or the second page is silently lost.
alert() {
  echo "[sitter $(date '+%H:%M:%S')] ALERT $*" | tee -a "$LOG" "$ALERTS" >&2
  printf '%s\n' "$*" >> "$SENT"
}

verified=""
idle_ticks=0
tick=0
last_beat=0
last_alert=""
say "babysitting · cadence ${GAP}s · stall ${STALL_MIN}min · heartbeat ${BEAT_EVERY}s"
say "paging via $SENT (campaign-pager.sh) · idle-page ${IDLE_PAGE_MIN}min · disk floor $((DISK_MIN_KB/1048576)) GiB"

while :; do
  tick=$((tick + 1))

  if ! pgrep -f "$LEGS" >/dev/null 2>&1; then
    say "all legs exited — final coverage pass"
    for c in "${CELLS[@]}"; do
      case " $verified " in *" $c "*) continue ;; esac
      .venv/bin/python scripts/sand42/coverage-ledger.py "$c" 2>&1 | tee -a "$LOG"
      verified="$verified $c"
    done
    say "babysitter done — every leg verified, or its gaps are in the log above"
    break
  fi

  health=$(STALL_MIN="$STALL_MIN" .venv/bin/python - <<'PY'
import json, os, pathlib, sys, time
sys.path.insert(0, "src")
from mailroom_sandbox.job.specialist_posture import SPECIALIST_POSTURE as SP

stall = float(os.environ.get("STALL_MIN", "15"))
jobs = pathlib.Path.home() / ".mailroom" / "jobs"
now = time.time()
running, trouble = [], []
for f in jobs.glob("sand42-*-awq-*.json"):
    try:
        d = json.loads(f.read_text())
    except ValueError:
        continue
    rid = str(d.get("job_id") or f.stem)
    state = str(d.get("state") or "")
    done = int(d.get("done") or 0)
    total = int(d.get("total") or 0) or 50
    errs = int(d.get("errors") or 0)
    if state == "running":
        running.append((rid, d, done, total, errs))
        continue
    fin = float(d.get("finished_at") or 0)
    if fin and now - fin < 900:            # only recent history, or old failures page forever
        if done < total:
            trouble.append(f"SHORT {rid} {done}/{total} state={state}")
        if errs:
            trouble.append(f"ERRORS={errs} {rid} (finished {done}/{total})")

if trouble:
    print("; ".join(trouble))
    raise SystemExit(0)
if not running:
    print("IDLE")
    raise SystemExit(0)
for rid, d, done, total, errs in running:
    cls = rid.split("sand42-50-")[-1].rsplit("-specialist-awq-", 1)[0]
    cell = rid.rsplit("-awq-", 1)[-1]
    started = float(d.get("started_at") or now)
    updated = float(d.get("updated_at") or now)
    cap = int((SP.get(rid) or {}).get("max_wall_seconds") or 2400)
    elapsed, stale = now - started, (now - updated) / 60.0
    flags = []
    if errs:
        flags.append(f"ERRORS={errs}")
    if stale > stall and done < total:
        flags.append(f"STALL={stale:.0f}min")
    if elapsed > 0.85 * cap:
        flags.append(f"WALL={elapsed/60:.0f}min/{cap/60:.0f}min")
    print(f"RUN {cell} {cls} {done}/{total} err={errs} elapsed={elapsed/60:.0f}min "
          f"stale={stale:.0f}min " + (" ".join(flags) if flags else "ok"))
PY
)

  case "$health" in
    IDLE)
      # A leg is alive but nothing is running: a wedged deploy, or a leg that died without
      # printing its marker. Silence is the failure mode nobody notices.
      idle_ticks=$((idle_ticks + 1))
      if [ $(( idle_ticks * GAP / 60 )) -ge "$IDLE_PAGE_MIN" ]; then
        alert "no run active for $(( idle_ticks * GAP / 60 ))min while a leg is alive — wedged deploy, or a leg died without its marker"
        idle_ticks=0
      fi
      ;;
    *ERRORS=*|*STALL=*|*WALL=*|*SHORT=*)
      idle_ticks=0
      [ "$health" != "$last_alert" ] && { alert "$health"; last_alert="$health"; }
      ;;
    *)
      idle_ticks=0
      last_alert=""
      if [ $(( $(date +%s) - last_beat )) -ge "$BEAT_EVERY" ]; then
        say "$health"
        last_beat=$(date +%s)
      fi
      ;;
  esac

  # Disk: the campaign writes ~200 MB, but a volume that fills mid-leg fails as a metrics
  # problem, which reads like a capture bug rather than a full disk.
  if [ $(( tick % 10 )) -eq 0 ]; then
    free_kb=$(df -k . | awk 'NR==2 {print $4}')
    if [ -n "$free_kb" ] && [ "$free_kb" -lt "$DISK_MIN_KB" ]; then
      alert "disk: $(( free_kb / 1048576 )) GiB free on the campaign volume (floor $(( DISK_MIN_KB / 1048576 )) GiB)"
    fi
  fi

  # Per-leg coverage. pipefail is set, so the ledger's status survives the tee — a leg that
  # lands non-compliant pages rather than waiting to be noticed.
  for c in "${CELLS[@]}"; do
    case " $verified " in *" $c "*) continue ;; esac
    grep -q "RE-RUN COMPLETE" "$HOME/sand42-$c.log" 2>/dev/null || continue
    say "── $c leg finished — verifying coverage ──"
    if ! .venv/bin/python scripts/sand42/coverage-ledger.py "$c" 2>&1 | tee -a "$LOG"; then
      alert "$c: coverage gate FAILED — captures or paired n incomplete; repair with scripts/sand42/topup-one-class.sh"
    fi
    verified="$verified $c"
  done

  sleep "$GAP"
done
