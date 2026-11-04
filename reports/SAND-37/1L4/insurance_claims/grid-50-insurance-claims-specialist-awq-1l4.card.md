# Insurance Claims — 1× L4 · C8 · n=50

**Run:** `grid-50-insurance-claims-specialist-awq-1l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | insurance_claims_specialist |
| Prompt | insurance_claims_specialist_simplified |
| Temperature | 0.1 (vendored call site) |
| Output cap (max_tokens) | 8,192 |
| Input cap (max_input_chars) | 13,500 |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 50 docs (fingerprint b53ba23fea0a) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `grid-50-insurance-claims-specialist-awq-1l4` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 50 |
| Spec hash | 01f8863b… |
| **Time** |  |
| Wall (busy) | 87.42 s |
| GPU seconds | 87.74 s |
| Cold boot | 0.32 s |
| **Cost** |  |
| Busy-window GPU $ | $0.019426 |
| Billed GPU $ (incl. boot) | $0.019498 |
| Idle $ | not captured |
| Cost per document | $0.000389 |
| Cost per ok document | $0.000389 |
| Cost per 1M tokens | $0.1065 |
| **Tokens** |  |
| Prompt tokens | 162,525 |
| Completion tokens | 19,876 (10.9%) |
| Total tokens | 182,401 |
| Tokens per document | 3,648 |
| Per document: instructions + template | 2,707 (74.2%) |
| Per document: document text | 543 (14.9%) |
| Per document: output | 398 (10.9%) |
| Instruction tokens per model call | 2,707 over 50 calls |
| Token split basis | fit across documents, 4.58 chars/token |
| Completion p95 / max (ok docs) | 624 / 956 |
| **Throughput** |  |
| Tokens / second | 2,086.6 |
| Tokens / second per L4 | 2,086.6 |
| Documents / minute | 34.32 |
| **Latency (per document, ok rows)** |  |
| Mean | 15.12 s |
| p50 | 13.96 s |
| p95 | 26.71 s |
| Max | 36.73 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 8.65× of 8 |
| Slot occupancy | 108.1% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 50 |
| Mean TTFT per replica | 0.997 s |
| Prefix-cache hit per replica | 57.9% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 0 |
| **Quality** |  |
| Overall extraction score | 0.6838 (sd 0.069) |
| Score min / max | 0.5809 / 0.8056 |
| Scoring method | `suite` |
| Schema-valid rate | 0.20 |
| Parse errors | 0 |
| Errors | 0 / 50 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-ee3512878a0003b7` | yes | 0.7930 | 12.8 | 2831 | 332 | — |
| 2 | `DOC-edc5811634a19b7a` | yes | 0.8056 | 12.8 | 2835 | 342 | — |
| 3 | `DOC-dc33a3e5a8cf5b6b` | yes | 0.8012 | 12.8 | 2832 | 342 | — |
| 4 | `DOC-c0e145a5a0a0d4bd` | yes | 0.7930 | 12.8 | 2833 | 346 | — |
| 5 | `DOC-4cd6ca1171e8885e` | yes | 0.7729 | 12.9 | 2832 | 352 | — |
| 6 | `DOC-bf5c2cc12aca8aad` | yes | 0.7830 | 13.0 | 2834 | 357 | — |
| 7 | `DOC-8dcc97d49f2004f5` | yes | 0.7908 | 15.4 | 2835 | 367 | — |
| 8 | `DOC-884dc887726dcfa5` | yes | 0.8000 | 16.8 | 2833 | 403 | — |
| 9 | `DOC-2d2ec2092b012662` | yes | 0.8000 | 12.4 | 2831 | 340 | — |
| 10 | `DOC-fa698a867428a0ed` | yes | 0.6453 | 10.1 | 3016 | 335 | — |
| 11 | `DOC-dcb4333f78bfe249` | yes | 0.6411 | 12.6 | 2934 | 350 | — |
| 12 | `DOC-bce319dabbc42e89` | yes | 0.7857 | 14.0 | 2831 | 359 | — |
| 13 | `DOC-4fd4cf5db3cfdb47` | yes | 0.6309 | 14.1 | 2940 | 364 | — |
| 14 | `DOC-4dda6e74e78edd70` | yes | 0.6387 | 14.8 | 2949 | 369 | — |
| 15 | `DOC-d5e1b8ed3350fb36` | yes | 0.6290 | 15.4 | 2969 | 372 | — |
| 16 | `DOC-9f75d0ce11867685` | yes | 0.6387 | 13.3 | 3044 | 342 | — |
| 17 | `DOC-b3be1f4b2b6142ed` | yes | 0.6955 | 8.5 | 2815 | 286 | — |
| 18 | `DOC-1e95a2ae82adc61c` | yes | 0.6817 | 14.2 | 3143 | 376 | — |
| 19 | `DOC-a1a2afde18ded42d` | yes | 0.6843 | 14.8 | 3086 | 396 | — |
| 20 | `DOC-a0be2aba09a3f580` | yes | 0.6885 | 12.1 | 3095 | 375 | — |
| 21 | `DOC-85e24caa52979f50` | yes | 0.6836 | 13.4 | 3121 | 392 | — |
| 22 | `DOC-17abdc452037b6eb` | yes | 0.6930 | 14.3 | 3129 | 410 | — |
| 23 | `DOC-2435c398b95844bc` | yes | 0.6795 | 17.2 | 3080 | 481 | — |
| 24 | `DOC-576c9233159914e3` | yes | 0.6825 | 18.9 | 3080 | 505 | — |
| 25 | `DOC-7a128ee6e786bd0e` | yes | 0.7024 | 9.2 | 2808 | 251 | — |
| 26 | `DOC-c0d9bf1e6be4ad51` | yes | 0.7015 | 11.6 | 2808 | 314 | — |
| 27 | `DOC-b28fe495a873ca59` | yes | 0.6895 | 10.7 | 2807 | 287 | — |
| 28 | `DOC-db1d2b3ea4d2d24f` | yes | 0.6750 | 10.5 | 2804 | 286 | — |
| 29 | `DOC-596b1f881ecf4a8a` | yes | 0.6496 | 10.9 | 2806 | 300 | — |
| 30 | `DOC-df5ebe3e7263b6c6` | yes | 0.7067 | 10.8 | 2815 | 283 | — |
| 31 | `DOC-d6d57b7a18431923` | yes | 0.6959 | 10.2 | 2803 | 276 | — |
| 32 | `DOC-826b2ac305c2b791` | yes | 0.6955 | 10.6 | 2810 | 281 | — |
| 33 | `DOC-1bc5f212af3bd4c2` | yes | 0.6138 | 14.2 | 2990 | 392 | — |
| 34 | `DOC-ab3b194998a42322` | yes | 0.6131 | 12.4 | 3016 | 370 | — |
| 35 | `DOC-4e21681f375a247d` | yes | 0.6188 | 12.2 | 2985 | 369 | — |
| 36 | `DOC-a0c5db2835e31ef6` | yes | 0.6010 | 10.7 | 2871 | 345 | — |
| 37 | `DOC-4348717727f6d6b4` | yes | 0.6331 | 13.9 | 3004 | 402 | — |
| 38 | `DOC-d62e0d8ac987119d` | yes | 0.6131 | 16.9 | 3031 | 397 | — |
| 39 | `DOC-804fbeed2ab25ae8` | yes | 0.5809 | 15.3 | 2873 | 349 | — |
| 40 | `DOC-01f1577c446c646d` | yes | 0.5993 | 15.5 | 2868 | 355 | — |
| 41 | `DOC-b199013b1823372d` | yes | 0.5827 | 17.7 | 2882 | 359 | — |
| 42 | `DOC-f80fe4950664c6e0` | yes | 0.5952 | 18.5 | 2884 | 366 | — |
| 43 | `DOC-91fe413a7105d6fc` | yes | 0.6822 | 24.2 | 5106 | 495 | — |
| 44 | `DOC-e08d7fd014fde496` | yes | 0.6087 | 20.7 | 4487 | 528 | — |
| 45 | `DOC-4df9e8f7fd1c31c3` | yes | 0.6051 | 27.8 | 4883 | 624 | — |
| 46 | `DOC-db02c129ee1d5261` | yes | 0.7439 | 22.0 | 5515 | 576 | — |
| 47 | `DOC-d3f320a3ba9c105b` | yes | 0.6187 | 26.7 | 5234 | 708 | — |
| 48 | `DOC-009ee40e247a0a6e` | yes | 0.6083 | 18.3 | 4688 | 558 | — |
| 49 | `DOC-06844413e427f8c2` | yes | 0.7653 | 18.2 | 5336 | 556 | — |
| 50 | `DOC-0966e6d5a9e7bd71` | yes | 0.7532 | 36.7 | 4683 | 956 | — |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `grid-50-insurance-claims-specialist-awq-1l4.card.json`._
