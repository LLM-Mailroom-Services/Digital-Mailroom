#!/usr/bin/env bash
# run_batch_eval.sh — CHTC/HTCondor job executable (HUB-026, DMR-044).
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
# Requires the two input tarballs (see README.md one-time setup):
#   mailroom-sandbox.tar.gz   — git archive of packages/local-mailroom-sandbox
#   env-mailroom-sandbox.tar.gz — conda-pack of the mailroom-sandbox env
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen3-8B}"
# Engine parity knobs (compose/Modal contract); overridable per submission via
# the .sub `environment = "MODEL=...,MAX_MODEL_LEN=..."` line.
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-256}"
TP_SIZE="${TP_SIZE:-}"
PORT=8000
export MODEL MAX_MODEL_LEN GPU_MEMORY_UTILIZATION MAX_NUM_SEQS

# Absolute results dir: the script `cd`s into the unpacked package, so a
# relative `results/` would land in mailroom-sandbox/ while HTCondor transfers
# the job's initial directory (DMR-044 path fix).
RESULTS_DIR="$(pwd)/results"
mkdir -p "$RESULTS_DIR"

echo "== unpack portable env =="
if [ ! -f env-mailroom-sandbox.tar.gz ]; then
    echo "FATAL: env-mailroom-sandbox.tar.gz not transferred" >&2
    exit 1
fi
mkdir -p env
tar -xzf env-mailroom-sandbox.tar.gz -C env
# conda-pack requires activating from the unpacked prefix
source env/bin/activate
echo "python: $(command -v python)"

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

echo "== serve vLLM in-process =="
# Parity with deploy/docker-compose.yml + deploy/modal_vllm.py (same image tag,
# same argv). TP_SIZE is optional (70B-class multi-GPU jobs).
vllm serve "$MODEL" --host 0.0.0.0 --port "$PORT" \
    --max-model-len "$MAX_MODEL_LEN" \
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION" \
    --max-num-seqs "$MAX_NUM_SEQS" \
    ${TP_SIZE:+--tensor-parallel-size "$TP_SIZE"} \
    --no-enable-log-requests \
    > "$RESULTS_DIR/vllm_serve.log" 2>&1 &
VLLM_PID=$!
trap 'kill "$VLLM_PID" 2>/dev/null || true; cp -r reports "$RESULTS_DIR/" 2>/dev/null || true' EXIT

echo "== wait for /v1/models =="
HEALTHY=0
for _ in $(seq 1 120); do
    if curl -sf "http://localhost:${PORT}/v1/models" > /dev/null; then
        echo "vLLM healthy"
        HEALTHY=1
        break
    fi
    if ! kill -0 "$VLLM_PID" 2> /dev/null; then
        echo "FATAL: vLLM exited during startup" >&2
        tail -50 "$RESULTS_DIR/vllm_serve.log" >&2
        exit 1
    fi
    sleep 10
done
if [ "$HEALTHY" -ne 1 ]; then
    echo "FATAL: /v1/models not healthy after 20m" >&2
    tail -50 "$RESULTS_DIR/vllm_serve.log" >&2
    exit 1
fi

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

echo "== collect =="
cp -r reports "$RESULTS_DIR/" 2> /dev/null || true
echo "done: $(ls "$RESULTS_DIR")"
