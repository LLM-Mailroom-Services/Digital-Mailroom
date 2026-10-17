# Corporate Records — 2× L4 · C16 · n=50

**Run:** `sand42-50-corporate-records-specialist-awq-2l4-c16` · **Model:** Qwen/Qwen3-8B-AWQ · vLLM v0.29.0 · Modal `sandbox-vllm` · L4 @ $0.80/GPU-hr

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
| Run ID | `sand42-50-corporate-records-specialist-awq-2l4-c16` |
| GPUs / replicas | 2 |
| Concurrency | 16 (8 per replica) |
| Documents | 50 |
| Spec hash | 7d4a833c… |
| **Time** |  |
| Wall (busy) | 58.45 s |
| GPU seconds | 59.44 s |
| Cold boot | 0.23 s |
| **Cost** |  |
| Busy-window GPU $ | $0.025976 |
| Billed GPU $ | $0.026416 |
| Billed seconds | 59.44 s |
| Idle $ | $0.007421 (16.70 s) |
| Cost per document | $0.000528 |
| Cost per ok document | $0.000528 |
| Cost per 1M tokens | $0.1286 |
| **Tokens** |  |
| Prompt tokens | 197,319 |
| Completion tokens | 8,021 (3.9%) |
| Total tokens | 205,340 |
| Tokens per document | 4,107 |
| Per document: instructions + template | 2,090 (50.9%) |
| Per document: document text | 1,856 (45.2%) |
| Per document: output | 160 (3.9%) |
| Instruction tokens per model call | 2,090 over 50 calls |
| Token split basis | fit across documents, 4.21 chars/token |
| Completion p95 / max (ok docs) | 201 / 239 |
| **Throughput** |  |
| Tokens / second | 3,513.3 |
| Tokens / second per L4 | 1,756.6 |
| Documents / minute | 51.33 |
| **Latency (per document, ok rows)** |  |
| Mean | 13.36 s |
| p50 | 12.51 s |
| p95 | 25.31 s |
| Max | 25.57 s |
| **Engine (vLLM /metrics)** |  |
| Parallelism (Σ latency ÷ wall) | 11.43× of 16 |
| Slot occupancy | 71.4% |
| Coverage | replicas observed: 2 of 2 |
| Requests per replica (this run) | 17 / 33 |
| Mean TTFT per replica | 0.641 s / 2.612 s |
| Prefix-cache hit per replica | 49.9% / 49.9% |
| Preemptions per replica (this run) | 0 / 0 |
| Length-capped finishes per replica (this run) | 0 / 0 |
| **GPU hardware (nvidia-smi)** | 17 samples · serving-replica nvidia-smi |
| GPU utilization | 81.2 % mean (p95 100.0 / peak 100.0 / min 0.0) |
| Sampling coverage | 97.9 % |
| GPU power draw | 64.6 W (min 33.3 / max 73.1) of 72 W cap |
| GPU memory bandwidth | 65.1 % (min 0.0 / max 100.0) |
| GPU SM clock | 1,424 MHz (min 960 / max 2,040) |
| GPU temperature | 77.0 C (min 69.0 / max 81.0) |
| GPU memory used | 20,996 MiB (min 20,996 / max 20,997) |
| **Quality** |  |
| Overall extraction score | 0.4880 (sd 0.250) |
| Score min / max | 0.0635 / 0.8889 |
| Scoring method | `suite` |
| Schema-valid rate | 0.96 |
| Parse errors | 0 |
| Errors | 0 / 50 |
| **Paired n** |  |
| Documents a paired delta can use | 50 of 50 |

## Figure

![Corporate Records run dashboard](sand42-50-corporate-records-specialist-awq-2l4-c16.card.png)

## Per-document results

| # | Document | OK | Score | Latency (s) | Prompt tok | Completion tok | Error |
| ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `DOC-732b812b7d9d9653` | yes | 0.8889 | 8.4 | 5572 | 165 | — |
| 2 | `DOC-68d5a8753fcc3675` | yes | 0.4405 | 8.4 | 5671 | 178 | — |
| 3 | `DOC-b3ad98e5530dfeaf` | yes | 0.2820 | 5.2 | 2521 | 190 | — |
| 4 | `DOC-9376c6bfa6779d5e` | yes | 0.4822 | 3.6 | 2200 | 131 | — |
| 5 | `DOC-020d77c0107d273d` | yes | 0.4746 | 17.4 | 2302 | 116 | — |
| 6 | `DOC-91f89b9c0d285ac7` | yes | 0.6667 | 17.5 | 6902 | 126 | — |
| 7 | `DOC-9ca44c7926a47ede` | yes | 0.5024 | 17.5 | 2292 | 131 | — |
| 8 | `DOC-c4c9c37a96291975` | yes | 0.0813 | 19.0 | 2424 | 136 | — |
| 9 | `DOC-0a262afc80c73247` | yes | 0.1136 | 20.0 | 3124 | 143 | — |
| 10 | `DOC-a040ac19abb88fec` | yes | 0.4121 | 20.3 | 2206 | 141 | — |
| 11 | `DOC-6790430ae2a6c724` | yes | 0.1846 | 20.4 | 4477 | 142 | — |
| 12 | `DOC-fbcdd16e24f143ac` | yes | 0.1582 | 20.4 | 2456 | 155 | — |
| 13 | `DOC-e545bbd5f5ea61b6` | yes | 0.3636 | 20.5 | 2788 | 158 | — |
| 14 | `DOC-81ae205a3b0bf16f` | yes | 0.2480 | 20.5 | 2515 | 158 | — |
| 15 | `DOC-12a6d4cd092cf66d` | yes | 0.5026 | 21.9 | 7710 | 158 | — |
| 16 | `DOC-e077f1f7e80e1e04` | yes | 0.1624 | 14.0 | 4043 | 151 | — |
| 17 | `DOC-f134b9491efc5c57` | yes | 0.7949 | 6.6 | 2865 | 152 | — |
| 18 | `DOC-0f56fe8db6df01bd` | yes | 0.0635 | 25.3 | 5368 | 161 | — |
| 19 | `DOC-01054efd0980066b` | yes | 0.8222 | 25.3 | 5122 | 159 | — |
| 20 | `DOC-2819b889b134ea01` | yes | 0.7500 | 25.6 | 5344 | 171 | — |
| 21 | `DOC-fc9f56d999bd7566` | yes | 0.6667 | 8.1 | 2509 | 188 | — |
| 22 | `DOC-e478fa89043a29e3` | yes | 0.8205 | 8.5 | 2910 | 151 | — |
| 23 | `DOC-d015968793450753` | yes | 0.8056 | 8.6 | 5082 | 166 | — |
| 24 | `DOC-b832b5eaa2b4848c` | yes | 0.1068 | 7.2 | 2762 | 158 | — |
| 25 | `DOC-bfa92eb6c72569ee` | yes | 0.1184 | 7.4 | 3771 | 158 | — |
| 26 | `DOC-0a8eb16fff7e67ca` | yes | 0.6923 | 6.5 | 5246 | 150 | — |
| 27 | `DOC-37152a33cfb70d37` | yes | 0.4103 | 6.9 | 2902 | 160 | — |
| 28 | `DOC-2f19002c84083aa8` | yes | 0.4978 | 16.4 | 5200 | 165 | — |
| 29 | `DOC-4dc719baa790a79c` | yes | 0.6667 | 14.8 | 2669 | 163 | — |
| 30 | `DOC-204c3c7c0ba021cd` | yes | 0.4746 | 11.2 | 2226 | 133 | — |
| 31 | `DOC-a5fd7fe18b094f20` | yes | 0.8485 | 13.6 | 5919 | 145 | — |
| 32 | `DOC-474a0002b4c03be1` | yes | 0.8205 | 13.8 | 2938 | 149 | — |
| 33 | `DOC-f21f3dadebb121e3` | yes | 0.7843 | 8.8 | 3308 | 180 | — |
| 34 | `DOC-9467462d9bb34f8e` | yes | 0.5417 | 18.2 | 5345 | 157 | — |
| 35 | `DOC-78f2456f571403a9` | yes | 0.1531 | 7.4 | 2345 | 144 | — |
| 36 | `DOC-1e8e3ce47882ae71` | yes | 0.1485 | 21.5 | 3063 | 198 | — |
| 37 | `DOC-2338d194d5250def` | yes | 0.4867 | 6.2 | 5258 | 128 | — |
| 38 | `DOC-00193d0c070747e6` | yes | 0.7143 | 14.9 | 3225 | 173 | — |
| 39 | `DOC-ffb48271e0a5e812` | yes | 0.6667 | 11.8 | 5344 | 139 | — |
| 40 | `DOC-d4dfbfe8049d41f9` | yes | 0.4907 | 8.2 | 3856 | 179 | — |
| 41 | `DOC-842215e36884da89` | yes | 0.2467 | 6.7 | 5226 | 158 | — |
| 42 | `DOC-41b53ea487b84955` | yes | 0.7500 | 21.3 | 4617 | 239 | — |
| 43 | `DOC-a973ebf005e0e785` | yes | 0.4278 | 16.8 | 6146 | 234 | — |
| 44 | `DOC-80e90a37bb750a3c` | yes | 0.1654 | 13.2 | 2776 | 201 | — |
| 45 | `DOC-e6906e59f9bd74ca` | yes | 0.6200 | 10.5 | 2978 | 160 | — |
| 46 | `DOC-866139125545b36a` | yes | 0.7733 | 10.1 | 5397 | 161 | — |
| 47 | `DOC-606242f2919653a4` | yes | 0.2332 | 10.0 | 5253 | 160 | — |
| 48 | `DOC-d0aebe650be3e512` | yes | 0.4976 | 6.1 | 2405 | 163 | — |
| 49 | `DOC-dfe42f3747f299e6` | yes | 0.7500 | 9.9 | 5870 | 168 | — |
| 50 | `DOC-27bbad54b6fd107e` | yes | 0.6250 | 5.7 | 2871 | 171 | — |

_Generated 2026-10-13T04:33:01+00:00 by `sandbox run card`. Machine-readable twin: `sand42-50-corporate-records-specialist-awq-2l4-c16.card.json`._
