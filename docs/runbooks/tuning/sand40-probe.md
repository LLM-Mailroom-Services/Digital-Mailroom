<!-- Generated from config/runbooks/catalog.yaml. Edit the catalog, then: sandbox runbook write -->

# SAND-40 validation probe (executed 2026-10-01) — n=20 contracts and merger on 2×L4 · 64K YaRN

**id:** `sand40-probe` · **family:** `grid` · **serving:** `grid-awq-2l4-64k`

Spend-gated probe before the SAND-40 scale run. Two nested n=20 draws (the seeded prefix of the SAND-37 2×L4 n=50 contracts and merger documents) on the 64K YaRN engine with the optimized long-document settings. About $0.30–$0.80 GPU. Do not start until that spend is approved.

Edit [`config/runbooks/catalog.yaml`](../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show sand40-probe`.

## Pins (from catalog serving variant)

| Knob | Value |
| --- | --- |
| Model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` |
| Image | `v0.29.0` |
| max_model_len | `65536` |
| max_num_seqs | `16` |
| max_containers | `2` |
| min_containers | `2` |
| scaledown_seconds | `120` |
| quantization | `awq_marlin` |
| prefix caching / eager | `1 / 0` |

## Configs

- `config/runs/sand40-probe-20-contracts-specialist-awq-2l4-64k.yaml`
- `config/runs/sand40-probe-20-merger-specialist-awq-2l4-64k.yaml`

## Per-cell posture (live)

| Run | Task | Conc. | max_tokens | max_input_chars | cost_cap | max_wall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `sand40-probe-20-contracts-specialist-awq-2l4-64k` | `contracts_specialist` | 32 | 6144 | 128000 | $0.80 | 2400s |
| `sand40-probe-20-merger-specialist-awq-2l4-64k` | `merger_agreement_specialist` | 32 | 6144 | 128000 | $1.00 | 3600s |

Source: `src/mailroom_sandbox/job/specialist_posture.py`.

## Notes

- Spend gate: about $0.30–$0.80 at 2 × $0.80/GPU-hr, plus one cold boot. Cost caps are $0.80 (contracts) and $1.00 (merger) and are the abort guard. Needs spend approval before deploy. Modal credentials for the Hermes account are on the operator machine.
- Sample: each probe is the seed-42 prefix of the scored n=50 cell (contracts → grid-50-contracts-specialist-awq-2l4-rerun; merger → grid-50-merger-specialist-awq-2l4). The n=20 set is a subset of those 50 documents.
- Serving is the 64K YaRN deploy (MODAL_VLLM_HF_OVERRIDES). Sampling is native chat-completion fields on the OpenAI client (temperature 0.7, top_p 0.8, top_k 20, presence_penalty 1.0). The LangChain pipeline is not part of this deploy.
- Cards land under reports/SAND-37/probes/<specialist>/. The master card reports them in a matched-document appendix and never pools them into a column.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# SAND-40 validation probe (executed 2026-10-01) — n=20 contracts and merger on 2×L4 · 64K YaRN
# sandbox runbook show sand40-probe
set -euo pipefail

# serving variant: grid-awq-2l4-64k
# runbook: sand40-probe
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_IMAGE_TAG=v0.29.0
export MODAL_VLLM_MAX_MODEL_LEN=65536
export MODAL_VLLM_MAX_NUM_SEQS=16
export MODAL_VLLM_GPU_MEMORY_UTILIZATION=0.90
export MODAL_VLLM_ENABLE_PREFIX_CACHING=1
export MODAL_VLLM_ENFORCE_EAGER=0
export MODAL_VLLM_MAX_CONTAINERS=2
export MODAL_VLLM_MIN_CONTAINERS=2
export MODAL_VLLM_SCALEDOWN_SECONDS=120
export MODAL_VLLM_QUANTIZATION=awq_marlin
export MODAL_VLLM_TP_SIZE=1
export MODAL_VLLM_KV_CACHE_DTYPE=fp8
export MODAL_VLLM_CUDAGRAPH_CAPTURE_SIZES='1,2,4,8,16'
export MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS='{"enable_thinking": false}'
export MODAL_VLLM_MAX_INPUTS=32
export MODAL_VLLM_HF_OVERRIDES='{"rope_parameters": {"factor": 2.0, "original_max_position_embeddings": 32768, "rope_theta": 1000000, "rope_type": "yarn"}}'
export PHOENIX_TRACING=disabled
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current

sandbox run benchmark-check --config config/runs/sand40-probe-20-contracts-specialist-awq-2l4-64k.yaml

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

for cfg in \
  config/runs/sand40-probe-20-contracts-specialist-awq-2l4-64k.yaml \
  config/runs/sand40-probe-20-merger-specialist-awq-2l4-64k.yaml
do
  sandbox run preflight --config "$cfg" --live --force
  sandbox run scrape-metrics --config "$cfg" --label before
  sandbox run start --config "$cfg" --job-mode endpoint --watch
  sandbox run scrape-metrics --config "$cfg" --label after
  sandbox run card --config "$cfg"
done

./deploy/teardown_vllm.sh   # ONLY after this run

sandbox run card --config config/runs/sand40-probe-20-contracts-specialist-awq-2l4-64k.yaml
sandbox run card --config config/runs/sand40-probe-20-merger-specialist-awq-2l4-64k.yaml
```
