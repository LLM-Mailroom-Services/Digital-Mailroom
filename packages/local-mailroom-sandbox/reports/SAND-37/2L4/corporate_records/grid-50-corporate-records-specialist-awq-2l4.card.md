# Corporate Records — 2× L4 · C32 · n=50

**Run:** `grid-50-corporate-records-specialist-awq-2l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `grid-50-corporate-records-specialist-awq-2l4` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 50 |
| Spec hash | ae7a4401… |
| **Time** |  |
| Wall (busy) | 21.17 s |
| GPU seconds | 21.48 s |
| Cold boot | 0.31 s |
| **Cost** |  |
| Busy-window GPU $ | $0.009410 |
| Billed GPU $ (incl. boot) | $0.009547 |
| Idle $ | not captured |
| Cost per document | $0.000188 |
| Cost per ok document | $0.000188 |
| Cost per 1M tokens | $0.0406 |
| **Tokens** |  |
| Prompt tokens | 223,160 |
| Completion tokens | 8,354 (3.6%) |
| Total tokens | 231,514 |
| Tokens per document | 4,630 |
| Per document: instructions + template | 2,125 (45.9%) |
| Per document: document text | 2,338 (50.5%) |
| Per document: output | 167 (3.6%) |
| Instruction tokens per model call | 2,125 over 50 calls |
| Token split basis | fit across documents, 4.35 chars/token |
| Completion p95 / max (ok docs) | 233 / 247 |
| **Throughput** |  |
| Tokens / second | 10,934.4 |
| Tokens / second per L4 | 5,467.2 |
| Documents / minute | 141.69 |
| **Latency (per document, ok rows)** |  |
| Mean | 22.44 s |
| p50 | 24.07 s |
| p95 | 34.64 s |
| Max | 36.48 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 52.98× of 32 |
| Slot occupancy | 165.6% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 24 / 26 |
| Mean TTFT per replica | 3.685 s / 4.204 s |
| Prefix-cache hit per replica | 45.5% / 48.8% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **Quality** |  |
| Overall extraction score | 0.4520 (sd 0.235) |
| Score min / max | 0.0813 / 0.8889 |
| Scoring method | `suite` |
| Schema-valid rate | 0.94 |
| Parse errors | 0 |
| Errors | 0 / 50 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-417996c5cc3d91f5` | yes | 0.4402 | 16.9 | 2232 | 97 | — |
| 2 | `DOC-e42fbaa25765ec5f` | yes | 0.1325 | 18.0 | 2249 | 97 | — |
| 3 | `DOC-9bdcc670eb06437b` | yes | 0.4402 | 20.2 | 2446 | 125 | — |
| 4 | `DOC-db84eb3d59faee66` | yes | 0.0813 | 22.4 | 2644 | 147 | — |
| 5 | `DOC-d8a8d7c000ae6495` | yes | 0.1027 | 22.5 | 2687 | 151 | — |
| 6 | `DOC-4042dc3ecd9ac9b4` | yes | 0.1499 | 22.7 | 5283 | 157 | — |
| 7 | `DOC-e12f100d091e15b5` | yes | 0.4658 | 23.8 | 2310 | 150 | — |
| 8 | `DOC-5dc965bfd05b8bf5` | yes | 0.2115 | 24.4 | 5308 | 154 | — |
| 9 | `DOC-7ca9eefc5f17d24f` | yes | 0.1401 | 24.4 | 2456 | 155 | — |
| 10 | `DOC-cdc3f9c110996846` | yes | 0.3939 | 24.4 | 4257 | 164 | — |
| 11 | `DOC-1e0470c03b023106` | yes | 0.7949 | 25.7 | 5338 | 159 | — |
| 12 | `DOC-c9fa372f38de2b5e` | yes | 0.3571 | 25.9 | 3160 | 163 | — |
| 13 | `DOC-34077127acc64d5e` | yes | 0.5515 | 26.3 | 5910 | 160 | — |
| 14 | `DOC-0d28ca4c116b9f53` | yes | 0.4872 | 26.2 | 3334 | 158 | — |
| 15 | `DOC-9cd96711a8928ec5` | yes | 0.3590 | 28.1 | 4953 | 170 | — |
| 16 | `DOC-08829e0f817f1211` | yes | 0.4524 | 28.0 | 2947 | 163 | — |
| 17 | `DOC-1578b671836c78e9` | yes | 0.7436 | 28.5 | 5810 | 152 | — |
| 18 | `DOC-51092450a52e256c` | yes | 0.4423 | 28.5 | 5466 | 174 | — |
| 19 | `DOC-0d9dd64d13b1c270` | yes | 0.1480 | 30.0 | 2512 | 171 | — |
| 20 | `DOC-732b812b7d9d9653` | yes | 0.8889 | 31.3 | 5572 | 165 | — |
| 21 | `DOC-42999d0d46a55578` | yes | 0.7436 | 31.4 | 4943 | 158 | — |
| 22 | `DOC-c40a11ac7f2c7b5b` | yes | 0.3889 | 31.4 | 2656 | 182 | — |
| 23 | `DOC-e366f6c8f425cd09` | yes | 0.3611 | 31.5 | 4797 | 189 | — |
| 24 | `DOC-4a77d0b316e1cc01` | yes | 0.6970 | 32.4 | 5497 | 206 | — |
| 25 | `DOC-a14783cfd27c88c1` | yes | 0.5962 | 33.2 | 4571 | 181 | — |
| 26 | `DOC-3c328f7374a079a9` | yes | 0.7333 | 33.2 | 4845 | 188 | — |
| 27 | `DOC-ef2f0660ed8b6f24` | yes | 0.4497 | 33.5 | 6125 | 233 | — |
| 28 | `DOC-30ce0f05432fc57f` | yes | 0.4405 | 15.7 | 2647 | 171 | — |
| 29 | `DOC-9523246260be90e0` | yes | 0.8333 | 33.9 | 5812 | 188 | — |
| 30 | `DOC-85c7b49cdac19586` | yes | 0.6953 | 33.9 | 5388 | 200 | — |
| 31 | `DOC-087da9fdf781f7db` | yes | 0.3333 | 14.3 | 5240 | 137 | — |
| 32 | `DOC-a973ebf005e0e785` | yes | 0.4278 | 34.6 | 6146 | 211 | — |
| 33 | `DOC-ffb48271e0a5e812` | yes | 0.6667 | 13.1 | 5344 | 145 | — |
| 34 | `DOC-bda69bc956881bab` | yes | 0.6667 | 35.7 | 7261 | 247 | — |
| 35 | `DOC-8018aaaf98b8597e` | yes | 0.7879 | 11.5 | 5234 | 147 | — |
| 36 | `DOC-2aa6196b22606d9c` | yes | 0.4423 | 19.0 | 5877 | 214 | — |
| 37 | `DOC-b28a8210ab812830` | yes | 0.0976 | 10.5 | 2515 | 158 | — |
| 38 | `DOC-0636dbc980a43715` | yes | 0.1413 | 11.9 | 2250 | 116 | — |
| 39 | `DOC-263580addaac6d20` | yes | 0.8056 | 36.5 | 5241 | 238 | — |
| 40 | `DOC-a52b3ad21666d339` | yes | 0.1694 | 10.2 | 3538 | 169 | — |
| 41 | `DOC-5cc2960a21fca151` | yes | 0.2467 | 8.7 | 5228 | 163 | — |
| 42 | `DOC-b865a8f75657643a` | yes | 0.7333 | 8.3 | 6078 | 161 | — |
| 43 | `DOC-5c087a08edcb4a91` | yes | 0.5088 | 13.2 | 5096 | 192 | — |
| 44 | `DOC-b7680bb9f72c5e65` | yes | 0.2878 | 14.6 | 5257 | 157 | — |
| 45 | `DOC-30fe9f6e442b9df3` | yes | 0.1689 | 13.0 | 4047 | 150 | — |
| 46 | `DOC-e12651c80e736fb8` | yes | 0.4679 | 15.4 | 2760 | 176 | — |
| 47 | `DOC-36df577431fb1032` | yes | 0.2679 | 11.5 | 5485 | 158 | — |
| 48 | `DOC-a2110b2cebe63cb7` | yes | 0.7556 | 12.0 | 5308 | 166 | — |
| 49 | `DOC-69ffaec3ba2b2cde` | yes | 0.1547 | 10.0 | 5230 | 160 | — |
| 50 | `DOC-dfe42f3747f299e6` | yes | 0.7500 | 9.6 | 5870 | 161 | — |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `grid-50-corporate-records-specialist-awq-2l4.card.json`._
