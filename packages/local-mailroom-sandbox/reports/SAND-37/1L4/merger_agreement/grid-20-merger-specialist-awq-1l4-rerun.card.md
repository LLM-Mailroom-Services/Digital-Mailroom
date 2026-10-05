# Merger Agreements — 1× L4 · C8 · n=20

**Run:** `grid-20-merger-specialist-awq-1l4-rerun` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | merger_agreement_specialist |
| Prompt | merger_agreement_specialist_simplified |
| Temperature | 0.7 (posture knob) |
| Output cap (max_tokens) | 8,192 |
| Input cap (max_input_chars) | 30,000 |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 20 docs (fingerprint 7e2b12cc13df) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `grid-20-merger-specialist-awq-1l4-rerun` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 20 |
| Spec hash | 42a52cdf… |
| **Time** |  |
| Wall (busy) | 316.14 s |
| GPU seconds | 316.68 s |
| Cold boot | 0.54 s |
| **Cost** |  |
| Busy-window GPU $ | $0.070254 |
| Billed GPU $ (incl. boot) | $0.070373 |
| Idle $ | $0.043172 (194.27 s) |
| Cost per document | $0.003513 |
| Cost per ok document | $0.003903 |
| Cost per 1M tokens | $0.3846 |
| **Tokens** |  |
| Prompt tokens | 167,210 |
| Completion tokens | 15,448 (8.5%) |
| Total tokens | 182,658 |
| Tokens per document | 10,148 |
| Per document: instructions + template | 2,623 (25.8%) |
| Per document: document text | 6,667 (65.7%) |
| Per document: output | 858 (8.5%) |
| Instruction tokens per model call | 2,623 over 18 calls |
| Token split basis | document chars ÷ 4.5 chars/token; instructions are the remainder |
| Completion p95 / max (ok docs) | 1,279 / 1,661 |
| **Throughput** |  |
| Tokens / second | 577.8 |
| Tokens / second per L4 | 577.8 |
| Documents / minute | 3.80 |
| **Latency (per document, ok rows)** |  |
| Mean | 54.16 s |
| p50 | 50.46 s |
| p95 | 66.15 s |
| Max | 113.31 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 4.92× of 8 |
| Slot occupancy | 61.4% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 20 |
| Mean TTFT per replica | 4.890 s |
| Prefix-cache hit per replica | 30.6% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 2 |
| **Quality** |  |
| Overall extraction score | 0.0129 (sd 0.024) |
| Score min / max | 0.0000 / 0.0625 |
| Scoring method | `suite+maud` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 2 / 20 |
| **Clause scoring (MAUD)** |  |
| Questions answered / labeled | 39 / 289 (13.5%) |
| Micro accuracy | 1.4% |
| Precision on answered | 10.3% |
| Clean subset | 2 / 121 |
| Suite field score (mean) | not captured |

## Errors

| Error | Count |
| --- | ---: |
| LengthFinishReasonError | 2 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-52f9a5be69429299` | yes | 0.0000 | 44.1 | 9517 | 537 | — |
| 2 | `DOC-0a733ab86f2390ae` | yes | 0.0000 | 51.8 | 8841 | 673 | — |
| 3 | `DOC-d0495abfa5f3d8ee` | yes | 0.0000 | 58.7 | 9008 | 796 | — |
| 4 | `DOC-c1d57615929b483e` | yes | 0.0625 | 58.7 | 9148 | 786 | — |
| 5 | `DOC-7430de65e5471741` | yes | 0.0526 | 65.5 | 9060 | 838 | — |
| 6 | `DOC-d554890e66786170` | yes | 0.0000 | 66.1 | 10446 | 857 | — |
| 7 | `DOC-5fbb9ee2f4b4b114` | yes | 0.0588 | 49.5 | 9027 | 814 | — |
| 8 | `DOC-5fa0ba13cf68b593` | yes | 0.0000 | 38.9 | 9125 | 628 | — |
| 9 | `DOC-30eda1e78a5f6fb5` | yes | 0.0000 | 49.4 | 9124 | 772 | — |
| 10 | `DOC-511062d64bc9afc6` | yes | 0.0000 | 45.6 | 9338 | 680 | — |
| 11 | `DOC-be8461dd68cfe458` | yes | 0.0000 | 113.3 | 9054 | 1661 | — |
| 12 | `DOC-f4e726a7f2c25494` | yes | 0.0000 | 51.4 | 9345 | 822 | — |
| 13 | `DOC-ecf69d7e102ef62a` | yes | 0.0000 | 57.6 | 9271 | 922 | — |
| 14 | `DOC-1e016055aa435e71` | yes | 0.0000 | 47.7 | 9148 | 814 | — |
| 15 | `DOC-63beb09b179ea4ee` | yes | 0.0000 | 46.9 | 9374 | 859 | — |
| 16 | `DOC-169bbcdc5d9e609c` | yes | 0.0000 | 35.1 | 9975 | 832 | — |
| 17 | `DOC-fcaddb5bdc94ce63` | yes | 0.0588 | 39.2 | 9123 | 878 | — |
| 18 | `DOC-03712a2b0a99a314` | yes | 0.0000 | 55.4 | 9286 | 1279 | — |
| 19 | `DOC-4ab4ecd86ecf275d` | no | — | 320.2 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9590, total_to |
| 20 | `DOC-8fe2855a2310cdbe` | no | — | 258.9 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9249, total_to |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `grid-20-merger-specialist-awq-1l4-rerun.card.json`._
