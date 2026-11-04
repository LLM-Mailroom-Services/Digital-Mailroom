# Run report — `run-20-correspondence-specialist-awq`

Modal × vLLM specialist extract: **20 correspondence docs**, subclass-stratified
(2/3 scale of `run-30-correspondence-specialist` quotas), on **Qwen/Qwen3-8B-AWQ**
at **concurrency 8** on **2×L4 data-parallel** (MIN=MAX=2 pinned, one warm app
shared with the 50-doc follow-up), DMR-074 **production** prompt pin.

| | |
| --- | --- |
| run_id | `run-20-correspondence-specialist-awq` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local DMR-074 pin, sha `b141f0d9…`) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel, one replica per L4) |
| context / quant | `max_model_len=32768`, AWQ, gpu_util=0.90, max_num_seqs=6 |
| engine flags | prefix_caching=on, enforce_eager=on, async_scheduling=off, attention_backend=default, no reasoning/tool parsers |
| modal | `sandbox-vllm`, max_containers=2, min_containers=2 (pinned warm), scaledown=120 |
| profile / provider | `modal-vllm` / `vllm` |
| dataset | mailroom-dataset `ground_truth`, split=test, rev `46a4d3c2`, seed 42 |
| draw | 20 correspondence docs; fingerprint `2181af10e87b` |
| git | `59b9d35` (dirty=True at Run B time; Run A ran at same commit, dirty=False) |
| spec_hash | `7279cd71cf83f919b4d3be4ebf1a5e376090a3fe4fc41742dc42a12e6a3f1e5e` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **20 / 20** (`error_count=0`) |
| **overall_extraction_score** | **0.22799** |
| exact_match | 0.22799 |
| schema_valid_rate | 0.90 (18/20) |
| offline_fallback rows | 0 |
| parse_error_count | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (busy interval) | 75.084 s |
| concurrency | 8 (~4 per replica) |
| cold boot (measured at preflight) | 0.553 s (endpoint already warm) |
| gpu_seconds (1-replica export) | 75.637 s (wall + cold boot) |
| estimated GPU cost (billed, 2 replicas) | **$0.033616** |
| cost per document (billed, 2 replicas) | $0.00168080 |
| serving-record export (1-replica basis) | $0.016808 ($0.00084040/doc) — doubled for billing: the export assumes one GPU |
| token-proxy cost | $0.001992 ($0.00009960/doc) |
| latency e2e / p50 / max | 25.168468 / 26.595458 / 35.414844 s |
| prompt / completion / total tokens | 49878 / 3813 / 53691 |
| throughput | 715.08 tok/s |
| slot utilization | 0.838 (busy_slot 62.9 s vs wall 75.1 s) |
| cost cap | $0.40 (config) → under cap |

**Concurrency proof (not serial):**

- sum(per-doc latency) = 503.4 s
- wall = 75.084 s → speedup **6.70x** at concurrency 8
- serial would show wall ≈ sum(latency); observed wall is the batched value.

## Engine observations (KV / prefix cache)

- Deploy logs confirm `enforce_eager` (CUDA-graphs disabled, faster cold boot),
  AWQ custom fusions (`norm_quant`, `act_quant`), engine init ~14.6 s per replica.
- `/metrics` (sampled replica, cumulative since deploy): prefix-cache
  **61.3% hit rate** (34,672 / 56,588 queried tokens) after Run A — the shared
  production system prompt amortizes prefill across requests as designed.
- Engine stat logger during runs: `Running: 0 reqs` at scrape instants
  (waves drain fast at c8 on 2 replicas), `GPU KV cache usage: 0.0%` idle —
  no KV pressure observed; `max_num_seqs=6` never bound short correspondence prompts.
- Per-replica APC caches are independent (shared prefixes cached twice);
  the second replica's counters were not sampled (round-robin routing) —
  hit rates above are one replica's view, not fleet-wide.
- Async scheduling stayed **off** (structured extraction outputs required).

## Strata (seed 42, split=test)

Scaled 2/3 from run-30 quotas (12→8 / 3→2):

| subclass | n | mean overall |
| --- | --- | --- |
| email | 8 | 0.2034 |
| letter | 2 | 0.1195 |
| press_release | 2 | 0.0823 |
| memo | 2 | 0.2871 |
| meeting_request | 2 | 0.3695 |
| demand | 2 | 0.3079 |
| notice | 2 | 0.3000 |
| **total** | **20** | **0.22799** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-5cdfee2b0ef0a218` | meeting_request | 0.2029 | 0.0000 | 35.4 | 1728 | 158 | None |
| 2 | `DOC-47c480a8749b6128` | email | 0.0278 | 0.0000 | 18.8 | 2031 | 202 | None |
| 3 | `DOC-b714773e73596e20` | notice | 0.1333 | 0.0000 | 27.6 | 2181 | 199 | None |
| 4 | `DOC-166a38f8097667fe` | memo | 0.5000 | 0.1112 | 9.8 | 1985 | 207 | None |
| 5 | `DOC-228d359edcc4d302` | email | 0.3333 | 0.1333 | 5.4 | 1738 | 132 | None |
| 6 | `DOC-1f7ea83aa0ef6fc6` | press_release | 0.1228 | 0.0000 | 30.2 | 5305 | 619 | None |
| 7 | `DOC-4eb0e9385b81cc4b` | email | 0.0303 | 0.0000 | 9.7 | 1780 | 142 | None |
| 8 | `DOC-84ffaa54f0382296` | email | 0.2029 | 0.0000 | 33.7 | 1735 | 141 | None |
| 9 | `DOC-a14148982aa7bc36` | email | 0.2050 | 0.0000 | 34.5 | 2584 | 144 | None |
| 10 | `DOC-5c54a5baef4b9f06` | email | 0.1276 | 0.0000 | 30.0 | 1714 | 130 | None |
| 11 | `DOC-d93fc6f9d8a12c94` | memo | 0.0741 | 0.0000 | 35.4 | 1924 | 171 | None |
| 12 | `DOC-8a4d83e88d9283c4` | press_release | 0.0417 | 0.0000 | 28.4 | 4424 | 167 | None |
| 13 | `DOC-bfbaa0b7fefa7640` | demand | 0.4524 | 0.1112 | 22.8 | 1686 | 159 | None |
| 14 | `DOC-c2c4ef739985acb6` | demand | 0.1633 | 0.0000 | 26.0 | 1996 | 206 | None |
| 15 | `DOC-f6a9a00e53cc7973` | notice | 0.4667 | 0.1176 | 22.5 | 6879 | 168 | None |
| 16 | `DOC-a0d2177d94df8da4` | email | 0.5555 | 0.1250 | 26.0 | 1793 | 156 | None |
| 17 | `DOC-cf33df0934b38188` | letter | 0.0533 | 0.0000 | 25.9 | 2638 | 204 | None |
| 18 | `DOC-6357890dcb31f6b2` | meeting_request | 0.5362 | 0.1112 | 27.2 | 2224 | 174 | None |
| 19 | `DOC-35146decb7e3ffb8` | letter | 0.1856 | 0.0000 | 23.2 | 1836 | 211 | None |
| 20 | `DOC-16be7fa7e8ae5431` | email | 0.1451 | 0.0000 | 24.2 | 1697 | 123 | None |

- scored rows: 20/20; min=0.0278 max=0.5555 mean=0.2280
- *Data note (2026-09-28):* the latency column above sums to 496.7 s and has a
  median of 26.0 s, while the run-level figures (and the serving export) record
  503.369 s and p50 26.595 s. The rows were reconstructed from captured stdout;
  the score column matches the stated mean. Treat per-row latencies as approximate.

## Deploy env actually used

```bash
modal profile activate hermes-agent-jjb   # verified via `modal profile current`
export SANDBOX_PROFILE=modal-vllm MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ \
  MODAL_VLLM_QUANTIZATION=awq MODAL_VLLM_MAX_MODEL_LEN=32768 \
  MODAL_VLLM_GPU=L4 MODAL_VLLM_IMAGE_TAG=v0.29.0 \
  MODAL_VLLM_MAX_CONTAINERS=2 MODAL_VLLM_MIN_CONTAINERS=2 \
  MODAL_VLLM_SCALEDOWN_SECONDS=120 MODAL_VLLM_MAX_NUM_SEQS=6 \
  MODAL_VLLM_GPU_MEMORY_UTILIZATION=0.90 \
  MODAL_VLLM_ENABLE_PREFIX_CACHING=1 MODAL_VLLM_ENFORCE_EAGER=1
# (MODAL_VLLM_API_TOKEN lives in local .env only — never in git)
```

- Endpoint: `https://hermes-agent-jjb--sandbox-vllm-serve.modal.run`
  (2 containers verified via `modal container list`; `sandbox health` models probe
  listed `Qwen/Qwen3-8B-AWQ`; direct chat probe returned usage tokens).
- No teardown between Run A and Run B (same warm app); teardown after Run B.

## Artifacts

| path | role |
| --- | --- |
| `config/runs/run-20-correspondence-specialist-awq.yaml` | run spec |
| `data/runtime/runs/run-20-correspondence-specialist-awq/` | run dir |
| `data/runtime/runs/run-20-correspondence-specialist-awq/dataset.jsonl` | seeded draw (20) |
| `data/runtime/runs/run-20-correspondence-specialist-awq/items.jsonl` | per-doc results (reconstructed from captured run output — see note) |
| `data/runtime/runs/run-20-correspondence-specialist-awq/stdout.log` | full captured run output |
| `reports/experiment_log.jsonl` | sandbox experiment record (gitignored) |
| `reports/serving/run-20-correspondence-specialist-awq.serving.json` | serving-record export (1-replica basis) |

## Reproduce

```bash
modal profile activate hermes-agent-jjb
export SANDBOX_PROFILE=modal-vllm MODAL_VLLM_MODEL=Qwen/Qwen3-8B-AWQ \
  MODAL_VLLM_QUANTIZATION=awq MODAL_VLLM_MAX_MODEL_LEN=32768 \
  MODAL_VLLM_GPU=L4 MODAL_VLLM_IMAGE_TAG=v0.29.0 \
  MODAL_VLLM_MAX_CONTAINERS=2 MODAL_VLLM_MIN_CONTAINERS=2 \
  MODAL_VLLM_SCALEDOWN_SECONDS=120
# set VLLM_BASE_URL + VLLM_API_KEY after deploy (never commit tokens)
modal run deploy/modal_vllm.py::download_model
modal deploy deploy/modal_vllm.py --strategy recreate
sandbox cutover --profile modal-vllm
sandbox health --profile modal-vllm
sandbox run benchmark-check --config config/runs/run-20-correspondence-specialist-awq.yaml
sandbox run preflight --config config/runs/run-20-correspondence-specialist-awq.yaml --live
sandbox run start --config config/runs/run-20-correspondence-specialist-awq.yaml --job-mode endpoint --watch
# NO teardown here if Run B follows on the same warm app.
```

## Notes

- **First attempt superseded:** the initial `start` finished 20/20
  (overall=0.244565, wall=80.43 s) but its stdout was piped through `tail`,
  so per-doc rows were unrecoverable — and the isolated specialist path does
  not persist `items.jsonl` itself (it returns rows in-memory; only the
  per-item whole-run path writes them). The run was repeated on the identical
  seed-42 draw (fingerprint `2181af10e87b`) with full stdout capture; this
  report records the repeat (overall=0.22799, wall=75.084 s). Both attempts
  are in `reports/experiment_log.jsonl`.
- Prompt tokens identical across attempts (49,878); completions differ
  (3,908 vs 3,813) — sampling nondeterminism at temperature 0.1, not a defect.
- *(Corrected 2026-09-28: the earlier correspondence runs were not `*_simplified`
  and the score lift is confounded — see the Run B report, §Comparison footnote ³.)*
- Production prompt vs the older `*_simplified` correspondence runs: schema
  validity jumps (0.90 here vs ~0.25-class before) and score roughly triples
  (0.228 vs 0.087–0.089) — prompt, not scale-out, is the dominant variable.
- Health `chat` probe reports `json_object rejected (404)` while plain chat
  returns 200 with usage — the harness extraction path does not depend on the
  probe's `response_format` lesion; 20/20 ok confirms the live path.
