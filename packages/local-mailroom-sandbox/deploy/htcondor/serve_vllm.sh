#!/usr/bin/env bash
# serve_vllm.sh — job executable for vllm_serve.sub (owned-GPU server path).
# Serves until the job is removed; keepalive pings nothing, HTCondor owns
# the lifetime. Forward it from your laptop with condor_ssh_to_job + the
# vllm-remote profile (README.md).
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen3-8B}"
PORT=8000
VLLM_API_KEY="${VLLM_API_KEY:-}"
# Engine parity knobs (compose/Modal contract), overridable per submission.
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-256}"
TP_SIZE="${TP_SIZE:-}"

ARGS=(
    serve "$MODEL"
    --host 0.0.0.0
    --port "$PORT"
    --max-model-len "$MAX_MODEL_LEN"
    --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
    --max-num-seqs "$MAX_NUM_SEQS"
)
if [ -n "$TP_SIZE" ]; then
    ARGS+=(--tensor-parallel-size "$TP_SIZE")
fi
if [ -n "$VLLM_API_KEY" ]; then
    export VLLM_API_KEY
fi
exec vllm "${ARGS[@]}" --no-enable-log-requests
