# Run report — `run-20-merger-specialist-awq` (complete)

Qwen AWQ cross-agent merger baseline: **contracts_specialist (CUAD v33 prompt)
on 20 MERGER_AGREEMENT docs** (quotas 7/7/3/2/1, train split — same draw
`624e026fc985` as the Granite merger leg for doc-level comparability), on
**Qwen/Qwen3-8B-AWQ** at **concurrency 8** on **1×L4** (MIN=MAX=1 pinned).

| | |
| --- | --- |
| run_id | `run-20-merger-specialist-awq` |
| task / agent | `contracts_specialist` (cross-agent by design — AGENT CONFOUND, see below) |
| prompt | `contracts_specialist_v33_simplified` (local DMR-074 pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1×L4, `awq`, 32768, gpu_util=0.90, max_num_seqs=6, APC on, eager on, no parsers |
| deploy | Qwen block R2 (cold boot #2 of sequence: 135 s → `/v1/models` 200; warm probe 0.25 s) |
| dataset | mailroom-dataset `ground_truth`, split=train, rev `46a4d3c2`, seed 42 |
| git | `3b8cecc` (c=8 enforcement) |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **15 / 5 / 20** |
| errors (all) | `OpenAIConnectionError: Connection error` ×5 (intermittent, ok docs interleaved — proxy saturation drops at c=8 on longest docs, not systematic) |
| overall_extraction_score / exact_match | **0.0** (agent-confound artifact: CUAD contract schema vs MAUD ground truth; schema_valid 1.0 on all 15 ok) |
| schema_valid_rate | 1.0 (15/15 ok) |
| wall (harness busy) | 740.1 s |
| command span (dispatch→summary) | ~102 min — client timeout/backoff inflation under c=8 saturation (cost finding, not a defect) |
| concurrency proof | sum latency 5278.6 s / wall 740.1 s = **7.13× at c=8** |
| prompt / completion / total tokens | 225182 / 23580 / 248762 |
| token-proxy cost | ≈ $0.0098 ($0.00065/ok-doc) |
| est. GPU cost (busy) | $0.164 ($0.0082/doc, $0.011/ok-doc) |
| caps | $0.70 / 3600 s → under cap |

## Qwen-vs-Granite merger delta

| | Granite (`run-20-merger-granite`, merger specialist) | Qwen (this run, contracts specialist) |
| --- | --- | --- |
| ok / fail (/20) | 11 / 5 (+4 unattempted, cap-abort) | **15 / 5** (complete) |
| score | unknown (abort pre-score) | 0.0 (schema mismatch, valid JSON) |
| wall | 5789.9 s (partial 16) | **740.1 s** (full 20) |
| GPU $ | $1.2866 (partial) | **$0.164** (full) |
| error mode | thinking-leakage parse fails | connection drops (transient) |
| decode behavior | ~12k tokens/doc @ ~19 tok/s | ~1.2k tokens/attempted doc (~1.6k per completed doc; connection errors return no usage) @ ~40+ tok/s |

Not a pure model delta (different agents by design): the clean reads are
throughput/cost (Qwen ~8× faster wall, ~8× cheaper GPU on full completes) and
robustness (Qwen fails transient, Granite fails systematic-parse).
