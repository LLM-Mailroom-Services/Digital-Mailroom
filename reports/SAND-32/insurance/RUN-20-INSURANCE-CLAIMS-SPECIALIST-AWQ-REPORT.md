# Run report — `run-20-insurance-claims-specialist-awq`

Modal × vLLM specialist extract: **20 insurance_claim docs**, subclass-stratified
(2/3 scale of `run-30-insurance-claims-specialist` quotas), on **Qwen/Qwen3-8B-AWQ**
at **concurrency 8** (legacy AWQ completion posture / improved-awq-c8 alignment).

| | |
| --- | --- |
| run_id | `run-20-insurance-claims-specialist-awq` |
| task / agent | `insurance_claims_specialist` |
| prompt | `insurance_claims_specialist_simplified` (local DMR-074 pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1× L4 |
| context / quant | `max_model_len=32768`, AWQ, gpu_util=0.90, max_num_seqs=6 |
| modal | `sandbox-vllm`, max_containers=1, min_containers=0, scaledown=120 |
| profile / provider | `modal-vllm` / `vllm` |
| dataset | mailroom-dataset `ground_truth`, split=test, rev `46a4d3c2`, seed 42 |
| draw | 20 insurance_claim docs; fingerprint `82ea2b70a8f4` |
| git | `500eeee` (dirty=True) |
| spec_hash | `c52b1f8d1548d86b038e0ed01c943a1e2dc9c2a0442de27cb09404b4dbab3504` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **20 / 20** (`error_count=0`) |
| **overall_extraction_score** | **0.671435** |
| exact_match | 0.671435 |
| schema_valid_rate | 0.25 (5/20) |
| offline_fallback rows | 0 |
| parse_error_count | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (busy interval) | 422.152 s |
| concurrency | 8 |
| cold boot (measured at preflight) | 0.361 s (endpoint already warm) |
| gpu_seconds | 422.513 s (wall + cold boot) |
| estimated GPU cost | **$0.093892** |
| cost per document | $0.00469460 |
| latency e2e / p50 / max | 128.025659 / 145.269082 / 184.188645 s |
| prompt / completion / total tokens | 68687 / 9731 / 78418 |
| cost cap | $0.40 (config) → under cap |

**Concurrency proof (not serial):**
- sum(per-doc latency) = 2560.5 s
- wall = 422.152 s → speedup **6.07x** at concurrency 8
- serial would show wall ≈ sum(latency); observed wall is the batched value.

## Strata (seed 42, split=test)

Scaled 2/3 from run-30 quotas (6→4 / 3→2):

| subclass | n | mean overall |
| --- | --- | --- |
| auto | 4 | 0.6984 |
| carrier | 4 | 0.6409 |
| property | 4 | 0.7151 |
| inpatient | 4 | 0.7038 |
| outpatient | 2 | 0.6149 |
| pde | 2 | 0.5830 |
| **total** | **20** | **0.671435** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-0620aa1de7449f50` | auto | 0.7623 | 0.6285 | 70.6 | 2829 | 286 | None |
| 2 | `DOC-7c2169da60bedb97` | auto | 0.7623 | 0.6667 | 58.4 | 2828 | 281 | None |
| 3 | `DOC-6356fdf0e6dd934d` | carrier | 0.6398 | 0.5806 | 17.5 | 3121 | 329 | None |
| 4 | `DOC-89dbe9bbd1ae3838` | carrier | 0.6442 | 0.5454 | 129.1 | 2968 | 934 | None |
| 5 | `DOC-d5d6261d51f109c5` | carrier | 0.6398 | 0.5625 | 46.5 | 2987 | 362 | None |
| 6 | `DOC-db7f08c116d0a922` | carrier | 0.6398 | 0.5625 | 144.1 | 2942 | 352 | None |
| 7 | `DOC-99bb7223b1982799` | inpatient | 0.7150 | 0.5294 | 90.1 | 3097 | 460 | None |
| 8 | `DOC-20cff462f8b9336f` | inpatient | 0.6884 | 0.5294 | 30.9 | 3070 | 337 | None |
| 9 | `DOC-7d3d0d15f83308f7` | inpatient | 0.7041 | 0.5294 | 167.0 | 3107 | 956 | None |
| 10 | `DOC-f27711f30aa77d8c` | inpatient | 0.7076 | 0.5294 | 184.2 | 3099 | 719 | None |
| 11 | `DOC-58cd43db8992c962` | auto | 0.6462 | 0.6000 | 181.2 | 2806 | 287 | None |
| 12 | `DOC-12c181c55f304b23` | auto | 0.6228 | 0.6000 | 180.4 | 2803 | 258 | None |
| 13 | `DOC-589fd31239dd5097` | outpatient | 0.6123 | 0.4849 | 182.2 | 2981 | 323 | None |
| 14 | `DOC-be210d6df88e575c` | outpatient | 0.6176 | 0.5333 | 177.6 | 3002 | 347 | None |
| 15 | `DOC-e480fc375d82e795` | pde | 0.5996 | 0.5000 | 153.4 | 2882 | 342 | None |
| 16 | `DOC-78b40355a26dc927` | pde | 0.5663 | 0.5714 | 152.3 | 2900 | 316 | None |
| 17 | `DOC-bdd463f6ea17eff4` | property | 0.7370 | 0.5405 | 135.3 | 5004 | 528 | None |
| 18 | `DOC-f63be6e8a4f03348` | property | 0.7569 | 0.5641 | 130.1 | 4650 | 567 | None |
| 19 | `DOC-6d23cffc38904d1d` | property | 0.7257 | 0.5405 | 146.5 | 5468 | 639 | None |
| 20 | `DOC-868d4ca20d89b69b` | property | 0.6410 | 0.3396 | 183.3 | 6143 | 1108 | None |

## Artifacts

| path | role |
| --- | --- |
| `config/runs/run-20-insurance-claims-specialist-awq.yaml` | run spec |
| `data/runtime/runs/run-20-insurance-claims-specialist-awq/` | run dir |
| `data/runtime/runs/run-20-insurance-claims-specialist-awq/dataset.jsonl` | seeded draw (20) |
| `data/runtime/runs/run-20-insurance-claims-specialist-awq/items.jsonl` | per-doc results |
| `reports/experiment_log.jsonl` | sandbox experiment record (gitignored) |
| `reports/serving/run-20-insurance-claims-specialist-awq.serving.json` | serving-record export |

## Reproduce

```bash
modal profile activate hermes-agent-jjb
eval "$(sandbox modal-matrix env Qwen/Qwen3-8B-AWQ)"
export SANDBOX_PROFILE=modal-vllm
export MODAL_VLLM_MAX_CONTAINERS=1 MODAL_VLLM_MIN_CONTAINERS=0
export MODAL_VLLM_SCALEDOWN_SECONDS=120
# set VLLM_BASE_URL + VLLM_API_KEY after deploy (never commit tokens)
modal run deploy/modal_vllm.py::download_model
modal deploy deploy/modal_vllm.py --strategy recreate
sandbox cutover --profile modal-vllm
sandbox run benchmark-check --config config/runs/run-20-insurance-claims-specialist-awq.yaml
sandbox run preflight --config config/runs/run-20-insurance-claims-specialist-awq.yaml --live
sandbox run start --config config/runs/run-20-insurance-claims-specialist-awq.yaml --job-mode endpoint --watch
./deploy/teardown_vllm.sh
```

## Notes

- *Data note (2026-09-28):* `reports/serving/run-20-insurance-claims-specialist-awq.serving.json`
  was exported from the run store and infers wall from item timestamps (428.984 s →
  gpu 429.345 s, $0.09541, speedup 5.97×). This report and `archive/MODAL-RUNS-REPORT.md`
  use the harness busy interval (422.152 s → $0.093892, 6.07×). Its `prompt_version`
  `insurance_claims_specialist_v1` is the eval-environment catalog key for the same
  bytes as the `insurance_claims_specialist_simplified` pin (`config/prompts/eval_environment_lineage.json`).

- Phoenix `ModuleNotFoundError: opentelemetry` warnings during the run were **soft
  failures** in vendored `phoenix_setup.py` (tracing init catches and continues).
  They did **not** fail items. Fix applied mid-run: installed
  `opentelemetry-sdk` + `opentelemetry-exporter-otlp-proto-http` into `.venv`
  via `uv pip`, and set `PHOENIX_TRACING=disabled` in local `.env` (sink was
  already `none` for this specialist run).
- Cold-boot figure is near-zero because `/v1/models` was probed while the L4
  container was already warm from the health check before `start`.
