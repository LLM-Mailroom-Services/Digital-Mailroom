#!/usr/bin/env bash
# DMR-063: loud teardown for the Modal sandbox-vllm deployment.
#
# Guarantees the GPU app is STOPPED and verified dead — no container left
# warm burning L4 $ after a run. Volumes (weights + vLLM compile cache)
# persist; a later `modal deploy` reuses them. Idempotent: safe to re-run.
#
# Specialist suite (DMR-076/077): one warm app per operator track (or all
# five for single-operator --suite full); call this ONLY after the last
# config in that track. max_containers=1, min_containers=0, scaledown=120
# (attended; 600 unattended) — teardown STILL required after the last run
# so you do not wait out the scaledown window.
#
#   ./deploy/teardown_vllm.sh [app-name]
#
# Exit 0 = app stopped and verified; exit 1 = verification failed (loud).
set -euo pipefail

APP="${1:-${MODAL_VLLM_APP:-sandbox-vllm}}"

echo "== teardown: $APP =="
if ! command -v modal >/dev/null 2>&1; then
    echo "ERROR: modal CLI not found — install the [deploy] extra first" >&2
    exit 1
fi

# App-scoped cache Volumes, mirroring deploy/modal_vllm.py — so a concurrent
# second fleet's caches are reported, not the default app's.
if [ "$APP" = "sandbox-vllm" ]; then SUFFIX=""; else SUFFIX="-${APP#sandbox-vllm-}"; fi
HF_VOLUME="sandbox-hf-cache${SUFFIX}"
VLLM_VOLUME="sandbox-vllm-cache${SUFFIX}"

# Exact app-name matching: `modal app list`'s Description column truncates long
# names and a substring match lets `sandbox-vllm` hit a concurrent
# `sandbox-vllm-a`, so parse the JSON by exact description instead.
_PY=""
if [ -x .venv/bin/python ]; then _PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then _PY="python3"; fi

_deployed_count() {
    if [ -n "$_PY" ]; then
        modal app list --json 2>/dev/null | "$_PY" -c '
import json, sys
try:
    data = json.load(sys.stdin)
except ValueError:
    data = []
print(sum(1 for a in data
          if isinstance(a, dict) and a.get("description") == sys.argv[1]
          and a.get("state") == "deployed"))
' "$APP" || echo 0
        return
    fi
    # Fallback (no Python): require the app name to be its own table cell.
    modal app list 2>/dev/null | grep -cE "│ ${APP} +│ *deployed" || true
}

# 1) Stop serving NOW (scale-to-zero immediately; no scaledown-window burn).
# Non-interactive (CI/cron) runs get --yes so teardown never stalls on a prompt.
FLAGS=""
if [ ! -t 0 ]; then FLAGS="--yes"; fi
echo "-> modal app stop $APP $FLAGS"
modal app stop "$APP" $FLAGS

# 2) Verify: poll until no deployment of the app is running.
for i in $(seq 1 30); do
    running=$(_deployed_count)
    if [ "${running:-0}" -eq 0 ]; then
        echo "-> verified: no '$APP' deployment running (stopped)"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: '$APP' still shows a running deployment after 30 polls:" >&2
        modal app list 2>/dev/null | grep -F "$APP" >&2 || true
        exit 1
    fi
    sleep 2
done

# 3) Prove the cost-bearing state is gone and the data-bearing state remains.
echo "-> remaining app state:"
modal app list 2>/dev/null | grep -F "$APP" || echo "   (none listed)"
echo "-> volumes persist (weights + compile cache):"
modal volume ls "$HF_VOLUME" >/dev/null 2>&1 && echo "   $HF_VOLUME OK"
modal volume ls "$VLLM_VOLUME" >/dev/null 2>&1 && echo "   $VLLM_VOLUME OK"

# 4) Best-effort spend visibility (needs billing permission; never fatal).
echo "-> spend check (best-effort):"
modal billing summary 2>/dev/null | head -8 || echo "   (billing summary unavailable — see modal.com/dashboard)"

echo "== teardown complete: $APP stopped, zero containers warm =="
