# Run report — `sand032-s3-corr50-repeat`

SAND-032 Modal × vLLM specialist extract: **50 correspondence docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 32** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s3-corr50-repeat` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=16 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16], max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 50 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `8e4572ae7fba` |
| git | `d79d863 (dirty)` |
| spec_hash | `bb2c69c6464f1de4f28a0bcf0573be9c500804aa9423d47b8c1544f764ea03db` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **50 / 50** (errors 0) |
| **overall_extraction_score** | **0.3043** (sd 0.2139, min 0.0000, max 0.7917) |
| schema_valid_rate | 1.000 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 21.210 s |
| concurrency | 32 (16 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.194 s |
| latency p50 / p95 / max | 10.79 / 17.84 / 21.15 s |
| prompt / completion tokens | 109864 / 8595 |
| throughput | 5585.1 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 0.009427 |
| **$ per doc (busy)** | **0.000189** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.3 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 2 of 2** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790546353.94`: requests Δ 25 (cumulative 325), measured TTFT mean 6.630 s (vLLM histogram, cumulative), prefix-cache hit 49.0%, preemptions 0, length-capped finishes 7, KV usage at scrape 0%.
- replica `1790546749.43`: requests Δ 25 (cumulative 195), measured TTFT mean 6.673 s (vLLM histogram, cumulative), prefix-cache hit 38.5%, preemptions 0, length-capped finishes 2, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 553.9 s over wall 21.2 s = **26.12×** effective parallelism at c32 (82% of the ideal 32×).
- **Tail:** slowest doc `DOC-f4b4c8c623ccb915` (press_release) 21.1 s = 100% of wall — p95/p50 = 1.65×.
- **Prompt length vs latency:** Pearson r = 0.26 across 50 docs (not prefill-dominated).
- **Decode budget:** mean completion 172 tok/doc, mean prompt 2197 tok/doc.
- **Subclass spread:** best `meeting_request` 0.536 (n=1), worst `letter` 0.225 (n=3).
- **Field-level extraction:** 28/50 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s3-corr50-repeat-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s3-corr50-repeat-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| email | 28 | 0.2817 |
| memo | 9 | 0.3079 |
| notice | 4 | 0.4179 |
| press_release | 3 | 0.2567 |
| letter | 3 | 0.2248 |
| demand | 2 | 0.4509 |
| meeting_request | 1 | 0.5362 |
| **total** | **50** | **0.3043** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-c2826f69ed293da4` | memo | 0.1053 | 0.0000 | ✓ | 8.3 | 1698 | 103 |  |
| 2 | `DOC-f36a37e1a9c1351e` | press_release | 0.1667 | 0.0000 | ✓ | 8.3 | 1707 | 107 |  |
| 3 | `DOC-1d5664e2c826ad07` | email | 0.3889 | 0.1428 | ✓ | 8.3 | 1685 | 115 |  |
| 4 | `DOC-47647a5fdcd45666` | email | 0.3333 | 0.1250 | ✓ | 9.0 | 1916 | 136 |  |
| 5 | `DOC-4eb0e9385b81cc4b` | email | 0.0303 | 0.0000 | ✓ | 9.1 | 1784 | 139 |  |
| 6 | `DOC-16dfd03aed14e557` | email | 0.0784 | 0.0000 | ✓ | 10.2 | 1674 | 107 |  |
| 7 | `DOC-20b4e31d9a4bf994` | email | 0.2359 | 0.0000 | ✓ | 10.7 | 1855 | 114 |  |
| 8 | `DOC-690cb07fef21747b` | email | 0.5088 | 0.1333 | ✓ | 10.8 | 1954 | 148 |  |
| 9 | `DOC-553256644e7b4547` | email | 0.0952 | 0.0000 | ✓ | 11.5 | 1773 | 123 |  |
| 10 | `DOC-44b1e5a60b363d3e` | letter | 0.0889 | 0.0000 | ✓ | 11.9 | 1996 | 151 |  |
| 11 | `DOC-cb4f8fb4ccb52f44` | email | 0.0833 | 0.0000 | ✓ | 12.1 | 1739 | 155 |  |
| 12 | `DOC-38265bcc6ecfecc3` | email | 0.1111 | 0.0000 | ✓ | 12.0 | 1729 | 154 |  |
| 13 | `DOC-c71d3ca0b727a0d4` | email | 0.0833 | 0.0000 | ✓ | 12.2 | 1779 | 134 |  |
| 14 | `DOC-c4debd478f2c06e0` | email | 0.2045 | 0.0000 | ✓ | 12.5 | 1936 | 139 |  |
| 15 | `DOC-2bdbf0be591edea6` | memo | 0.0800 | 0.0000 | ✓ | 12.6 | 1729 | 143 |  |
| 16 | `DOC-d0c241ea24439be2` | email | 0.4689 | 0.1176 | ✓ | 12.5 | 1793 | 167 |  |
| 17 | `DOC-a8efd6e4c4d49aaf` | email | 0.5308 | 0.1112 | ✓ | 13.5 | 1940 | 178 |  |
| 18 | `DOC-314aa51db90c8c92` | memo | 0.4167 | 0.1112 | ✓ | 13.7 | 2541 | 178 |  |
| 19 | `DOC-383b9badb01a1a00` | email | 0.1010 | 0.0000 | ✓ | 13.8 | 4829 | 157 |  |
| 20 | `DOC-228e51bba45b5c7d` | email | 0.2693 | 0.0000 | ✓ | 13.8 | 2506 | 179 |  |
| 21 | `DOC-9ec94a2619e46dfb` | email | 0.4000 | 0.1112 | ✓ | 14.4 | 1742 | 167 |  |
| 22 | `DOC-8eed243667c985bd` | email | 0.7917 | 0.2222 | ✓ | 14.5 | 2149 | 195 |  |
| 23 | `DOC-91f5631a20c62dc5` | email | 0.6877 | 0.1176 | ✓ | 14.4 | 1922 | 197 |  |
| 24 | `DOC-a318b50872273528` | email | 0.0889 | 0.0000 | ✓ | 15.3 | 2028 | 187 |  |
| 25 | `DOC-c45ecc852b2cb0f4` | meeting_request | 0.5362 | 0.1176 | ✓ | 15.6 | 1823 | 190 |  |
| 26 | `DOC-38c54645bf0e601a` | email | 0.3140 | 0.0000 | ✓ | 15.8 | 2025 | 200 |  |
| 27 | `DOC-5adf644f3cb1d34e` | email | 0.0000 | 0.0000 | ✓ | 3.9 | 1668 | 84 |  |
| 28 | `DOC-21460a9f6d7e6348` | memo | 0.7255 | 0.2499 | ✓ | 8.0 | 1806 | 129 |  |
| 29 | `DOC-8754555168547e16` | email | 0.3458 | 0.0000 | ✓ | 16.4 | 2631 | 215 |  |
| 30 | `DOC-e624b1b9823e53f5` | memo | 0.4617 | 0.1112 | ✓ | 16.5 | 2386 | 266 |  |
| 31 | `DOC-2cde0c6d0c70b02b` | memo | 0.0909 | 0.0000 | ✓ | 16.5 | 2206 | 225 |  |
| 32 | `DOC-17ac4251c7d94cea` | email | 0.1111 | 0.0000 | ✓ | 4.0 | 1730 | 123 |  |
| 33 | `DOC-edd0a288e32f0d3b` | notice | 0.6667 | 0.2222 | ✓ | 9.3 | 1976 | 154 |  |
| 34 | `DOC-d3d85dc1b1514bec` | notice | 0.5384 | 0.1333 | ✓ | 9.4 | 1913 | 179 |  |
| 35 | `DOC-d6e2bbd8c5e394a4` | demand | 0.7857 | 0.2499 | ✓ | 6.8 | 1732 | 155 |  |
| 36 | `DOC-9b2bc061621a56be` | email | 0.3523 | 0.0000 | ✓ | 8.5 | 2043 | 146 |  |
| 37 | `DOC-2431095adda97989` | memo | 0.1752 | 0.0000 | ✓ | 17.8 | 2075 | 262 |  |
| 38 | `DOC-1dcf4dfd5ec6defb` | email | 0.2744 | 0.0000 | ✓ | 17.9 | 3002 | 266 |  |
| 39 | `DOC-c4074ed5b08f097e` | memo | 0.3827 | 0.1333 | ✓ | 5.9 | 1724 | 132 |  |
| 40 | `DOC-a6fff0ef0e406461` | email | 0.1346 | 0.0000 | ✓ | 6.7 | 1843 | 175 |  |
| 41 | `DOC-f6a9a00e53cc7973` | notice | 0.1333 | 0.0000 | ✓ | 9.3 | 6883 | 195 |  |
| 42 | `DOC-ff15276697cdfbb2` | demand | 0.1162 | 0.0000 | ✓ | 6.7 | 2322 | 191 |  |
| 43 | `DOC-c01ab1c1c673f355` | letter | 0.4743 | 0.1333 | ✓ | 6.1 | 1863 | 132 |  |
| 44 | `DOC-96438076efc6cc7b` | email | 0.3333 | 0.1176 | ✓ | 6.4 | 1778 | 159 |  |
| 45 | `DOC-595ab9fc19465909` | notice | 0.3333 | 0.1112 | ✓ | 8.1 | 1840 | 181 |  |
| 46 | `DOC-76375ebb4cd91de9` | letter | 0.1111 | 0.0000 | ✓ | 7.7 | 2516 | 193 |  |
| 47 | `DOC-9422c8775b387935` | press_release | 0.5235 | 0.1112 | ✓ | 7.1 | 2588 | 233 |  |
| 48 | `DOC-5b63f9fe205d564b` | email | 0.5303 | 0.1250 | ✓ | 6.5 | 1894 | 170 |  |
| 49 | `DOC-ee6bae4d269c1911` | memo | 0.3333 | 0.1112 | ✓ | 10.8 | 2830 | 269 |  |
| 50 | `DOC-f4b4c8c623ccb915` | press_release | 0.0800 | 0.0000 | ✓ | 21.1 | 4363 | 398 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s3-corr50-repeat.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s3-corr50-repeat
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s3-corr50-repeat.yaml` | run spec |
| `reports/serving/sand032-s3-corr50-repeat.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s3-corr50-repeat/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s3-corr50-repeat/` | offline Braintrust-shaped rows — disposed after this report is committed |
