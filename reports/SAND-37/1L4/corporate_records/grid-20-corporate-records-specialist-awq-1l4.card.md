# Corporate Records — 1× L4 · C8 · n=20

**Run:** `grid-20-corporate-records-specialist-awq-1l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Draw | 20 docs (fingerprint 49db8ebd55c5) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `grid-20-corporate-records-specialist-awq-1l4` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 20 |
| Spec hash | c13d7e79… |
| **Time** |  |
| Wall (busy) | 23.36 s |
| GPU seconds | 23.66 s |
| Cold boot | 0.30 s |
| **Cost** |  |
| Busy-window GPU $ | $0.005191 |
| Billed GPU $ (incl. boot) | $0.005257 |
| Idle $ | not captured |
| Cost per document | $0.000260 |
| Cost per ok document | $0.000260 |
| Cost per 1M tokens | $0.0515 |
| **Tokens** |  |
| Prompt tokens | 97,183 |
| Completion tokens | 3,608 (3.6%) |
| Total tokens | 100,791 |
| Tokens per document | 5,040 |
| Per document: instructions + template | 2,158 (42.8%) |
| Per document: document text | 2,701 (53.6%) |
| Per document: output | 180 (3.6%) |
| Instruction tokens per model call | 2,158 over 20 calls |
| Token split basis | fit across documents, 4.37 chars/token |
| Completion p95 / max (ok docs) | 239 / 247 |
| **Throughput** |  |
| Tokens / second | 4,314.9 |
| Tokens / second per L4 | 4,314.9 |
| Documents / minute | 51.37 |
| **Latency (per document, ok rows)** |  |
| Mean | 14.23 s |
| p50 | 14.40 s |
| p95 | 20.53 s |
| Max | 20.71 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 12.18× of 8 |
| Slot occupancy | 152.3% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 20 |
| Mean TTFT per replica | 1.841 s |
| Prefix-cache hit per replica | 47.2% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 0 |
| **Quality** |  |
| Overall extraction score | 0.4592 (sd 0.245) |
| Score min / max | 0.0813 / 0.8889 |
| Scoring method | `suite` |
| Schema-valid rate | 0.95 |
| Parse errors | 0 |
| Errors | 0 / 20 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-db84eb3d59faee66` | yes | 0.0813 | 14.4 | 2644 | 173 | — |
| 2 | `DOC-732b812b7d9d9653` | yes | 0.8889 | 14.4 | 5572 | 165 | — |
| 3 | `DOC-9cd96711a8928ec5` | yes | 0.3590 | 14.4 | 4953 | 169 | — |
| 4 | `DOC-c40a11ac7f2c7b5b` | yes | 0.3889 | 14.4 | 2656 | 182 | — |
| 5 | `DOC-a14783cfd27c88c1` | yes | 0.5962 | 14.5 | 4571 | 183 | — |
| 6 | `DOC-4a77d0b316e1cc01` | yes | 0.6970 | 19.7 | 5497 | 204 | — |
| 7 | `DOC-263580addaac6d20` | yes | 0.8056 | 20.5 | 5241 | 238 | — |
| 8 | `DOC-bda69bc956881bab` | yes | 0.6667 | 20.7 | 7261 | 247 | — |
| 9 | `DOC-9bdcc670eb06437b` | yes | 0.4402 | 12.6 | 2446 | 124 | — |
| 10 | `DOC-4042dc3ecd9ac9b4` | yes | 0.1499 | 15.0 | 5283 | 157 | — |
| 11 | `DOC-08829e0f817f1211` | yes | 0.4524 | 15.0 | 2947 | 162 | — |
| 12 | `DOC-9523246260be90e0` | yes | 0.8333 | 17.5 | 5812 | 190 | — |
| 13 | `DOC-087da9fdf781f7db` | yes | 0.4359 | 11.4 | 5240 | 133 | — |
| 14 | `DOC-a2110b2cebe63cb7` | yes | 0.7556 | 13.3 | 5308 | 166 | — |
| 15 | `DOC-ef2f0660ed8b6f24` | yes | 0.4497 | 20.0 | 6125 | 239 | — |
| 16 | `DOC-a973ebf005e0e785` | yes | 0.4278 | 16.3 | 6146 | 234 | — |
| 17 | `DOC-36df577431fb1032` | yes | 0.1846 | 9.0 | 5485 | 152 | — |
| 18 | `DOC-69ffaec3ba2b2cde` | yes | 0.1547 | 7.8 | 5230 | 160 | — |
| 19 | `DOC-a52b3ad21666d339` | yes | 0.1694 | 7.9 | 3538 | 169 | — |
| 20 | `DOC-5cc2960a21fca151` | yes | 0.2467 | 5.9 | 5228 | 161 | — |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `grid-20-corporate-records-specialist-awq-1l4.card.json`._
