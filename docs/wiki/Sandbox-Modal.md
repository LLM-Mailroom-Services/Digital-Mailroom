# Modal deployment (remote GPU vLLM)

Deploy vLLM on Modal for zero-infra remote GPU serving. SDK **1.5.5**
(pinned) + vLLM **v0.28.0** (matches local compose pin).

**Full reference:** [`deploy/README.md`](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/blob/main/packages/local-mailroom-sandbox/deploy/README.md)

---

## Setup

```bash
pip install -e ".[deploy]"
modal token new
```

---

## Deploy workflow

```bash
# 1. Set knobs
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_API_TOKEN="$(openssl rand -hex 24)"

# 2. Pre-warm weights (CPU-only, no GPU spend)
modal run deploy/modal_vllm.py::download_model
#    fails loudly on an empty snapshot (repo id/revision/HF_TOKEN hints, DMR-053)

# 2b. Debug / verify (DMR-053)
modal run deploy/modal_vllm.py --debug   # masked resolved config
modal run deploy/modal_vllm.py --check   # probes /models (401-bearer + mismatch hints)

# 3. Deploy (prints the URL)
modal deploy deploy/modal_vllm.py

# 4. Connect the sandbox
export VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
export VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox health --profile modal-vllm
```

---

## Environment knobs

| Variable | Default | Purpose |
| --- | --- | --- |
| `MODAL_VLLM_MODEL` | `Qwen/Qwen3-8B` | HF model id |
| `MODAL_VLLM_GPU` | `L4` | GPU type (24 GB) |
| `MODAL_VLLM_MAX_MODEL_LEN` | `16384` | Context cap — DMR-056: boot-valid default (v0.28.0 raises when the KV pool can't hold one request); AWQ/FP8 rows use 32768 |
| `MODAL_VLLM_GPU_MEMORY_UTILIZATION` | `0.90` | GPU memory fraction |
| `MODAL_VLLM_MAX_NUM_SEQS` | `256` | Concurrency cap |
| `MODAL_VLLM_TP_SIZE` | from GPU `:N` suffix (1 single-GPU) | Tensor-parallel size — must match `MODAL_VLLM_GPU="A100-80GB:2"` for 70B-class |
| `MODAL_VLLM_QUANTIZATION` | empty | `awq` / `gptq` / ... |
| `MODAL_VLLM_IMAGE_TAG` | `v0.28.0` | vLLM version pin |
| `MODAL_VLLM_REVISION` | empty | HF revision pin |
| `MODAL_VLLM_API_TOKEN` | empty | Bearer token (maps to `VLLM_API_KEY`) |
| `HF_TOKEN` | empty | Gated/private weights |
| `MODAL_VLLM_SCALEDOWN_SECONDS` | `900` | Idle warm window |
| `MODAL_VLLM_MAX_CONTAINERS` | `1` | Cost guard |
| `MODAL_VLLM_MIN_CONTAINERS` | `0` | Scale-to-zero |
| `MODAL_VLLM_STARTUP_TIMEOUT_SECONDS` | `1200` | First-boot budget |

---

## Engine posture (v0.28.0)

| Flag | Value | Why |
| --- | --- | --- |
| `--host` / `--port` | `0.0.0.0` / `8000` | Reachable from compose network / Modal proxy |
| `--max-model-len` | `16384` (knob) | DMR-056: L4-bf16 8B rows cannot hold 32768 — v0.28.0 RAISES at boot (does not shrink-and-warn) |
| `--gpu-memory-utilization` | `0.90` (knob) | Headroom below vLLM's 0.92 default |
| `--max-num-seqs` | `256` (knob) | Same concurrency on any GPU |
| `--no-enable-log-requests` | on | v0.28.0 made request logging opt-in |
| `--revision` / `--quantization` | optional | Weight pin / quantized checkpoints |

---

## Cost (verified 2026-09-09)

| GPU | ≈ $/hr |
| --- | --- |
| L4 | 0.80 |
| A10 | 1.10 |
| A100 40 GB | 2.10 |
| A100 80 GB | 2.50 |
| H100 SXM5 | 3.95 |
| H200 SXM | 4.54 |
| B200 | 6.25 |

Scale-to-zero: no GPU billing while idle. `max_containers=1` by default.
Volumes: $0.09/GiB/mo (first 1 TiB free).

---

## Teardown

```bash
modal app stop sandbox-vllm                  # stop serving (volumes persist)
modal volume ls sandbox-hf-cache             # weights survive
modal volume ls sandbox-vllm-cache           # JIT/CUDA-graph cache
```

---

## Security

- Private endpoint: bearer enforced by vLLM (`MODAL_VLLM_API_TOKEN` → `VLLM_API_KEY`).
- Secrets built at deploy time from local env (`Secret.from_dict`).
- `/health` is deliberately unauthenticated (liveness only).
- `/v1`, `/v2`, `/inference`, `/cohere` require the bearer.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `401` | `VLLM_API_KEY` must equal `MODAL_VLLM_API_TOKEN` |
| First request slow | Pre-warm or raise `MODAL_VLLM_SCALEDOWN_SECONDS` |
| CUDA OOM at boot | Lower `MAX_MODEL_LEN`, quantize, or bigger GPU |
| `ValueError: To serve at least one request with the model's max seq len...` | v0.28.0 admission check: the KV pool can't hold one request at `max_model_len` — cap at 16384 for L4-bf16 8B rows or use an AWQ/FP8 checkpoint (DMR-056) |
| `--disable-log-requests` error | v0.28.0 renamed it; use `--no-enable-log-requests` |
| `Secret.from_local` error | SDK 1.5.5 removed it; this file uses `from_dict` |
| `download_model` cached 0 files | wrong repo id/revision or gated repo without `HF_TOKEN` (DMR-053) |
| cold start takes minutes | expected — masked boot config is printed to the container log; pre-warm + `sandbox-vllm-cache` are the mitigations |
