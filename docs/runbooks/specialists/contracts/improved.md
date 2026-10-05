<!-- Generated from config/runbooks/catalog.yaml. Edit the catalog, then: sandbox runbook write -->

# Improved run configurations

Generated family rollup. Canonical per-id cards live at their catalog paths.

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

---

# 1×A100-40GB Qwen3-14B-AWQ isolated sorter n=400 (C=32)

**id:** `a100-qwen3-14b-awq-sorter400` · **family:** `improved` · **serving:** `awq-14b-a100`

Isolated SorterAgent eval (not a specialist extract). Official Qwen/Qwen3-14B-AWQ on one A100-40GB with AWQ-Marlin, fp8 KV, CUDA graphs, prefix caching, thinking off, C=32. Prompt pin sorter_v1. One cold boot; MIN=MAX=1 until teardown. Do not start this run without spend approval.

Edit [`config/runbooks/catalog.yaml`](../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show a100-qwen3-14b-awq-sorter400`.

## Pins (from catalog serving variant)

| Knob | Value |
| --- | --- |
| Model | `Qwen/Qwen3-14B-AWQ` |
| GPU | `A100-40GB` |
| Image | `v0.29.0` |
| max_model_len | `32768` |
| max_num_seqs | `32` |
| max_containers | `1` |
| min_containers | `1` |
| scaledown_seconds | `600` |
| quantization | `awq_marlin` |
| prefix caching / eager | `1 / 0` |

## Configs

- `config/runs/run-400-sorter-qwen3-14b-awq-a100.yaml`

## Notes

- CLI: pass --profile AFTER the subcommand (sandbox health --profile modal-vllm). Never paste unicode ellipsis into commands.
- Pretty logs: open sandbox watch --web --config config/runs/run-400-sorter-qwen3-14b-awq-a100.yaml in a second pane (http://127.0.0.1:8765/) BEFORE sandbox run start. start --watch is the CLI session layer only and does not tail Modal dispatch logs.
- Canonical deploy knobs: set -a; eval "$(sandbox run deploy-env --config config/runs/run-400-sorter-qwen3-14b-awq-a100.yaml)"; set +a. Then download_model and modal deploy --strategy recreate once.
- benchmark-check is skipped (L4 specialist gate). Engine pins are still catalog-asserted against the run YAML.
- Trace sink is none so preflight is not blocked without Langfuse keys. Family default remains Langfuse when LANGFUSE_* are set; flip spec.trace.sink to langfuse then re-preflight. Keep PHOENIX_TRACING=disabled unless the Phoenix extra is installed.

## Purpose

Run a **400-document isolated sorter** eval on a **higher-parameter Qwen 3** than the L4 8B-AWQ baseline, with AWQ weights, A100 serving, C=32 continuous batching, KV + CUDA-graph optimizations, and one warm replica.

## Model choice

| Option | Hub id | GPU SKU | Verdict |
| --- | --- | --- | --- |
| Primary | `Qwen/Qwen3-14B-AWQ` | `A100-40GB` (`MODAL_VLLM_GPU`) | Conservative C=32 + 32k ctx + graphs. Official Qwen AWQ (~10GB weights). Already in `config/models.yaml`. |
| Stretch | `Qwen/Qwen3-32B-AWQ` | `A100-80GB` | Official Qwen AWQ (~20GB). C=32 on 40GB is an OOM/KV risk. Use only with a copied YAML (`engine.model` + `modal.gpu: A100-80GB`, cost cap ×1.2). |
| Not this card | `Qwen/Qwen3-8B-AWQ` on L4 | `L4` | Current specialist/sorter baseline (c=8 on L4 extract; SAND-032 sorter used 2×L4). |

14B-AWQ is the matrix row default GPU **L4** (it fits). This runbook **overrides to A100-40GB** so C=32 has KV headroom. Do not flip the L4 8B specialist suite.

## Serving knobs

| Knob | Value | Why |
| --- | --- | --- |
| `MODAL_VLLM_MODEL` | `Qwen/Qwen3-14B-AWQ` | Official AWQ checkpoint |
| `MODAL_VLLM_GPU` | `A100-40GB` | 1× 40GB; Ampere AWQ-Marlin |
| `MODAL_VLLM_QUANTIZATION` | `awq_marlin` | Ampere kernel (not Hopper FP8) |
| `MODAL_VLLM_MAX_MODEL_LEN` | `32768` | AWQ KV pool; v0.29.0 raises if one 32k request cannot fit |
| `MODAL_VLLM_MAX_NUM_SEQS` | `32` | Admission must cover C=32 on **one** replica |
| `MODAL_VLLM_GPU_MEMORY_UTILIZATION` | `0.90` | Leave 10% for graphs / fragmentation |
| `MODAL_VLLM_ENABLE_PREFIX_CACHING` | `1` | Shared sorter system prompt |
| `MODAL_VLLM_ENFORCE_EAGER` | `0` | CUDA graphs on (`enforce_eager=false`) |
| `MODAL_VLLM_CUDAGRAPH_CAPTURE_SIZES` | `1,2,4,8,16,32` | Capture batch sizes up to C |
| `MODAL_VLLM_KV_CACHE_DTYPE` | `fp8` | Larger KV pool; A100 FP8 is weight-only Marlin for **weights**, KV fp8 is still the pool lever |
| `MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS` | `{"enable_thinking": false}` | Avoid Granite-class 8192-token thinking / 408s |
| `MODAL_VLLM_MAX_CONTAINERS` | `1` | No scale-out unless measured queueing |
| `MODAL_VLLM_MIN_CONTAINERS` | `1` | Pin warm from deploy until teardown (one cold boot) |
| `MODAL_VLLM_SCALEDOWN_SECONDS` | `600` | Safety idle window if min ever drops; teardown at end anyway |
| `MODAL_VLLM_TP_SIZE` | `1` | 14B-AWQ fits one GPU |
| `max_tokens` / `max_input_chars` | `2048` / `12000` | Overlay sorter caps; hard retry cap `job.max_retries: 2` |
| `job.concurrency` | `32` | Default JobSpec C=4 starves dispatch; size C to A100 decode, not L4 c=8 |

## Dataset and prompt

| Item | Pin |
| --- | --- |
| Task | `isolated` (SorterAgent only) |
| Prompt | `config/prompts/sorter_v1.txt` (`sorter_v1`). There is **no** `sorter_local_v1`. Production lookup is still `sorter_v14`; runtime override patches that key with v1 text. |
| Corpus | `Lucius-Morningstar/mailroom-dataset` @ `ed7576b676343e0b402ec5412cded301e629bdee`, `split: train`, seed 42 |
| n | 400 proportional to train mix (132/123/73/54/18) |

## Cost estimate (do not treat as a live invoice)

Rates from `deploy/README.md` (modal.com/pricing, verified 2026-09-09) and `src/mailroom_sandbox/job/metrics.py`: **A100-40GB = $2.10/hr** ($0.000583/s). Formula from `docs/RUN-COST-DERIVATION.md`: Modal bills container-seconds, not tokens. `download_model` is CPU-only.

Anchor: SAND-032 `sand032-s6-sorter1000` isolated 8B-AWQ, 2×L4, C=32, thinking off — **458 docs in 1791.4s wall** (~3.91s wall/doc), GPU $/doc **$0.001869**, completion p50 **147** (not 8192 thinking).

| Band | Warm wall (400 docs) | +300s graphs boot | GPU $ @ $2.10/hr | $/doc |
| --- | --- | --- | --- | --- |
| Optimistic (A100 offsets 14B vs 8B-on-2×L4) | 1565s | 1865s | **$1.09** | $0.0027 |
| Likely (×1.5 wall vs S6) | 2347s | 2647s | **$1.54** | $0.0039 |
| Heavy (×2 wall / KV pressure) | 3130s | 3430s | **$2.00** | $0.0050 |
| Pinned-min idle (operator gap 5 min) | — | +300s | +$0.18 | — |
| Forgotten scaledown (no teardown) | — | +600s | +$0.35 | — |

**Headline: budget ~$1.50–$2.20 GPU for 400 docs if you teardown promptly after one cold boot; `cost_cap_usd: 4.00` (~1.9 GPU-hours) is the abort guard.**

Token-proxy (same OpenRouter Qwen-flash map as `Qwen/Qwen3-14B-AWQ`, $0.03/$0.13 per 1M) at S6 p50 7994 in + 147 out: **~$0.00026/doc**, **~$0.10 for n=400**. GPU true cost is ~6–20× the token proxy on this posture (same lesson as contracts L4 vs API).

Extrapolation: linear in N at fixed C if KV stays below cliff. Doubling N ≈ doubles warm GPU-hours; do **not** add a second A100 unless queueing is measured (`max_containers=1`).

## Pretty logging

```bash
sandbox watch --web --config config/runs/run-400-sorter-qwen3-14b-awq-a100.yaml
# http://127.0.0.1:8765/
sandbox run start --config config/runs/run-400-sorter-qwen3-14b-awq-a100.yaml --job-mode endpoint --watch
```

See `docs/pretty-logging/mailroom-themed-logging.md` and `docs/snippets/pretty_logs.md`.

## Failure modes

| Symptom | Likely cause | Mitigation |
| --- | --- | --- |
| HTTP 408 / proxy timeout | C too high vs decode; thinking left on; `max_tokens` huge | Confirm `enable_thinking: false`; drop C to 16; keep `max_tokens` 2048; overlay `llm_call_timeout_seconds` is 600 |
| OOM at load | Wrong GPU SKU or 32B on 40GB | Stay on 14B + A100-40GB; 32B only on A100-80GB |
| Boot raise: KV cannot hold one 32768 request | util too high or fp8 KV off | Keep `kv_cache_dtype: fp8`; lower `max_model_len` to 16384 only as last resort |
| CUDA graph capture fail | `enforce_eager=true` with capture sizes | YAML already requires `enforce_eager: false`; recapture after image pin change |
| KV cache full / latency cliff | C=32 × long sorter windows | Lower C or `max_num_seqs`; S6 was prefill-bound (p95 530s) |
| LengthFinish / 8192-token burn | Thinking mode | Chat-template kwargs + overlay `reasoning_effort: none` |
| Phoenix import errors | OTEL sidecar | `PHOENIX_TRACING=disabled` |
| Starved GPU | JobSpec default C=4 | This YAML pins C=32 |
| Second cold boot | `modal deploy --strategy recreate` mid-run or scaledown 120 with min=0 | Deploy once; min_containers=1; teardown only at end |

## Stretch 32B (not the start config)

Copy the YAML, set `engine.model: Qwen/Qwen3-32B-AWQ`, `modal.gpu: A100-80GB`, raise `cost_cap_usd` to 5.0. Expect ~1.2× $/hr ($2.50 vs $2.10) plus slower decode. Verify KV after `/health`.

## Do not

- Share one Modal token / ~/.modal.toml profile across operators
- Tear down or modal deploy --strategy recreate between classes on one track
- Set MODAL_VLLM_GPU=L4:2 + TP for Qwen3-8B (use MAX_CONTAINERS=2 instead)
- Edit run-30-*-specialist.yaml for a one-off model swap

## Operator script

```bash
# 1×A100-40GB Qwen3-14B-AWQ isolated sorter n=400 (C=32)
# sandbox runbook show a100-qwen3-14b-awq-sorter400
set -euo pipefail

# serving variant: awq-14b-a100
# runbook: a100-qwen3-14b-awq-sorter400
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MODEL=Qwen/Qwen3-14B-AWQ
export MODAL_VLLM_GPU=A100-40GB
export MODAL_VLLM_IMAGE_TAG=v0.29.0
export MODAL_VLLM_MAX_MODEL_LEN=32768
export MODAL_VLLM_MAX_NUM_SEQS=32
export MODAL_VLLM_GPU_MEMORY_UTILIZATION=0.90
export MODAL_VLLM_ENABLE_PREFIX_CACHING=1
export MODAL_VLLM_ENFORCE_EAGER=0
export MODAL_VLLM_MAX_CONTAINERS=1
export MODAL_VLLM_MIN_CONTAINERS=1
export MODAL_VLLM_SCALEDOWN_SECONDS=600
export MODAL_VLLM_QUANTIZATION=awq_marlin
export MODAL_VLLM_TP_SIZE=1
export MODAL_VLLM_KV_CACHE_DTYPE=fp8
export MODAL_VLLM_CUDAGRAPH_CAPTURE_SIZES='1,2,4,8,16,32'
export MODAL_VLLM_DEFAULT_CHAT_TEMPLATE_KWARGS='{"enable_thinking": false}'
export PHOENIX_TRACING=disabled
export SANDBOX_AGENT_KNOBS='{"sorter":{"max_tokens":2048,"max_input_chars":12000}}'
export MODAL_VLLM_API_TOKEN="${MODAL_VLLM_API_TOKEN:-$(openssl rand -hex 24)}"

modal profile activate "${SANDBOX_MODAL_PROFILE_TRACK_A:-hermes-agent-jjb}"
modal profile current
# runbook extra_env (already in the export block above)

# equivalent: eval "$(sandbox modal-matrix env Qwen/Qwen3-14B-AWQ --gpu A100-40GB)"

modal run deploy/modal_vllm.py::download_model

modal deploy deploy/modal_vllm.py --strategy recreate

# set VLLM_BASE_URL from deploy output + VLLM_API_KEY=$MODAL_VLLM_API_TOKEN
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm

sandbox run preflight --config config/runs/run-400-sorter-qwen3-14b-awq-a100.yaml --live
sandbox run start --config config/runs/run-400-sorter-qwen3-14b-awq-a100.yaml --job-mode endpoint --watch

./deploy/teardown_vllm.sh   # ONLY after this run

sandbox run status --config config/runs/run-400-sorter-qwen3-14b-awq-a100.yaml
sandbox scorecard --run run-400-sorter-qwen3-14b-awq-a100
modal billing summary
```

---

# AWQ + 32768 + concurrency 8 (contracts N=20)

**id:** `improved-awq-c8` · **family:** `improved` · **serving:** `awq-32k`

SAND-019 corrected contracts path. Window 32768 clears the 16k 400; run-scoped max_tokens 8192 clears LengthFinish; concurrency 8 on one L4. Same seed-42 draw as run-20-contracts-awq.

Edit [`config/runbooks/catalog.yaml`](../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-awq-c8`.

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

./deploy/teardown_vllm.sh   # ONLY after this run
```

---

# AWQ 32768 correspondence N=20 (concurrency 5)

**id:** `improved-correspondence-awq` · **family:** `improved` · **serving:** `awq-32k`

SAND-019 short-doc AWQ path. Same 1×L4 / 1-container topology.

Edit [`config/runbooks/catalog.yaml`](../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-correspondence-awq`.

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

./deploy/teardown_vllm.sh   # ONLY after this run
```

---

# AWQ 32768 correspondence N=20 (concurrency 8)

**id:** `improved-correspondence-awq-c8` · **family:** `improved` · **serving:** `awq-32k`

Same seed-42 correspondence draw as improved-correspondence-awq (fingerprint 285f423d3708). Only concurrency changes (5 → 8).

Edit [`config/runbooks/catalog.yaml`](../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-correspondence-awq-c8`.

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

./deploy/teardown_vllm.sh   # ONLY after this run
```

---

# FP16 isolation twin of correspondence AWQ-c8

**id:** `improved-correspondence-fp16-c8` · **family:** `improved` · **serving:** `baseline`

issue #21. Same draw (fingerprint 285f423d3708) and concurrency 8, but Qwen/Qwen3-8B bf16 at 16384. PREPARED ONLY until spend/auth are approved.

Edit [`config/runbooks/catalog.yaml`](../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-correspondence-fp16-c8`.

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

./deploy/teardown_vllm.sh   # ONLY after this run
```

---

# Granite 4.2-8B FP8 on 1×L4 (SAND-027 Leg A swap-in)

**id:** `improved-granite-fp8` · **family:** `improved` · **serving:** `granite-fp8`

Same singular L4 / 1-container topology as the Qwen baseline, swapped to ibm-granite/granite-4.2-8b-fp8 at 32768. Do not edit run-30 YAMLs — live /v1/models probe requires engine.model to match, so copy specs after smoke.

Edit [`config/runbooks/catalog.yaml`](../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-granite-fp8`.

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
- Thinking spans are separable (native `granite` parser on v0.29.0; `granite_thinking_parser` needs vLLM >= 0.30 and crash-loops the pinned image)

## Notes

- sandbox run benchmark-check accepts the five run-20-*-granite 1×L4 pinned configs (GRANITE_ONE_GPU_RUNS); Qwen defaults unchanged.
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
export MODAL_VLLM_REASONING_PARSER=granite
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
# smoke: Thinking spans are separable (native `granite` parser on v0.29.0; `granite_thinking_parser` needs vLLM >= 0.30 and crash-loops the pinned image)

./deploy/teardown_vllm.sh   # ONLY after this run
```

---

# Second L4 — data parallel (still 1 GPU / container)

**id:** `improved-second-l4` · **family:** `improved` · **serving:** `second-l4-dp`

Raise MAX_CONTAINERS to 2. Each replica is a full vLLM on its own L4 with the baseline Qwen3-8B knobs. Modal @web_server round-robins. Do not use GPU=L4:2 + tensor parallel for 8B.

Edit [`config/runbooks/catalog.yaml`](../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-second-l4`.

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

Edit [`config/runbooks/catalog.yaml`](../../../../config/runbooks/catalog.yaml), then `sandbox runbook write`. Print this card: `sandbox runbook show improved-scale-matrix`.

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
