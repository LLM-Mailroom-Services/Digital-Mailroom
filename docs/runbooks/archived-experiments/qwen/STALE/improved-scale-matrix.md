<!-- Generated from config/runbooks/catalog.yaml. Edit the catalog, then: sandbox runbook write -->

# L4 scale-matrix cells (not the singular 1-container path)

**id:** `improved-scale-matrix` · **family:** `improved` · **serving:** `scale-short-doc`

DMR-068 / SAND-022 throughput protocol. These cells pin replica fleets (often 4×L4) and short-doc max_num_seqs=256. GPU cells pending spend.

Edit [`config/runbooks/catalog.yaml`](../../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-scale-matrix`.

## Pins (from catalog serving variant)

| Knob | Value |
| --- | --- |
| Model | `Qwen/Qwen3-8B` |
| GPU | `L4` |
| Image | `v0.29.0` |
| max_model_len | `16384` |
| max_num_seqs | `256` |
| max_containers | `1` |
| min_containers | `0` |
| scaledown_seconds | `600` |
| quantization | `(none)` |
| prefix caching / eager | `1 / 1` |

## Configs

- `config/runs/scale-c1-4xl4-c16.yaml`
- `config/runs/scale-d1-awq-4xl4-c16.yaml`
- `config/runs/scale-e1-fp8-l4-4xl4-c16.yaml`
- `config/runs/scale-f1-qwen35-9b-fp8-4xl4-c16.yaml`
- `config/runs/scale-g1-qwen35-35b-tp2-1xl4x2-c16.yaml`

## Notes

- See docs/scale-matrix.md for the decision rule (D1 vs C1 AWQ gate).
- Pin MIN_CONTAINERS = MAX_CONTAINERS = R per cell. Teardown after every cell.
- G1 is the only cell that uses GPU=L4:2 + TP (model does not fit one L4).
- Execution pending spend approval — this runbook documents the specs; it does not authorize GPU time.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# L4 scale-matrix cells (not the singular 1-container path)
# sandbox runbook show improved-scale-matrix
set -euo pipefail

# serving variant: scale-short-doc
# runbook: improved-scale-matrix
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_IMAGE_TAG=v0.29.0
export MODAL_VLLM_MAX_MODEL_LEN=16384
export MODAL_VLLM_MAX_NUM_SEQS=256
export MODAL_VLLM_GPU_MEMORY_UTILIZATION=0.90
export MODAL_VLLM_ENABLE_PREFIX_CACHING=1
export MODAL_VLLM_ENFORCE_EAGER=1
export MODAL_VLLM_MAX_CONTAINERS=1
export MODAL_VLLM_MIN_CONTAINERS=0
export MODAL_VLLM_SCALEDOWN_SECONDS=600
export MODAL_VLLM_QUANTIZATION=""
export MODAL_VLLM_TP_SIZE=1
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"
# runbook extra_env (already in the export block above)

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current
```
