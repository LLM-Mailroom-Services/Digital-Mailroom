# Corporate Records — 1× L4 · C8 · n=50

**Run:** `grid-50-corporate-records-specialist-awq-1l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

## Conditions

| Condition | Value |
| --- | --- |
| Task | corporate_records_specialist |
| Prompt | corporate_records_specialist_simplified |
| Temperature | 0.1 (vendored call site) |
| Output cap (max_tokens) | 8,192 |
| Input cap (max_input_chars) | 15,000 |
| Job retries | 2 |
| Dataset | Lucius-Morningstar/mailroom-dataset ground_truth @ ed7576b6, split=all, seed 42 |
| Draw | 50 docs (fingerprint d3139c5e07c1) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `grid-50-corporate-records-specialist-awq-1l4` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 50 |
| Spec hash | 95c64a58… |
| **Time** |  |
| Wall (busy) | 71.15 s |
| GPU seconds | 71.44 s |
| Cold boot | 0.28 s |
| **Cost** |  |
| Busy-window GPU $ | $0.015812 |
| Billed GPU $ (incl. boot) | $0.015875 |
| Idle $ | not captured |
| Cost per document | $0.000316 |
| Cost per ok document | $0.000316 |
| Cost per 1M tokens | $0.0683 |
| **Tokens** |  |
| Prompt tokens | 223,160 |
| Completion tokens | 8,360 (3.6%) |
| Total tokens | 231,520 |
| Tokens per document | 4,630 |
| Per document: instructions + template | 2,125 (45.9%) |
| Per document: document text | 2,338 (50.5%) |
| Per document: output | 167 (3.6%) |
| Instruction tokens per model call | 2,125 over 50 calls |
| Token split basis | fit across documents, 4.35 chars/token |
| Completion p95 / max (ok docs) | 237 / 247 |
| **Throughput** |  |
| Tokens / second | 3,253.9 |
| Tokens / second per L4 | 3,253.9 |
| Documents / minute | 42.16 |
| **Latency (per document, ok rows)** |  |
| Mean | 13.12 s |
| p50 | 13.19 s |
| p95 | 19.80 s |
| Max | 22.25 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 9.22× of 8 |
| Slot occupancy | 115.2% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 50 |
| Mean TTFT per replica | 1.425 s |
| Prefix-cache hit per replica | 48.2% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 0 |
| **Quality** |  |
| Overall extraction score | 0.4492 (sd 0.249) |
| Score min / max | 0.0580 / 0.8889 |
| Scoring method | `suite` |
| Schema-valid rate | 0.94 |
| Parse errors | 0 |
| Errors | 0 / 50 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-e42fbaa25765ec5f` | yes | 0.1325 | 13.3 | 2249 | 97 | — |
| 2 | `DOC-5dc965bfd05b8bf5` | yes | 0.1859 | 14.7 | 5308 | 154 | — |
| 3 | `DOC-42999d0d46a55578` | yes | 0.7436 | 14.7 | 4943 | 153 | — |
| 4 | `DOC-7ca9eefc5f17d24f` | yes | 0.1401 | 14.9 | 2456 | 155 | — |
| 5 | `DOC-34077127acc64d5e` | yes | 0.5515 | 15.1 | 5910 | 160 | — |
| 6 | `DOC-a14783cfd27c88c1` | yes | 0.5962 | 19.8 | 4571 | 182 | — |
| 7 | `DOC-263580addaac6d20` | yes | 0.8056 | 21.9 | 5241 | 239 | — |
| 8 | `DOC-bda69bc956881bab` | yes | 0.6667 | 22.3 | 7261 | 247 | — |
| 9 | `DOC-0d9dd64d13b1c270` | yes | 0.1146 | 12.5 | 2512 | 161 | — |
| 10 | `DOC-1e0470c03b023106` | yes | 0.7949 | 13.3 | 5338 | 159 | — |
| 11 | `DOC-c9fa372f38de2b5e` | yes | 0.3571 | 13.2 | 3160 | 163 | — |
| 12 | `DOC-c40a11ac7f2c7b5b` | yes | 0.0580 | 10.6 | 2656 | 157 | — |
| 13 | `DOC-e366f6c8f425cd09` | yes | 0.6944 | 16.0 | 4797 | 193 | — |
| 14 | `DOC-4a77d0b316e1cc01` | yes | 0.6970 | 18.8 | 5497 | 204 | — |
| 15 | `DOC-732b812b7d9d9653` | yes | 0.8889 | 13.3 | 5572 | 165 | — |
| 16 | `DOC-3c328f7374a079a9` | yes | 0.7333 | 14.0 | 4845 | 191 | — |
| 17 | `DOC-9cd96711a8928ec5` | yes | 0.3590 | 11.4 | 4953 | 169 | — |
| 18 | `DOC-db84eb3d59faee66` | yes | 0.0813 | 11.3 | 2644 | 159 | — |
| 19 | `DOC-51092450a52e256c` | yes | 0.4423 | 13.2 | 5466 | 174 | — |
| 20 | `DOC-4042dc3ecd9ac9b4` | yes | 0.1499 | 11.1 | 5283 | 156 | — |
| 21 | `DOC-e12f100d091e15b5` | yes | 0.4682 | 8.1 | 2310 | 137 | — |
| 22 | `DOC-417996c5cc3d91f5` | yes | 0.4402 | 6.5 | 2232 | 97 | — |
| 23 | `DOC-85c7b49cdac19586` | yes | 0.6953 | 15.3 | 5388 | 196 | — |
| 24 | `DOC-9bdcc670eb06437b` | yes | 0.4402 | 12.1 | 2446 | 125 | — |
| 25 | `DOC-9523246260be90e0` | yes | 0.8333 | 13.5 | 5812 | 168 | — |
| 26 | `DOC-1578b671836c78e9` | yes | 0.8205 | 13.5 | 5810 | 167 | — |
| 27 | `DOC-0d28ca4c116b9f53` | yes | 0.4872 | 11.8 | 3334 | 158 | — |
| 28 | `DOC-08829e0f817f1211` | yes | 0.4524 | 12.0 | 2947 | 167 | — |
| 29 | `DOC-cdc3f9c110996846` | yes | 0.1419 | 12.2 | 4257 | 166 | — |
| 30 | `DOC-d8a8d7c000ae6495` | yes | 0.1000 | 9.8 | 2687 | 147 | — |
| 31 | `DOC-ef2f0660ed8b6f24` | yes | 0.4497 | 18.3 | 6125 | 237 | — |
| 32 | `DOC-a973ebf005e0e785` | yes | 0.4278 | 16.3 | 6146 | 234 | — |
| 33 | `DOC-087da9fdf781f7db` | yes | 0.3333 | 11.3 | 5240 | 137 | — |
| 34 | `DOC-ffb48271e0a5e812` | yes | 0.6667 | 11.0 | 5344 | 144 | — |
| 35 | `DOC-30ce0f05432fc57f` | yes | 0.4405 | 12.0 | 2647 | 159 | — |
| 36 | `DOC-e12651c80e736fb8` | yes | 0.4679 | 13.4 | 2760 | 176 | — |
| 37 | `DOC-2aa6196b22606d9c` | yes | 0.4423 | 16.2 | 5877 | 214 | — |
| 38 | `DOC-b7680bb9f72c5e65` | yes | 0.2878 | 12.7 | 5257 | 165 | — |
| 39 | `DOC-8018aaaf98b8597e` | yes | 0.7879 | 10.4 | 5234 | 147 | — |
| 40 | `DOC-0636dbc980a43715` | yes | 0.1413 | 8.5 | 2250 | 116 | — |
| 41 | `DOC-5c087a08edcb4a91` | yes | 0.5088 | 13.0 | 5096 | 197 | — |
| 42 | `DOC-b28a8210ab812830` | yes | 0.0976 | 13.2 | 2515 | 160 | — |
| 43 | `DOC-30fe9f6e442b9df3` | yes | 0.2624 | 13.5 | 4047 | 163 | — |
| 44 | `DOC-36df577431fb1032` | yes | 0.2679 | 13.6 | 5485 | 157 | — |
| 45 | `DOC-a2110b2cebe63cb7` | yes | 0.7556 | 13.8 | 5308 | 166 | — |
| 46 | `DOC-a52b3ad21666d339` | yes | 0.1667 | 11.2 | 3538 | 168 | — |
| 47 | `DOC-69ffaec3ba2b2cde` | yes | 0.1547 | 10.5 | 5230 | 160 | — |
| 48 | `DOC-dfe42f3747f299e6` | yes | 0.7500 | 10.3 | 5870 | 162 | — |
| 49 | `DOC-5cc2960a21fca151` | yes | 0.2467 | 10.6 | 5228 | 172 | — |
| 50 | `DOC-b865a8f75657643a` | yes | 0.7333 | 6.2 | 6078 | 160 | — |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `grid-50-corporate-records-specialist-awq-1l4.card.json`._
