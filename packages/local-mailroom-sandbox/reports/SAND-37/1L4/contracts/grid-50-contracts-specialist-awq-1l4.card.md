# Contracts — 1× L4 · C8 · n=50

**Run:** `grid-50-contracts-specialist-awq-1l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | contracts_specialist |
| Prompt | contracts_specialist_v33_simplified |
| Temperature | 0.7 (posture knob) |
| Output cap (max_tokens) | 8,192 |
| Input cap (max_input_chars) | 24,000 |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 50 docs (fingerprint c29633d769b5) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `grid-50-contracts-specialist-awq-1l4` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 50 |
| Spec hash | 663799cf… |
| **Time** |  |
| Wall (busy) | 655.16 s |
| GPU seconds | 655.60 s |
| Cold boot | 0.45 s |
| **Cost** |  |
| Busy-window GPU $ | $0.145591 |
| Billed GPU $ (incl. boot) | $0.145690 |
| Idle $ | $0.053876 (242.44 s) |
| Cost per document | $0.002912 |
| Cost per ok document | $0.003098 |
| Cost per 1M tokens | $0.3493 |
| **Tokens** |  |
| Prompt tokens | 342,770 |
| Completion tokens | 74,037 (17.8%) |
| Total tokens | 416,807 |
| Tokens per document | 8,868 |
| Per document: instructions + template | 2,835 (32.0%) |
| Per document: document text | 4,458 (50.3%) |
| Per document: output | 1,575 (17.8%) |
| Instruction tokens per model call | 2,835 over 47 calls |
| Token split basis | fit across documents, 4.39 chars/token |
| Completion p95 / max (ok docs) | 2,829 / 3,391 |
| **Throughput** |  |
| Tokens / second | 636.2 |
| Tokens / second per L4 | 636.2 |
| Documents / minute | 4.58 |
| **Latency (per document, ok rows)** |  |
| Mean | 70.25 s |
| p50 | 68.15 s |
| p95 | 108.92 s |
| Max | 134.23 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 6.52× of 8 |
| Slot occupancy | 81.5% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 50 |
| Mean TTFT per replica | 1.776 s |
| Prefix-cache hit per replica | 44.2% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 3 |
| **Quality** |  |
| Overall extraction score | 0.6020 (sd 0.118) |
| Score min / max | 0.3429 / 0.8000 |
| Scoring method | `suite+cuad` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 3 / 50 |
| **Clause scoring (CUAD)** |  |
| Docs with CUAD labels | 39 |
| Micro precision / recall / F1 | 0.624 / 0.559 / 0.590 |
| Metadata value checks | 71 / 110 |
| Suite field score (mean) | not captured |

## Errors

| Error | Count |
| --- | ---: |
| LengthFinishReasonError | 3 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-ea746c407db93af2` | yes | — | 45.7 | 4804 | 884 | — |
| 2 | `DOC-2ca7b08d2d439f1e` | yes | — | 46.2 | 7616 | 909 | — |
| 3 | `DOC-5892b6dc609c8d0f` | yes | — | 64.6 | 7606 | 1216 | — |
| 4 | `DOC-962cc639f3ebee80` | yes | — | 68.9 | 7359 | 1312 | — |
| 5 | `DOC-9696c5996f24d85d` | yes | — | 72.7 | 4377 | 1339 | — |
| 6 | `DOC-9b569749ea3d6f42` | yes | — | 81.5 | 11640 | 1493 | — |
| 7 | `DOC-c7f557969d953fae` | yes | — | 83.3 | 8119 | 1558 | — |
| 8 | `DOC-2e3e2bb13d6c83ca` | yes | — | 66.1 | 13464 | 1314 | — |
| 9 | `DOC-25f822c661011bfe` | yes | 0.4667 | 44.1 | 7821 | 886 | — |
| 10 | `DOC-ba6d7a0ea5100bbb` | yes | 0.7143 | 61.2 | 7887 | 1227 | — |
| 11 | `DOC-6712aa595cfe3e2c` | yes | 0.4706 | 52.9 | 7666 | 1121 | — |
| 12 | `DOC-98ff556893f1a98f` | yes | 0.7500 | 22.3 | 3200 | 510 | — |
| 13 | `DOC-54ad252b1e5e8d58` | yes | 0.5926 | 77.6 | 8244 | 1717 | — |
| 14 | `DOC-e235bc9735f96335` | yes | 0.5833 | 49.3 | 7449 | 1154 | — |
| 15 | `DOC-c30c293d38a2cd8b` | yes | 0.7407 | 41.0 | 9794 | 929 | — |
| 16 | `DOC-9e063c6e3baf1233` | yes | 0.5714 | 104.0 | 7486 | 2312 | — |
| 17 | `DOC-440a54573c24b918` | yes | 0.5000 | 40.6 | 3493 | 948 | — |
| 18 | `DOC-ade03c57c5f78e21` | yes | 0.6250 | 51.8 | 4093 | 1212 | — |
| 19 | `DOC-09c0c774c3e5ec74` | yes | 0.7097 | 54.6 | 8507 | 1299 | — |
| 20 | `DOC-4be26020b0470e43` | yes | 0.5714 | 66.1 | 7501 | 1591 | — |
| 21 | `DOC-ee4369c8980926dc` | yes | 0.5882 | 96.9 | 7993 | 2228 | — |
| 22 | `DOC-99ca00712a84f039` | yes | 0.6316 | 74.5 | 5337 | 1750 | — |
| 23 | `DOC-34904aee099a62c7` | yes | 0.5926 | 100.6 | 6946 | 2286 | — |
| 24 | `DOC-83320eec5eec6235` | yes | 0.7179 | 71.5 | 7706 | 1591 | — |
| 25 | `DOC-f717fb61aa615da0` | yes | 0.6429 | 30.0 | 8165 | 661 | — |
| 26 | `DOC-15262384b17086bb` | yes | 0.6667 | 81.6 | 8178 | 1858 | — |
| 27 | `DOC-fca31a55b1d526ea` | yes | 0.7273 | 61.5 | 5459 | 1397 | — |
| 28 | `DOC-770401d1d47fd744` | yes | 0.6452 | 68.5 | 7751 | 1483 | — |
| 29 | `DOC-55df050fcb737129` | yes | 0.5714 | 81.3 | 5461 | 1870 | — |
| 30 | `DOC-d66d8f6c92207c3c` | yes | 0.7619 | 78.8 | 4746 | 1768 | — |
| 31 | `DOC-c68a4dd90660c113` | yes | 0.6154 | 81.1 | 7851 | 1782 | — |
| 32 | `DOC-c2ac5762c7f227fa` | no | — | 373.2 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=8143, total_to |
| 33 | `DOC-06229aa6571f9d46` | yes | 0.6250 | 35.2 | 6154 | 790 | — |
| 34 | `DOC-8a776dec500b074c` | yes | 0.3448 | 53.8 | 8308 | 1138 | — |
| 35 | `DOC-93e9bb030e2b282d` | yes | 0.7586 | 97.9 | 8560 | 2088 | — |
| 36 | `DOC-f9b36fee351217c2` | yes | 0.3429 | 103.0 | 7931 | 2248 | — |
| 37 | `DOC-adad5ef793c0e409` | no | — | 371.5 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=8247, total_to |
| 38 | `DOC-03f1f6c0db99e651` | yes | 0.6154 | 128.6 | 7683 | 2829 | — |
| 39 | `DOC-364e40f0752551a3` | yes | 0.4211 | 55.8 | 10159 | 1318 | — |
| 40 | `DOC-4ab8d1d37d3af05c` | yes | 0.6207 | 108.9 | 7678 | 2430 | — |
| 41 | `DOC-e853a8ab86c5a54d` | yes | 0.5217 | 69.9 | 4692 | 1558 | — |
| 42 | `DOC-9a2c7cc21a860fc4` | yes | 0.7143 | 79.4 | 7027 | 1796 | — |
| 43 | `DOC-e492894fbfa36087` | yes | 0.3704 | 66.6 | 8030 | 1530 | — |
| 44 | `DOC-dfa5c8eb1e7b837c` | yes | 0.8000 | 68.2 | 6055 | 1632 | — |
| 45 | `DOC-a2ce7adbf6f5cb8d` | yes | 0.7368 | 67.1 | 6729 | 1675 | — |
| 46 | `DOC-0de76b97986b57b3` | yes | 0.5882 | 134.2 | 7735 | 3207 | — |
| 47 | `DOC-561364d531fca179` | yes | 0.5600 | 49.6 | 7519 | 1292 | — |
| 48 | `DOC-d1c45d175a8abeb5` | yes | 0.4000 | 53.5 | 6851 | 1510 | — |
| 49 | `DOC-f333c4b8048d5d8c` | yes | 0.6000 | 108.9 | 7940 | 3391 | — |
| 50 | `DOC-01633b99e74dc9f2` | no | — | 224.7 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=8129, total_to |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `grid-50-contracts-specialist-awq-1l4.card.json`._
