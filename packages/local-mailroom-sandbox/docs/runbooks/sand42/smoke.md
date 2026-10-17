<!-- Generated from config/runbooks/catalog.yaml. Edit the catalog, then: sandbox runbook write -->

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
