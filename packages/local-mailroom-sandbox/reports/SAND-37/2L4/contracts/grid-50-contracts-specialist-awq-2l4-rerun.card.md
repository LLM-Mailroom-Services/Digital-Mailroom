# Contracts — 2× L4 · C32 · n=50

**Run:** `grid-50-contracts-specialist-awq-2l4-rerun` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `grid-50-contracts-specialist-awq-2l4-rerun` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 50 |
| Spec hash | 3b6ca5ac… |
| **Time** |  |
| Wall (busy) | 312.76 s |
| GPU seconds | 313.05 s |
| Cold boot | 0.29 s |
| **Cost** |  |
| Busy-window GPU $ | $0.139007 |
| Billed GPU $ (incl. boot) | $0.139135 |
| Idle $ | $0.067994 (152.99 s) |
| Cost per document | $0.002780 |
| Cost per ok document | $0.002837 |
| Cost per 1M tokens | $0.3181 |
| **Tokens** |  |
| Prompt tokens | 360,560 |
| Completion tokens | 76,386 (17.5%) |
| Total tokens | 436,946 |
| Tokens per document | 8,917 |
| Per document: instructions + template | 2,853 (32.0%) |
| Per document: document text | 4,506 (50.5%) |
| Per document: output | 1,559 (17.5%) |
| Instruction tokens per model call | 2,853 over 49 calls |
| Token split basis | fit across documents, 4.40 chars/token |
| Completion p95 / max (ok docs) | 2,688 / 2,915 |
| **Throughput** |  |
| Tokens / second | 1,397.0 |
| Tokens / second per L4 | 698.5 |
| Documents / minute | 9.59 |
| **Latency (per document, ok rows)** |  |
| Mean | 104.34 s |
| p50 | 103.35 s |
| p95 | 156.58 s |
| Max | 213.62 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 17.11× of 32 |
| Slot occupancy | 53.5% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 27 / 23 |
| Mean TTFT per replica | 8.764 s / 4.795 s |
| Prefix-cache hit per replica | 42.1% / 44.6% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 1 |
| **Quality** |  |
| Overall extraction score | 0.6146 (sd 0.127) |
| Score min / max | 0.2727 / 0.8571 |
| Scoring method | `suite+cuad` |
| Schema-valid rate | 1.00 |
| Parse errors | 0 |
| Errors | 1 / 50 |
| **Clause scoring (CUAD)** |  |
| Docs with CUAD labels | 40 |
| Micro precision / recall / F1 | 0.703 / 0.531 / 0.605 |
| Metadata value checks | 77 / 113 |
| Suite field score (mean) | not captured |

## Errors

| Error | Count |
| --- | ---: |
| LengthFinishReasonError | 1 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-98ff556893f1a98f` | yes | 0.8571 | 36.4 | 3200 | 395 | — |
| 2 | `DOC-adad5ef793c0e409` | yes | 0.5185 | 54.0 | 8247 | 741 | — |
| 3 | `DOC-2e3e2bb13d6c83ca` | yes | — | 58.2 | 13464 | 558 | — |
| 4 | `DOC-ee4369c8980926dc` | yes | 0.5217 | 77.0 | 7993 | 1182 | — |
| 5 | `DOC-34904aee099a62c7` | yes | 0.6364 | 77.3 | 6946 | 1198 | — |
| 6 | `DOC-f717fb61aa615da0` | yes | 0.4444 | 80.3 | 8165 | 1211 | — |
| 7 | `DOC-25f822c661011bfe` | yes | 0.4375 | 80.8 | 7821 | 1236 | — |
| 8 | `DOC-9696c5996f24d85d` | yes | — | 81.4 | 4377 | 959 | — |
| 9 | `DOC-440a54573c24b918` | yes | 0.5714 | 86.9 | 3493 | 1039 | — |
| 10 | `DOC-ade03c57c5f78e21` | yes | 0.7500 | 101.1 | 4093 | 1242 | — |
| 11 | `DOC-09c0c774c3e5ec74` | yes | 0.2727 | 103.3 | 8507 | 1264 | — |
| 12 | `DOC-55df050fcb737129` | yes | 0.6667 | 103.3 | 5461 | 1621 | — |
| 13 | `DOC-2ca7b08d2d439f1e` | yes | — | 108.4 | 7616 | 1320 | — |
| 14 | `DOC-5892b6dc609c8d0f` | yes | — | 109.3 | 7606 | 1703 | — |
| 15 | `DOC-770401d1d47fd744` | yes | 0.6667 | 112.3 | 7751 | 1376 | — |
| 16 | `DOC-c30c293d38a2cd8b` | yes | 0.7200 | 113.4 | 9794 | 804 | — |
| 17 | `DOC-ba6d7a0ea5100bbb` | yes | 0.6667 | 116.1 | 7887 | 1790 | — |
| 18 | `DOC-83320eec5eec6235` | yes | 0.7692 | 119.0 | 7706 | 1417 | — |
| 19 | `DOC-4be26020b0470e43` | yes | 0.5714 | 120.4 | 7501 | 1451 | — |
| 20 | `DOC-c7f557969d953fae` | yes | — | 120.6 | 8119 | 1433 | — |
| 21 | `DOC-93e9bb030e2b282d` | yes | 0.7692 | 68.1 | 8560 | 1126 | — |
| 22 | `DOC-c68a4dd90660c113` | yes | 0.5600 | 88.0 | 7851 | 1525 | — |
| 23 | `DOC-99ca00712a84f039` | yes | 0.5714 | 126.0 | 5337 | 1952 | — |
| 24 | `DOC-e235bc9735f96335` | yes | 0.7586 | 129.8 | 7449 | 1549 | — |
| 25 | `DOC-6712aa595cfe3e2c` | yes | 0.5556 | 133.8 | 7666 | 2125 | — |
| 26 | `DOC-962cc639f3ebee80` | yes | — | 133.9 | 7359 | 1640 | — |
| 27 | `DOC-9b569749ea3d6f42` | yes | — | 136.8 | 11640 | 1667 | — |
| 28 | `DOC-15262384b17086bb` | yes | 0.5600 | 137.4 | 8178 | 2201 | — |
| 29 | `DOC-54ad252b1e5e8d58` | yes | 0.7857 | 138.0 | 8244 | 1696 | — |
| 30 | `DOC-d66d8f6c92207c3c` | yes | 0.6250 | 140.4 | 4746 | 1776 | — |
| 31 | `DOC-c2ac5762c7f227fa` | yes | — | 147.3 | 8143 | 1932 | — |
| 32 | `DOC-fca31a55b1d526ea` | yes | 0.8333 | 156.6 | 5459 | 2688 | — |
| 33 | `DOC-ea746c407db93af2` | yes | — | 157.6 | 4804 | 1225 | — |
| 34 | `DOC-364e40f0752551a3` | yes | 0.4571 | 61.0 | 10159 | 956 | — |
| 35 | `DOC-0de76b97986b57b3` | yes | 0.5882 | 86.2 | 7735 | 1729 | — |
| 36 | `DOC-f9b36fee351217c2` | yes | 0.6316 | 94.3 | 7931 | 1870 | — |
| 37 | `DOC-01633b99e74dc9f2` | yes | 0.4706 | 52.4 | 8129 | 1209 | — |
| 38 | `DOC-03f1f6c0db99e651` | yes | 0.6154 | 115.8 | 7683 | 1347 | — |
| 39 | `DOC-e853a8ab86c5a54d` | yes | 0.5882 | 90.9 | 4692 | 1350 | — |
| 40 | `DOC-9a2c7cc21a860fc4` | yes | 0.7143 | 83.7 | 7027 | 1868 | — |
| 41 | `DOC-dfa5c8eb1e7b837c` | yes | 0.8182 | 77.6 | 6055 | 1527 | — |
| 42 | `DOC-8a776dec500b074c` | yes | 0.3448 | 109.5 | 8308 | 1721 | — |
| 43 | `DOC-06229aa6571f9d46` | yes | 0.6316 | 107.7 | 6154 | 1718 | — |
| 44 | `DOC-561364d531fca179` | yes | 0.6667 | 77.7 | 7519 | 1917 | — |
| 45 | `DOC-d1c45d175a8abeb5` | yes | 0.6316 | 79.2 | 6851 | 1836 | — |
| 46 | `DOC-e492894fbfa36087` | yes | 0.5000 | 92.8 | 8030 | 2232 | — |
| 47 | `DOC-4ab8d1d37d3af05c` | yes | 0.5714 | 118.2 | 7678 | 2727 | — |
| 48 | `DOC-f333c4b8048d5d8c` | yes | 0.6316 | 98.8 | 7940 | 2422 | — |
| 49 | `DOC-9e063c6e3baf1233` | yes | 0.6341 | 213.6 | 7486 | 2915 | — |
| 50 | `DOC-a2ce7adbf6f5cb8d` | no | — | 239.9 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=6729, total_to |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `grid-50-contracts-specialist-awq-2l4-rerun.card.json`._
