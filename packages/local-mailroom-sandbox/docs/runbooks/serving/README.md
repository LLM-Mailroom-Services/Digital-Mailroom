<!-- Generated from config/runbooks/catalog.yaml. Edit the catalog, then: sandbox runbook write -->

# Modal + vLLM serving (default path)

Generated family rollup. Canonical per-id cards live at their catalog paths.

# Modal vLLM — deploy, point, verify, teardown (default path)

**id:** `modal-vllm-serving` · **family:** `serving` · **serving:** `qwen35-9b`

The sandbox default. One Modal L4 serves Qwen/Qwen3.5-9B (online fp8) behind an OpenAI /v1 surface; the host needs no GPU and no Ollama daemon. Pre-warm the weights, deploy once, export VLLM_BASE_URL/VLLM_API_KEY, verify with health, run any eval against the same warm endpoint, then tear it down.

Edit [`config/runbooks/catalog.yaml`](../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show modal-vllm-serving`.

## Pins (from catalog serving variant)

| Knob | Value |
| --- | --- |
| Model | `Qwen/Qwen3.5-9B` |
| GPU | `L4` |
| Image | `v0.29.0` |
| max_model_len | `16384` |
| max_num_seqs | `6` |
| max_containers | `1` |
| min_containers | `0` |
| scaledown_seconds | `120` |
| quantization | `fp8` |
| prefix caching / eager | `1 / 1` |

## Notes

- VLLM_BASE_URL is the FULL base URL: the URL `modal deploy` prints plus /v1. Without /v1 every chat call 404s.
- Export MODAL_WORKSPACE=<workspace slug> instead and the profile derives the same URL; health follows it too.
- VLLM_API_KEY is the same value as MODAL_VLLM_API_TOKEN; the script exports it for you. A right URL with no bearer still returns 401, so export it in any other shell you run evals from.
- One deploy serves every specialist class — do not redeploy between classes. For the 5×30 suite on this endpoint use `sandbox runbook show full`.
- Attended scaledown is 120s. Unattended/overnight: export MODAL_VLLM_SCALEDOWN_SECONDS=600 before deploy.
- Teardown is a runbook step, not an afterthought: ./deploy/teardown_vllm.sh stops the app so scale-to-zero is not the only cost guard. The script leaves it commented: run it by hand after your last eval, so pasting the lifecycle never stops the endpoint before an eval has run.
- Offline or CPU-only work is the explicit opt-out: --profile ollama (or SANDBOX_PROFILE=ollama).

## The default contract

| Piece | Value |
| --- | --- |
| Profile | `modal-vllm` (CLI default, `.env.example`) |
| Mailroom provider | `vllm` (`DEFAULT_PROVIDER`) |
| Endpoint | `https://<workspace>--sandbox-vllm-serve.modal.run/v1` |
| Auth | `VLLM_API_KEY` = `MODAL_VLLM_API_TOKEN` (bearer) |
| Serving shape | one L4, one container, Qwen/Qwen3.5-9B online fp8 (text-only), 16384 ctx, `max_num_seqs` 6 |
| API counterpart | `--profile openrouter` runs `qwen/qwen3.5-9b`, the same weights (`models.yaml` `openrouter_preference`) |
| Cost guard | `min_containers` 0, `scaledown_seconds` 120 (600 unattended), teardown at the end |

`sandbox health` exits 1 with a hint when `VLLM_BASE_URL` is unset — the
profile's static `localhost:8000` value is only a parity fallback, never
the Modal endpoint.

## When to leave this runbook

- More concurrency / longer context: pick the matching `serving` variant
  and the catalog runbook that cites it (`improved-awq-c8`, `grid-2l4`, …).
- The frozen Qwen3-8B eval campaign: `l4-qwen3-8b` (5×30 specialists, bf16 Qwen3-8B on L4).
- Local post-processing only: `--profile ollama` (mock/offline paths do
  not need any endpoint).

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# Modal vLLM — deploy, point, verify, teardown (default path)
# sandbox runbook show modal-vllm-serving
set -euo pipefail

# serving variant: qwen35-9b
# runbook: modal-vllm-serving
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3.5-9B
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_IMAGE_TAG=v0.29.0
export MODAL_VLLM_MAX_MODEL_LEN=16384
export MODAL_VLLM_MAX_NUM_SEQS=6
export MODAL_VLLM_GPU_MEMORY_UTILIZATION=0.90
export MODAL_VLLM_ENABLE_PREFIX_CACHING=1
export MODAL_VLLM_ENFORCE_EAGER=1
export MODAL_VLLM_MAX_CONTAINERS=1
export MODAL_VLLM_MIN_CONTAINERS=0
export MODAL_VLLM_SCALEDOWN_SECONDS=120
export MODAL_VLLM_QUANTIZATION=fp8
export MODAL_VLLM_TP_SIZE=1
export MODAL_VLLM_LIMIT_MM_PER_PROMPT='{"image":0,"video":0,"audio":0}'
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py

# REQUIRED before health (shell or .env): `sandbox health` exits 1 without an endpoint
# VLLM_BASE_URL is the FULL base: deploy output + '/v1'
#   e.g. export VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
#   or: export MODAL_WORKSPACE=<workspace slug>  (the profile derives that URL)
#   (without /v1 every chat call 404s — the profile appends /chat/completions)
export VLLM_API_KEY="$MODAL_VLLM_API_TOKEN"   # bearer this deploy was started with
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

# ./deploy/teardown_vllm.sh   # run by hand ONLY after the last eval on this endpoint
```

---
