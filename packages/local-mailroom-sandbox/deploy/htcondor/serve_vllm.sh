#!/usr/bin/env bash
# serve_vllm.sh — job executable for vllm_serve.sub (owned-GPU server path).
# Serves until the job is removed; keepalive pings nothing, HTCondor owns
# the lifetime. Forward it from your laptop with condor_ssh_to_job + the
# vllm-remote profile (README.md).
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen3-8B}"
PORT=8000
VLLM_API_KEY="${VLLM_API_KEY:-}"

ARGS=(serve "$MODEL" --host 0.0.0.0 --port "$PORT" --max-model-len "${MAX_MODEL_LEN:-32768}")
if [ -n "$VLLM_API_KEY" ]; then
    export VLLM_API_KEY
fi
exec vllm "${ARGS[@]}" --no-enable-log-requests
