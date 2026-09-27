# Run report — `run-20-contracts-awq-c8`

SAND-019 **corrected + 8-concurrency** AWQ contracts run. Same 20-contract
seeded draw (seed 42, fingerprint `9c87afb3c10c`) as `run-20-contracts-awq`, so
c4/c8 are directly comparable. Three changes vs the c4 run: window 16384 ->
32768, run-scoped `max_tokens` 4096 -> 8192, concurrency 4 -> 8.

| | |
|---|---|
| run_id | `run-20-contracts-awq-c8` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v33` (local, pinned) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1x L4 |
| context / quant | `max_model_len=32768`, AWQ, gpu_util=0.90, max_num_seqs=256 |
| run-scoped knobs | `contracts_specialist.max_tokens=8192`, `max_input_chars=24000` (SANDBOX_AGENT_KNOBS) |
| profile / provider | `modal-vllm` / `vllm` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `46a4d3c2`, seed 42 |
| draw | 20 contract docs (seeded class bucket; identical to c4) |
| git | `0d1fac8` |
| spec_hash | `a3ea308024c737e04b0e9d4674851492e946a82f229af1d2f4a51e9ea59ce255` |

## Headline results

| metric | value |
|---|---|
| docs ok / total | **17 / 20** (`error_count=3`) |
| **overall_extraction_score** | **0.0** (not measurable from Hub GT — see below) |
| offline_fallback rows | 0 |

## Serving / cost metrics

| metric | value |
|---|---|
| wall (busy interval) | 1528.047 s |
| concurrency | 8 |
| cold boot (measured) | 161.144 s |
| gpu_seconds | 1689.19 s (wall + cold boot) |
| estimated GPU cost | **$0.375376** |
| cost per document | $0.01876880 |
| latency e2e / p50 / max | 532.049 / 619.629 / 817.619 s |
| prompt / completion / total tokens | 194388 / 25614 / 220002 |
| throughput | 143.98 tok/s |
| cost cap | $0.55 (config) -> under cap |

**Concurrency proof (effective, not serialized):**
- sum(per-doc latency) = 10641.0 s
- wall = 1528.047 s -> speedup **6.96x** at concurrency 8
- serial would show wall ~= sum(latency); the observed speedup ≈ the configured 8-way fan-out.

## Corrections: what landed and what did not

| issue in c4 | status in c8 |
|---|---|
| `400` context overflow (12289 in + 4096 out > 16384) | **FIXED** by the 32768 window |
| `LengthFinishReasonError` at 4096 output | **NOT fixed** — 3 docs hit the raised 8192 cap. Raising `max_input_chars` 18000->24000 let the model see more and emit more, so the cap moved rather than cleared. |
| concurrency 4 | **c8, effective** — 6.96x sum/wall, though p50 rose (8 long decodes share one L4) |

### Residual errors (3/20)

All three are `LengthFinishReasonError` (the model produced the full 8192-token
budget without terminating a parseable object). The c4 `400` is gone; the
truncation is now the only failure mode. Recommended next step: **guided/JSON
structured decoding (xgrammar) or a tighter contract prompt**, not a larger
`max_tokens` — an 8192 budget already costs ~2x decode and the p50 shows it.

## Accuracy is not measurable from this GT

Every row scores `0.0` — but that is a **ground-truth gap, not a model verdict**:
the Hub `ground_truth` config carries *triage* labels for contracts
(`intent`, `keywords`, `cuad_clause_labels` — empty `{}` for this draw — `maud_clause_labels`),
not the contract extraction schema the scorer evaluates (`parties`, `governing_law`,
`term_length`, `cuad_clauses`, ...). The per-row audit confirms it
(`matched_gt=0` for every field; `entity_list_scores={}`). Correspondence had a
1:1 GT vocabulary; contracts does not. **Contract extraction accuracy is
unmeasurable until the Hub GT is extended with the contract schema** (a data
card, not a harness change).

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | latency s | prompt tok | compl tok | error |
|---|---|---|---|---|---|---|---|---|
| 1 | `DOC-d70e8d97f84d8b0d` | Supply | 0.0 | 0.0 | 727.6 | 8748 | 1104 | None |
| 2 | `DOC-4df3ec0469a627b0` | Consulting Agreements | 0.0 | 0.0 | 80.9 | 13049 | 1677 | None |
| 3 | `DOC-c1aa1b554216024f` | IP | 0.0 | 0.0 | 91.3 | 7991 | 386 | None |
| 4 | `DOC-30c38dd3a2964c8e` | Development | 0.0 | 0.0 | 178.1 | 13315 | 1186 | None |
| 5 | `DOC-385a86c69f8e562c` | Sponsorship | 0.0 | 0.0 | 140.1 | 11467 | 1659 | None |
| 6 | `DOC-fa0782d2f5c0b92b` | Collaboration | 0.0 | 0.0 | 439.8 | None | None | LengthFinish |
| 7 | `DOC-b4afef1ebe586f9d` | Collaboration | 0.0 | 0.0 | 697.6 | None | None | LengthFinish |
| 8 | `DOC-8cae10ecec1f5866` | Development | 0.0 | 0.0 | 29.3 | 13283 | 759 | None |
| 9 | `DOC-c6361838af8260cf` | Collaboration | 0.0 | 0.0 | 739.4 | 12866 | 1334 | None |
| 10 | `DOC-f5896eb268079643` | Strategic Alliance | 0.0 | 0.0 | 779.5 | 12794 | 3029 | None |
| 11 | `DOC-e69313c4bb90489c` | Transportation | 0.0 | 0.0 | 817.6 | 13485 | 1559 | None |
| 12 | `DOC-f8b0d4bcbac60ca2` | Endorsement | 0.0 | 0.0 | 805.8 | 8731 | 1364 | None |
| 13 | `DOC-5a81b8611e5a352c` | Promotion | 0.0 | 0.0 | 807.2 | 13300 | 1253 | None |
| 14 | `DOC-d500e66c59a36220` | Distributor | 0.0 | 0.0 | 627.6 | 11045 | 2837 | None |
| 15 | `DOC-035731e655e67aab` | Endorsement | 0.0 | 0.0 | 611.7 | None | None | LengthFinish |
| 16 | `DOC-ad2584f5a3504c6f` | Sponsorship | 0.0 | 0.0 | 627.8 | 12131 | 1533 | None |
| 17 | `DOC-fe06800cc62e5e19` | Reseller | 0.0 | 0.0 | 658.5 | 12686 | 2375 | None |
| 18 | `DOC-4b57f485708ab60b` | Collaboration | 0.0 | 0.0 | 610.5 | 11546 | 1477 | None |
| 19 | `DOC-f66065aa2d79804f` | IP | 0.0 | 0.0 | 588.7 | 8871 | 979 | None |
| 20 | `DOC-01849fa3020a5ac1` | Strategic Alliance | 0.0 | 0.0 | 582.1 | 9080 | 1103 | None |

- ok rows: 17/20; all ok rows score 0.0 (GT gap above)

## API comparison

Headline cost/token metrics for the local/Modal vs OpenRouter comparison live in
[`RUN-20-CONTRACTS-AWQ-C8-SERVING.md`](RUN-20-CONTRACTS-AWQ-C8-SERVING.md) and the
machine-readable twin (regenerate with `sandbox metrics serving-record --run …`;
`job.metrics.serving_record_from_store` extends the API-bucket `record_from_run` base).

