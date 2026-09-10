#!/usr/bin/env bash
# run_batch_eval.sh — CHTC/HTCondor job executable (HUB-026, DMR-044, DMR-053).
#
# Runs INSIDE the vLLM container on the execute node:
#   1. unpack the portable conda env (sandbox deps; conda-pack output)
#   2. install the eval stack (mailroom v0.6.0 + the sandbox) and PROVE it is
#      importable — a missing stack must fail the job, never silently mock
#   3. serve the model in-process on localhost:8000 (compose/Modal parity flags)
#   4. wait for /v1/models health (hard failure on death OR timeout)
#   5. run the sandbox evals with SANDBOX_PROFILE=vllm-local
#   6. guard: fail if any record shows offline_fallback > 0 (live-or-loud)
#   7. leave everything under results/ for HTCondor to transfer back
#
# DEBUGGING (DMR-053):
#   - every step logs a timestamped line to stderr AND results/run.log
#   - SANDBOX_DEBUG=1 turns on `set -x` (full trace on stderr)
#   - any failure dumps a diagnostics block into run.log: python/package
#     versions, the masked engine env, dataset row counts, and the vLLM log
#     tail — then the job exits non-zero so HTCondor marks it failed
#
# Requires the two input tarballs (see README.md one-time setup):
#   mailroom-sandbox.tar.gz   — git archive of packages/local-mailroom-sandbox
#   env-mailroom-sandbox.tar.gz — conda-pack of the mailroom-sandbox env
set -euo pipefail
if [ "${SANDBOX_DEBUG:-0}" = "1" ]; then
    set -x
    export PS4='+ [${BASH_SOURCE}:${LINENO}] '
fi

MODEL="${MODEL:-Qwen/Qwen3-8B}"
# Engine parity knobs (compose/Modal contract); overridable per submission via
# the .sub `environment = "MODEL=...,MAX_MODEL_LEN=..."` line.
# DMR-056: 16384 default — L4-bf16 8B-class rows cannot hold 32768 (v0.28.0
# raises at boot); AWQ/FP8 rows set 32768 explicitly.
MAX_MODEL_LEN="${MAX_MODEL_LEN:-16384}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-256}"
TP_SIZE="${TP_SIZE:-}"
QUANTIZATION="${QUANTIZATION:-}"
REVISION="${REVISION:-}"
PORT=8000
export MODEL MAX_MODEL_LEN GPU_MEMORY_UTILIZATION MAX_NUM_SEQS TP_SIZE QUANTIZATION REVISION

# Absolute results dir: the script `cd`s into the unpacked package, so a
# relative `results/` would land in mailroom-sandbox/ while HTCondor transfers
# the job's initial directory (DMR-044 path fix).
RESULTS_DIR="$(pwd)/results"
mkdir -p "$RESULTS_DIR"
RUN_LOG="$RESULTS_DIR/run.log"
: > "$RUN_LOG"

log() {
    local line
    line="[$(date -u +%FT%TZ)] $*"
    printf '%s\n' "$line" | tee -a "$RUN_LOG" >&2
}

DIAG_DUMPED=0

dump_diagnostics() {
    [ "$DIAG_DUMPED" = "1" ] && return
    DIAG_DUMPED=1
    {
        echo "===== diagnostics ($(date -u +%FT%TZ)) ====="
        echo "-- python: $(command -v python || echo missing)"
        python - <<'PY' 2>/dev/null || echo "(version probe failed)"
import importlib

for name in ("vllm", "torch", "openai", "mailroom", "llm_dojo_scoring", "mailroom_sandbox", "langchain_openai"):
    try:
        mod = importlib.import_module(name)
        print(f"{name} = {getattr(mod, '__version__', '?')}")
    except Exception as exc:
        print(f"{name} = UNAVAILABLE ({type(exc).__name__})")
PY
        echo "-- engine env (masked):"
        env | sort | sed -E 's/((MODAL_VLLM_API_TOKEN|VLLM_API_KEY|HF_TOKEN|OPENROUTER_API_KEY|LANGFUSE_SECRET_KEY)=).*/\1<redacted>/' \
            | grep -E '^(MODEL|MAX_MODEL_LEN|GPU_MEMORY_UTILIZATION|MAX_NUM_SEQS|TP_SIZE|SANDBOX_|DEFAULT_PROVIDER|VLLM_|HF_TOKEN|MAILROOM_)' || true
        echo "-- dataset:"
        if [ -f dataset.jsonl ]; then
            echo "rows=$(wc -l < dataset.jsonl) bytes=$(wc -c < dataset.jsonl)"
        else
            echo "dataset.jsonl absent"
        fi
        if [ -f reports/experiment_log.jsonl ]; then
            echo "experiment records=$(wc -l < reports/experiment_log.jsonl)"
        fi
        if [ -f "$RESULTS_DIR/vllm_serve.log" ]; then
            echo "-- vllm_serve.log tail:"
            tail -30 "$RESULTS_DIR/vllm_serve.log" || true
        fi
        echo "===== end diagnostics ====="
    } >> "$RUN_LOG" 2>&1
    cat "$RUN_LOG" >&2 || true
}

fail() {
    echo "FATAL: $*" >&2
    dump_diagnostics
    exit 1
}

on_exit() {
    local rc=$?
    if [ "$rc" -ne 0 ]; then
        dump_diagnostics
    else
        {
            echo "[$(date -u +%FT%TZ)] run finished rc=0"
            echo "results: $(ls "$RESULTS_DIR")"
        } >> "$RUN_LOG" 2>&1 || true
    fi
    if [ -n "${VLLM_PID:-}" ]; then
        kill "$VLLM_PID" 2>/dev/null || true
    fi
}
trap on_exit EXIT

log "job start model=$MODEL max_model_len=$MAX_MODEL_LEN gpu_util=$GPU_MEMORY_UTILIZATION max_num_seqs=$MAX_NUM_SEQS tp=${TP_SIZE:-1}"

echo "== unpack portable env =="
if [ ! -f env-mailroom-sandbox.tar.gz ]; then
    fail "env-mailroom-sandbox.tar.gz not transferred (see README §4 one-time setup)"
fi
mkdir -p env
tar -xzf env-mailroom-sandbox.tar.gz -C env
# conda-pack requires activating from the unpacked prefix
source env/bin/activate
log "python: $(command -v python)"

echo "== unpack sandbox package =="
tar -xzf mailroom-sandbox.tar.gz
cd mailroom-sandbox

echo "== install sandbox into env (light deps; torch/vLLM come from the container) =="
VLLM_DOJO_PIN="${SANDBOX_DOJO_PIN:-v0.12.2}"
pip install --no-deps "llm-dojo-scoring @ git+https://github.com/Exios66/llm-dojo-scoring.git@${VLLM_DOJO_PIN}"
pip install --no-deps -e .
# Light runtime deps the container lacks (openai is also in the conda env).
pip install pyyaml python-dotenv httpx structlog pydantic "openai>=1.30"
# The eval agents import agents.sorter / graph.build_graph / pipeline.bins from
# the MAILROOM dist (llm-mailroom v0.6.0) — NOT llm-entity-extraction (its
# agents/ lacks sorter.py and would shadow mailroom's on sys.path).
# --no-deps: torch/vLLM stay the container's; mailroom's tree is torch-free.
pip install --no-deps "mailroom @ git+https://github.com/Exios66/llm-mailroom.git@v0.6.0"
# Fallback when the conda env was not built with the [pipeline] extra (README §4).
pip install "langchain-core>=0.3.0" "langchain-openai>=0.3" "langgraph>=0.2.0" \
    "langgraph-checkpoint-sqlite>=1.0" "sqlalchemy[asyncio]>=2.0" "aiosqlite>=0.19"

echo "== preflight: eval agent stack importable (live-or-loud) =="
python - <<'PY'
import importlib

for mod in (
    "agents.sorter",
    "agents.contracts_specialist",
    "graph.build_graph",
    "pipeline.bins",
    "llm.client",
    "langchain_openai",
    "openai",
):
    try:
        importlib.import_module(mod)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"FATAL: cannot import {mod}: {exc!r} — eval would silently mock")
print("OK: eval agent stack importable")
PY
log "preflight gate passed"

echo "== serve vLLM in-process =="
# Parity with deploy/docker-compose.yml + deploy/modal_vllm.py (same image tag,
# same argv). TP_SIZE is optional (70B-class multi-GPU jobs).
vllm serve "$MODEL" --host 0.0.0.0 --port "$PORT" \
    --max-model-len "$MAX_MODEL_LEN" \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    --max-num-seqs "$MAX_NUM_SEQS" \
    ${TP_SIZE:+--tensor-parallel-size "$TP_SIZE"} \
    ${QUANTIZATION:+--quantization "$QUANTIZATION"} \
    ${REVISION:+--revision "$REVISION"} \
    --no-enable-log-requests \
    > "$RESULTS_DIR/vllm_serve.log" 2>&1 &
VLLM_PID=$!
log "vllm serve pid=$VLLM_PID (log: results/vllm_serve.log)"

echo "== wait for /v1/models =="
HEALTHY=0
# DMR-056: bounded probe (--max-time 5); forward the bearer when the job env
# carries VLLM_API_KEY (v0.28.0 enforces it automatically — a keyless probe
# would 401 forever and false-fail after 20 minutes).
CURL_AUTH=()
if [ -n "$VLLM_API_KEY" ]; then
    CURL_AUTH=(-H "Authorization: Bearer $VLLM_API_KEY")
fi
for i in $(seq 1 120); do
    if curl -sf --max-time 5 "${CURL_AUTH[@]}" "http://localhost:${PORT}/v1/models" > /dev/null; then
        echo "vLLM healthy"
        HEALTHY=1
        break
    fi
    if ! kill -0 "$VLLM_PID" 2> /dev/null; then
        fail "vLLM exited during startup (tail below)"
    fi
    if [ $((i % 10)) -eq 0 ]; then
        log "health wait: $((i * 10))s elapsed, still warming (cold start can take minutes)"
    fi
    sleep 10
done
if [ "$HEALTHY" -ne 1 ]; then
    fail "/v1/models not healthy after 20m"
fi
log "vLLM healthy after ~$((i * 10))s"

export SANDBOX_PROFILE=vllm-local
export DEFAULT_PROVIDER=vllm
export VLLM_BASE_URL="http://localhost:${PORT}/v1"
# Vendored langchain agents (sorter/specialists) build their OWN ChatOpenAI
# against OPENROUTER_BASE_URL — point it at the in-container vLLM or those
# calls fail auth and fall back to mock.
export OPENROUTER_BASE_URL="http://localhost:${PORT}/v1"
# no VLLM_API_KEY: llm/client.py sends api_key="not-needed"; vLLM serves open.

echo "== offline fixture prep (no network) =="
python -m mailroom_sandbox.cli datasets prepare

echo "== evals =="
# --model "$MODEL" rewrites every agent to the served model (overlay.rewrite_agents)
# so a .sub MODEL= override cannot desync agents from the engine.
python -m mailroom_sandbox.cli eval sorter --local --model "$MODEL" --dry-run
python -m mailroom_sandbox.cli eval sorter --local --model "$MODEL"
python -m mailroom_sandbox.cli eval extract --local --model "$MODEL"

echo "== guard: live-or-loud (offline_fallback must be 0) =="
python - <<'PY'
import json
import pathlib
import sys

path = pathlib.Path("reports/experiment_log.jsonl")
rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.is_file() else []
if not rows:
    print("FATAL: no experiment-log records produced — evals did not run", file=sys.stderr)
    sys.exit(1)
for rec in rows:
    name = rec.get("experiment_name")
    scores = rec.get("scores") or {}
    fallback = scores.get("offline_fallback")
    if fallback is not None and int(fallback or 0) > 0:
        print(f"FATAL: record {name} offline_fallback={fallback} (mock!)", file=sys.stderr)
        sys.exit(1)
    for doc in rec.get("docs") or []:
        if isinstance(doc, dict) and doc.get("offline_fallback"):
            print(f"FATAL: record {name} has offline_fallback docs (mock!)", file=sys.stderr)
            sys.exit(1)
print(f"OK: {len(rows)} record(s) live (offline_fallback=0)")
PY
log "live-or-loud guard passed"

echo "== collect =="
cp -r reports "$RESULTS_DIR/" 2> /dev/null || true
log "done: $(ls "$RESULTS_DIR")"