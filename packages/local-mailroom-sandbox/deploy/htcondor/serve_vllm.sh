#!/usr/bin/env bash
# serve_vllm.sh — job executable for vllm_serve.sub (owned-GPU server path).
# Serves until the job is removed; keepalive pings nothing, HTCondor owns
# the lifetime. Forward it from your laptop with condor_ssh_to_job + the
# vllm-remote profile (README.md).
#
# Debug (DMR-053): SANDBOX_DEBUG=1 traces every command; the effective argv +
# knobs are echoed to the job .out/.err before the server starts so a stuck
# boot is diagnosable from the submit-side logs.
set -euo pipefail
if [ "${SANDBOX_DEBUG:-0}" = "1" ]; then
    set -x
fi

MODEL="${MODEL:-Qwen/Qwen3-8B}"
PORT=8000
VLLM_API_KEY="${VLLM_API_KEY:-}"
# Engine parity knobs (compose/Modal contract), overridable per submission.
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-256}"
TP_SIZE="${TP_SIZE:-}"

echo "[$(date -u +%FT%TZ)] serve_vllm start model=$MODEL max_model_len=$MAX_MODEL_LEN gpu_util=$GPU_MEMORY_UTILIZATION max_num_seqs=$MAX_NUM_SEQS tp=${TP_SIZE:-1} auth=$([ -n "$VLLM_API_KEY" ] && echo on || echo off)"

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
echo "[$(date -u +%FT%TZ)] argv: vllm ${ARGS[*]} --no-enable-log-requests"
exec vllm "${ARGS[@]}" --no-enable-log-requests