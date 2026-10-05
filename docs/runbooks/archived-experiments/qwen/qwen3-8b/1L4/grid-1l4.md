<!-- Generated from config/runbooks/catalog.yaml. Edit the catalog, then: sandbox runbook write -->

# Specialist grid — 1×L4 · C8 cells (n=20 and n=50, all five classes)

**id:** `grid-1l4` · **family:** `grid` · **serving:** `grid-awq-1l4`

SAND-037 aligned grid, 1×L4 half: ten Qwen3-8B-AWQ specialist cells on one warm L4 serving the SAND-032 frozen L5 engine (awq_marlin, fp8 KV, CUDA graphs, max_num_seqs 16, thinking off, max_inputs 32) at client concurrency 8. Nested split=all draws, frozen v1 simplified prompts, decode 8192 at temperature 0.7. Deploy once, short classes first, teardown after the last cell.

Edit [`config/runbooks/catalog.yaml`](../../../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show grid-1l4`.

## Pins (from catalog serving variant)

| Knob | Value |
| --- | --- |
| Model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` |
| Image | `v0.29.0` |
| max_model_len | `32768` |
| max_num_seqs | `16` |
| max_containers | `1` |
| min_containers | `1` |
| scaledown_seconds | `120` |
| quantization | `awq_marlin` |
| prefix caching / eager | `1 / 0` |

## Configs

- `config/runs/grid-20-correspondence-specialist-awq-1l4.yaml`
- `config/runs/grid-20-insurance-claims-specialist-awq-1l4.yaml`
- `config/runs/grid-20-corporate-records-specialist-awq-1l4.yaml`
- `config/runs/grid-20-contracts-specialist-awq-1l4.yaml`
- `config/runs/grid-20-merger-specialist-awq-1l4-rerun.yaml`
- `config/runs/grid-50-correspondence-specialist-awq-1l4.yaml`
- `config/runs/grid-50-insurance-claims-specialist-awq-1l4.yaml`
- `config/runs/grid-50-corporate-records-specialist-awq-1l4.yaml`
- `config/runs/grid-50-contracts-specialist-awq-1l4.yaml`
- `config/runs/grid-50-merger-specialist-awq-1l4.yaml`

## Per-cell posture (live)

| Run | Task | Conc. | max_tokens | max_input_chars | cost_cap | max_wall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `grid-20-correspondence-specialist-awq-1l4` | `correspondence_specialist` | 8 | 8192 | 12000 | $0.30 | 2400s |
| `grid-20-insurance-claims-specialist-awq-1l4` | `insurance_claims_specialist` | 8 | 8192 | 13500 | $0.40 | 2400s |
| `grid-20-corporate-records-specialist-awq-1l4` | `corporate_records_specialist` | 8 | 8192 | 15000 | $0.40 | 2400s |
| `grid-20-contracts-specialist-awq-1l4` | `contracts_specialist` | 8 | 8192 | 24000 | $0.70 | 3600s |
| `grid-20-merger-specialist-awq-1l4-rerun` | `merger_agreement_specialist` | 8 | 8192 | 30000 | $0.70 | 3600s |
| `grid-50-correspondence-specialist-awq-1l4` | `correspondence_specialist` | 8 | 8192 | 12000 | $0.40 | 3600s |
| `grid-50-insurance-claims-specialist-awq-1l4` | `insurance_claims_specialist` | 8 | 8192 | 13500 | $0.50 | 3600s |
| `grid-50-corporate-records-specialist-awq-1l4` | `corporate_records_specialist` | 8 | 8192 | 15000 | $0.50 | 3600s |
| `grid-50-contracts-specialist-awq-1l4` | `contracts_specialist` | 8 | 8192 | 24000 | $0.80 | 4800s |
| `grid-50-merger-specialist-awq-1l4` | `merger_agreement_specialist` | 8 | 8192 | 30000 | $1.00 | 5400s |

Source: `src/mailroom_sandbox/job/specialist_posture.py`.

## Notes

- Reports: each run brackets start with vLLM /metrics scrapes and writes reports/SAND-37/1L4/<specialist>/<run_id>.card.md + .card.json (score, cost, tokens, throughput, latency, per-replica engine telemetry, errors, per-document rows). The after step writes the finalized reports/SAND-37/1L4/L4x1-SCORE-COST-CARD.md + .json from those cards; commit the SAND-37 tree.
- Spend: likely ≈ $0.80 GPU at $0.80/hr (≈ 1 h warm: S3 per-L4 throughput on the same engine, scaled by the 0.7× S2a measured at C8 on one L4); the ten cost caps sum to $5.70 and are the abort guard. Needs spend approval before deploy.
- Canonical deploy knobs: set -a; eval "$(sandbox run deploy-env --config config/runs/grid-20-correspondence-specialist-awq-1l4.yaml)"; set +a. The export block below is identical (runbook check enforces it) and benchmark-check fails on any shell drift.
- Decode is max_tokens 8192 at temperature 0.7, applied from the specialist_posture grid row via SANDBOX_AGENT_KNOBS at start; do not export SANDBOX_AGENT_KNOBS by hand and do not raise max_tokens. A LengthFinishReasonError at 8192 is a runaway loop, not a long answer (longest successful output on record: 4,055 tokens).
- preflight --force archives any earlier generation of the same run_id (the serialized grid-50-contracts-specialist-awq-1l4 attempt, locked on the old spec) and re-locks; start then resumes the fresh lock.
- grid-20-merger-specialist-awq-1l4 and its -retry leg stay as committed history; the -rerun id is the aligned cell.
- Full cell status and the aligned spec: docs/SPECIALIST-GRID-PLAN.md.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# Specialist grid — 1×L4 · C8 cells (n=20 and n=50, all five classes)
# sandbox runbook show grid-1l4
set -euo pipefail

# serving variant: grid-awq-1l4
# runbook: grid-1l4
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_IMAGE_TAG=v0.29.0
export MODAL_VLLM_MAX_MODEL_LEN=32768
export MODAL_VLLM_MAX_NUM_SEQS=16
export MODAL_VLLM_GPU_MEMORY_UTILIZATION=0.90
export MODAL_VLLM_ENABLE_PREFIX_CACHING=1
export MODAL_VLLM_ENFORCE_EAGER=0
export MODAL_VLLM_MAX_CONTAINERS=1
export MODAL_VLLM_MIN_CONTAINERS=1
export MODAL_VLLM_SCALEDOWN_SECONDS=120
export MODAL_VLLM_QUANTIZATION=awq_marlin
export MODAL_VLLM_TP_SIZE=1
export MODAL_VLLM_KV_CACHE_DTYPE=fp8
export MODAL_VLLM_CUDAGRAPH_CAPTURE_SIZES='1,2,4,8,16'
export MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS='{"enable_thinking": false}'
export MODAL_VLLM_MAX_INPUTS=32
export PHOENIX_TRACING=disabled
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current

sandbox run benchmark-check --config config/runs/grid-20-correspondence-specialist-awq-1l4.yaml

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

for cfg in \
  config/runs/grid-20-correspondence-specialist-awq-1l4.yaml \
  config/runs/grid-20-insurance-claims-specialist-awq-1l4.yaml \
  config/runs/grid-20-corporate-records-specialist-awq-1l4.yaml \
  config/runs/grid-20-contracts-specialist-awq-1l4.yaml \
  config/runs/grid-20-merger-specialist-awq-1l4-rerun.yaml \
  config/runs/grid-50-correspondence-specialist-awq-1l4.yaml \
  config/runs/grid-50-insurance-claims-specialist-awq-1l4.yaml \
  config/runs/grid-50-corporate-records-specialist-awq-1l4.yaml \
  config/runs/grid-50-contracts-specialist-awq-1l4.yaml \
  config/runs/grid-50-merger-specialist-awq-1l4.yaml
do
  sandbox run preflight --config "$cfg" --live --force
  sandbox run scrape-metrics --config "$cfg" --label before
  sandbox run start --config "$cfg" --job-mode endpoint --watch
  sandbox run scrape-metrics --config "$cfg" --label after
  sandbox run card --config "$cfg"
done

./deploy/teardown_vllm.sh   # ONLY after this run

sandbox run card --runbook grid-1l4
sandbox metrics compare --runs grid-20-correspondence-specialist-awq-1l4,grid-20-insurance-claims-specialist-awq-1l4,grid-20-corporate-records-specialist-awq-1l4,grid-20-contracts-specialist-awq-1l4,grid-20-merger-specialist-awq-1l4-rerun
sandbox metrics compare --runs grid-50-correspondence-specialist-awq-1l4,grid-50-insurance-claims-specialist-awq-1l4,grid-50-corporate-records-specialist-awq-1l4,grid-50-contracts-specialist-awq-1l4,grid-50-merger-specialist-awq-1l4
```
