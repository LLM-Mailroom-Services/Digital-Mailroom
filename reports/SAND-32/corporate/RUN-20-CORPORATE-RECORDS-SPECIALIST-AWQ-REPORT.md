# Run report — `run-20-corporate-records-specialist-awq` (complete, clean)

Qwen AWQ corporate baseline: **corporate_records_specialist on 20
CORPORATE_RECORD docs** (quotas 4/4/3/2/2/2/1/1/1, test split), on
**Qwen/Qwen3-8B-AWQ** at **concurrency 8** on **1×L4** (MIN=MAX=1 pinned),
DMR-074 `corporate_records_specialist_simplified` pin. Hard retry cap
(`max_retries: 1`).

| | |
| --- | --- |
| run_id | `run-20-corporate-records-specialist-awq` |
| task / agent | `corporate_records_specialist` |
| prompt | `corporate_records_specialist_simplified` (local DMR-074 pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1×L4, `awq`, 32768 (same warm Qwen app; cold boot recorded once in merger report) |
| dataset | mailroom-dataset `ground_truth`, split=test, rev `46a4d3c2`, seed 42, draw `5a60f64b0989` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **20 / 0 / 20** |
| **overall_extraction_score** | **0.4231** (exact_match 0.4231) |
| schema_valid_rate | 0.95 (19/20) |
| parse errors | 0 |
| wall | 684.4 s |
| concurrency proof | sum latency 4418.0 s / wall 684.4 s = **6.46× at c=8** |
| prompt / completion / total tokens | 159804 / 30584 / 190388 |
| token-proxy cost | ≈ $0.0088 ($0.00044/doc) |
| est. GPU cost (busy) | $0.152 ($0.0076/doc) |
| caps | $0.40 / 2400 s → under cap |

Strongest Qwen AWQ leg of the sequence: perfect completion with the highest
measured extraction score (corporate 0.4231 vs correspondence AWQ 0.2280/0.2547;
merger legs unscored-or-zero for structural reasons).
