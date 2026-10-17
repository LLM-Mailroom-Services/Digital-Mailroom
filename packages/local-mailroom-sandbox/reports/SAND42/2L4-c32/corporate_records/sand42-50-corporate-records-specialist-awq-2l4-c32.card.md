# Corporate Records — 2× L4 · C32 · n=50

**Run:** `sand42-50-corporate-records-specialist-awq-2l4-c32` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `sand42-50-corporate-records-specialist-awq-2l4-c32` |
| GPUs / replicas | 2 |
| Concurrency | 32 (16 per replica) |
| Documents | 50 |
| Spec hash | 4c3e1631… |
| **Time** |  |
| Wall (busy) | 49.07 s |
| GPU seconds | 48.73 s |
| Cold boot | 0.43 s |
| **Cost** |  |
| Busy-window GPU $ | $0.021808 |
| Billed GPU $ | $0.021657 |
| Billed seconds | 48.73 s |
| Idle $ | $0.008692 (19.56 s) |
| Cost per document | $0.000433 |
| Cost per ok document | $0.000433 |
| Cost per 1M tokens | $0.1055 |
| **Tokens** |  |
| Prompt tokens | 197,319 |
| Completion tokens | 7,995 (3.9%) |
| Total tokens | 205,314 |
| Tokens per document | 4,106 |
| Per document: instructions + template | 2,090 (50.9%) |
| Per document: document text | 1,856 (45.2%) |
| Per document: output | 160 (3.9%) |
| Instruction tokens per model call | 2,090 over 50 calls |
| Token split basis | fit across documents, 4.21 chars/token |
| Completion p95 / max (ok docs) | 198 / 234 |
| **Throughput** |  |
| Tokens / second | 4,184.2 |
| Tokens / second per L4 | 2,092.1 |
| Documents / minute | 61.14 |
| **Latency (per document, ok rows)** |  |
| Mean | 18.89 s |
| p50 | 16.83 s |
| p95 | 31.52 s |
| Max | 33.25 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 19.25× of 32 |
| Slot occupancy | 60.1% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 21 / 29 |
| Mean TTFT per replica | 2.126 s / 8.062 s |
| Prefix-cache hit per replica | 45.5% / 52.7% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **GPU hardware (nvidia-smi)** | 14 samples · serving-replica nvidia-smi |
| GPU utilization | 63.7 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 100.0 % |
| GPU power draw | 56.1 W (min 30.3 / max 72.4) of 72 W cap |
| GPU memory bandwidth | 46.6 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,500 MHz (min 960 / max 2,040) |
| GPU temperature | 70.8 C (min 57.0 / max 82.0) |
| GPU memory used | 21,023 MiB (min 21,022 / max 21,026) |
| **Quality** |  |
| Overall extraction score | 0.5002 (sd 0.252) |
| Score min / max | 0.0635 / 0.8889 |
| Scoring method | `suite` |
| Schema-valid rate | 0.96 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Corporate Records run dashboard](sand42-50-corporate-records-specialist-awq-2l4-c32.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-91f89b9c0d285ac7` | yes | 0.6667 | 16.0 | 6902 | 126 | — |
| 2 | `DOC-9ca44c7926a47ede` | yes | 0.5024 | 16.0 | 2292 | 130 | — |
| 3 | `DOC-020d77c0107d273d` | yes | 0.4746 | 16.0 | 2302 | 116 | — |
| 4 | `DOC-a5fd7fe18b094f20` | yes | 0.8485 | 16.0 | 5919 | 145 | — |
| 5 | `DOC-204c3c7c0ba021cd` | yes | 0.4746 | 16.1 | 2226 | 152 | — |
| 6 | `DOC-0a262afc80c73247` | yes | 0.1136 | 16.3 | 3124 | 153 | — |
| 7 | `DOC-81ae205a3b0bf16f` | yes | 0.5813 | 16.3 | 2515 | 153 | — |
| 8 | `DOC-2819b889b134ea01` | yes | 0.7500 | 16.5 | 5344 | 151 | — |
| 9 | `DOC-9376c6bfa6779d5e` | yes | 0.4822 | 17.4 | 2200 | 131 | — |
| 10 | `DOC-e077f1f7e80e1e04` | yes | 0.1624 | 17.8 | 4043 | 153 | — |
| 11 | `DOC-c4c9c37a96291975` | yes | 0.0813 | 18.9 | 2424 | 136 | — |
| 12 | `DOC-a040ac19abb88fec` | yes | 0.4097 | 19.6 | 2206 | 141 | — |
| 13 | `DOC-474a0002b4c03be1` | yes | 0.8205 | 19.7 | 2938 | 150 | — |
| 14 | `DOC-2f19002c84083aa8` | yes | 0.4978 | 19.8 | 5200 | 165 | — |
| 15 | `DOC-732b812b7d9d9653` | yes | 0.8889 | 20.2 | 5572 | 165 | — |
| 16 | `DOC-e478fa89043a29e3` | yes | 0.8205 | 20.2 | 2910 | 151 | — |
| 17 | `DOC-12a6d4cd092cf66d` | yes | 0.5026 | 21.3 | 7710 | 157 | — |
| 18 | `DOC-f134b9491efc5c57` | yes | 0.7949 | 22.4 | 2865 | 152 | — |
| 19 | `DOC-0f56fe8db6df01bd` | yes | 0.0635 | 22.8 | 5368 | 168 | — |
| 20 | `DOC-b3ad98e5530dfeaf` | yes | 0.2820 | 22.6 | 2521 | 182 | — |
| 21 | `DOC-fbcdd16e24f143ac` | yes | 0.1582 | 23.9 | 2456 | 155 | — |
| 22 | `DOC-e545bbd5f5ea61b6` | yes | 0.6970 | 23.9 | 2788 | 157 | — |
| 23 | `DOC-01054efd0980066b` | yes | 0.8222 | 24.2 | 5122 | 159 | — |
| 24 | `DOC-9467462d9bb34f8e` | yes | 0.5417 | 25.5 | 5345 | 156 | — |
| 25 | `DOC-4dc719baa790a79c` | yes | 0.7255 | 27.4 | 2669 | 170 | — |
| 26 | `DOC-68d5a8753fcc3675` | yes | 0.4405 | 27.9 | 5671 | 177 | — |
| 27 | `DOC-fc9f56d999bd7566` | yes | 0.6667 | 28.6 | 2509 | 196 | — |
| 28 | `DOC-e6906e59f9bd74ca` | yes | 0.6200 | 11.1 | 2978 | 160 | — |
| 29 | `DOC-00193d0c070747e6` | yes | 0.7143 | 13.1 | 3225 | 173 | — |
| 30 | `DOC-dfe42f3747f299e6` | yes | 0.7500 | 8.9 | 5870 | 158 | — |
| 31 | `DOC-606242f2919653a4` | yes | 0.2332 | 9.5 | 5253 | 165 | — |
| 32 | `DOC-f21f3dadebb121e3` | yes | 0.7843 | 13.2 | 3308 | 180 | — |
| 33 | `DOC-80e90a37bb750a3c` | yes | 0.1495 | 13.0 | 2776 | 181 | — |
| 34 | `DOC-27bbad54b6fd107e` | yes | 0.8333 | 7.1 | 2871 | 169 | — |
| 35 | `DOC-866139125545b36a` | yes | 0.7733 | 10.2 | 5397 | 180 | — |
| 36 | `DOC-41b53ea487b84955` | yes | 0.7500 | 29.8 | 4617 | 228 | — |
| 37 | `DOC-b832b5eaa2b4848c` | yes | 0.1068 | 30.3 | 2762 | 95 | — |
| 38 | `DOC-a973ebf005e0e785` | yes | 0.4278 | 14.8 | 6146 | 234 | — |
| 39 | `DOC-6790430ae2a6c724` | yes | 0.1846 | 31.5 | 4477 | 142 | — |
| 40 | `DOC-2338d194d5250def` | yes | 0.4867 | 12.2 | 5258 | 128 | — |
| 41 | `DOC-d015968793450753` | yes | 0.8056 | 32.0 | 5082 | 171 | — |
| 42 | `DOC-ffb48271e0a5e812` | yes | 0.6667 | 16.1 | 5344 | 142 | — |
| 43 | `DOC-bfa92eb6c72569ee` | yes | 0.1184 | 16.6 | 3771 | 158 | — |
| 44 | `DOC-0a8eb16fff7e67ca` | yes | 0.3590 | 16.5 | 5246 | 159 | — |
| 45 | `DOC-78f2456f571403a9` | yes | 0.1809 | 15.3 | 2345 | 154 | — |
| 46 | `DOC-37152a33cfb70d37` | yes | 0.4103 | 17.0 | 2902 | 175 | — |
| 47 | `DOC-842215e36884da89` | yes | 0.2467 | 12.9 | 5226 | 161 | — |
| 48 | `DOC-d0aebe650be3e512` | yes | 0.4976 | 11.9 | 2405 | 163 | — |
| 49 | `DOC-d4dfbfe8049d41f9` | yes | 0.4934 | 14.4 | 3856 | 174 | — |
| 50 | `DOC-1e8e3ce47882ae71` | yes | 0.1485 | 33.3 | 3063 | 198 | — |

_Generated 2026-10-13T04:33:08+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-corporate-records-specialist-awq-2l4-c32.card.json`._
