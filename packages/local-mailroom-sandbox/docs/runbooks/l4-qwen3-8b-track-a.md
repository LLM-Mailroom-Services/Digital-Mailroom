<!-- Generated from config/runbooks/catalog.yaml. Edit the catalog, then: sandbox runbook write -->

# Operator A — 1×L4 Qwen3-8B (contracts → corporate → correspondence)

**id:** `l4-qwen3-8b-track-a` · **family:** `baseline` · **serving:** `baseline`

Track A on the Hermes wallet (hermes-agent-jjb). Same singular L4 / 1-container serving as l4-qwen3-8b. Do not share this profile with Operator B.

Edit [`config/runbooks/catalog.yaml`](../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show l4-qwen3-8b-track-a`.

## Pins (from catalog serving variant)

| Knob | Value |
| --- | --- |
| Model | `Qwen/Qwen3-8B` |
| GPU | `L4` |
| Image | `v0.29.0` |
| max_model_len | `16384` |
| max_num_seqs | `6` |
| max_containers | `1` |
| min_containers | `0` |
| scaledown_seconds | `120` |
| quantization | `(none)` |
| prefix caching / eager | `1 / 1` |

## Suite `run-30-specialists-track-a` (track=a)

Operator A — contracts + corporate_records + correspondence

DMR-075/078 sec/doc bands (L4 $0.80/hr): contracts c=4 + corporate c=4 +
correspondence c=5. Track B (merger c=3 + insurance c=5) stays within ~$0.06
without stacking both heavies (merger+contracts) on one operator.

Ordered configs:

1. `config/runs/run-30-contracts-specialist.yaml`
2. `config/runs/run-30-corporate-records-specialist.yaml`
3. `config/runs/run-30-correspondence-specialist.yaml`

## Per-doc-type posture (live)

| Run | Task | Conc. | max_tokens | max_input_chars | cost_cap | max_wall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `run-30-correspondence-specialist` | `correspondence_specialist` | 5 | 2048 | 12000 | $0.40 | 2400s |
| `run-30-insurance-claims-specialist` | `insurance_claims_specialist` | 5 | 3072 | 13500 | $0.50 | 3000s |
| `run-30-corporate-records-specialist` | `corporate_records_specialist` | 4 | 4096 | 15000 | $0.55 | 3600s |
| `run-30-contracts-specialist` | `contracts_specialist` | 4 | 4096 | 19891 | $0.80 | 4800s |
| `run-30-merger-specialist` | `merger_agreement_specialist` | 3 | 4096 | 19891 | $1.00 | 5400s |

Source: `src/mailroom_sandbox/job/specialist_posture.py`.

## Specialist prompts (eval-environment frozen v1)

| Run | Agent | Local stem | eval-environment key |
| --- | --- | --- | --- |
| `run-30-correspondence-specialist` | `correspondence_specialist` | `correspondence_specialist_simplified` | `correspondence_specialist_v1` |
| `run-30-insurance-claims-specialist` | `insurance_claims_specialist` | `insurance_claims_specialist_simplified` | `insurance_claims_specialist_v1` |
| `run-30-corporate-records-specialist` | `corporate_records_specialist` | `corporate_records_specialist_simplified` | `corporate_records_specialist_v1` |
| `run-30-contracts-specialist` | `contracts_specialist` | `contracts_specialist_v33_simplified` | `contracts_specialist_v1` |
| `run-30-merger-specialist` | `merger_agreement_specialist` | `merger_agreement_specialist_simplified` | `merger_agreement_specialist_v1` |

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# Operator A — 1×L4 Qwen3-8B (contracts → corporate → correspondence)
# sandbox runbook show l4-qwen3-8b-track-a
set -euo pipefail

# serving variant: baseline
# runbook: l4-qwen3-8b-track-a
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B
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
export MODAL_VLLM_QUANTIZATION=""
export MODAL_VLLM_TP_SIZE=1
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current

sandbox metrics estimate-suite --suite track-a

sandbox run benchmark-check --suite track-a

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py

# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

sandbox run suite --suite track-a
# sandbox run suite --suite track-a --execute --job-mode endpoint
for cfg in \
  config/runs/run-30-contracts-specialist.yaml \
  config/runs/run-30-corporate-records-specialist.yaml \
  config/runs/run-30-correspondence-specialist.yaml
do
  sandbox run preflight --config "$cfg" --live
  sandbox run start --config "$cfg" --job-mode endpoint --watch
done

./deploy/teardown_vllm.sh   # ONLY after the last config in this track
```
