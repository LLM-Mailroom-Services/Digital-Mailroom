<!-- Generated from config/runbooks/catalog.yaml. Edit the catalog, then: sandbox runbook write -->

# SAND-042 paired concurrency × fleet grid (n=50, five specialists)

Generated family rollup. Canonical per-id cards live at their catalog paths.

# SAND-042 — 1×L4 · client concurrency 8 · n=50 × 5 specialists (paired)

**id:** `sand42-1l4-c8` · **family:** `sand42` · **serving:** `grid-awq-1l4`

One warm L4 serving the SAND-037 frozen L5 engine (awq_marlin, fp8 KV, CUDA graphs, max_num_seqs 16, thinking off, max_inputs 32) at client concurrency 8. Five specialists, n=50 each, on ONE subclass-stratified draw (every doc sub-type of every class represented, proportional, min 1). v1 simplified stems only. Deploy once, chain all five, teardown after the last. Container GPU telemetry (nvidia-smi util/power/temp/mem) is sampled inside the serving replica for the whole cell and pulled onto each run card.

Edit [`config/runbooks/catalog.yaml`](../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show sand42-1l4-c8`.

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

- `config/runs/sand42-50-correspondence-specialist-awq-1l4-c8.yaml`
- `config/runs/sand42-50-insurance-claims-specialist-awq-1l4-c8.yaml`
- `config/runs/sand42-50-corporate-records-specialist-awq-1l4-c8.yaml`
- `config/runs/sand42-50-contracts-specialist-awq-1l4-c8.yaml`
- `config/runs/sand42-50-merger-specialist-awq-1l4-c8.yaml`

## Notes

- Reports: each run writes reports/SAND42/1L4-c8/<specialist>/<run_id>.card.md + .card.json; the after step writes reports/SAND42/1L4-c8/SAND42-1L4-C8-SCORE-COST-CARD.md + .json from those cards. Commit the SAND42 tree.
- Spend (estimate): short classes ~5 min each; contracts ~18 min / ~$0.26 (chunked, 50->85 calls); merger ~1.3 h / ~$1.04 (chunked, MEASURED by the 5-document probe: 438 s warm for 1,702,602 chars, scaled 10.66x to the full 18,160,427-char draw). The five cost caps sum to $4.15 and are the abort guard. Needs spend approval before deploy.
- Canonical deploy knobs: set -a; eval "$(sandbox run deploy-env --config config/runs/sand42-50-correspondence-specialist-awq-1l4-c8.yaml)"; set +a. MODAL_VLLM_TELEMETRY_LABEL is part of that block (one label per cell).
- Decode: max_tokens 8192 at temperature 0.7 for contracts, 6144 for merger (SAND-040 optimised: top_p 0.8 / presence 1.0 / one length re-sample), 0.1 elsewhere. Contracts and merger run WHOLE-DOCUMENT CHUNKED extraction — the old head+tail cap dropped 62 % of contract and 93 % of merger text, and merger MAUD accuracy measured 0.0 on that truncated arm with 3/50 hard length failures. Do not raise max_tokens.
- MIN=MAX=1 pins the single replica warm from deploy to teardown, so the whole cell pays one cold boot.
- Pairing: the five draws are identical to the other three cells (same strata block, same seed 42, same revision). Do not edit the dataset block of one cell without the others.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# SAND-042 — 1×L4 · client concurrency 8 · n=50 × 5 specialists (paired)
# sandbox runbook show sand42-1l4-c8
set -euo pipefail

# serving variant: grid-awq-1l4
# runbook: sand42-1l4-c8
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
export MODAL_VLLM_TELEMETRY_LABEL=sand42-1l4-c8
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current
# runbook extra_env (already in the export block above)

sandbox run benchmark-check --config config/runs/sand42-50-correspondence-specialist-awq-1l4-c8.yaml

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# VLLM_BASE_URL is the FULL base: deploy output + '/v1'
#   e.g. export VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
#   (without /v1 every chat call 404s — the profile appends /chat/completions)
# export VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

# SAND-047: sample /metrics MID-RUN every $MIDRUN_INTERVAL seconds.
# The before/after scrapes fire at each run's DRAINED EDGES, where
# kv_cache_usage_perc gauges a pre-allocated cache with no live sequences
# and therefore reads 0 by construction — a mid sample is the only source.
# It goes through `scrape-metrics` on purpose: that also preserves the
# VERBATIM exporter text (~120 families) at the mid point, and appends
# every sample to vllm_metrics_mid.series.jsonl so the card reports the
# run's MAXIMUM instead of whichever probe happened to run last.
MIDRUN_INTERVAL="${MIDRUN_INTERVAL:-30}"
MIDRUN_CFG_FILE="$HOME/.sand42-1l4-c8-active-cfg"
echo config/runs/sand42-50-correspondence-specialist-awq-1l4-c8.yaml > "$MIDRUN_CFG_FILE"
while :; do
  cfg="$(cat "$MIDRUN_CFG_FILE" 2>/dev/null || true)"
  [ -n "$cfg" ] && sandbox run scrape-metrics --config "$cfg" --label mid || true
  sleep "$MIDRUN_INTERVAL"
done >>"$HOME/sand42-1l4-c8-midrun.log" 2>&1 &
MIDRUN_PID=$!
trap 'kill "$MIDRUN_PID" 2>/dev/null || true' EXIT

for cfg in \
  config/runs/sand42-50-correspondence-specialist-awq-1l4-c8.yaml \
  config/runs/sand42-50-insurance-claims-specialist-awq-1l4-c8.yaml \
  config/runs/sand42-50-corporate-records-specialist-awq-1l4-c8.yaml \
  config/runs/sand42-50-contracts-specialist-awq-1l4-c8.yaml \
  config/runs/sand42-50-merger-specialist-awq-1l4-c8.yaml
do
  sandbox run preflight --config "$cfg" --live --force
  sandbox run scrape-metrics --config "$cfg" --label before
  echo "$cfg" > "$HOME/.sand42-1l4-c8-active-cfg"
  sandbox run start --config "$cfg" --job-mode endpoint --watch
  sandbox run scrape-metrics --config "$cfg" --label after
  .venv/bin/python scripts/sand42/midrun_kv.py fold --cell 1l4-c8 >/dev/null 2>&1 || true
  sandbox run card --config "$cfg"
done

./deploy/teardown_vllm.sh   # ONLY after this run

sandbox run card --runbook sand42-1l4-c8
sandbox metrics compare --runs sand42-50-correspondence-specialist-awq-1l4-c8,sand42-50-insurance-claims-specialist-awq-1l4-c8,sand42-50-corporate-records-specialist-awq-1l4-c8,sand42-50-contracts-specialist-awq-1l4-c8,sand42-50-merger-specialist-awq-1l4-c8
```

---

# SAND-042 — 1×L4 · client concurrency 16 · n=50 × 5 specialists (paired)

**id:** `sand42-1l4-c16` · **family:** `sand42` · **serving:** `grid-awq-1l4`

The concurrency-16 twin of sand42-1l4-c8: identical engine, prompts, decode, documents and one-cold-boot chaining; only the client concurrency differs (8 → 16 on the same single L4). This is the cell that shows whether an L4 has batching headroom above C8, at the same GPU count.

Edit [`config/runbooks/catalog.yaml`](../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show sand42-1l4-c16`.

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

- `config/runs/sand42-50-correspondence-specialist-awq-1l4-c16.yaml`
- `config/runs/sand42-50-insurance-claims-specialist-awq-1l4-c16.yaml`
- `config/runs/sand42-50-corporate-records-specialist-awq-1l4-c16.yaml`
- `config/runs/sand42-50-contracts-specialist-awq-1l4-c16.yaml`
- `config/runs/sand42-50-merger-specialist-awq-1l4-c16.yaml`

## Notes

- Reports: reports/SAND42/1L4-c16/<specialist>/<run_id>.card.* then the after step writes reports/SAND42/1L4-c16/SAND42-1L4-C16-SCORE-COST-CARD.md + .json.
- Spend (estimate): short classes ~5 min each; contracts ~18 min / ~$0.26 (chunked, 50->85 calls); merger ~1.3 h / ~$1.04 (chunked, MEASURED by the 5-document probe: 438 s warm for 1,702,602 chars, scaled 10.66x to the full 18,160,427-char draw). The five cost caps sum to $4.15 and are the abort guard. Needs spend approval before deploy.
- C16 on one L4 is the only posture here that exceeds the SAND-037 grid's C8; per-replica admission stays max_num_seqs 16, so C16 is exactly the admission cap. Watch vLLM preemptions and the KV-cache usage scrape on the long classes.
- Decode: max_tokens 8192 at temperature 0.7 for contracts, 6144 for merger (SAND-040 optimised: top_p 0.8 / presence 1.0 / one length re-sample), 0.1 elsewhere. Contracts and merger run WHOLE-DOCUMENT CHUNKED extraction — the old head+tail cap dropped 62 % of contract and 93 % of merger text, and merger MAUD accuracy measured 0.0 on that truncated arm with 3/50 hard length failures. Do not raise max_tokens.
- Pairing: identical draws to the other three cells. Compare against sand42-1l4-c8 (same GPU count, different concurrency) — that pair isolates concurrency alone.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# SAND-042 — 1×L4 · client concurrency 16 · n=50 × 5 specialists (paired)
# sandbox runbook show sand42-1l4-c16
set -euo pipefail

# serving variant: grid-awq-1l4
# runbook: sand42-1l4-c16
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
export MODAL_VLLM_TELEMETRY_LABEL=sand42-1l4-c16
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current
# runbook extra_env (already in the export block above)

sandbox run benchmark-check --config config/runs/sand42-50-correspondence-specialist-awq-1l4-c16.yaml

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# VLLM_BASE_URL is the FULL base: deploy output + '/v1'
#   e.g. export VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
#   (without /v1 every chat call 404s — the profile appends /chat/completions)
# export VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

# SAND-047: sample /metrics MID-RUN every $MIDRUN_INTERVAL seconds.
# The before/after scrapes fire at each run's DRAINED EDGES, where
# kv_cache_usage_perc gauges a pre-allocated cache with no live sequences
# and therefore reads 0 by construction — a mid sample is the only source.
# It goes through `scrape-metrics` on purpose: that also preserves the
# VERBATIM exporter text (~120 families) at the mid point, and appends
# every sample to vllm_metrics_mid.series.jsonl so the card reports the
# run's MAXIMUM instead of whichever probe happened to run last.
MIDRUN_INTERVAL="${MIDRUN_INTERVAL:-30}"
MIDRUN_CFG_FILE="$HOME/.sand42-1l4-c16-active-cfg"
echo config/runs/sand42-50-correspondence-specialist-awq-1l4-c16.yaml > "$MIDRUN_CFG_FILE"
while :; do
  cfg="$(cat "$MIDRUN_CFG_FILE" 2>/dev/null || true)"
  [ -n "$cfg" ] && sandbox run scrape-metrics --config "$cfg" --label mid || true
  sleep "$MIDRUN_INTERVAL"
done >>"$HOME/sand42-1l4-c16-midrun.log" 2>&1 &
MIDRUN_PID=$!
trap 'kill "$MIDRUN_PID" 2>/dev/null || true' EXIT

for cfg in \
  config/runs/sand42-50-correspondence-specialist-awq-1l4-c16.yaml \
  config/runs/sand42-50-insurance-claims-specialist-awq-1l4-c16.yaml \
  config/runs/sand42-50-corporate-records-specialist-awq-1l4-c16.yaml \
  config/runs/sand42-50-contracts-specialist-awq-1l4-c16.yaml \
  config/runs/sand42-50-merger-specialist-awq-1l4-c16.yaml
do
  sandbox run preflight --config "$cfg" --live --force
  sandbox run scrape-metrics --config "$cfg" --label before
  echo "$cfg" > "$HOME/.sand42-1l4-c16-active-cfg"
  sandbox run start --config "$cfg" --job-mode endpoint --watch
  sandbox run scrape-metrics --config "$cfg" --label after
  .venv/bin/python scripts/sand42/midrun_kv.py fold --cell 1l4-c16 >/dev/null 2>&1 || true
  sandbox run card --config "$cfg"
done

./deploy/teardown_vllm.sh   # ONLY after this run

sandbox run card --runbook sand42-1l4-c16
sandbox metrics compare --runs sand42-50-correspondence-specialist-awq-1l4-c16,sand42-50-insurance-claims-specialist-awq-1l4-c16,sand42-50-corporate-records-specialist-awq-1l4-c16,sand42-50-contracts-specialist-awq-1l4-c16,sand42-50-merger-specialist-awq-1l4-c16
```

---

# SAND-042 — 2×L4 · client concurrency 8 (4 per replica) · n=50 × 5 specialists (paired)

**id:** `sand42-2l4-c8` · **family:** `sand42` · **serving:** `grid-awq-2l4`

Two replicas (MIN=MAX=2, one warm fleet, one cold boot per replica) at client concurrency 8 split equally — 4 in flight per replica. Same engine, prompts, decode and documents as the 1×L4 cells. The 2×L4 cells are not a per-replica-load twin of the 1×L4 cells (C8/2 = 4); the matched-load pairs in this grid are 1×L4 C8 vs 2×L4 C16 and 1×L4 C16 vs 2×L4 C32 (8 and 16 per replica each).

Edit [`config/runbooks/catalog.yaml`](../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show sand42-2l4-c8`.

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

- `config/runs/sand42-50-correspondence-specialist-awq-2l4-c8.yaml`
- `config/runs/sand42-50-insurance-claims-specialist-awq-2l4-c8.yaml`
- `config/runs/sand42-50-corporate-records-specialist-awq-2l4-c8.yaml`
- `config/runs/sand42-50-contracts-specialist-awq-2l4-c8.yaml`
- `config/runs/sand42-50-merger-specialist-awq-2l4-c8.yaml`

## Notes

- Reports: reports/SAND42/2L4-c8/<specialist>/<run_id>.card.* then the after step writes reports/SAND42/2L4-c8/SAND42-2L4-C8-SCORE-COST-CARD.md + .json.
- Spend (estimate): as the 1xL4 cell, billed on two GPUs; merger ~39 min wall at the same ~1.30 GPU-hours. The five cost caps sum to $6.20 and are the abort guard. Needs spend approval before deploy.
- Client concurrency is split equally across replicas: 8 → 4 per replica. Modal round-robins, so per-replica load is 4; measure the split with the per-replica /metrics scrape (SAND-040 saw bursty affinity at C32).
- MIN=MAX=2 keeps both replicas warm across all five classes. Teardown only after the fifth: two warm replicas bill two GPUs.
- Decode: max_tokens 8192 at temperature 0.7 for contracts, 6144 for merger (SAND-040 optimised: top_p 0.8 / presence 1.0 / one length re-sample), 0.1 elsewhere. Contracts and merger run WHOLE-DOCUMENT CHUNKED extraction — the old head+tail cap dropped 62 % of contract and 93 % of merger text, and merger MAUD accuracy measured 0.0 on that truncated arm with 3/50 hard length failures. Do not raise max_tokens.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# SAND-042 — 2×L4 · client concurrency 8 (4 per replica) · n=50 × 5 specialists (paired)
# sandbox runbook show sand42-2l4-c8
set -euo pipefail

# serving variant: grid-awq-2l4
# runbook: sand42-2l4-c8
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
export MODAL_VLLM_TELEMETRY_LABEL=sand42-2l4-c8
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current
# runbook extra_env (already in the export block above)

sandbox run benchmark-check --config config/runs/sand42-50-correspondence-specialist-awq-2l4-c8.yaml

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# VLLM_BASE_URL is the FULL base: deploy output + '/v1'
#   e.g. export VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
#   (without /v1 every chat call 404s — the profile appends /chat/completions)
# export VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

# SAND-047: sample /metrics MID-RUN every $MIDRUN_INTERVAL seconds.
# The before/after scrapes fire at each run's DRAINED EDGES, where
# kv_cache_usage_perc gauges a pre-allocated cache with no live sequences
# and therefore reads 0 by construction — a mid sample is the only source.
# It goes through `scrape-metrics` on purpose: that also preserves the
# VERBATIM exporter text (~120 families) at the mid point, and appends
# every sample to vllm_metrics_mid.series.jsonl so the card reports the
# run's MAXIMUM instead of whichever probe happened to run last.
MIDRUN_INTERVAL="${MIDRUN_INTERVAL:-30}"
MIDRUN_CFG_FILE="$HOME/.sand42-2l4-c8-active-cfg"
echo config/runs/sand42-50-correspondence-specialist-awq-2l4-c8.yaml > "$MIDRUN_CFG_FILE"
while :; do
  cfg="$(cat "$MIDRUN_CFG_FILE" 2>/dev/null || true)"
  [ -n "$cfg" ] && sandbox run scrape-metrics --config "$cfg" --label mid || true
  sleep "$MIDRUN_INTERVAL"
done >>"$HOME/sand42-2l4-c8-midrun.log" 2>&1 &
MIDRUN_PID=$!
trap 'kill "$MIDRUN_PID" 2>/dev/null || true' EXIT

for cfg in \
  config/runs/sand42-50-correspondence-specialist-awq-2l4-c8.yaml \
  config/runs/sand42-50-insurance-claims-specialist-awq-2l4-c8.yaml \
  config/runs/sand42-50-corporate-records-specialist-awq-2l4-c8.yaml \
  config/runs/sand42-50-contracts-specialist-awq-2l4-c8.yaml \
  config/runs/sand42-50-merger-specialist-awq-2l4-c8.yaml
do
  sandbox run preflight --config "$cfg" --live --force
  sandbox run scrape-metrics --config "$cfg" --label before
  echo "$cfg" > "$HOME/.sand42-2l4-c8-active-cfg"
  sandbox run start --config "$cfg" --job-mode endpoint --watch
  sandbox run scrape-metrics --config "$cfg" --label after
  .venv/bin/python scripts/sand42/midrun_kv.py fold --cell 2l4-c8 >/dev/null 2>&1 || true
  sandbox run card --config "$cfg"
done

./deploy/teardown_vllm.sh   # ONLY after this run

sandbox run card --runbook sand42-2l4-c8
sandbox metrics compare --runs sand42-50-correspondence-specialist-awq-2l4-c8,sand42-50-insurance-claims-specialist-awq-2l4-c8,sand42-50-corporate-records-specialist-awq-2l4-c8,sand42-50-contracts-specialist-awq-2l4-c8,sand42-50-merger-specialist-awq-2l4-c8
```

---

# SAND-042 — 2×L4 · client concurrency 16 (8 per replica) · n=50 × 5 specialists (paired)

**id:** `sand42-2l4-c16` · **family:** `sand42` · **serving:** `grid-awq-2l4`

Two replicas at client concurrency 16 split equally — 8 in flight per replica, which is the same per-replica load as 1×L4 C8. That pair (1×L4 C8 vs 2×L4 C16) is the grid's clean matched-load scale-out contrast: same per-replica load, double the GPUs.

Edit [`config/runbooks/catalog.yaml`](../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show sand42-2l4-c16`.

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

- `config/runs/sand42-50-correspondence-specialist-awq-2l4-c16.yaml`
- `config/runs/sand42-50-insurance-claims-specialist-awq-2l4-c16.yaml`
- `config/runs/sand42-50-corporate-records-specialist-awq-2l4-c16.yaml`
- `config/runs/sand42-50-contracts-specialist-awq-2l4-c16.yaml`
- `config/runs/sand42-50-merger-specialist-awq-2l4-c16.yaml`

## Notes

- Reports: reports/SAND42/2L4-c16/<specialist>/<run_id>.card.* then the after step writes reports/SAND42/2L4-c16/SAND42-2L4-C16-SCORE-COST-CARD.md + .json.
- Spend (estimate): as the 1xL4 cell, billed on two GPUs; merger ~39 min wall at the same ~1.30 GPU-hours. The five cost caps sum to $6.20 and are the abort guard. Needs spend approval before deploy.
- Client concurrency is split equally across replicas: 16 → 8 per replica. This is the matched-load twin of sand42-1l4-c8 (8 per replica on one GPU).
- MIN=MAX=2 keeps both replicas warm across all five classes; teardown only after the fifth.
- Decode: max_tokens 8192 at temperature 0.7 for contracts, 6144 for merger (SAND-040 optimised: top_p 0.8 / presence 1.0 / one length re-sample), 0.1 elsewhere. Contracts and merger run WHOLE-DOCUMENT CHUNKED extraction — the old head+tail cap dropped 62 % of contract and 93 % of merger text, and merger MAUD accuracy measured 0.0 on that truncated arm with 3/50 hard length failures. Do not raise max_tokens.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# SAND-042 — 2×L4 · client concurrency 16 (8 per replica) · n=50 × 5 specialists (paired)
# sandbox runbook show sand42-2l4-c16
set -euo pipefail

# serving variant: grid-awq-2l4
# runbook: sand42-2l4-c16
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
export MODAL_VLLM_TELEMETRY_LABEL=sand42-2l4-c16
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current
# runbook extra_env (already in the export block above)

sandbox run benchmark-check --config config/runs/sand42-50-correspondence-specialist-awq-2l4-c16.yaml

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# VLLM_BASE_URL is the FULL base: deploy output + '/v1'
#   e.g. export VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
#   (without /v1 every chat call 404s — the profile appends /chat/completions)
# export VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

# SAND-047: sample /metrics MID-RUN every $MIDRUN_INTERVAL seconds.
# The before/after scrapes fire at each run's DRAINED EDGES, where
# kv_cache_usage_perc gauges a pre-allocated cache with no live sequences
# and therefore reads 0 by construction — a mid sample is the only source.
# It goes through `scrape-metrics` on purpose: that also preserves the
# VERBATIM exporter text (~120 families) at the mid point, and appends
# every sample to vllm_metrics_mid.series.jsonl so the card reports the
# run's MAXIMUM instead of whichever probe happened to run last.
MIDRUN_INTERVAL="${MIDRUN_INTERVAL:-30}"
MIDRUN_CFG_FILE="$HOME/.sand42-2l4-c16-active-cfg"
echo config/runs/sand42-50-correspondence-specialist-awq-2l4-c16.yaml > "$MIDRUN_CFG_FILE"
while :; do
  cfg="$(cat "$MIDRUN_CFG_FILE" 2>/dev/null || true)"
  [ -n "$cfg" ] && sandbox run scrape-metrics --config "$cfg" --label mid || true
  sleep "$MIDRUN_INTERVAL"
done >>"$HOME/sand42-2l4-c16-midrun.log" 2>&1 &
MIDRUN_PID=$!
trap 'kill "$MIDRUN_PID" 2>/dev/null || true' EXIT

for cfg in \
  config/runs/sand42-50-correspondence-specialist-awq-2l4-c16.yaml \
  config/runs/sand42-50-insurance-claims-specialist-awq-2l4-c16.yaml \
  config/runs/sand42-50-corporate-records-specialist-awq-2l4-c16.yaml \
  config/runs/sand42-50-contracts-specialist-awq-2l4-c16.yaml \
  config/runs/sand42-50-merger-specialist-awq-2l4-c16.yaml
do
  sandbox run preflight --config "$cfg" --live --force
  sandbox run scrape-metrics --config "$cfg" --label before
  echo "$cfg" > "$HOME/.sand42-2l4-c16-active-cfg"
  sandbox run start --config "$cfg" --job-mode endpoint --watch
  sandbox run scrape-metrics --config "$cfg" --label after
  .venv/bin/python scripts/sand42/midrun_kv.py fold --cell 2l4-c16 >/dev/null 2>&1 || true
  sandbox run card --config "$cfg"
done

./deploy/teardown_vllm.sh   # ONLY after this run

sandbox run card --runbook sand42-2l4-c16
sandbox metrics compare --runs sand42-50-correspondence-specialist-awq-2l4-c16,sand42-50-insurance-claims-specialist-awq-2l4-c16,sand42-50-corporate-records-specialist-awq-2l4-c16,sand42-50-contracts-specialist-awq-2l4-c16,sand42-50-merger-specialist-awq-2l4-c16
```

---

# SAND-042 — 2×L4 · client concurrency 32 (16 per replica, at the admission ceiling) · n=50 × 5 specialists (paired)

**id:** `sand42-2l4-c32` · **family:** `sand42` · **serving:** `grid-awq-2l4`

Two replicas at client concurrency 32 split equally — 16 in flight per replica, which is exactly the engine's max_num_seqs, i.e. the scheduler's admission ceiling: any further request queues instead of running. That makes this cell the saturation point of the grid, and 1×L4 C16 vs 2×L4 C32 the matched-load scale-out pair AT saturation (16 per replica each). It also reproduces SAND-037's 2×L4 C32 point on the paired 250-document draw, so it is the bridge tying the grid back to the only earlier C32 measurement.

Edit [`config/runbooks/catalog.yaml`](../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show sand42-2l4-c32`.

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

- `config/runs/sand42-50-correspondence-specialist-awq-2l4-c32.yaml`
- `config/runs/sand42-50-insurance-claims-specialist-awq-2l4-c32.yaml`
- `config/runs/sand42-50-corporate-records-specialist-awq-2l4-c32.yaml`
- `config/runs/sand42-50-contracts-specialist-awq-2l4-c32.yaml`
- `config/runs/sand42-50-merger-specialist-awq-2l4-c32.yaml`

## Notes

- Reports: reports/SAND42/2L4-c32/<specialist>/<run_id>.card.* then the after step writes reports/SAND42/2L4-c32/SAND42-2L4-C32-SCORE-COST-CARD.md + .json. This cell supplies the FIFTH section of reports/SAND42/SAND42-MASTER-REPORT.md and a fifth column in the comparison tables.
- Added last (SAND-047): the original grid pins client concurrency to {8,16}. C32 joins the 2×L4 arm only, because it is the 2×L4 saturation point (16/replica = max_num_seqs) and precisely the per-replica load sand42-1l4-c16 already ran. It is the grid's only concurrency above 16.
- Spend (estimate): the five cost caps are the 2-replica row of the same table (sum $6.20) and are the abort guard — caps are keyed by replicas, not concurrency, and saturation should raise per-request latency while total throughput plateaus, not raise the cost of scoring the same 250 documents. Needs spend approval before deploy.
- Client concurrency is split equally across replicas: 32 → 16 per replica. At the ceiling per-replica queueing is expected, so read num_requests_waiting and preemptions on BOTH replicas: SAND-037 saw one replica hold 16 running + 7 queued while the other ran 6, so an even split is not guaranteed.
- MIN=MAX=2 keeps both replicas warm across all five classes; teardown only after the fifth.
- Decode: max_tokens 8192 at temperature 0.7 for contracts, 6144 for merger (SAND-040 optimised: top_p 0.8 / presence 1.0 / one length re-sample), 0.1 elsewhere. Contracts and merger run WHOLE-DOCUMENT CHUNKED extraction — the old head+tail cap dropped 62 % of contract and 93 % of merger text, and merger MAUD accuracy measured 0.0 on that truncated arm with 3/50 hard length failures. Do not raise max_tokens.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# SAND-042 — 2×L4 · client concurrency 32 (16 per replica, at the admission ceiling) · n=50 × 5 specialists (paired)
# sandbox runbook show sand42-2l4-c32
set -euo pipefail

# serving variant: grid-awq-2l4
# runbook: sand42-2l4-c32
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
export MODAL_VLLM_TELEMETRY_LABEL=sand42-2l4-c32
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current
# runbook extra_env (already in the export block above)

sandbox run benchmark-check --config config/runs/sand42-50-correspondence-specialist-awq-2l4-c32.yaml

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# VLLM_BASE_URL is the FULL base: deploy output + '/v1'
#   e.g. export VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
#   (without /v1 every chat call 404s — the profile appends /chat/completions)
# export VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

# SAND-047: sample /metrics MID-RUN every $MIDRUN_INTERVAL seconds.
# The before/after scrapes fire at each run's DRAINED EDGES, where
# kv_cache_usage_perc gauges a pre-allocated cache with no live sequences
# and therefore reads 0 by construction — a mid sample is the only source.
# It goes through `scrape-metrics` on purpose: that also preserves the
# VERBATIM exporter text (~120 families) at the mid point, and appends
# every sample to vllm_metrics_mid.series.jsonl so the card reports the
# run's MAXIMUM instead of whichever probe happened to run last.
MIDRUN_INTERVAL="${MIDRUN_INTERVAL:-30}"
MIDRUN_CFG_FILE="$HOME/.sand42-2l4-c32-active-cfg"
echo config/runs/sand42-50-correspondence-specialist-awq-2l4-c32.yaml > "$MIDRUN_CFG_FILE"
while :; do
  cfg="$(cat "$MIDRUN_CFG_FILE" 2>/dev/null || true)"
  [ -n "$cfg" ] && sandbox run scrape-metrics --config "$cfg" --label mid || true
  sleep "$MIDRUN_INTERVAL"
done >>"$HOME/sand42-2l4-c32-midrun.log" 2>&1 &
MIDRUN_PID=$!
trap 'kill "$MIDRUN_PID" 2>/dev/null || true' EXIT

for cfg in \
  config/runs/sand42-50-correspondence-specialist-awq-2l4-c32.yaml \
  config/runs/sand42-50-insurance-claims-specialist-awq-2l4-c32.yaml \
  config/runs/sand42-50-corporate-records-specialist-awq-2l4-c32.yaml \
  config/runs/sand42-50-contracts-specialist-awq-2l4-c32.yaml \
  config/runs/sand42-50-merger-specialist-awq-2l4-c32.yaml
do
  sandbox run preflight --config "$cfg" --live --force
  sandbox run scrape-metrics --config "$cfg" --label before
  echo "$cfg" > "$HOME/.sand42-2l4-c32-active-cfg"
  sandbox run start --config "$cfg" --job-mode endpoint --watch
  sandbox run scrape-metrics --config "$cfg" --label after
  .venv/bin/python scripts/sand42/midrun_kv.py fold --cell 2l4-c32 >/dev/null 2>&1 || true
  sandbox run card --config "$cfg"
done

./deploy/teardown_vllm.sh   # ONLY after this run

sandbox run card --runbook sand42-2l4-c32
sandbox metrics compare --runs sand42-50-correspondence-specialist-awq-2l4-c32,sand42-50-insurance-claims-specialist-awq-2l4-c32,sand42-50-corporate-records-specialist-awq-2l4-c32,sand42-50-contracts-specialist-awq-2l4-c32,sand42-50-merger-specialist-awq-2l4-c32
```

---

# SAND-042 live smoke — 5 corporate records on 1×L4 · C8 (pre-spend check)

**id:** `sand42-smoke` · **family:** `sand42` · **serving:** `grid-awq-1l4`

Five corporate records, a strict subset of the 1L4-c8 condition's 50-document draw, on the same engine, prompt, decode and gates as that condition. Proves the deploy env, the stratified draw, the scored path and the in-container GPU telemetry (nvidia-smi util / power / temperature / memory) actually work BEFORE the four scored conditions spend. Not a benchmark cell: it is excluded from the condition cards and the comparison.

Edit [`config/runbooks/catalog.yaml`](../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show sand42-smoke`.

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

- `config/runs/sand42-check-5-corporate-records-awq-1l4-c8.yaml`

## Notes

- Profile: set SANDBOX_MODAL_PROFILE_TRACK_A to the wallet you want (the catalog default is hermes-agent-jjb; exios66 is also configured locally).
- Spend (estimate): one cold boot (~2-4 min) + a few minutes warm for 5 documents ≈ $0.05-0.15 at $0.80/GPU-hr; cost_cap_usd 0.20 is the abort guard.
- GPU telemetry check: the after-scrape must print `gpu telemetry (sand42-1l4-c8): N samples, util mean ... max ...`. If it warns `gpu telemetry not captured`, the sampler or the volume read is broken — fix that before spending on the conditions.
- Report: reports/SAND42/1L4-c8/corporate_records/<run_id>.card.md + .card.json, with engine_telemetry.gpu carrying the util / power / temperature / memory series.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# SAND-042 live smoke — 5 corporate records on 1×L4 · C8 (pre-spend check)
# sandbox runbook show sand42-smoke
set -euo pipefail

# serving variant: grid-awq-1l4
# runbook: sand42-smoke
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
export MODAL_VLLM_TELEMETRY_LABEL=sand42-1l4-c8
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current
# runbook extra_env (already in the export block above)

sandbox run benchmark-check --config config/runs/sand42-check-5-corporate-records-awq-1l4-c8.yaml

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# VLLM_BASE_URL is the FULL base: deploy output + '/v1'
#   e.g. export VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
#   (without /v1 every chat call 404s — the profile appends /chat/completions)
# export VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

# SAND-047: sample /metrics MID-RUN every $MIDRUN_INTERVAL seconds.
# The before/after scrapes fire at each run's DRAINED EDGES, where
# kv_cache_usage_perc gauges a pre-allocated cache with no live sequences
# and therefore reads 0 by construction — a mid sample is the only source.
# It goes through `scrape-metrics` on purpose: that also preserves the
# VERBATIM exporter text (~120 families) at the mid point, and appends
# every sample to vllm_metrics_mid.series.jsonl so the card reports the
# run's MAXIMUM instead of whichever probe happened to run last.
MIDRUN_INTERVAL="${MIDRUN_INTERVAL:-30}"
MIDRUN_CFG_FILE="$HOME/.sand42-1l4-c8-active-cfg"
echo config/runs/sand42-check-5-corporate-records-awq-1l4-c8.yaml > "$MIDRUN_CFG_FILE"
while :; do
  cfg="$(cat "$MIDRUN_CFG_FILE" 2>/dev/null || true)"
  [ -n "$cfg" ] && sandbox run scrape-metrics --config "$cfg" --label mid || true
  sleep "$MIDRUN_INTERVAL"
done >>"$HOME/sand42-1l4-c8-midrun.log" 2>&1 &
MIDRUN_PID=$!
trap 'kill "$MIDRUN_PID" 2>/dev/null || true' EXIT

sandbox run preflight --config config/runs/sand42-check-5-corporate-records-awq-1l4-c8.yaml --live --force
sandbox run scrape-metrics --config config/runs/sand42-check-5-corporate-records-awq-1l4-c8.yaml --label before
echo config/runs/sand42-check-5-corporate-records-awq-1l4-c8.yaml > "$HOME/.sand42-1l4-c8-active-cfg"
sandbox run start --config config/runs/sand42-check-5-corporate-records-awq-1l4-c8.yaml --job-mode endpoint --watch
sandbox run scrape-metrics --config config/runs/sand42-check-5-corporate-records-awq-1l4-c8.yaml --label after
.venv/bin/python scripts/sand42/midrun_kv.py fold --cell 1l4-c8 >/dev/null 2>&1 || true
sandbox run card --config config/runs/sand42-check-5-corporate-records-awq-1l4-c8.yaml

./deploy/teardown_vllm.sh   # ONLY after this run

sandbox run card --config config/runs/sand42-check-5-corporate-records-awq-1l4-c8.yaml
```

---

# SAND-042 noise floor — correspondence re-run on the same 50 documents (1×L4 · C8)

**id:** `sand42-noise-floor` · **family:** `sand42` · **serving:** `grid-awq-1l4`

One extra correspondence cell on the identical 50 documents and identical settings as sand42-1l4-c8, under a different run id. The spread of the per-document score differences between the two runs is the run-to-run noise floor for every SAND-042 delta, re-measured on the SAND-042 draw (the SAND-037/39 floor in docs/BENCHMARK-PROGRAM.md §3 was measured on a different draw). One class, ~6 min, well under $0.20.

Edit [`config/runbooks/catalog.yaml`](../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show sand42-noise-floor`.

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

- `config/runs/sand42-noisefloor-correspondence-awq-1l4-c8.yaml`

## Notes

- Spend approved 2026-10-12 (operator): the flag was blocking the generated script only, never the config. Still preferred INSIDE the sand42-1l4-c8 re-run's boot rather than as its own cold boot — that leg's script appends this config last, and the mid-run sampler folds its samples into the sand42-1l4-c8 cell.
- Prefer running it inside the sand42-1l4-c8 deploy rather than as its own cold boot: append this config to that runbook's configs list and drop the blocked flag.
- Reports: the card lands beside the C8 cell at reports/SAND42/1L4-c8/correspondence/. The after step writes reports/SAND42/SAND42-NOISE-FLOOR.md with the paired SD_diff and the n it implies.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# SAND-042 noise floor — correspondence re-run on the same 50 documents (1×L4 · C8)
# sandbox runbook show sand42-noise-floor
set -euo pipefail

# serving variant: grid-awq-1l4
# runbook: sand42-noise-floor
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
export MODAL_VLLM_TELEMETRY_LABEL=sand42-1l4-c8
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current
# runbook extra_env (already in the export block above)

sandbox run benchmark-check --config config/runs/sand42-noisefloor-correspondence-awq-1l4-c8.yaml

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# VLLM_BASE_URL is the FULL base: deploy output + '/v1'
#   e.g. export VLLM_BASE_URL=https://<workspace>--sandbox-vllm-serve.modal.run/v1
#   (without /v1 every chat call 404s — the profile appends /chat/completions)
# export VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

# SAND-047: sample /metrics MID-RUN every $MIDRUN_INTERVAL seconds.
# The before/after scrapes fire at each run's DRAINED EDGES, where
# kv_cache_usage_perc gauges a pre-allocated cache with no live sequences
# and therefore reads 0 by construction — a mid sample is the only source.
# It goes through `scrape-metrics` on purpose: that also preserves the
# VERBATIM exporter text (~120 families) at the mid point, and appends
# every sample to vllm_metrics_mid.series.jsonl so the card reports the
# run's MAXIMUM instead of whichever probe happened to run last.
MIDRUN_INTERVAL="${MIDRUN_INTERVAL:-30}"
MIDRUN_CFG_FILE="$HOME/.sand42-1l4-c8-active-cfg"
echo config/runs/sand42-noisefloor-correspondence-awq-1l4-c8.yaml > "$MIDRUN_CFG_FILE"
while :; do
  cfg="$(cat "$MIDRUN_CFG_FILE" 2>/dev/null || true)"
  [ -n "$cfg" ] && sandbox run scrape-metrics --config "$cfg" --label mid || true
  sleep "$MIDRUN_INTERVAL"
done >>"$HOME/sand42-1l4-c8-midrun.log" 2>&1 &
MIDRUN_PID=$!
trap 'kill "$MIDRUN_PID" 2>/dev/null || true' EXIT

sandbox run preflight --config config/runs/sand42-noisefloor-correspondence-awq-1l4-c8.yaml --live --force
sandbox run scrape-metrics --config config/runs/sand42-noisefloor-correspondence-awq-1l4-c8.yaml --label before
echo config/runs/sand42-noisefloor-correspondence-awq-1l4-c8.yaml > "$HOME/.sand42-1l4-c8-active-cfg"
sandbox run start --config config/runs/sand42-noisefloor-correspondence-awq-1l4-c8.yaml --job-mode endpoint --watch
sandbox run scrape-metrics --config config/runs/sand42-noisefloor-correspondence-awq-1l4-c8.yaml --label after
.venv/bin/python scripts/sand42/midrun_kv.py fold --cell 1l4-c8 >/dev/null 2>&1 || true
sandbox run card --config config/runs/sand42-noisefloor-correspondence-awq-1l4-c8.yaml

./deploy/teardown_vllm.sh   # ONLY after this run

sandbox run card --config config/runs/sand42-noisefloor-correspondence-awq-1l4-c8.yaml
sandbox run card --runbook sand42-noise-floor
```

---
