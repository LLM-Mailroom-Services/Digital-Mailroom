# Corporate Records — 2× L4 · C32 · n=100

**Run:** `sand40-100-corporate-records-specialist-awq-2l4` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Draw | 100 docs (fingerprint 76d8a17658f7) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand40-100-corporate-records-specialist-awq-2l4` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 100 |
| Spec hash | 770b562a… |
| **Time** |  |
| Wall (busy) | 48.11 s |
| GPU seconds | 48.44 s |
| Cold boot | 0.33 s |
| **Cost** |  |
| Busy-window GPU $ | $0.021381 |
| Billed GPU $ (incl. boot) | $0.021529 |
| Idle $ | not captured |
| Cost per document | $0.000214 |
| Cost per ok document | $0.000214 |
| Cost per 1M tokens | $0.0488 |
| **Tokens** |  |
| Prompt tokens | 421,101 |
| Completion tokens | 16,622 (3.8%) |
| Total tokens | 437,723 |
| Tokens per document | 4,377 |
| Per document: instructions + template | 2,110 (48.2%) |
| Per document: document text | 2,101 (48.0%) |
| Per document: output | 166 (3.8%) |
| Instruction tokens per model call | 2,110 over 100 calls |
| Token split basis | fit across documents, 4.40 chars/token |
| Completion p95 / max (ok docs) | 233 / 250 |
| **Throughput** |  |
| Tokens / second | 9,098.8 |
| Tokens / second per L4 | 4,549.4 |
| Documents / minute | 124.72 |
| **Latency (per document, ok rows)** |  |
| Mean | 20.52 s |
| p50 | 19.92 s |
| p95 | 31.77 s |
| Max | 40.40 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 42.65× of 32 |
| Slot occupancy | 133.3% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 49 / 51 |
| Mean TTFT per replica | 2.594 s / 3.680 s |
| Prefix-cache hit per replica | 39.2% / 39.9% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **Quality** |  |
| Overall extraction score | 0.4755 (sd 0.246) |
| Score min / max | 0.0813 / 0.8889 |
| Scoring method | `suite` |
| Schema-valid rate | 0.97 |
| Parse errors | 0 |
| Errors | 0 / 100 |

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-4d8e8b87f161d432` | yes | 0.4167 | 19.0 | 2565 | 120 | — |
| 2 | `DOC-c2304ee259662c25` | yes | 0.5292 | 19.0 | 5297 | 121 | — |
| 3 | `DOC-a1bf2ddf032e38ea` | yes | 0.4627 | 19.1 | 2245 | 120 | — |
| 4 | `DOC-6d17fda455311945` | yes | 0.8056 | 19.4 | 7276 | 135 | — |
| 5 | `DOC-e42fbaa25765ec5f` | yes | 0.4658 | 20.0 | 2249 | 133 | — |
| 6 | `DOC-e545bbd5f5ea61b6` | yes | 0.6970 | 20.9 | 2788 | 155 | — |
| 7 | `DOC-5dc965bfd05b8bf5` | yes | 0.1859 | 20.9 | 5308 | 150 | — |
| 8 | `DOC-7ca9eefc5f17d24f` | yes | 0.1401 | 21.2 | 2456 | 154 | — |
| 9 | `DOC-d50133030490ea0a` | yes | 0.1051 | 21.9 | 3035 | 147 | — |
| 10 | `DOC-732b812b7d9d9653` | yes | 0.8889 | 22.6 | 5572 | 156 | — |
| 11 | `DOC-3e20fef7d0be1ab6` | yes | 0.7949 | 23.1 | 5219 | 153 | — |
| 12 | `DOC-0a262afc80c73247` | yes | 0.1136 | 23.3 | 3124 | 147 | — |
| 13 | `DOC-1e0470c03b023106` | yes | 0.7949 | 23.3 | 5338 | 159 | — |
| 14 | `DOC-cc3d181a639616d7` | yes | 0.1136 | 23.8 | 3196 | 155 | — |
| 15 | `DOC-42999d0d46a55578` | yes | 0.7436 | 24.3 | 4943 | 158 | — |
| 16 | `DOC-34077127acc64d5e` | yes | 0.5515 | 24.3 | 5910 | 160 | — |
| 17 | `DOC-3c328f7374a079a9` | yes | 0.7333 | 24.8 | 4845 | 169 | — |
| 18 | `DOC-1b024f18a5882a8e` | yes | 0.4470 | 25.2 | 5644 | 166 | — |
| 19 | `DOC-ec57149494f0c9a0` | yes | 0.7857 | 26.3 | 3177 | 173 | — |
| 20 | `DOC-a14783cfd27c88c1` | yes | 0.5962 | 27.1 | 4571 | 190 | — |
| 21 | `DOC-c40a11ac7f2c7b5b` | yes | 0.3889 | 27.3 | 2656 | 182 | — |
| 22 | `DOC-d2969f9629acc901` | yes | 0.1488 | 28.3 | 2466 | 162 | — |
| 23 | `DOC-c9fa372f38de2b5e` | yes | 0.3571 | 28.2 | 3160 | 163 | — |
| 24 | `DOC-74e0f47369572741` | yes | 0.1547 | 28.6 | 5271 | 189 | — |
| 25 | `DOC-7294152c69239b1e` | yes | 0.4471 | 29.5 | 4613 | 199 | — |
| 26 | `DOC-e366f6c8f425cd09` | yes | 0.6944 | 31.6 | 4797 | 187 | — |
| 27 | `DOC-b7be4de1447c8a24` | yes | 0.1458 | 31.8 | 3656 | 232 | — |
| 28 | `DOC-4a77d0b316e1cc01` | yes | 0.7273 | 32.8 | 5497 | 209 | — |
| 29 | `DOC-263580addaac6d20` | yes | 0.8056 | 33.6 | 5241 | 238 | — |
| 30 | `DOC-bda69bc956881bab` | yes | 0.6667 | 35.2 | 7261 | 250 | — |
| 31 | `DOC-020d77c0107d273d` | yes | 0.4722 | 36.2 | 2302 | 116 | — |
| 32 | `DOC-345450f6677c2a8a` | yes | 0.1547 | 18.1 | 5362 | 150 | — |
| 33 | `DOC-cb828c5701c751f3` | yes | 0.1547 | 19.0 | 2952 | 153 | — |
| 34 | `DOC-310fa993e212a342` | yes | 0.1813 | 17.5 | 2453 | 161 | — |
| 35 | `DOC-417996c5cc3d91f5` | yes | 0.4402 | 14.1 | 2232 | 97 | — |
| 36 | `DOC-51092450a52e256c` | yes | 0.4423 | 19.8 | 5466 | 167 | — |
| 37 | `DOC-0d9dd64d13b1c270` | yes | 0.1146 | 40.4 | 2512 | 161 | — |
| 38 | `DOC-db84eb3d59faee66` | yes | 0.0813 | 19.9 | 2644 | 146 | — |
| 39 | `DOC-c80ef83120793a69` | yes | 0.5171 | 16.6 | 2267 | 150 | — |
| 40 | `DOC-b856ca94d75a431a` | yes | 0.6923 | 22.4 | 2808 | 162 | — |
| 41 | `DOC-e12f100d091e15b5` | yes | 0.4658 | 18.4 | 2310 | 137 | — |
| 42 | `DOC-5052ed547d53cfbf` | yes | 0.8718 | 19.1 | 3886 | 150 | — |
| 43 | `DOC-9bdcc670eb06437b` | yes | 0.4402 | 15.5 | 2446 | 124 | — |
| 44 | `DOC-9cd96711a8928ec5` | yes | 0.3590 | 23.5 | 4953 | 171 | — |
| 45 | `DOC-4042dc3ecd9ac9b4` | yes | 0.1499 | 20.1 | 5283 | 160 | — |
| 46 | `DOC-f70b11ab7f823e2d` | yes | 0.7619 | 18.4 | 3138 | 157 | — |
| 47 | `DOC-9467462d9bb34f8e` | yes | 0.5417 | 18.2 | 5345 | 161 | — |
| 48 | `DOC-325f25ad3bf7d458` | yes | 0.2820 | 22.7 | 2519 | 181 | — |
| 49 | `DOC-0d28ca4c116b9f53` | yes | 0.4872 | 15.8 | 3334 | 158 | — |
| 50 | `DOC-f1e8af2071cb17fa` | yes | 0.4167 | 22.0 | 5083 | 169 | — |
| 51 | `DOC-b73c5e5708c43511` | yes | 0.2271 | 18.6 | 5157 | 165 | — |
| 52 | `DOC-9523246260be90e0` | yes | 0.8333 | 20.3 | 5812 | 186 | — |
| 53 | `DOC-08829e0f817f1211` | yes | 0.5238 | 15.9 | 2947 | 161 | — |
| 54 | `DOC-cde69e0ba4db2419` | yes | 0.2820 | 26.6 | 2523 | 184 | — |
| 55 | `DOC-85c7b49cdac19586` | yes | 0.6602 | 24.7 | 5388 | 200 | — |
| 56 | `DOC-1578b671836c78e9` | yes | 0.7436 | 21.5 | 5810 | 153 | — |
| 57 | `DOC-feab935f7db4b9cf` | yes | 0.8462 | 22.2 | 5253 | 151 | — |
| 58 | `DOC-1853b495e0848fca` | yes | 0.7692 | 21.0 | 5266 | 152 | — |
| 59 | `DOC-0636dbc980a43715` | yes | 0.1413 | 7.4 | 2250 | 116 | — |
| 60 | `DOC-087da9fdf781f7db` | yes | 0.3333 | 14.0 | 5240 | 137 | — |
| 61 | `DOC-a195b29d1b417e2f` | yes | 0.4432 | 19.4 | 4801 | 216 | — |
| 62 | `DOC-d8a8d7c000ae6495` | yes | 0.1027 | 14.9 | 2687 | 144 | — |
| 63 | `DOC-cdc3f9c110996846` | yes | 0.7273 | 21.8 | 4257 | 164 | — |
| 64 | `DOC-d361e5631ac2bebb` | yes | 0.4615 | 30.4 | 5060 | 237 | — |
| 65 | `DOC-6993b10b8f79da64` | yes | 0.3571 | 16.8 | 2924 | 144 | — |
| 66 | `DOC-bb25adbf606096a4` | yes | 0.4423 | 21.6 | 3698 | 191 | — |
| 67 | `DOC-674588a5b4c8d642` | yes | 0.4103 | 15.7 | 3264 | 159 | — |
| 68 | `DOC-78f2456f571403a9` | yes | 0.1531 | 15.7 | 2345 | 153 | — |
| 69 | `DOC-30ce0f05432fc57f` | yes | 0.4405 | 20.9 | 2647 | 171 | — |
| 70 | `DOC-ffb48271e0a5e812` | yes | 0.6667 | 18.4 | 5344 | 144 | — |
| 71 | `DOC-8e3fa7aa97eda92a` | yes | 0.7857 | 19.7 | 5261 | 175 | — |
| 72 | `DOC-5c087a08edcb4a91` | yes | 0.5088 | 16.9 | 5096 | 163 | — |
| 73 | `DOC-e54512dab9fa64a4` | yes | 0.5000 | 19.2 | 3048 | 172 | — |
| 74 | `DOC-7a7b8110d33a84be` | yes | 0.6231 | 14.8 | 2642 | 154 | — |
| 75 | `DOC-e1e86caf042eb7b9` | yes | 0.6200 | 14.9 | 3067 | 156 | — |
| 76 | `DOC-8018aaaf98b8597e` | yes | 0.6667 | 17.4 | 5234 | 150 | — |
| 77 | `DOC-30fe9f6e442b9df3` | yes | 0.1689 | 16.1 | 4047 | 150 | — |
| 78 | `DOC-b7680bb9f72c5e65` | yes | 0.2878 | 20.5 | 5257 | 161 | — |
| 79 | `DOC-e12651c80e736fb8` | yes | 0.4679 | 22.1 | 2760 | 176 | — |
| 80 | `DOC-8663fca594565055` | yes | 0.7556 | 18.5 | 3440 | 159 | — |
| 81 | `DOC-0db97c4753dcbaea` | yes | 0.7619 | 22.5 | 4209 | 229 | — |
| 82 | `DOC-2aa6196b22606d9c` | yes | 0.4423 | 25.0 | 5877 | 235 | — |
| 83 | `DOC-ef2f0660ed8b6f24` | yes | 0.4497 | 28.3 | 6125 | 233 | — |
| 84 | `DOC-571cffbc7867e8ef` | yes | 0.1326 | 21.1 | 2538 | 185 | — |
| 85 | `DOC-a973ebf005e0e785` | yes | 0.4278 | 26.1 | 6146 | 234 | — |
| 86 | `DOC-a2110b2cebe63cb7` | yes | 0.7556 | 14.4 | 5308 | 166 | — |
| 87 | `DOC-b28a8210ab812830` | yes | 0.0976 | 16.6 | 2515 | 158 | — |
| 88 | `DOC-63fffca0c0a261ec` | yes | 0.8431 | 17.4 | 5135 | 165 | — |
| 89 | `DOC-36df577431fb1032` | yes | 0.1846 | 12.6 | 5485 | 154 | — |
| 90 | `DOC-5cc2960a21fca151` | yes | 0.2467 | 12.7 | 5228 | 163 | — |
| 91 | `DOC-dfe42f3747f299e6` | yes | 0.7500 | 10.1 | 5870 | 158 | — |
| 92 | `DOC-478a8974f4909fc3` | yes | 0.7333 | 8.1 | 6078 | 154 | — |
| 93 | `DOC-20e622adc7603fc5` | yes | 0.8571 | 15.2 | 5201 | 183 | — |
| 94 | `DOC-69ffaec3ba2b2cde` | yes | 0.1547 | 13.4 | 5230 | 160 | — |
| 95 | `DOC-a52b3ad21666d339` | yes | 0.1694 | 13.5 | 3538 | 170 | — |
| 96 | `DOC-d564c7cabec90e84` | yes | 0.2467 | 11.9 | 5206 | 164 | — |
| 97 | `DOC-c85fadd4401ec219` | yes | 0.7179 | 7.7 | 5693 | 179 | — |
| 98 | `DOC-e646013a1cfd084b` | yes | 0.8056 | 13.9 | 3122 | 214 | — |
| 99 | `DOC-ffb94478e4033b99` | yes | 0.1547 | 9.9 | 5323 | 157 | — |
| 100 | `DOC-b865a8f75657643a` | yes | 0.7333 | 8.9 | 6078 | 154 | — |

_Generated 2026-10-01T06:44:50+00:00 by `sandbox run card`. Machine-readable twin: `sand40-100-corporate-records-specialist-awq-2l4.card.json`._
