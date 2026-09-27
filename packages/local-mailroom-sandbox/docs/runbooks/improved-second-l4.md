<!-- Generated from config/runbooks/catalog.yaml. Edit the catalog, then: sandbox runbook write -->

# Second L4 — data parallel (still 1 GPU / container)

**id:** `improved-second-l4` · **family:** `improved` · **serving:** `second-l4-dp`

Raise MAX_CONTAINERS to 2. Each replica is a full vLLM on its own L4 with the baseline Qwen3-8B knobs. Modal @web_server round-robins. Do not use GPU=L4:2 + tensor parallel for 8B.

Edit [`config/runbooks/catalog.yaml`](../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-second-l4`.

## Pins (from catalog serving variant)

| Knob | Value |
| --- | --- |
| Model | `Qwen/Qwen3-8B` |
| GPU | `L4` |
| Image | `v0.29.0` |
| max_model_len | `16384` |
| max_num_seqs | `6` |
| max_containers | `2` |
| min_containers | `0` |
| scaledown_seconds | `120` |
| quantization | `(none)` |
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

## Notes

- Per-replica max_num_seqs stays 6 (total admission ≈ 8–12).
- Doubles $/hr while warm. Only raise after measured queueing.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# Second L4 — data parallel (still 1 GPU / container)
# sandbox runbook show improved-second-l4
set -euo pipefail

# serving variant: second-l4-dp
# runbook: improved-second-l4
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_IMAGE_TAG=v0.29.0
export MODAL_VLLM_MAX_MODEL_LEN=16384
export MODAL_VLLM_MAX_NUM_SEQS=6
export MODAL_VLLM_GPU_MEMORY_UTILIZATION=0.90
export MODAL_VLLM_ENABLE_PREFIX_CACHING=1
export MODAL_VLLM_ENFORCE_EAGER=1
export MODAL_VLLM_MAX_CONTAINERS=2
export MODAL_VLLM_MIN_CONTAINERS=0
export MODAL_VLLM_SCALEDOWN_SECONDS=120
export MODAL_VLLM_QUANTIZATION=""
export MODAL_VLLM_TP_SIZE=1
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current

sandbox metrics estimate-suite --suite full

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

sandbox run suite --suite full
# sandbox run suite --suite full --execute --job-mode endpoint
for cfg in \
  config/runs/run-30-contracts-specialist.yaml \
  config/runs/run-30-merger-specialist.yaml \
  config/runs/run-30-corporate-records-specialist.yaml \
  config/runs/run-30-correspondence-specialist.yaml \
  config/runs/run-30-insurance-claims-specialist.yaml
do
  sandbox run preflight --config "$cfg" --live
  sandbox run start --config "$cfg" --job-mode endpoint --watch
done

./deploy/teardown_vllm.sh   # ONLY after the last config in this track
```
