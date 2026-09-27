<!-- Generated from config/runbooks/catalog.yaml. Edit the catalog, then: sandbox runbook write -->

# Granite 4.2-8B FP8 on 1×L4 (SAND-027 Leg A swap-in)

**id:** `improved-granite-fp8` · **family:** `improved` · **serving:** `granite-fp8`

Same singular L4 / 1-container topology as the Qwen baseline, swapped to ibm-granite/granite-4.2-8b-fp8 at 32768. Do not edit run-30 YAMLs — live /v1/models probe requires engine.model to match, so copy specs after smoke.

Edit [`config/runbooks/catalog.yaml`](../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-granite-fp8`.

## Pins (from catalog serving variant)

| Knob | Value |
| --- | --- |
| Model | `ibm-granite/granite-4.2-8b-fp8` |
| GPU | `L4` |
| Image | `v0.29.0` |
| max_model_len | `32768` |
| max_num_seqs | `6` |
| max_containers | `1` |
| min_containers | `0` |
| scaledown_seconds | `120` |
| quantization | `compressed-tensors` |
| prefix caching / eager | `1 / 1` |

## Suite `run-30-specialists-full` (track=full)

Single operator — all five run-30 specialists (alternative to A∥B)

Original DMR-076 warm-once path: contracts → merger → corporate →
correspondence → insurance on one Hermes wallet. Use when only one Modal
account is available; otherwise prefer track-a ∥ track-b for parallel wall.

Ordered configs:

1. `config/runs/run-30-contracts-specialist.yaml`
2. `config/runs/run-30-merger-specialist.yaml`
3. `config/runs/run-30-corporate-records-specialist.yaml`
4. `config/runs/run-30-correspondence-specialist.yaml`
5. `config/runs/run-30-insurance-claims-specialist.yaml`

## Deploy smoke

- Confirm /v1/models data[0].id is ibm-granite/granite-4.2-8b-fp8
- Confirm the replica booted at max_model_len=32768 (bf16 Granite 32k fails on 1×L4)
- One structured-output json_object completion succeeds
- Thinking spans are separable (granite_thinking_parser; plugin fallback on v0.29.0)

## Notes

- sandbox run benchmark-check is Qwen-only. Skip it for Granite.
- After smoke, copy run-30-*-specialist.yaml and set engine.model / vllm.max_model_len / quantization to this variant before --live preflight.
- Draw one 100-row bucket per class (seed 42) and slice 20/50 — do not re-draw.
- OpenRouter twin id is ibm-granite/granite-4.2-8b (same string as the HF bf16 repo). Reports must say the Modal leg served -fp8.
- Live deploy + H5 tag decision remain SAND-027-6; this runbook is the operator path, not an authorization to spend.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# Granite 4.2-8B FP8 on 1×L4 (SAND-027 Leg A swap-in)
# sandbox runbook show improved-granite-fp8
set -euo pipefail

# serving variant: granite-fp8
# runbook: improved-granite-fp8
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=ibm-granite/granite-4.2-8b-fp8
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_IMAGE_TAG=v0.29.0
export MODAL_VLLM_MAX_MODEL_LEN=32768
export MODAL_VLLM_MAX_NUM_SEQS=6
export MODAL_VLLM_GPU_MEMORY_UTILIZATION=0.90
export MODAL_VLLM_ENABLE_PREFIX_CACHING=1
export MODAL_VLLM_ENFORCE_EAGER=1
export MODAL_VLLM_MAX_CONTAINERS=1
export MODAL_VLLM_MIN_CONTAINERS=0
export MODAL_VLLM_SCALEDOWN_SECONDS=120
export MODAL_VLLM_QUANTIZATION=compressed-tensors
export MODAL_VLLM_TP_SIZE=1
export MODAL_VLLM_REASONING_PARSER=granite_thinking_parser
export MODAL_VLLM_TOOL_CALL_PARSER=qwen3_coder
export MODAL_VLLM_ENABLE_AUTO_TOOL_CHOICE=1
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current
# runbook extra_env (already in the export block above)

# equivalent: eval "$(sandbox modal-matrix env ibm-granite/granite-4.2-8b-fp8)"

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm
# smoke: Confirm /v1/models data[0].id is ibm-granite/granite-4.2-8b-fp8
# smoke: Confirm the replica booted at max_model_len=32768 (bf16 Granite 32k fails on 1×L4)
# smoke: One structured-output json_object completion succeeds
# smoke: Thinking spans are separable (granite_thinking_parser; plugin fallback on v0.29.0)

./deploy/teardown_vllm.sh   # ONLY after the this run
```
