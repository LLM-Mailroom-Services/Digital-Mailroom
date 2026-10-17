# Corporate Records — 1× L4 · C8 · n=50

**Run:** `sand42-50-corporate-records-specialist-awq-1l4-c8` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `sand42-50-corporate-records-specialist-awq-1l4-c8` |
| GPUs / replicas | 1 |
| Concurrency | 8 (8 per replica) |
| Documents | 50 |
| Spec hash | 4640639b… |
| **Time** |  |
| Wall (busy) | 88.40 s |
| GPU seconds | 83.29 s |
| Cold boot | 0.14 s |
| **Cost** |  |
| Busy-window GPU $ | $0.019645 |
| Billed GPU $ | $0.018509 |
| Billed seconds | 83.29 s |
| Idle $ | $0.004801 (21.61 s) |
| Cost per document | $0.000370 |
| Cost per ok document | $0.000370 |
| Cost per 1M tokens | $0.0901 |
| **Tokens** |  |
| Prompt tokens | 197,319 |
| Completion tokens | 8,154 (4.0%) |
| Total tokens | 205,473 |
| Tokens per document | 4,109 |
| Per document: instructions + template | 2,090 (50.9%) |
| Per document: document text | 1,856 (45.2%) |
| Per document: output | 163 (4.0%) |
| Instruction tokens per model call | 2,090 over 50 calls |
| Token split basis | fit across documents, 4.21 chars/token |
| Completion p95 / max (ok docs) | 204 / 239 |
| **Throughput** |  |
| Tokens / second | 2,324.3 |
| Tokens / second per L4 | 2,324.3 |
| Documents / minute | 33.94 |
| **Latency (per document, ok rows)** |  |
| Mean | 10.69 s |
| p50 | 10.79 s |
| p95 | 14.50 s |
| Max | 17.92 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 6.04× of 8 |
| Slot occupancy | 75.6% |
| Coverage | replicas observed: 1 of 1 |
| Requests per replica (this run) | 50 |
| Mean TTFT per replica | 1.201 s |
| Prefix-cache hit per replica | 50.9% |
| Preemptions per replica (this run) | 0 |
| Length-capped finishes per replica (this run) | 0 |
| **GPU hardware (nvidia-smi)** | 14 samples · serving-replica nvidia-smi |
| GPU utilization | 84.6 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 100.0 % |
| GPU power draw | 64.7 W (min 31.7 / max 72.7) of 72 W cap |
| GPU memory bandwidth | 69.6 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,383 MHz (min 990 / max 2,040) |
| GPU temperature | 69.4 C (min 64.0 / max 73.0) |
| GPU memory used | 21,028 MiB (min 21,028 / max 21,028) |
| **Quality** |  |
| Overall extraction score | 0.4823 (sd 0.248) |
| Score min / max | 0.0635 / 0.8889 |
| Scoring method | `suite` |
| Schema-valid rate | 0.96 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Corporate Records run dashboard](sand42-50-corporate-records-specialist-awq-1l4-c8.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-6790430ae2a6c724` | yes | 0.1846 | 10.8 | 4477 | 142 | — |
| 2 | `DOC-01054efd0980066b` | yes | 0.8222 | 10.8 | 5122 | 158 | — |
| 3 | `DOC-e545bbd5f5ea61b6` | yes | 0.3636 | 10.8 | 2788 | 155 | — |
| 4 | `DOC-fbcdd16e24f143ac` | yes | 0.1582 | 10.8 | 2456 | 155 | — |
| 5 | `DOC-12a6d4cd092cf66d` | yes | 0.5026 | 10.9 | 7710 | 158 | — |
| 6 | `DOC-9ca44c7926a47ede` | yes | 0.5024 | 10.9 | 2292 | 167 | — |
| 7 | `DOC-81ae205a3b0bf16f` | yes | 0.2480 | 10.9 | 2515 | 169 | — |
| 8 | `DOC-020d77c0107d273d` | yes | 0.4746 | 17.9 | 2302 | 203 | — |
| 9 | `DOC-91f89b9c0d285ac7` | yes | 0.6667 | 11.4 | 6902 | 128 | — |
| 10 | `DOC-c4c9c37a96291975` | yes | 0.0813 | 11.5 | 2424 | 136 | — |
| 11 | `DOC-a040ac19abb88fec` | yes | 0.4097 | 12.8 | 2206 | 141 | — |
| 12 | `DOC-0a262afc80c73247` | yes | 0.1136 | 13.0 | 3124 | 153 | — |
| 13 | `DOC-2819b889b134ea01` | yes | 0.7500 | 13.1 | 5344 | 151 | — |
| 14 | `DOC-0f56fe8db6df01bd` | yes | 0.0635 | 13.2 | 5368 | 161 | — |
| 15 | `DOC-732b812b7d9d9653` | yes | 0.8889 | 13.8 | 5572 | 156 | — |
| 16 | `DOC-68d5a8753fcc3675` | yes | 0.4405 | 9.9 | 5671 | 178 | — |
| 17 | `DOC-e077f1f7e80e1e04` | yes | 0.1624 | 8.2 | 4043 | 160 | — |
| 18 | `DOC-9376c6bfa6779d5e` | yes | 0.4822 | 6.8 | 2200 | 139 | — |
| 19 | `DOC-f134b9491efc5c57` | yes | 0.7949 | 7.2 | 2865 | 148 | — |
| 20 | `DOC-2f19002c84083aa8` | yes | 0.4363 | 9.1 | 5200 | 162 | — |
| 21 | `DOC-b3ad98e5530dfeaf` | yes | 0.2820 | 10.7 | 2521 | 190 | — |
| 22 | `DOC-1e8e3ce47882ae71` | yes | 0.1485 | 12.2 | 3063 | 198 | — |
| 23 | `DOC-fc9f56d999bd7566` | yes | 0.6667 | 11.6 | 2509 | 204 | — |
| 24 | `DOC-4dc719baa790a79c` | yes | 0.6667 | 10.5 | 2669 | 163 | — |
| 25 | `DOC-e478fa89043a29e3` | yes | 0.8205 | 10.2 | 2910 | 151 | — |
| 26 | `DOC-474a0002b4c03be1` | yes | 0.8205 | 10.2 | 2938 | 152 | — |
| 27 | `DOC-d015968793450753` | yes | 0.7222 | 11.0 | 5082 | 159 | — |
| 28 | `DOC-a5fd7fe18b094f20` | yes | 0.8485 | 9.8 | 5919 | 145 | — |
| 29 | `DOC-204c3c7c0ba021cd` | yes | 0.4746 | 7.1 | 2226 | 133 | — |
| 30 | `DOC-b832b5eaa2b4848c` | yes | 0.1068 | 9.1 | 2762 | 157 | — |
| 31 | `DOC-9467462d9bb34f8e` | yes | 0.5417 | 9.4 | 5345 | 162 | — |
| 32 | `DOC-41b53ea487b84955` | yes | 0.7500 | 16.6 | 4617 | 239 | — |
| 33 | `DOC-bfa92eb6c72569ee` | yes | 0.1184 | 10.8 | 3771 | 158 | — |
| 34 | `DOC-37152a33cfb70d37` | yes | 0.4103 | 9.9 | 2902 | 161 | — |
| 35 | `DOC-00193d0c070747e6` | yes | 0.7143 | 12.0 | 3225 | 181 | — |
| 36 | `DOC-ffb48271e0a5e812` | yes | 0.6667 | 8.9 | 5344 | 144 | — |
| 37 | `DOC-0a8eb16fff7e67ca` | yes | 0.6923 | 9.0 | 5246 | 150 | — |
| 38 | `DOC-a973ebf005e0e785` | yes | 0.4278 | 14.5 | 6146 | 212 | — |
| 39 | `DOC-f21f3dadebb121e3` | yes | 0.7843 | 13.2 | 3308 | 181 | — |
| 40 | `DOC-80e90a37bb750a3c` | yes | 0.1495 | 11.8 | 2776 | 188 | — |
| 41 | `DOC-78f2456f571403a9` | yes | 0.1531 | 10.1 | 2345 | 144 | — |
| 42 | `DOC-e6906e59f9bd74ca` | yes | 0.6200 | 12.0 | 2978 | 160 | — |
| 43 | `DOC-2338d194d5250def` | yes | 0.4867 | 10.5 | 5258 | 129 | — |
| 44 | `DOC-d4dfbfe8049d41f9` | yes | 0.4934 | 12.5 | 3856 | 175 | — |
| 45 | `DOC-866139125545b36a` | yes | 0.7733 | 11.6 | 5397 | 168 | — |
| 46 | `DOC-606242f2919653a4` | yes | 0.2332 | 8.9 | 5253 | 156 | — |
| 47 | `DOC-842215e36884da89` | yes | 0.2467 | 7.9 | 5226 | 162 | — |
| 48 | `DOC-d0aebe650be3e512` | yes | 0.4976 | 6.4 | 2405 | 163 | — |
| 49 | `DOC-dfe42f3747f299e6` | yes | 0.7500 | 6.7 | 5870 | 166 | — |
| 50 | `DOC-27bbad54b6fd107e` | yes | 0.5000 | 5.1 | 2871 | 183 | — |

_Generated 2026-10-13T04:32:42+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-corporate-records-specialist-awq-1l4-c8.card.json`._
