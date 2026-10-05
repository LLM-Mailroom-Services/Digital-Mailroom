<!-- Generated from config/runbooks/catalog.yaml. Edit the catalog, then: sandbox runbook write -->

# AWQ on 1×L4 (Qwen3-8B-AWQ, contracts N=20)

**id:** `improved-awq` · **family:** `improved` · **serving:** `awq-16k`

Optional cost-saver. Official Qwen3-8B AWQ is a drop-in Hub id. The DMR-068 accuracy gate (≥1.5× docs/min and ≥98% accuracy) is NOT green in-repo — do not flip the default 5×30 suite. This run YAML still boots at 16384; prefer improved-awq-c8 for the corrected 32768 window.

Edit [`config/runbooks/catalog.yaml`](../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-awq`.

## Pins (from catalog serving variant)

| Knob | Value |
| --- | --- |
| Model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` |
| Image | `v0.29.0` |
| max_model_len | `16384` |
| max_num_seqs | `6` |
| max_containers | `1` |
| min_containers | `0` |
| scaledown_seconds | `120` |
| quantization | `awq` |
| prefix caching / eager | `1 / 1` |

## Configs

- `config/runs/run-20-contracts-awq.yaml`

## Notes

- Keep run-30-*-specialist.yaml on bf16 Qwen3-8B. Copy a YAML if an alternate scorecard needs matching engine.model.
- benchmark-check accepts AWQ as a warning, not an error.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# AWQ on 1×L4 (Qwen3-8B-AWQ, contracts N=20)
# sandbox runbook show improved-awq
set -euo pipefail

# serving variant: awq-16k
# runbook: improved-awq
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ
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
export MODAL_VLLM_QUANTIZATION=awq
export MODAL_VLLM_TP_SIZE=1
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current

# equivalent: eval "$(sandbox modal-matrix env Qwen/Qwen3-8B-AWQ)"

sandbox run benchmark-check --config config/runs/run-20-contracts-awq.yaml

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

sandbox run preflight --config config/runs/run-20-contracts-awq.yaml --live
sandbox run start --config config/runs/run-20-contracts-awq.yaml --job-mode endpoint --watch

./deploy/teardown_vllm.sh   # ONLY after this run
```
