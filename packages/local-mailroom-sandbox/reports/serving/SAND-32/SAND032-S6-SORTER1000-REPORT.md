# SAND-032 sand032-s6-sorter1000 — isolated LLM sorter (SorterAgent only)

Public HF `mailroom-dataset` @ `ed7576b` only (no partner or proprietary data). `task: isolated` calls `SorterAgent` alone — no reviewer, specialist, or judge prompts.

| field | value |
| --- | --- |
| engine | `Qwen/Qwen3-8B-AWQ`, 2× L4, seqs 16, kv `fp8`, `awq_marlin`, graphs [1, 2, 4, 8, 16], batched tokens default |
| concurrency | 32 |
| docs ok / total | 457 / 458 |
| **accuracy** | **0.8950** |
| **macro-F1** | **0.8635** |
| wall s | 1791.4 |
| tok/s | 8475 |
| GPU $/doc | 0.001869 |
| latency p50 / p95 s | 37.0 / 530.5 |
| prompt tokens p50 / max | 7994 / 297760 |
| completion tokens p50 / max | 147 / 4602 |

## Figures

![Per-class F1 for the isolated sorter](../figures/sand032-s6-sorter1000-per-class-f1.svg)

_Table view: **Per-class** below._

## Per-class

| class | n | precision | recall | F1 |
| --- | --- | --- | --- | --- |
| contract | 181 | 0.796 | 0.994 | 0.885 |
| corporate_record | 136 | 0.990 | 0.743 | 0.849 |
| correspondence | 41 | 1.000 | 0.951 | 0.975 |
| insurance_claim | 81 | 0.988 | 1.000 | 0.994 |
| merger_agreement | 18 | 1.000 | 0.444 | 0.615 |

## Confusion matrix

| expected ↓ / predicted → | contract | corporate_record | correspondence | insurance_claim | merger_agreement |
| --- | --- | --- | --- | --- | --- |
| contract | 180 | 0 | 0 | 1 | 0 |
| corporate_record | 35 | 101 | 0 | 0 | 0 |
| correspondence | 1 | 1 | 39 | 0 | 0 |
| insurance_claim | 0 | 0 | 0 | 81 | 0 |
| merger_agreement | 10 | 0 | 0 | 0 | 8 |

## Findings

- The vendored sorter reads whole documents: a ~5.4k-token base prompt plus chunked long docs (prompt tokens scale with document length). This run is prefill-bound; a head-truncated sorter input is the main cost lever for the runbook.
- Items recorded before the storage fix carry `SorterAgent.classify`'s tuple as a string; scores here come from `scripts/sand032/rescore.py` (post hoc, no LLM calls).
