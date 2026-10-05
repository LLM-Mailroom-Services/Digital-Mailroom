# Insurance Claims — 2× L4 · C32 · n=50

**Run:** `grid-50-insurance-claims-specialist-awq-2l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `grid-50-insurance-claims-specialist-awq-2l4` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 50 |
| Spec hash | cc07eba2… |
| **Time** |  |
| Wall (busy) | 35.60 s |
| GPU seconds | 35.93 s |
| Cold boot | 0.33 s |
| **Cost** |  |
| Busy-window GPU $ | $0.015822 |
| Billed GPU $ (incl. boot) | $0.015967 |
| Idle $ | $0.001286 (2.89 s) |
| Cost per document | $0.000316 |
| Cost per ok document | $0.000316 |
| Cost per 1M tokens | $0.0867 |
| **Tokens** |  |
| Prompt tokens | 162,525 |
| Completion tokens | 20,014 (11.0%) |
| Total tokens | 182,539 |
| Tokens per document | 3,651 |
| Per document: instructions + template | 2,707 (74.2%) |
| Per document: document text | 543 (14.9%) |
| Per document: output | 400 (11.0%) |
| Instruction tokens per model call | 2,707 over 50 calls |
| Token split basis | fit across documents, 4.58 chars/token |
| Completion p95 / max (ok docs) | 709 / 956 |
| **Throughput** |  |
| Tokens / second | 5,127.5 |
| Tokens / second per L4 | 2,563.8 |
| Documents / minute | 84.27 |
| **Latency (per document, ok rows)** |  |
| Mean | 20.93 s |
| p50 | 19.64 s |
| p95 | 32.63 s |
| Max | 33.37 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 29.40× of 32 |
| Slot occupancy | 91.9% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 24 / 26 |
| Mean TTFT per replica | 2.411 s / 3.608 s |
| Prefix-cache hit per replica | 55.1% / 58.3% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **Quality** |  |
| Overall extraction score | 0.6859 (sd 0.068) |
| Score min / max | 0.5417 / 0.8056 |
| Scoring method | `suite` |
| Schema-valid rate | 0.24 |
| Parse errors | 0 |
| Errors | 0 / 50 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-df5ebe3e7263b6c6` | yes | 0.6240 | 15.3 | 2815 | 290 | — |
| 2 | `DOC-826b2ac305c2b791` | yes | 0.6955 | 15.3 | 2810 | 283 | — |
| 3 | `DOC-db1d2b3ea4d2d24f` | yes | 0.6750 | 15.3 | 2804 | 285 | — |
| 4 | `DOC-d6d57b7a18431923` | yes | 0.6959 | 15.3 | 2803 | 290 | — |
| 5 | `DOC-b28fe495a873ca59` | yes | 0.6895 | 16.5 | 2807 | 286 | — |
| 6 | `DOC-7a128ee6e786bd0e` | yes | 0.7024 | 16.6 | 2808 | 293 | — |
| 7 | `DOC-596b1f881ecf4a8a` | yes | 0.7163 | 16.7 | 2806 | 322 | — |
| 8 | `DOC-b3be1f4b2b6142ed` | yes | 0.6955 | 17.1 | 2815 | 331 | — |
| 9 | `DOC-fa698a867428a0ed` | yes | 0.6353 | 17.5 | 3016 | 335 | — |
| 10 | `DOC-ee3512878a0003b7` | yes | 0.7930 | 17.5 | 2831 | 332 | — |
| 11 | `DOC-2d2ec2092b012662` | yes | 0.8000 | 17.8 | 2831 | 340 | — |
| 12 | `DOC-dc33a3e5a8cf5b6b` | yes | 0.8056 | 17.8 | 2832 | 342 | — |
| 13 | `DOC-c0d9bf1e6be4ad51` | yes | 0.7015 | 18.0 | 2808 | 311 | — |
| 14 | `DOC-c0e145a5a0a0d4bd` | yes | 0.7930 | 18.3 | 2833 | 342 | — |
| 15 | `DOC-9f75d0ce11867685` | yes | 0.6345 | 19.1 | 3044 | 333 | — |
| 16 | `DOC-edc5811634a19b7a` | yes | 0.8056 | 19.8 | 2835 | 338 | — |
| 17 | `DOC-8dcc97d49f2004f5` | yes | 0.7986 | 19.9 | 2835 | 344 | — |
| 18 | `DOC-bce319dabbc42e89` | yes | 0.7991 | 20.7 | 2831 | 350 | — |
| 19 | `DOC-4cd6ca1171e8885e` | yes | 0.7729 | 21.9 | 2832 | 352 | — |
| 20 | `DOC-bf5c2cc12aca8aad` | yes | 0.7830 | 22.0 | 2834 | 357 | — |
| 21 | `DOC-4fd4cf5db3cfdb47` | yes | 0.6839 | 22.8 | 2940 | 357 | — |
| 22 | `DOC-884dc887726dcfa5` | yes | 0.7375 | 23.4 | 2833 | 350 | — |
| 23 | `DOC-d5e1b8ed3350fb36` | yes | 0.6290 | 23.8 | 2969 | 363 | — |
| 24 | `DOC-a1a2afde18ded42d` | yes | 0.6843 | 24.4 | 3086 | 382 | — |
| 25 | `DOC-a0be2aba09a3f580` | yes | 0.6913 | 25.0 | 3095 | 358 | — |
| 26 | `DOC-4dda6e74e78edd70` | yes | 0.6428 | 25.5 | 2949 | 375 | — |
| 27 | `DOC-85e24caa52979f50` | yes | 0.7114 | 25.7 | 3121 | 386 | — |
| 28 | `DOC-1e95a2ae82adc61c` | yes | 0.6817 | 26.2 | 3143 | 395 | — |
| 29 | `DOC-2435c398b95844bc` | yes | 0.7009 | 26.8 | 3080 | 459 | — |
| 30 | `DOC-17abdc452037b6eb` | yes | 0.6930 | 26.8 | 3129 | 417 | — |
| 31 | `DOC-576c9233159914e3` | yes | 0.6825 | 29.7 | 3080 | 505 | — |
| 32 | `DOC-ab3b194998a42322` | yes | 0.6131 | 17.4 | 3016 | 338 | — |
| 33 | `DOC-dcb4333f78bfe249` | yes | 0.6411 | 33.4 | 2934 | 332 | — |
| 34 | `DOC-a0c5db2835e31ef6` | yes | 0.6010 | 16.8 | 2871 | 334 | — |
| 35 | `DOC-b199013b1823372d` | yes | 0.5827 | 16.3 | 2882 | 343 | — |
| 36 | `DOC-804fbeed2ab25ae8` | yes | 0.5809 | 16.8 | 2873 | 349 | — |
| 37 | `DOC-d62e0d8ac987119d` | yes | 0.6265 | 19.4 | 3031 | 410 | — |
| 38 | `DOC-01f1577c446c646d` | yes | 0.5993 | 18.2 | 2868 | 332 | — |
| 39 | `DOC-4e21681f375a247d` | yes | 0.6411 | 18.4 | 2985 | 347 | — |
| 40 | `DOC-1bc5f212af3bd4c2` | yes | 0.6279 | 20.1 | 2990 | 401 | — |
| 41 | `DOC-4348717727f6d6b4` | yes | 0.6456 | 20.2 | 3004 | 383 | — |
| 42 | `DOC-f80fe4950664c6e0` | yes | 0.5952 | 18.4 | 2884 | 366 | — |
| 43 | `DOC-91fe413a7105d6fc` | yes | 0.6924 | 20.1 | 5106 | 491 | — |
| 44 | `DOC-db02c129ee1d5261` | yes | 0.6961 | 19.2 | 5515 | 529 | — |
| 45 | `DOC-06844413e427f8c2` | yes | 0.7653 | 19.2 | 5336 | 559 | — |
| 46 | `DOC-009ee40e247a0a6e` | yes | 0.5417 | 21.1 | 4688 | 541 | — |
| 47 | `DOC-e08d7fd014fde496` | yes | 0.6711 | 22.2 | 4487 | 554 | — |
| 48 | `DOC-d3f320a3ba9c105b` | yes | 0.5976 | 24.9 | 5234 | 709 | — |
| 49 | `DOC-4df9e8f7fd1c31c3` | yes | 0.6685 | 32.6 | 4883 | 937 | — |
| 50 | `DOC-0966e6d5a9e7bd71` | yes | 0.7532 | 33.1 | 4683 | 956 | — |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `grid-50-insurance-claims-specialist-awq-2l4.card.json`._
