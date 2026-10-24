# Run report — `sand032-s3-corr50`

SAND-032 Modal × vLLM specialist extract: **50 correspondence docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 32** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s3-corr50` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=16 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16], max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 50 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `8e4572ae7fba` |
| git | `76d11cc (dirty)` |
| spec_hash | `bb2c69c6464f1de4f28a0bcf0573be9c500804aa9423d47b8c1544f764ea03db` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **50 / 50** (errors 0) |
| **overall_extraction_score** | **0.3004** (sd 0.2088, min 0.0000, max 0.8095) |
| schema_valid_rate | 0.980 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 16.024 s |
| concurrency | 32 (16 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.193 s |
| latency p50 / p95 / max | 6.83 / 12.93 / 15.96 s |
| prompt / completion tokens | 109864 / 8639 |
| throughput | 7395.3 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 0.007122 |
| **$ per doc (busy)** | **0.000142** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.3 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 2 of 2** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790546353.94`: requests Δ 35 (cumulative 204), measured TTFT mean 0.711 s (vLLM histogram, cumulative), prefix-cache hit 74.9%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.
- replica `1790546749.43`: requests Δ 15 (cumulative 66), measured TTFT mean 1.149 s (vLLM histogram, cumulative), prefix-cache hit 55.1%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 366.9 s over wall 16.0 s = **22.89×** effective parallelism at c32 (72% of the ideal 32×).
- **Tail:** slowest doc `DOC-f4b4c8c623ccb915` (press_release) 16.0 s = 100% of wall — p95/p50 = 1.89×.
- **Prompt length vs latency:** Pearson r = 0.34 across 50 docs (not prefill-dominated).
- **Decode budget:** mean completion 173 tok/doc, mean prompt 2197 tok/doc.
- **Subclass spread:** best `meeting_request` 0.536 (n=1), worst `letter` 0.225 (n=3).
- **Field-level extraction:** 29/50 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s3-corr50-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s3-corr50-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| email | 28 | 0.2753 |
| memo | 9 | 0.3075 |
| notice | 4 | 0.3923 |
| press_release | 3 | 0.2789 |
| letter | 3 | 0.2248 |
| demand | 2 | 0.4628 |
| meeting_request | 1 | 0.5362 |
| **total** | **50** | **0.3004** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-c2826f69ed293da4` | memo | 0.1053 | 0.0000 | ✓ | 4.2 | 1698 | 103 |  |
| 2 | `DOC-f36a37e1a9c1351e` | press_release | 0.1667 | 0.0000 | ✓ | 4.3 | 1707 | 109 |  |
| 3 | `DOC-1d5664e2c826ad07` | email | 0.3889 | 0.1428 | ✓ | 4.3 | 1685 | 115 |  |
| 4 | `DOC-4eb0e9385b81cc4b` | email | 0.0303 | 0.0000 | ✓ | 4.7 | 1784 | 131 |  |
| 5 | `DOC-c4debd478f2c06e0` | email | 0.3156 | 0.0000 | ✓ | 4.6 | 1936 | 135 |  |
| 6 | `DOC-c71d3ca0b727a0d4` | email | 0.0833 | 0.0000 | ✓ | 4.8 | 1779 | 134 |  |
| 7 | `DOC-47647a5fdcd45666` | email | 0.3333 | 0.1250 | ✓ | 4.7 | 1916 | 136 |  |
| 8 | `DOC-44b1e5a60b363d3e` | letter | 0.0889 | 0.0000 | ✓ | 5.2 | 1996 | 151 |  |
| 9 | `DOC-690cb07fef21747b` | email | 0.5088 | 0.1333 | ✓ | 5.1 | 1954 | 148 |  |
| 10 | `DOC-cb4f8fb4ccb52f44` | email | 0.0833 | 0.0000 | ✓ | 5.4 | 1739 | 152 |  |
| 11 | `DOC-383b9badb01a1a00` | email | 0.1010 | 0.0000 | ✓ | 5.5 | 4829 | 157 |  |
| 12 | `DOC-d0c241ea24439be2` | email | 0.4689 | 0.1176 | ✓ | 5.7 | 1793 | 167 |  |
| 13 | `DOC-9ec94a2619e46dfb` | email | 0.4000 | 0.1112 | ✓ | 6.1 | 1742 | 172 |  |
| 14 | `DOC-a8efd6e4c4d49aaf` | email | 0.5308 | 0.1112 | ✓ | 6.1 | 1940 | 180 |  |
| 15 | `DOC-38c54645bf0e601a` | email | 0.3140 | 0.0000 | ✓ | 6.9 | 2025 | 198 |  |
| 16 | `DOC-2bdbf0be591edea6` | memo | 0.0800 | 0.0000 | ✓ | 7.1 | 1729 | 145 |  |
| 17 | `DOC-91f5631a20c62dc5` | email | 0.3544 | 0.0000 | ✓ | 7.2 | 1922 | 211 |  |
| 18 | `DOC-16dfd03aed14e557` | email | 0.0784 | 0.0000 | ✓ | 7.5 | 1674 | 107 |  |
| 19 | `DOC-228e51bba45b5c7d` | email | 0.2693 | 0.0000 | ✓ | 8.3 | 2506 | 178 |  |
| 20 | `DOC-8eed243667c985bd` | email | 0.7917 | 0.2105 | ✓ | 8.3 | 2149 | 177 |  |
| 21 | `DOC-c45ecc852b2cb0f4` | meeting_request | 0.5362 | 0.1176 | ✓ | 8.7 | 1823 | 189 |  |
| 22 | `DOC-20b4e31d9a4bf994` | email | 0.2359 | 0.0000 | ✓ | 8.7 | 1855 | 114 |  |
| 23 | `DOC-2431095adda97989` | memo | 0.1752 | 0.0000 | ✓ | 9.5 | 2075 | 278 |  |
| 24 | `DOC-553256644e7b4547` | email | 0.0952 | 0.0000 | ✓ | 9.6 | 1773 | 148 |  |
| 25 | `DOC-2cde0c6d0c70b02b` | memo | 0.0870 | 0.0000 | ✓ | 9.5 | 2206 | 225 |  |
| 26 | `DOC-a318b50872273528` | email | 0.1167 | 0.0000 | ✓ | 9.8 | 2028 | 178 |  |
| 27 | `DOC-5adf644f3cb1d34e` | email | 0.0000 | 0.0000 | ✓ | 3.8 | 1668 | 87 |  |
| 28 | `DOC-9b2bc061621a56be` | email | 0.3523 | 0.0000 | ✓ | 5.8 | 2043 | 139 |  |
| 29 | `DOC-8754555168547e16` | email | 0.3458 | 0.0000 | ✓ | 10.7 | 2631 | 215 |  |
| 30 | `DOC-21460a9f6d7e6348` | memo | 0.7255 | 0.2354 | ✗ | 6.5 | 1806 | 134 |  |
| 31 | `DOC-edd0a288e32f0d3b` | notice | 0.6667 | 0.2222 | ✓ | 6.6 | 1976 | 154 |  |
| 32 | `DOC-38265bcc6ecfecc3` | email | 0.0784 | 0.0000 | ✓ | 10.8 | 1729 | 172 |  |
| 33 | `DOC-17ac4251c7d94cea` | email | 0.1111 | 0.0000 | ✓ | 3.7 | 1730 | 123 |  |
| 34 | `DOC-314aa51db90c8c92` | memo | 0.4167 | 0.1112 | ✓ | 11.1 | 2541 | 186 |  |
| 35 | `DOC-d6e2bbd8c5e394a4` | demand | 0.8095 | 0.2499 | ✓ | 6.8 | 1732 | 156 |  |
| 36 | `DOC-96438076efc6cc7b` | email | 0.3333 | 0.1250 | ✓ | 4.9 | 1778 | 159 |  |
| 37 | `DOC-c4074ed5b08f097e` | memo | 0.3827 | 0.1333 | ✓ | 6.0 | 1724 | 132 |  |
| 38 | `DOC-a6fff0ef0e406461` | email | 0.1346 | 0.0000 | ✓ | 6.8 | 1843 | 171 |  |
| 39 | `DOC-f6a9a00e53cc7973` | notice | 0.1333 | 0.0000 | ✓ | 7.4 | 6883 | 178 |  |
| 40 | `DOC-ff15276697cdfbb2` | demand | 0.1162 | 0.0000 | ✓ | 6.9 | 2322 | 191 |  |
| 41 | `DOC-595ab9fc19465909` | notice | 0.3333 | 0.1112 | ✓ | 7.3 | 1840 | 181 |  |
| 42 | `DOC-d3d85dc1b1514bec` | notice | 0.4359 | 0.1112 | ✓ | 8.6 | 1913 | 223 |  |
| 43 | `DOC-1dcf4dfd5ec6defb` | email | 0.2744 | 0.0000 | ✓ | 12.9 | 3002 | 265 |  |
| 44 | `DOC-c01ab1c1c673f355` | letter | 0.4743 | 0.1333 | ✓ | 6.3 | 1863 | 132 |  |
| 45 | `DOC-76375ebb4cd91de9` | letter | 0.1111 | 0.0000 | ✓ | 8.0 | 2516 | 200 |  |
| 46 | `DOC-e624b1b9823e53f5` | memo | 0.4617 | 0.1112 | ✓ | 13.6 | 2386 | 266 |  |
| 47 | `DOC-ee6bae4d269c1911` | memo | 0.3333 | 0.1112 | ✓ | 9.5 | 2830 | 269 |  |
| 48 | `DOC-5b63f9fe205d564b` | email | 0.5800 | 0.1250 | ✓ | 6.7 | 1894 | 169 |  |
| 49 | `DOC-9422c8775b387935` | press_release | 0.5901 | 0.1176 | ✓ | 8.7 | 2588 | 215 |  |
| 50 | `DOC-f4b4c8c623ccb915` | press_release | 0.0800 | 0.0000 | ✓ | 16.0 | 4363 | 384 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s3-corr50.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s3-corr50
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s3-corr50.yaml` | run spec |
| `reports/serving/sand032-s3-corr50.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s3-corr50/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s3-corr50/` | offline Braintrust-shaped rows — disposed after this report is committed |
