# Merger Agreements — 2× L4 · C32 · n=20

**Run:** `sand40-probe-20-merger-specialist-awq-2l4-64k` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | merger_agreement_specialist |
| Prompt | merger_agreement_specialist_maud_v1 |
| Temperature | 0.7 (posture knob) |
| Output cap (max_tokens) | 6,144 |
| Input cap (max_input_chars) | 128,000 |
| Optimized long-document settings | yes |
| top_p | 0.8 |
| top_k | 20 |
| presence_penalty | 1.0 |
| Length re-samples | 1 |
| Chunk window (chars) | 120000 |
| Chunk overlap (chars) | 8000 |
| hf_overrides | `{"rope_parameters": {"factor": 2.0, "original_max_position_embeddings": 32768, "rope_theta": 1000000, "rope_type": "yarn"}}` |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 20 docs (fingerprint 7e2b12cc13df) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 65536 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand40-probe-20-merger-specialist-awq-2l4-64k` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 20 |
| Spec hash | 92316045… |
| **Time** |  |
| Wall (busy) | 1,472.97 s |
| GPU seconds | 1,473.10 s |
| Cold boot | 0.14 s |
| **Cost** |  |
| Busy-window GPU $ | $0.654652 |
| Billed GPU $ (incl. boot) | $0.654713 |
| Idle $ | $0.427074 (960.92 s) |
| Cost per document | $0.032733 |
| Cost per ok document | $0.032733 |
| Cost per 1M tokens | $0.3249 |
| **Tokens** |  |
| Prompt tokens | 1,929,564 |
| Completion tokens | 85,063 (4.2%) |
| Total tokens | 2,014,627 |
| Tokens per document | 100,731 |
| Completion p95 / max (ok docs) | 8,297 / 12,770 |
| **Throughput** |  |
| Tokens / second | 1,367.7 |
| Tokens / second per L4 | 683.9 |
| Documents / minute | 0.81 |
| **Latency (per document, ok rows)** |  |
| Mean | 819.28 s |
| p50 | 760.86 s |
| p95 | 1,133.91 s |
| Max | 1,820.54 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 11.12× of 32 |
| Slot occupancy | 34.8% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 38 / 46 |
| Mean TTFT per replica | 16.933 s / 82.757 s |
| Prefix-cache hit per replica | 21.6% / 13.9% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 8 / 2 |
| **Quality** |  |
| Overall extraction score | 0.1233 (sd 0.077) |
| Score min / max | 0.0000 / 0.2500 |
| Scoring method | `suite+maud` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 0 / 20 |
| **Clause scoring (MAUD)** |  |
| Questions answered / labeled | 230 / 322 (71.4%) |
| Micro accuracy | 12.7% |
| Precision on answered | 17.8% |
| Clean subset | 15 / 135 |
| Suite field score (mean) | not captured |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-d0495abfa5f3d8ee` | yes | 0.1250 | 347.6 | 68549 | 1846 | — |
| 2 | `DOC-511062d64bc9afc6` | yes | 0.2500 | 513.2 | 94360 | 3209 | — |
| 3 | `DOC-1e016055aa435e71` | yes | 0.0000 | 611.2 | 103239 | 2569 | — |
| 4 | `DOC-7430de65e5471741` | yes | 0.2105 | 633.2 | 72975 | 3012 | — |
| 5 | `DOC-63beb09b179ea4ee` | yes | 0.2353 | 675.5 | 78473 | 3509 | — |
| 6 | `DOC-d554890e66786170` | yes | 0.1250 | 703.5 | 87818 | 3018 | — |
| 7 | `DOC-be8461dd68cfe458` | yes | 0.0000 | 704.5 | 80433 | 2940 | — |
| 8 | `DOC-30eda1e78a5f6fb5` | yes | 0.1667 | 707.8 | 101577 | 6182 | — |
| 9 | `DOC-03712a2b0a99a314` | yes | 0.1176 | 753.6 | 110354 | 4378 | — |
| 10 | `DOC-0a733ab86f2390ae` | yes | 0.1333 | 755.4 | 76100 | 3508 | — |
| 11 | `DOC-ecf69d7e102ef62a` | yes | 0.0714 | 766.3 | 92137 | 3870 | — |
| 12 | `DOC-8fe2855a2310cdbe` | yes | 0.1765 | 801.7 | 109179 | 3882 | — |
| 13 | `DOC-c1d57615929b483e` | yes | 0.0625 | 805.5 | 123059 | 3604 | — |
| 14 | `DOC-5fbb9ee2f4b4b114` | yes | 0.1765 | 823.2 | 73208 | 4556 | — |
| 15 | `DOC-f4e726a7f2c25494` | yes | 0.0000 | 863.9 | 68218 | 3247 | — |
| 16 | `DOC-169bbcdc5d9e609c` | yes | 0.0000 | 927.5 | 128031 | 4247 | — |
| 17 | `DOC-5fa0ba13cf68b593` | yes | 0.1333 | 1,008.2 | 101133 | 3499 | — |
| 18 | `DOC-fcaddb5bdc94ce63` | yes | 0.1765 | 1,029.3 | 77230 | 2920 | — |
| 19 | `DOC-52f9a5be69429299` | yes | 0.1176 | 1,133.9 | 98158 | 8297 | — |
| 20 | `DOC-4ab4ecd86ecf275d` | yes | 0.1875 | 1,820.5 | 185333 | 12770 | — |

_Generated 2026-10-01T04:48:47+00:00 by `sandbox run card`. Machine-readable twin: `sand40-probe-20-merger-specialist-awq-2l4-64k.card.json`._
