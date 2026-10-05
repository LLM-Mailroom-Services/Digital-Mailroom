# Insurance Claims — 2× L4 · C32 · n=100

**Run:** `sand40-100-insurance-claims-specialist-awq-2l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Draw | 100 docs (fingerprint d78a97b685ab) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand40-100-insurance-claims-specialist-awq-2l4` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 100 |
| Spec hash | a21e118a… |
| **Time** |  |
| Wall (busy) | 81.50 s |
| GPU seconds | 81.79 s |
| Cold boot | 0.29 s |
| **Cost** |  |
| Busy-window GPU $ | $0.036223 |
| Billed GPU $ (incl. boot) | $0.036352 |
| Idle $ | $0.005584 (12.56 s) |
| Cost per document | $0.000362 |
| Cost per ok document | $0.000362 |
| Cost per 1M tokens | $0.0982 |
| **Tokens** |  |
| Prompt tokens | 327,213 |
| Completion tokens | 41,631 (11.3%) |
| Total tokens | 368,844 |
| Tokens per document | 3,688 |
| Per document: instructions + template | 2,702 (73.2%) |
| Per document: document text | 570 (15.5%) |
| Per document: output | 416 (11.3%) |
| Instruction tokens per model call | 2,702 over 100 calls |
| Token split basis | fit across documents, 4.46 chars/token |
| Completion p95 / max (ok docs) | 697 / 1,683 |
| **Throughput** |  |
| Tokens / second | 4,525.6 |
| Tokens / second per L4 | 2,262.8 |
| Documents / minute | 73.62 |
| **Latency (per document, ok rows)** |  |
| Mean | 22.06 s |
| p50 | 20.42 s |
| p95 | 38.45 s |
| Max | 58.46 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 27.07× of 32 |
| Slot occupancy | 84.6% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 48 / 52 |
| Mean TTFT per replica | 2.247 s / 3.227 s |
| Prefix-cache hit per replica | 40.2% / 40.6% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **Quality** |  |
| Overall extraction score | 0.6715 (sd 0.064) |
| Score min / max | 0.5796 / 0.8056 |
| Scoring method | `suite` |
| Schema-valid rate | 0.23 |
| Parse errors | 0 |
| Errors | 0 / 100 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-8cf0d471d8ec695d` | yes | 0.7967 | 15.5 | 2830 | 343 | — |
| 2 | `DOC-fa698a867428a0ed` | yes | 0.6387 | 15.3 | 3016 | 341 | — |
| 3 | `DOC-edc5811634a19b7a` | yes | 0.8056 | 15.5 | 2835 | 341 | — |
| 4 | `DOC-dcb4333f78bfe249` | yes | 0.6363 | 15.5 | 2934 | 338 | — |
| 5 | `DOC-28295fb236ac02ca` | yes | 0.6341 | 15.3 | 2959 | 331 | — |
| 6 | `DOC-884dc887726dcfa5` | yes | 0.7375 | 15.5 | 2833 | 350 | — |
| 7 | `DOC-4fd4cf5db3cfdb47` | yes | 0.6309 | 15.6 | 2940 | 359 | — |
| 8 | `DOC-b1fad3c1c6ab0f6a` | yes | 0.6442 | 15.7 | 2949 | 358 | — |
| 9 | `DOC-e818dc7448fea142` | yes | 0.8000 | 15.7 | 2835 | 357 | — |
| 10 | `DOC-3ddb0ec69ce4f93f` | yes | 0.6487 | 15.7 | 2949 | 361 | — |
| 11 | `DOC-8dcc97d49f2004f5` | yes | 0.7908 | 17.3 | 2835 | 311 | — |
| 12 | `DOC-89dbe9bbd1ae3838` | yes | 0.6442 | 17.6 | 2972 | 366 | — |
| 13 | `DOC-ee3512878a0003b7` | yes | 0.7930 | 18.2 | 2831 | 332 | — |
| 14 | `DOC-2d2ec2092b012662` | yes | 0.8000 | 18.9 | 2831 | 340 | — |
| 15 | `DOC-e7bc347246615526` | yes | 0.6298 | 18.8 | 2949 | 338 | — |
| 16 | `DOC-c89c9134db9e8f1e` | yes | 0.6398 | 19.6 | 3002 | 344 | — |
| 17 | `DOC-1e95a2ae82adc61c` | yes | 0.6817 | 19.8 | 3143 | 392 | — |
| 18 | `DOC-c0e145a5a0a0d4bd` | yes | 0.7930 | 20.3 | 2833 | 342 | — |
| 19 | `DOC-2d574972cb7a2f63` | yes | 0.6396 | 20.6 | 2980 | 350 | — |
| 20 | `DOC-bce319dabbc42e89` | yes | 0.7991 | 21.0 | 2831 | 350 | — |
| 21 | `DOC-4cd6ca1171e8885e` | yes | 0.7729 | 21.5 | 2832 | 355 | — |
| 22 | `DOC-9f75d0ce11867685` | yes | 0.6345 | 21.4 | 3044 | 352 | — |
| 23 | `DOC-d5e1b8ed3350fb36` | yes | 0.6290 | 22.3 | 2969 | 363 | — |
| 24 | `DOC-d3d2943dbe2d4ef9` | yes | 0.6368 | 23.0 | 2991 | 369 | — |
| 25 | `DOC-4dda6e74e78edd70` | yes | 0.6428 | 23.3 | 2949 | 375 | — |
| 26 | `DOC-85e8bca0769880bf` | yes | 0.6978 | 24.2 | 3141 | 389 | — |
| 27 | `DOC-a1a2afde18ded42d` | yes | 0.6885 | 24.8 | 3086 | 399 | — |
| 28 | `DOC-576c9233159914e3` | yes | 0.6825 | 26.5 | 3080 | 448 | — |
| 29 | `DOC-e0c3e056397d7806` | yes | 0.6375 | 12.7 | 2812 | 278 | — |
| 30 | `DOC-b3be1f4b2b6142ed` | yes | 0.6955 | 14.7 | 2815 | 289 | — |
| 31 | `DOC-63692b8a349be3ad` | yes | 0.6237 | 12.7 | 2808 | 294 | — |
| 32 | `DOC-89fc7bbb8ccef92c` | yes | 0.7133 | 15.6 | 3052 | 306 | — |
| 33 | `DOC-ed19a2628827f390` | yes | 0.7029 | 12.3 | 2811 | 298 | — |
| 34 | `DOC-c0d9bf1e6be4ad51` | yes | 0.7015 | 16.5 | 2808 | 314 | — |
| 35 | `DOC-df5ebe3e7263b6c6` | yes | 0.7051 | 12.1 | 2815 | 286 | — |
| 36 | `DOC-4d04bd1e2f23c81b` | yes | 0.7132 | 12.8 | 2799 | 299 | — |
| 37 | `DOC-1898a0fbb779070c` | yes | 0.6842 | 17.4 | 3068 | 340 | — |
| 38 | `DOC-0ed0eb663781836b` | yes | 0.6969 | 15.6 | 2806 | 280 | — |
| 39 | `DOC-7eb9512b93dd2f13` | yes | 0.6154 | 18.2 | 2807 | 290 | — |
| 40 | `DOC-826b2ac305c2b791` | yes | 0.6955 | 12.4 | 2810 | 283 | — |
| 41 | `DOC-db1d2b3ea4d2d24f` | yes | 0.7417 | 14.0 | 2804 | 281 | — |
| 42 | `DOC-a0be2aba09a3f580` | yes | 0.6913 | 19.1 | 3095 | 362 | — |
| 43 | `DOC-21ffbe92b56f949c` | yes | 0.6821 | 13.9 | 2806 | 277 | — |
| 44 | `DOC-d6d57b7a18431923` | yes | 0.6959 | 13.5 | 2803 | 276 | — |
| 45 | `DOC-b6993f654cb64a38` | yes | 0.6821 | 13.4 | 2810 | 290 | — |
| 46 | `DOC-7a128ee6e786bd0e` | yes | 0.7024 | 20.0 | 2808 | 303 | — |
| 47 | `DOC-596b1f881ecf4a8a` | yes | 0.6496 | 17.0 | 2806 | 297 | — |
| 48 | `DOC-b28fe495a873ca59` | yes | 0.6895 | 16.8 | 2807 | 300 | — |
| 49 | `DOC-35939293b668a1b0` | yes | 0.6895 | 14.1 | 2808 | 270 | — |
| 50 | `DOC-e572745d557c7fbf` | yes | 0.6894 | 22.0 | 3125 | 413 | — |
| 51 | `DOC-89236fcc6aa82a3d` | yes | 0.8000 | 37.6 | 2834 | 352 | — |
| 52 | `DOC-bf5c2cc12aca8aad` | yes | 0.7935 | 38.4 | 2834 | 345 | — |
| 53 | `DOC-dc33a3e5a8cf5b6b` | yes | 0.8012 | 38.5 | 2832 | 345 | — |
| 54 | `DOC-17abdc452037b6eb` | yes | 0.7041 | 23.3 | 3129 | 433 | — |
| 55 | `DOC-aacaf03452045b89` | yes | 0.6131 | 17.8 | 2981 | 385 | — |
| 56 | `DOC-85e24caa52979f50` | yes | 0.6836 | 26.1 | 3121 | 377 | — |
| 57 | `DOC-8bb9c14eb11704f2` | yes | 0.6220 | 19.9 | 3003 | 365 | — |
| 58 | `DOC-c7f433bb70f6ab0e` | yes | 0.6152 | 19.5 | 2986 | 331 | — |
| 59 | `DOC-1bc5f212af3bd4c2` | yes | 0.6454 | 21.5 | 2990 | 439 | — |
| 60 | `DOC-2435c398b95844bc` | yes | 0.6795 | 47.9 | 3080 | 485 | — |
| 61 | `DOC-c6339c641d801de5` | yes | 0.6152 | 16.6 | 3023 | 312 | — |
| 62 | `DOC-79244cf752911808` | yes | 0.6176 | 17.9 | 2969 | 331 | — |
| 63 | `DOC-4348717727f6d6b4` | yes | 0.6456 | 20.8 | 3004 | 391 | — |
| 64 | `DOC-fc5aa23171d955cf` | yes | 0.6265 | 19.9 | 2972 | 372 | — |
| 65 | `DOC-ab3b194998a42322` | yes | 0.6131 | 21.9 | 3016 | 378 | — |
| 66 | `DOC-a0c5db2835e31ef6` | yes | 0.6010 | 18.6 | 2871 | 334 | — |
| 67 | `DOC-d52f175e739a5f5f` | yes | 0.6265 | 22.7 | 2974 | 325 | — |
| 68 | `DOC-1f15cce85d6c9f8f` | yes | 0.6138 | 22.2 | 3012 | 373 | — |
| 69 | `DOC-13597dd5f0ca00c4` | yes | 0.5796 | 20.6 | 2888 | 345 | — |
| 70 | `DOC-01f1577c446c646d` | yes | 0.5993 | 21.8 | 2868 | 330 | — |
| 71 | `DOC-f80fe4950664c6e0` | yes | 0.5910 | 20.1 | 2884 | 344 | — |
| 72 | `DOC-0596b6ff5f3f7028` | yes | 0.5957 | 21.7 | 2912 | 375 | — |
| 73 | `DOC-56b5ff2db7cab57f` | yes | 0.6105 | 23.5 | 3019 | 411 | — |
| 74 | `DOC-4e21681f375a247d` | yes | 0.6411 | 24.8 | 2985 | 347 | — |
| 75 | `DOC-fa4420dfb29b9410` | yes | 0.5810 | 21.2 | 2908 | 389 | — |
| 76 | `DOC-9178d6cdb14bfac9` | yes | 0.6010 | 23.1 | 2872 | 344 | — |
| 77 | `DOC-804fbeed2ab25ae8` | yes | 0.5809 | 24.0 | 2873 | 349 | — |
| 78 | `DOC-5b455f179d11b3d3` | yes | 0.5910 | 21.3 | 2903 | 398 | — |
| 79 | `DOC-27b23fd94cc70d9d` | yes | 0.6052 | 26.5 | 2890 | 362 | — |
| 80 | `DOC-ec76076167291255` | yes | 0.6131 | 30.3 | 2974 | 384 | — |
| 81 | `DOC-b199013b1823372d` | yes | 0.5827 | 24.0 | 2882 | 343 | — |
| 82 | `DOC-2bb9b262e943bc89` | yes | 0.6265 | 28.0 | 3056 | 384 | — |
| 83 | `DOC-ffc9528cf71610fc` | yes | 0.6138 | 29.3 | 2986 | 390 | — |
| 84 | `DOC-d62e0d8ac987119d` | yes | 0.6265 | 32.1 | 3031 | 417 | — |
| 85 | `DOC-66a4bc121141fe7a` | yes | 0.6894 | 26.4 | 5690 | 436 | — |
| 86 | `DOC-0bdda3ecc67bae80` | yes | 0.6663 | 16.1 | 4998 | 435 | — |
| 87 | `DOC-cdd4f26b4f9db00c` | yes | 0.7779 | 19.5 | 4789 | 495 | — |
| 88 | `DOC-91fe413a7105d6fc` | yes | 0.6880 | 23.7 | 5106 | 503 | — |
| 89 | `DOC-65bd322c23c62250` | yes | 0.7004 | 26.4 | 4621 | 554 | — |
| 90 | `DOC-81a444ef841aea5f` | yes | 0.6164 | 33.9 | 4887 | 635 | — |
| 91 | `DOC-009ee40e247a0a6e` | yes | 0.6083 | 18.7 | 4688 | 568 | — |
| 92 | `DOC-e08d7fd014fde496` | yes | 0.6087 | 26.5 | 4487 | 531 | — |
| 93 | `DOC-06844413e427f8c2` | yes | 0.7649 | 22.2 | 5336 | 511 | — |
| 94 | `DOC-db02c129ee1d5261` | yes | 0.6926 | 24.4 | 5515 | 539 | — |
| 95 | `DOC-0966e6d5a9e7bd71` | yes | 0.7532 | 34.2 | 4683 | 956 | — |
| 96 | `DOC-d3f320a3ba9c105b` | yes | 0.5976 | 30.3 | 5234 | 697 | — |
| 97 | `DOC-4df9e8f7fd1c31c3` | yes | 0.6154 | 31.9 | 4883 | 937 | — |
| 98 | `DOC-02f77aa77391a8c2` | yes | 0.7531 | 44.2 | 5091 | 1299 | — |
| 99 | `DOC-46870fd360755337` | yes | 0.6732 | 55.0 | 5424 | 1683 | — |
| 100 | `DOC-da50072c19e4223c` | yes | 0.7260 | 58.5 | 5957 | 1647 | — |

_Generated 2026-10-01T06:44:51+00:00 by `sandbox run card`. Machine-readable twin: `sand40-100-insurance-claims-specialist-awq-2l4.card.json`._
