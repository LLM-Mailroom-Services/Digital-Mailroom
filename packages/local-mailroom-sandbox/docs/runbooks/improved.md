<!-- Generated from config/runbooks/catalog.yaml. Edit the catalog, then: sandbox runbook write -->

# Improved run configurations

Generated family rollup. Canonical per-id cards live beside this file.

# AWQ on 1×L4 (Qwen3-8B-AWQ, contracts N=20)

**id:** `improved-awq` · **family:** `improved` · **serving:** `awq-16k`

Optional cost-saver. Official Qwen3-8B AWQ is a drop-in Hub id. The DMR-068 accuracy gate (≥1.5× docs/min and ≥98% accuracy) is NOT green in-repo — do not flip the default 5×30 suite. This run YAML still boots at 16384; prefer improved-awq-c8 for the corrected 32768 window.

Edit [`config/runbooks/catalog.yaml`](../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-awq`.

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

./deploy/teardown_vllm.sh   # ONLY after the this run
```

---

# AWQ + 32768 + concurrency 8 (contracts N=20)

**id:** `improved-awq-c8` · **family:** `improved` · **serving:** `awq-32k`

SAND-019 corrected contracts path. Window 32768 clears the 16k 400; run-scoped max_tokens 8192 clears LengthFinish; concurrency 8 on one L4. Same seed-42 draw as run-20-contracts-awq.

Edit [`config/runbooks/catalog.yaml`](../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-awq-c8`.

## Pins (from catalog serving variant)

| Knob | Value |
| --- | --- |
| Model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` |
| Image | `v0.29.0` |
| max_model_len | `32768` |
| max_num_seqs | `6` |
| max_containers | `1` |
| min_containers | `0` |
| scaledown_seconds | `120` |
| quantization | `awq` |
| prefix caching / eager | `1 / 1` |

## Configs

- `config/runs/run-20-contracts-awq-c8.yaml`

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# AWQ + 32768 + concurrency 8 (contracts N=20)
# sandbox runbook show improved-awq-c8
set -euo pipefail

# serving variant: awq-32k
# runbook: improved-awq-c8
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ
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
export MODAL_VLLM_QUANTIZATION=awq
export MODAL_VLLM_TP_SIZE=1
export SANDBOX_AGENT_KNOBS='{"contracts_specialist":{"max_tokens":8192,"max_input_chars":24000}}'
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current
# runbook extra_env (already in the export block above)

# equivalent: eval "$(sandbox modal-matrix env Qwen/Qwen3-8B-AWQ)"

sandbox run benchmark-check --config config/runs/run-20-contracts-awq-c8.yaml

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

sandbox run preflight --config config/runs/run-20-contracts-awq-c8.yaml --live
sandbox run start --config config/runs/run-20-contracts-awq-c8.yaml --job-mode endpoint --watch --force

./deploy/teardown_vllm.sh   # ONLY after the this run
```

---

# AWQ 32768 correspondence N=20 (concurrency 5)

**id:** `improved-correspondence-awq` · **family:** `improved` · **serving:** `awq-32k`

SAND-019 short-doc AWQ path. Same 1×L4 / 1-container topology.

Edit [`config/runbooks/catalog.yaml`](../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-correspondence-awq`.

## Pins (from catalog serving variant)

| Knob | Value |
| --- | --- |
| Model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` |
| Image | `v0.29.0` |
| max_model_len | `32768` |
| max_num_seqs | `6` |
| max_containers | `1` |
| min_containers | `0` |
| scaledown_seconds | `120` |
| quantization | `awq` |
| prefix caching / eager | `1 / 1` |

## Configs

- `config/runs/run-20-correspondence-awq.yaml`

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# AWQ 32768 correspondence N=20 (concurrency 5)
# sandbox runbook show improved-correspondence-awq
set -euo pipefail

# serving variant: awq-32k
# runbook: improved-correspondence-awq
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ
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
export MODAL_VLLM_QUANTIZATION=awq
export MODAL_VLLM_TP_SIZE=1
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current

# equivalent: eval "$(sandbox modal-matrix env Qwen/Qwen3-8B-AWQ)"

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

sandbox run preflight --config config/runs/run-20-correspondence-awq.yaml --live
sandbox run start --config config/runs/run-20-correspondence-awq.yaml --job-mode endpoint --watch

./deploy/teardown_vllm.sh   # ONLY after the this run
```

---

# AWQ 32768 correspondence N=20 (concurrency 8)

**id:** `improved-correspondence-awq-c8` · **family:** `improved` · **serving:** `awq-32k`

Same seed-42 correspondence draw as improved-correspondence-awq (fingerprint 285f423d3708). Only concurrency changes (5 → 8).

Edit [`config/runbooks/catalog.yaml`](../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-correspondence-awq-c8`.

## Pins (from catalog serving variant)

| Knob | Value |
| --- | --- |
| Model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` |
| Image | `v0.29.0` |
| max_model_len | `32768` |
| max_num_seqs | `6` |
| max_containers | `1` |
| min_containers | `0` |
| scaledown_seconds | `120` |
| quantization | `awq` |
| prefix caching / eager | `1 / 1` |

## Configs

- `config/runs/run-20-correspondence-awq-c8.yaml`

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# AWQ 32768 correspondence N=20 (concurrency 8)
# sandbox runbook show improved-correspondence-awq-c8
set -euo pipefail

# serving variant: awq-32k
# runbook: improved-correspondence-awq-c8
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ
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
export MODAL_VLLM_QUANTIZATION=awq
export MODAL_VLLM_TP_SIZE=1
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current

# equivalent: eval "$(sandbox modal-matrix env Qwen/Qwen3-8B-AWQ)"

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

sandbox run preflight --config config/runs/run-20-correspondence-awq-c8.yaml --live
sandbox run start --config config/runs/run-20-correspondence-awq-c8.yaml --job-mode endpoint --watch

./deploy/teardown_vllm.sh   # ONLY after the this run
```

---

# FP16 isolation twin of correspondence AWQ-c8

**id:** `improved-correspondence-fp16-c8` · **family:** `improved` · **serving:** `baseline`

issue #21. Same draw (fingerprint 285f423d3708) and concurrency 8, but Qwen/Qwen3-8B bf16 at 16384. PREPARED ONLY until spend/auth are approved.

Edit [`config/runbooks/catalog.yaml`](../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-correspondence-fp16-c8`.

> **BLOCKED:** spend/auth not approved (issue

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

## Configs

- `config/runs/run-20-correspondence-fp16-c8.yaml`

## Notes

- Confirm lock fingerprint 285f423d3708 before scoring.
- Prompt pin is correspondence_specialist_production (isolation twin), not the simplified catalog stem.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# FP16 isolation twin of correspondence AWQ-c8
# sandbox runbook show improved-correspondence-fp16-c8
set -euo pipefail
echo "BLOCKED: spend/auth not approved (issue" >&2
false   # refuse execution until spend/auth are approved

# serving variant: baseline
# runbook: improved-correspondence-fp16-c8
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

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

sandbox run preflight --config config/runs/run-20-correspondence-fp16-c8.yaml --live
sandbox run start --config config/runs/run-20-correspondence-fp16-c8.yaml --job-mode endpoint --watch

./deploy/teardown_vllm.sh   # ONLY after the this run
```

---

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

---

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

---

# L4 scale-matrix cells (not the singular 1-container path)

**id:** `improved-scale-matrix` · **family:** `improved` · **serving:** `scale-short-doc`

DMR-068 / SAND-022 throughput protocol. These cells pin replica fleets (often 4×L4) and short-doc max_num_seqs=256. GPU cells pending spend.

Edit [`config/runbooks/catalog.yaml`](../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-scale-matrix`.

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

---
