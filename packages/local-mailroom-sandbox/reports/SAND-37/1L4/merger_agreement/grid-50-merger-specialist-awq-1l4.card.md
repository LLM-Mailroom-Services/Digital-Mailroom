# Merger Agreements — 1× L4 · C8 · n=50

**Run:** `grid-50-merger-specialist-awq-1l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Draw | 50 docs (fingerprint 23c90708536e) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `grid-50-merger-specialist-awq-1l4` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 50 |
| Spec hash | 318540cd… |
| **Time** |  |
| Wall (busy) | 588.41 s |
| GPU seconds | 589.40 s |
| Cold boot | 0.99 s |
| **Cost** |  |
| Busy-window GPU $ | $0.130758 |
| Billed GPU $ (incl. boot) | $0.130979 |
| Idle $ | $0.056809 (255.64 s) |
| Cost per document | $0.002615 |
| Cost per ok document | $0.002843 |
| Cost per 1M tokens | $0.2768 |
| **Tokens** |  |
| Prompt tokens | 428,281 |
| Completion tokens | 44,106 (9.3%) |
| Total tokens | 472,387 |
| Tokens per document | 10,269 |
| Per document: instructions + template | 2,644 (25.7%) |
| Per document: document text | 6,667 (64.9%) |
| Per document: output | 959 (9.3%) |
| Instruction tokens per model call | 2,644 over 46 calls |
| Token split basis | document chars ÷ 4.5 chars/token; instructions are the remainder |
| Completion p95 / max (ok docs) | 1,798 / 2,535 |
| **Throughput** |  |
| Tokens / second | 802.8 |
| Tokens / second per L4 | 802.8 |
| Documents / minute | 5.10 |
| **Latency (per document, ok rows)** |  |
| Mean | 57.87 s |
| p50 | 51.26 s |
| p95 | 109.72 s |
| Max | 146.06 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 7.27× of 8 |
| Slot occupancy | 90.9% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 50 |
| Mean TTFT per replica | 2.351 s |
| Prefix-cache hit per replica | 36.9% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 4 |
| **Quality** |  |
| Overall extraction score | 0.0480 (sd 0.049) |
| Score min / max | 0.0000 / 0.1875 |
| Scoring method | `suite+maud` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 4 / 50 |
| **Clause scoring (MAUD)** |  |
| Questions answered / labeled | 179 / 751 (23.8%) |
| Micro accuracy | 4.8% |
| Precision on answered | 20.1% |
| Clean subset | 21 / 324 |
| Suite field score (mean) | not captured |

## Errors

| Error | Count |
| --- | ---: |
| LengthFinishReasonError | 4 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-c1d57615929b483e` | yes | 0.0000 | 52.6 | 9148 | 701 | — |
| 2 | `DOC-038a485469f83c9a` | yes | 0.0625 | 61.6 | 9115 | 876 | — |
| 3 | `DOC-eb2b56fe30dc35f4` | yes | 0.0588 | 62.0 | 8971 | 867 | — |
| 4 | `DOC-3927f91bc3daffc3` | yes | 0.0625 | 69.4 | 9676 | 921 | — |
| 5 | `DOC-8c661a1693d4655b` | yes | 0.0000 | 69.6 | 9289 | 942 | — |
| 6 | `DOC-4ab4ecd86ecf275d` | yes | 0.1875 | 76.0 | 9590 | 983 | — |
| 7 | `DOC-d554890e66786170` | yes | 0.1875 | 82.2 | 10446 | 1067 | — |
| 8 | `DOC-c96b9c7e12f91576` | yes | 0.0000 | 45.4 | 9549 | 657 | — |
| 9 | `DOC-52f9a5be69429299` | yes | 0.0000 | 30.9 | 9517 | 546 | — |
| 10 | `DOC-0a733ab86f2390ae` | yes | 0.1333 | 49.6 | 8841 | 708 | — |
| 11 | `DOC-62456d43b50f73fa` | yes | 0.0625 | 49.9 | 9688 | 761 | — |
| 12 | `DOC-eac7882cff200545` | yes | 0.0000 | 62.9 | 9334 | 918 | — |
| 13 | `DOC-d0495abfa5f3d8ee` | yes | 0.0625 | 59.1 | 9008 | 867 | — |
| 14 | `DOC-7430de65e5471741` | yes | 0.0526 | 58.0 | 9060 | 962 | — |
| 15 | `DOC-d01014aed8ad8824` | yes | 0.0625 | 47.5 | 9377 | 712 | — |
| 16 | `DOC-8f599c800d19fd92` | yes | 0.0000 | 49.8 | 9146 | 817 | — |
| 17 | `DOC-fc07b37a0f0d1234` | yes | 0.0000 | 45.6 | 9170 | 714 | — |
| 18 | `DOC-5fbb9ee2f4b4b114` | yes | 0.0000 | 42.3 | 9027 | 693 | — |
| 19 | `DOC-8a0bdfe3d16c33b2` | yes | 0.0588 | 46.3 | 9360 | 732 | — |
| 20 | `DOC-37026835107f9684` | yes | 0.0833 | 52.7 | 9439 | 853 | — |
| 21 | `DOC-15f85636d1eb6b77` | yes | 0.0667 | 54.1 | 9514 | 889 | — |
| 22 | `DOC-511062d64bc9afc6` | yes | 0.0625 | 45.2 | 9338 | 796 | — |
| 23 | `DOC-be8461dd68cfe458` | yes | 0.0000 | 109.7 | 9054 | 1798 | — |
| 24 | `DOC-5fa0ba13cf68b593` | yes | 0.0000 | 37.5 | 9125 | 628 | — |
| 25 | `DOC-f4e726a7f2c25494` | yes | 0.0667 | 44.7 | 9345 | 792 | — |
| 26 | `DOC-74a69c5b3cdf1afc` | yes | 0.0000 | 83.8 | 10224 | 1455 | — |
| 27 | `DOC-1e016055aa435e71` | yes | 0.0000 | 36.3 | 9148 | 700 | — |
| 28 | `DOC-f90cc5fb2ceac154` | yes | 0.0000 | 57.4 | 9529 | 1071 | — |
| 29 | `DOC-1252fb5690e17c7b` | yes | 0.0556 | 83.2 | 9296 | 1495 | — |
| 30 | `DOC-882fabf7aba36941` | yes | 0.0000 | 146.1 | 9595 | 2535 | — |
| 31 | `DOC-bec74557186e9409` | yes | 0.0714 | 58.0 | 9430 | 1028 | — |
| 32 | `DOC-63beb09b179ea4ee` | yes | 0.0588 | 52.4 | 9374 | 893 | — |
| 33 | `DOC-2f9cf3ce009aaaf0` | yes | 0.0588 | 50.1 | 9043 | 842 | — |
| 34 | `DOC-2b9f668ab6cb8901` | yes | 0.1053 | 44.3 | 8927 | 770 | — |
| 35 | `DOC-f099c5c73d56631e` | yes | 0.0000 | 44.3 | 9893 | 764 | — |
| 36 | `DOC-5c44797b6add60e4` | yes | 0.0667 | 46.5 | 9230 | 866 | — |
| 37 | `DOC-8fe2855a2310cdbe` | yes | 0.0588 | 60.4 | 9249 | 1070 | — |
| 38 | `DOC-03712a2b0a99a314` | yes | 0.0000 | 45.5 | 9286 | 788 | — |
| 39 | `DOC-fcaddb5bdc94ce63` | yes | 0.0588 | 38.2 | 9123 | 723 | — |
| 40 | `DOC-d1e355800bff0425` | yes | 0.0625 | 39.4 | 9196 | 740 | — |
| 41 | `DOC-fd6090e354177e5b` | yes | 0.0000 | 58.5 | 8909 | 1001 | — |
| 42 | `DOC-ab735131c00271bc` | yes | 0.0556 | 34.2 | 8800 | 622 | — |
| 43 | `DOC-169bbcdc5d9e609c` | yes | 0.0000 | 45.1 | 9975 | 735 | — |
| 44 | `DOC-26fa94f698c37fc5` | yes | 0.1765 | 122.4 | 9043 | 2242 | — |
| 45 | `DOC-45f801408be08af6` | no | — | 484.8 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=10160, total_t |
| 46 | `DOC-f546c7d6cf2e77e2` | yes | 0.0526 | 47.6 | 8785 | 946 | — |
| 47 | `DOC-b866e2b4f5059213` | yes | 0.0556 | 63.9 | 9099 | 1620 | — |
| 48 | `DOC-30eda1e78a5f6fb5` | no | — | 408.0 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9124, total_to |
| 49 | `DOC-ecf69d7e102ef62a` | no | — | 384.0 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9271, total_to |
| 50 | `DOC-d5c4f12f934de48e` | no | — | 341.1 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9465, total_to |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `grid-50-merger-specialist-awq-1l4.card.json`._
