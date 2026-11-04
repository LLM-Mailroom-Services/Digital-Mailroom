#!/usr/bin/env bash
# SAND-032 per-run driver: env from YAML → gate → (deploy) → live preflight →
# /metrics before → run → /metrics after → serving record → offline BT rows → (stop).
#
#   scripts/sand032/run_one.sh <config.yaml> <deploy|warm> [stop]
#
# deploy = fresh fleet (redeploy + measured cold boot); warm = reuse the running
# fleet (serving block must be identical — benchmark-check enforces env == YAML).
set -euo pipefail
CFG="$1"; MODE="$2"; STOP="${3:-}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
PY="${SANDBOX_PY:-$ROOT/../local-mailroom-sandbox/.venv/bin/python}"
sbx() { PYTHONPATH=src "$PY" -c "import sys; from mailroom_sandbox.cli import main; sys.exit(main(sys.argv[1:]))" "$@"; }
RID="$(basename "$CFG" .yaml)"
RT="$ROOT/data/runtime/sand032"; LOG="$RT/logs"; mkdir -p "$LOG"
echo "$ROOT/$CFG" > "$RT/current"          # `sandbox watch --follow` target
ts() { python3 -c 'import time;print(time.time())'; }
stamp() { echo "\"$1\": $(ts)," >> "$LOG/$RID.times"; }
: > "$LOG/$RID.times"

[ -f "$RT/api_token" ] || { umask 077; openssl rand -hex 24 > "$RT/api_token"; }
set -a; eval "$(sbx run deploy-env --config "$CFG")"; set +a
export MODAL_VLLM_API_TOKEN="$(cat "$RT/api_token")" VLLM_API_KEY="$(cat "$RT/api_token")"
export SANDBOX_PROFILE=modal-vllm
[ "$(modal profile current)" = "exios66" ] || { echo "wrong Modal profile"; exit 3; }
APP="${MODAL_VLLM_APP_NAME:-sandbox-vllm}"
REPLICAS="$MODAL_VLLM_MAX_CONTAINERS"

# Any failure after this point stops the fleet — a failed step must never
# leave an L4 warm and billing (SAND-032 L0 lesson: a bad URL idled a GPU).
on_fail() {
  rc=$?
  [ $rc -eq 0 ] && return
  echo "run_one FAILED rc=$rc — stopping $APP to protect spend" | tee -a "$LOG/$RID.fail.log"
  modal app stop "$APP" -y >> "$LOG/$RID.fail.log" 2>&1 || true
  stamp stopped
  FLEET="$(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));o=[k for k,v in d.items() if not v.get("stop_ts")];print(o[-1] if o else "")' "$RT/fleets.json" 2>/dev/null || true)"
  [ -n "$FLEET" ] && python3 scripts/sand032/spend.py close "$FLEET" >/dev/null || true
}
trap on_fail EXIT

sbx run benchmark-check --config "$CFG" --modal-profile exios66 > "$LOG/$RID.bcheck.txt" 2>&1 \
  || { echo "benchmark-check FAILED"; tail -20 "$LOG/$RID.bcheck.txt"; exit 4; }

if [ "$MODE" = deploy ]; then
  stamp deploy_start
  python3 scripts/sand032/spend.py open "$RID" "$REPLICAS" >/dev/null
  modal deploy deploy/modal_vllm.py > "$LOG/$RID.deploy.log" 2>&1
  stamp deploy_done
fi
URL="$(grep -hoE 'https://[a-z0-9-]+--'"$APP"'-serve\.modal\.run' "$LOG"/*.deploy.log | tail -1)"
case "$URL" in https://*) ;; *) echo "could not parse deploy URL: '$URL'"; exit 6;; esac
export VLLM_BASE_URL="${URL}/v1"
echo "$VLLM_BASE_URL" > "$RT/base_url"

sbx run preflight --config "$CFG" --live > "$LOG/$RID.preflight.txt" 2>&1 \
  || { echo "preflight FAILED"; tail -30 "$LOG/$RID.preflight.txt"; exit 5; }
stamp ready
sbx run scrape-metrics --config "$CFG" --label before > "$LOG/$RID.scrape-before.txt" 2>&1 || true
stamp run_start
sbx run start --config "$CFG" --job-mode endpoint --watch > "$LOG/$RID.start.log" 2>&1 || echo "run start exit=$?" >> "$LOG/$RID.start.log"
stamp run_end
sbx run scrape-metrics --config "$CFG" --label after > "$LOG/$RID.scrape-after.txt" 2>&1 || true

WALL="$("$PY" - "$RID" <<'PY'
import json, sys
rid = sys.argv[1]; wall = ""
for line in open("reports/experiment_log.jsonl"):
    r = json.loads(line)
    if r.get("run_id") == rid or str(r.get("experiment_name", "")).endswith(rid):
        wall = r.get("wall_seconds") or wall
print(wall)
PY
)"
sbx metrics serving-record --run "$RID" ${WALL:+--wall-seconds "$WALL"} \
  --out "reports/serving/$RID.serving.json" > "$LOG/$RID.serving.txt" 2>&1 || true
sbx run export-bt --config "$CFG" > "$LOG/$RID.bt.txt" 2>&1 || true

if [ "$STOP" = stop ]; then
  modal app stop "$APP" -y > "$LOG/$RID.stop.log" 2>&1 || true
  stamp stopped
  FLEET="$(python3 -c 'import json,sys;d=json.load(open(sys.argv[1]));print([k for k,v in d.items() if not v.get("stop_ts")][-1])' "$RT/fleets.json")"
  python3 scripts/sand032/spend.py close "$FLEET" >/dev/null
fi
python3 scripts/sand032/spend.py write
echo "DONE $RID wall=${WALL:-?}"
