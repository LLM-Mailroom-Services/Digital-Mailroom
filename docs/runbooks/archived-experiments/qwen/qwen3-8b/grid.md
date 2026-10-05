<!-- Generated from config/runbooks/catalog.yaml. Edit the catalog, then: sandbox runbook write -->

# Qwen3-8B-AWQ specialist grid (SAND-037)

Generated family rollup. Canonical per-id cards live at their catalog paths.

# Specialist grid — 1×L4 · C8 cells (n=20 and n=50, all five classes)

**id:** `grid-1l4` · **family:** `grid` · **serving:** `grid-awq-1l4`

SAND-037 aligned grid, 1×L4 half: ten Qwen3-8B-AWQ specialist cells on one warm L4 serving the SAND-032 frozen L5 engine (awq_marlin, fp8 KV, CUDA graphs, max_num_seqs 16, thinking off, max_inputs 32) at client concurrency 8. Nested split=all draws, frozen v1 simplified prompts, decode 8192 at temperature 0.7. Deploy once, short classes first, teardown after the last cell.

Edit [`config/runbooks/catalog.yaml`](../../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show grid-1l4`.

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

---

# Specialist grid — 2×L4 · C32 cells (n=20 and n=50, all five classes)

**id:** `grid-2l4` · **family:** `grid` · **serving:** `grid-awq-2l4`

SAND-037 aligned grid, 2×L4 half: ten Qwen3-8B-AWQ specialist cells on one warm two-replica fleet serving the same frozen L5 engine at client concurrency 32 (16 per replica). Same draws, prompts and decode as grid-1l4; only the replica count and concurrency differ.

Edit [`config/runbooks/catalog.yaml`](../../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show grid-2l4`.

## Pins (from catalog serving variant)

| Knob | Value |
| --- | --- |
| Model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` |
| Image | `v0.29.0` |
| max_model_len | `32768` |
| max_num_seqs | `16` |
| max_containers | `2` |
| min_containers | `2` |
| scaledown_seconds | `120` |
| quantization | `awq_marlin` |
| prefix caching / eager | `1 / 0` |

## Configs

- `config/runs/grid-20-correspondence-specialist-awq-2l4.yaml`
- `config/runs/grid-20-insurance-claims-specialist-awq-2l4.yaml`
- `config/runs/grid-20-corporate-records-specialist-awq-2l4.yaml`
- `config/runs/grid-20-contracts-specialist-awq-2l4.yaml`
- `config/runs/grid-20-merger-specialist-awq-2l4.yaml`
- `config/runs/grid-50-correspondence-specialist-awq-2l4.yaml`
- `config/runs/grid-50-insurance-claims-specialist-awq-2l4.yaml`
- `config/runs/grid-50-corporate-records-specialist-awq-2l4.yaml`
- `config/runs/grid-50-contracts-specialist-awq-2l4-rerun.yaml`
- `config/runs/grid-50-merger-specialist-awq-2l4.yaml`

## Per-cell posture (live)

| Run | Task | Conc. | max_tokens | max_input_chars | cost_cap | max_wall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `grid-20-correspondence-specialist-awq-2l4` | `correspondence_specialist` | 32 | 8192 | 12000 | $0.40 | 2400s |
| `grid-20-insurance-claims-specialist-awq-2l4` | `insurance_claims_specialist` | 32 | 8192 | 13500 | $0.50 | 2400s |
| `grid-20-corporate-records-specialist-awq-2l4` | `corporate_records_specialist` | 32 | 8192 | 15000 | $0.50 | 2400s |
| `grid-20-contracts-specialist-awq-2l4` | `contracts_specialist` | 32 | 8192 | 24000 | $0.80 | 3200s |
| `grid-20-merger-specialist-awq-2l4` | `merger_agreement_specialist` | 32 | 8192 | 30000 | $1.00 | 3600s |
| `grid-50-correspondence-specialist-awq-2l4` | `correspondence_specialist` | 32 | 8192 | 12000 | $0.60 | 2400s |
| `grid-50-insurance-claims-specialist-awq-2l4` | `insurance_claims_specialist` | 32 | 8192 | 13500 | $0.80 | 2400s |
| `grid-50-corporate-records-specialist-awq-2l4` | `corporate_records_specialist` | 32 | 8192 | 15000 | $0.80 | 2400s |
| `grid-50-contracts-specialist-awq-2l4-rerun` | `contracts_specialist` | 32 | 8192 | 24000 | $1.20 | 3600s |
| `grid-50-merger-specialist-awq-2l4` | `merger_agreement_specialist` | 32 | 8192 | 30000 | $1.60 | 4000s |

Source: `src/mailroom_sandbox/job/specialist_posture.py`.

## Notes

- Reports: each run brackets start with vLLM /metrics scrapes and writes reports/SAND-37/2L4/<specialist>/<run_id>.card.md + .card.json (score, cost, tokens, throughput, latency, per-replica engine telemetry, errors, per-document rows). The after step writes the finalized reports/SAND-37/2L4/L4x2-SCORE-COST-CARD.md + .json from those cards; commit the SAND-37 tree.
- Spend: likely ≈ $0.55 GPU at 2 × $0.80/hr (≈ 18 min warm, from the S3 walls, plus one cold boot of ~2–4 min on each replica); the ten cost caps sum to $8.20 and are the abort guard. Needs spend approval before deploy.
- Canonical deploy knobs: set -a; eval "$(sandbox run deploy-env --config config/runs/grid-20-correspondence-specialist-awq-2l4.yaml)"; set +a. The export block below is identical.
- MIN=MAX=2 pins both replicas warm from deploy to teardown; per-replica admission is 16 at client concurrency 32.
- Decode is max_tokens 8192 at temperature 0.7 from the posture row; do not raise max_tokens mid-grid. Record any LengthFinishReasonError count as a finding.
- grid-50-contracts-specialist-awq-2l4 (plain awq, temperature 0.1) stays as committed history; the -rerun id is the aligned cell.
- Full cell status and the aligned spec: docs/SPECIALIST-GRID-PLAN.md.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# Specialist grid — 2×L4 · C32 cells (n=20 and n=50, all five classes)
# sandbox runbook show grid-2l4
set -euo pipefail

# serving variant: grid-awq-2l4
# runbook: grid-2l4
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_IMAGE_TAG=v0.29.0
export MODAL_VLLM_MAX_MODEL_LEN=32768
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
export PHOENIX_TRACING=disabled
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current

sandbox run benchmark-check --config config/runs/grid-20-correspondence-specialist-awq-2l4.yaml

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

for cfg in \
  config/runs/grid-20-correspondence-specialist-awq-2l4.yaml \
  config/runs/grid-20-insurance-claims-specialist-awq-2l4.yaml \
  config/runs/grid-20-corporate-records-specialist-awq-2l4.yaml \
  config/runs/grid-20-contracts-specialist-awq-2l4.yaml \
  config/runs/grid-20-merger-specialist-awq-2l4.yaml \
  config/runs/grid-50-correspondence-specialist-awq-2l4.yaml \
  config/runs/grid-50-insurance-claims-specialist-awq-2l4.yaml \
  config/runs/grid-50-corporate-records-specialist-awq-2l4.yaml \
  config/runs/grid-50-contracts-specialist-awq-2l4-rerun.yaml \
  config/runs/grid-50-merger-specialist-awq-2l4.yaml
do
  sandbox run preflight --config "$cfg" --live
  sandbox run scrape-metrics --config "$cfg" --label before
  sandbox run start --config "$cfg" --job-mode endpoint --watch
  sandbox run scrape-metrics --config "$cfg" --label after
  sandbox run card --config "$cfg"
done

./deploy/teardown_vllm.sh   # ONLY after this run

sandbox run card --runbook grid-2l4
sandbox metrics compare --runs grid-20-correspondence-specialist-awq-2l4,grid-20-insurance-claims-specialist-awq-2l4,grid-20-corporate-records-specialist-awq-2l4,grid-20-contracts-specialist-awq-2l4,grid-20-merger-specialist-awq-2l4
sandbox metrics compare --runs grid-50-correspondence-specialist-awq-2l4,grid-50-insurance-claims-specialist-awq-2l4,grid-50-corporate-records-specialist-awq-2l4,grid-50-contracts-specialist-awq-2l4-rerun,grid-50-merger-specialist-awq-2l4
```

---

# SAND-39 — 1×L4 · C8 · n=50 inverse leg of the SAND-37 2×L4 scale-out (five specialists)

**id:** `sand39-1l4-n50` · **family:** `grid` · **serving:** `grid-awq-1l4`

Matched-sample counterpart to SAND-37's 2×L4 · C32 · n=50 half: the same five specialists on the identical n=50 documents (mailroom-dataset @ ed7576b6, seed 42, split=all, one class bucket each), served by ONE warm L4 at client concurrency 8 to match every other 1×L4 experiment. Engine, prompts, decode and temperature are the SAND-37 aligned spec unchanged, so the comparison against 2×L4 · C32 isolates GPU count and concurrency. Results land in the SAND-37 tree and populate the SAND-39 column of the master score & cost card.

Edit [`config/runbooks/catalog.yaml`](../../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show sand39-1l4-n50`.

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

- `config/runs/grid-50-correspondence-specialist-awq-1l4.yaml`
- `config/runs/grid-50-insurance-claims-specialist-awq-1l4.yaml`
- `config/runs/grid-50-corporate-records-specialist-awq-1l4.yaml`
- `config/runs/grid-50-contracts-specialist-awq-1l4.yaml`
- `config/runs/grid-50-merger-specialist-awq-1l4.yaml`

## Per-cell posture (live)

| Run | Task | Conc. | max_tokens | max_input_chars | cost_cap | max_wall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `grid-50-correspondence-specialist-awq-1l4` | `correspondence_specialist` | 8 | 8192 | 12000 | $0.40 | 3600s |
| `grid-50-insurance-claims-specialist-awq-1l4` | `insurance_claims_specialist` | 8 | 8192 | 13500 | $0.50 | 3600s |
| `grid-50-corporate-records-specialist-awq-1l4` | `corporate_records_specialist` | 8 | 8192 | 15000 | $0.50 | 3600s |
| `grid-50-contracts-specialist-awq-1l4` | `contracts_specialist` | 8 | 8192 | 24000 | $0.80 | 4800s |
| `grid-50-merger-specialist-awq-1l4` | `merger_agreement_specialist` | 8 | 8192 | 30000 | $1.00 | 5400s |

Source: `src/mailroom_sandbox/job/specialist_posture.py`.

## Notes

- Matched sample: each config's dataset + prompt blocks are identical to its SAND-37 2×L4 n=50 counterpart, and a local preflight on 2026-09-30 drew the same 50 document ids in the same order for all five classes (contracts against the aligned -2l4-rerun cell).
- Reports: cards land in reports/SAND-37/1L4/<specialist>/grid-50-*-1l4.card.md + .card.json next to the SAND-37 n=20 cells. The after step refreshes 1L4/L4x1-SCORE-COST-CARD.md (n = 50 column) and regenerates reports/SAND-37/SAND-37-MASTER-SCORE-COST-CARD.md, whose SAND-39 column switches from pending to measured. Commit the SAND-37 tree.
- Spend: likely ≈ $0.50 GPU at $0.80/hr (≈ 29 min busy, extrapolated from SAND-37 1×L4 C8 n=20 measured 687 s per 100 documents, plus one cold boot); the five cost caps sum to $3.20 and are the abort guard. Needs spend approval before deploy.
- Record the teardown spend check (Metered Cost / Billed Cost lines) with sandbox run card --record-metered SAND-39 <metered> <billed> --master so the master card's cost accounting carries it.
- Credentials: SAND-038 makes the LangChain specialists (contracts, merger) send the active provider's key; an OPENROUTER_API_KEY in .env no longer reaches the vLLM endpoint.
- Decode is max_tokens 8192 at temperature 0.7 for contracts and merger from the posture row; do not raise max_tokens. A LengthFinishReasonError at 8192 is a recorded finding, not a reason to rerun.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# SAND-39 — 1×L4 · C8 · n=50 inverse leg of the SAND-37 2×L4 scale-out (five specialists)
# sandbox runbook show sand39-1l4-n50
set -euo pipefail

# serving variant: grid-awq-1l4
# runbook: sand39-1l4-n50
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

sandbox run benchmark-check --config config/runs/grid-50-correspondence-specialist-awq-1l4.yaml

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

for cfg in \
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
sandbox run card --record-metered SAND-39 <metered_usd> <billed_usd> --master
sandbox metrics compare --runs grid-50-correspondence-specialist-awq-1l4,grid-50-correspondence-specialist-awq-2l4
sandbox metrics compare --runs grid-50-contracts-specialist-awq-1l4,grid-50-contracts-specialist-awq-2l4-rerun
sandbox metrics compare --runs grid-50-merger-specialist-awq-1l4,grid-50-merger-specialist-awq-2l4
```

---

# SAND-40 validation probe (executed 2026-10-01) — n=20 contracts and merger on 2×L4 · 64K YaRN

**id:** `sand40-probe` · **family:** `grid` · **serving:** `grid-awq-2l4-64k`

Spend-gated probe before the SAND-40 scale run. Two nested n=20 draws (the seeded prefix of the SAND-37 2×L4 n=50 contracts and merger documents) on the 64K YaRN engine with the optimized long-document settings. About $0.30–$0.80 GPU. Do not start until that spend is approved.

Edit [`config/runbooks/catalog.yaml`](../../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show sand40-probe`.

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

---

# SAND-40 scale run — four specialists n=100 + † merger n=50 · 2×L4 · C32 · one 32K deploy

**id:** `sand40` · **family:** `grid` · **serving:** `grid-awq-2l4`

Fills the SAND-40 column of the master score & cost card on one deploy of the SAND-037 2×L4 engine (native 32768 window), no redeploy. Correspondence, insurance claims, corporate records and contracts run at n=100 on the aligned spec unchanged (each draw contains the n=50 documents). Merger runs the same 50 agreements as SAND-37 2×L4 with the optimized † settings (chunked whole-document extraction, MAUD v1 prompt, Qwen3 sampling, 6144 cap, one length re-sample), after a 5-agreement chunk gate.

Edit [`config/runbooks/catalog.yaml`](../../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show sand40`.

## Pins (from catalog serving variant)

| Knob | Value |
| --- | --- |
| Model | `Qwen/Qwen3-8B-AWQ` |
| GPU | `L4` |
| Image | `v0.29.0` |
| max_model_len | `32768` |
| max_num_seqs | `16` |
| max_containers | `2` |
| min_containers | `2` |
| scaledown_seconds | `120` |
| quantization | `awq_marlin` |
| prefix caching / eager | `1 / 0` |

## Configs

- Gate, runs first: `config/runs/sand40-check-5-merger-specialist-awq-2l4.yaml` (`sandbox run card --gate` must pass)
- `config/runs/sand40-100-correspondence-specialist-awq-2l4.yaml`
- `config/runs/sand40-100-insurance-claims-specialist-awq-2l4.yaml`
- `config/runs/sand40-100-corporate-records-specialist-awq-2l4.yaml`
- `config/runs/sand40-100-contracts-specialist-awq-2l4.yaml`
- `config/runs/sand40-50-merger-specialist-awq-2l4.yaml`

## Per-cell posture (live)

| Run | Task | Conc. | max_tokens | max_input_chars | cost_cap | max_wall |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `sand40-100-correspondence-specialist-awq-2l4` | `correspondence_specialist` | 32 | 8192 | 12000 | $1.00 | 3600s |
| `sand40-100-insurance-claims-specialist-awq-2l4` | `insurance_claims_specialist` | 32 | 8192 | 13500 | $1.20 | 3600s |
| `sand40-100-corporate-records-specialist-awq-2l4` | `corporate_records_specialist` | 32 | 8192 | 15000 | $1.20 | 3600s |
| `sand40-100-contracts-specialist-awq-2l4` | `contracts_specialist` | 32 | 8192 | 24000 | $1.20 | 3600s |
| `sand40-50-merger-specialist-awq-2l4` | `merger_agreement_specialist` | 32 | 6144 | 54000 | $2.50 | 5400s |
| `sand40-check-5-merger-specialist-awq-2l4` | `merger_agreement_specialist` | 32 | 6144 | 54000 | $0.40 | 1800s |

Source: `src/mailroom_sandbox/job/specialist_posture.py`.

## Notes

- Spend (estimate): four n=100 cells ≈ 12 min / ≈ $0.30 (SAND-37 2×L4 n=50 walls, doubled); gate ≈ 10–15 min / ≈ $0.20 (one chained agreement sets the wall); † merger n=50 ≈ 40–60 min / ≈ $1.10–1.60 (≈ 115k prompt tokens per agreement through ~8 chunk calls, 32 agreements in flight). Total ≈ $1.60–2.10 plus one cold boot per replica. Cost caps sum to $7.50 including the gate ($0.40). Needs spend approval before deploy.
- The gate runs first: 5 agreements with the † settings, then sandbox run card --gate checks every document is ok and that vLLM accepted every chunk the documents need (extract_chunked skips a rejected chunk silently). On failure the script tears the fleet down and stops; nothing scored has run.
- 32K chunk sizing: max_input_chars 54,000 → 47,000-char windows + 6,500-char overlap, within the posture context-fit guard (2.4 chars/token + 4,000 system tokens + 6,144 output ≤ 32,768). SAND-37 merger text measured ≥ 3.3 chars/token, so real requests stay well under the window.
- Merger stays n=50 (the SAND-37 2×L4 agreements), so the † cell compares like-for-like; the other four classes are n=100. Probe settings that are not used: the 64K YaRN window and the 128,000-char input.
- Cards land in reports/SAND-37/2L4/<specialist>/ (scale cells) and reports/SAND-37/probes/merger_agreement/ (gate). The after step regenerates reports/SAND-37/SAND-37-MASTER-SCORE-COST-CARD.md; its SAND-40 column switches from pending to measured. Commit the SAND-37 tree.
- Record the teardown spend check (Metered Cost / Billed Cost) with sandbox run card --record-metered SAND-40 <metered> <billed> --master.
- Teardown follows the last cell. Do not leave the two-replica fleet warm: min_containers=2 bills both GPUs until teardown.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# SAND-40 scale run — four specialists n=100 + † merger n=50 · 2×L4 · C32 · one 32K deploy
# sandbox runbook show sand40
set -euo pipefail

# serving variant: grid-awq-2l4
# runbook: sand40
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ
export MODAL_VLLM_GPU=L4
export MODAL_VLLM_IMAGE_TAG=v0.29.0
export MODAL_VLLM_MAX_MODEL_LEN=32768
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
export PHOENIX_TRACING=disabled
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current

sandbox run benchmark-check --config config/runs/sand40-100-correspondence-specialist-awq-2l4.yaml

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

# gate: sand40-check-5-merger-specialist-awq-2l4 must pass before the scored cells
sandbox run preflight --config config/runs/sand40-check-5-merger-specialist-awq-2l4.yaml --live --force
sandbox run scrape-metrics --config config/runs/sand40-check-5-merger-specialist-awq-2l4.yaml --label before
sandbox run start --config config/runs/sand40-check-5-merger-specialist-awq-2l4.yaml --job-mode endpoint --watch
sandbox run scrape-metrics --config config/runs/sand40-check-5-merger-specialist-awq-2l4.yaml --label after
if ! sandbox run card --config config/runs/sand40-check-5-merger-specialist-awq-2l4.yaml --gate; then
  echo "gate failed: tearing down without running the scored cells" >&2
  ./deploy/teardown_vllm.sh
  exit 1
fi

for cfg in \
  config/runs/sand40-100-correspondence-specialist-awq-2l4.yaml \
  config/runs/sand40-100-insurance-claims-specialist-awq-2l4.yaml \
  config/runs/sand40-100-corporate-records-specialist-awq-2l4.yaml \
  config/runs/sand40-100-contracts-specialist-awq-2l4.yaml \
  config/runs/sand40-50-merger-specialist-awq-2l4.yaml
do
  sandbox run preflight --config "$cfg" --live --force
  sandbox run scrape-metrics --config "$cfg" --label before
  sandbox run start --config "$cfg" --job-mode endpoint --watch
  sandbox run scrape-metrics --config "$cfg" --label after
  sandbox run card --config "$cfg"
done

./deploy/teardown_vllm.sh   # ONLY after this run

sandbox run card --master
```

---
