# Corporate Records — 2× L4 · C8 · n=50

**Run:** `sand42-50-corporate-records-specialist-awq-2l4-c8` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Draw | 50 docs (fingerprint 76b083c7c46d) |
| Engine | awq_marlin · fp8 KV · CUDA graphs [1, 2, 4, 8, 16] · prefix caching on · thinking off |
| Admission | max_model_len 32768 · max_num_seqs 16 per replica · max_inputs 32 |

## Score & cost card

| Metric | Value |
| --- | ---: |
| **Run** |  |
| Run ID | `sand42-50-corporate-records-specialist-awq-2l4-c8` |
| GPUs / replicas | 2 |
| Concurrency | 8 (4 per replica) |
| Documents | 50 |
| Spec hash | b13d7fb4… |
| **Time** |  |
| Wall (busy) | 65.42 s |
| GPU seconds | 66.02 s |
| Cold boot | 0.28 s |
| **Cost** |  |
| Busy-window GPU $ | $0.029076 |
| Billed GPU $ | $0.029342 |
| Billed seconds | 66.02 s |
| Idle $ | $0.007516 (16.91 s) |
| Cost per document | $0.000587 |
| Cost per ok document | $0.000587 |
| Cost per 1M tokens | $0.1430 |
| **Tokens** |  |
| Prompt tokens | 197,319 |
| Completion tokens | 7,923 (3.9%) |
| Total tokens | 205,242 |
| Tokens per document | 4,105 |
| Per document: instructions + template | 2,090 (50.9%) |
| Per document: document text | 1,856 (45.2%) |
| Per document: output | 158 (3.9%) |
| Instruction tokens per model call | 2,090 over 50 calls |
| Token split basis | fit across documents, 4.21 chars/token |
| Completion p95 / max (ok docs) | 198 / 231 |
| **Throughput** |  |
| Tokens / second | 3,137.3 |
| Tokens / second per L4 | 1,568.6 |
| Documents / minute | 45.86 |
| **Latency (per document, ok rows)** |  |
| Mean | 7.76 s |
| p50 | 7.59 s |
| p95 | 10.82 s |
| Max | 12.26 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 5.93× of 8 |
| Slot occupancy | 74.1% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 30 / 20 |
| Mean TTFT per replica | 0.921 s / 0.681 s |
| Prefix-cache hit per replica | 51.2% / 48.1% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **GPU hardware (nvidia-smi)** | 19 samples · serving-replica nvidia-smi |
| GPU utilization | 82.4 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 100.0 % |
| GPU power draw | 65.6 W (min 30.9 / max 72.9) of 72 W cap |
| GPU memory bandwidth | 76.2 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,538 MHz (min 1,065 / max 2,040) |
| GPU temperature | 72.5 C (min 63.0 / max 81.0) |
| GPU memory used | 21,023 MiB (min 21,022 / max 21,024) |
| **Quality** |  |
| Overall extraction score | 0.4925 (sd 0.239) |
| Score min / max | 0.0635 / 0.8889 |
| Scoring method | `suite` |
| Schema-valid rate | 0.96 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Corporate Records run dashboard](sand42-50-corporate-records-specialist-awq-2l4-c8.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-020d77c0107d273d` | yes | 0.4746 | 7.6 | 2302 | 116 | — |
| 2 | `DOC-12a6d4cd092cf66d` | yes | 0.5026 | 7.6 | 7710 | 158 | — |
| 3 | `DOC-9ca44c7926a47ede` | yes | 0.5024 | 8.0 | 2292 | 131 | — |
| 4 | `DOC-6790430ae2a6c724` | yes | 0.1846 | 10.4 | 4477 | 142 | — |
| 5 | `DOC-fbcdd16e24f143ac` | yes | 0.1582 | 10.7 | 2456 | 155 | — |
| 6 | `DOC-81ae205a3b0bf16f` | yes | 0.2480 | 10.8 | 2515 | 158 | — |
| 7 | `DOC-e545bbd5f5ea61b6` | yes | 0.6970 | 10.8 | 2788 | 157 | — |
| 8 | `DOC-01054efd0980066b` | yes | 0.8222 | 10.9 | 5122 | 159 | — |
| 9 | `DOC-c4c9c37a96291975` | yes | 0.0813 | 6.1 | 2424 | 136 | — |
| 10 | `DOC-91f89b9c0d285ac7` | yes | 0.6667 | 8.8 | 6902 | 128 | — |
| 11 | `DOC-0a262afc80c73247` | yes | 0.1136 | 9.2 | 3124 | 158 | — |
| 12 | `DOC-a040ac19abb88fec` | yes | 0.4097 | 6.8 | 2206 | 141 | — |
| 13 | `DOC-732b812b7d9d9653` | yes | 0.8889 | 7.7 | 5572 | 156 | — |
| 14 | `DOC-0f56fe8db6df01bd` | yes | 0.0635 | 8.2 | 5368 | 163 | — |
| 15 | `DOC-e077f1f7e80e1e04` | yes | 0.1624 | 6.3 | 4043 | 166 | — |
| 16 | `DOC-2819b889b134ea01` | yes | 0.7500 | 9.3 | 5344 | 173 | — |
| 17 | `DOC-68d5a8753fcc3675` | yes | 0.4405 | 9.2 | 5671 | 177 | — |
| 18 | `DOC-9376c6bfa6779d5e` | yes | 0.4822 | 4.4 | 2200 | 131 | — |
| 19 | `DOC-b3ad98e5530dfeaf` | yes | 0.2820 | 6.4 | 2521 | 182 | — |
| 20 | `DOC-f134b9491efc5c57` | yes | 0.7949 | 4.9 | 2865 | 140 | — |
| 21 | `DOC-2f19002c84083aa8` | yes | 0.4978 | 8.1 | 5200 | 165 | — |
| 22 | `DOC-fc9f56d999bd7566` | yes | 0.6667 | 6.7 | 2509 | 176 | — |
| 23 | `DOC-e478fa89043a29e3` | yes | 0.8205 | 7.0 | 2910 | 151 | — |
| 24 | `DOC-1e8e3ce47882ae71` | yes | 0.1485 | 8.7 | 3063 | 198 | — |
| 25 | `DOC-4dc719baa790a79c` | yes | 0.6667 | 7.3 | 2669 | 163 | — |
| 26 | `DOC-474a0002b4c03be1` | yes | 0.8205 | 7.2 | 2938 | 152 | — |
| 27 | `DOC-d015968793450753` | yes | 0.7222 | 7.6 | 5082 | 158 | — |
| 28 | `DOC-a5fd7fe18b094f20` | yes | 0.7576 | 7.2 | 5919 | 143 | — |
| 29 | `DOC-b832b5eaa2b4848c` | yes | 0.1068 | 4.2 | 2762 | 95 | — |
| 30 | `DOC-204c3c7c0ba021cd` | yes | 0.4746 | 6.5 | 2226 | 133 | — |
| 31 | `DOC-9467462d9bb34f8e` | yes | 0.5417 | 7.8 | 5345 | 161 | — |
| 32 | `DOC-00193d0c070747e6` | yes | 0.4623 | 6.8 | 3225 | 158 | — |
| 33 | `DOC-bfa92eb6c72569ee` | yes | 0.4518 | 8.7 | 3771 | 160 | — |
| 34 | `DOC-a973ebf005e0e785` | yes | 0.4278 | 7.2 | 6146 | 212 | — |
| 35 | `DOC-41b53ea487b84955` | yes | 0.7500 | 12.3 | 4617 | 231 | — |
| 36 | `DOC-37152a33cfb70d37` | yes | 0.4103 | 9.1 | 2902 | 151 | — |
| 37 | `DOC-0a8eb16fff7e67ca` | yes | 0.6923 | 9.1 | 5246 | 168 | — |
| 38 | `DOC-ffb48271e0a5e812` | yes | 0.6667 | 7.2 | 5344 | 142 | — |
| 39 | `DOC-78f2456f571403a9` | yes | 0.1531 | 5.4 | 2345 | 151 | — |
| 40 | `DOC-80e90a37bb750a3c` | yes | 0.1495 | 6.1 | 2776 | 167 | — |
| 41 | `DOC-f21f3dadebb121e3` | yes | 0.7843 | 10.2 | 3308 | 180 | — |
| 42 | `DOC-e6906e59f9bd74ca` | yes | 0.6200 | 8.2 | 2978 | 160 | — |
| 43 | `DOC-d4dfbfe8049d41f9` | yes | 0.4934 | 8.5 | 3856 | 175 | — |
| 44 | `DOC-2338d194d5250def` | yes | 0.4867 | 6.7 | 5258 | 128 | — |
| 45 | `DOC-606242f2919653a4` | yes | 0.2332 | 7.0 | 5253 | 166 | — |
| 46 | `DOC-866139125545b36a` | yes | 0.7733 | 8.9 | 5397 | 180 | — |
| 47 | `DOC-842215e36884da89` | yes | 0.2467 | 7.4 | 5226 | 164 | — |
| 48 | `DOC-dfe42f3747f299e6` | yes | 0.7500 | 7.2 | 5870 | 166 | — |
| 49 | `DOC-d0aebe650be3e512` | yes | 0.4976 | 4.7 | 2405 | 163 | — |
| 50 | `DOC-27bbad54b6fd107e` | yes | 0.6250 | 5.1 | 2871 | 179 | — |

_Generated 2026-10-13T04:32:55+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-corporate-records-specialist-awq-2l4-c8.card.json`._
