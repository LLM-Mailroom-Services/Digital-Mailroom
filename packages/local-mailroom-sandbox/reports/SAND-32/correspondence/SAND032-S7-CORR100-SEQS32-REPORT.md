# Run report — `sand032-s7-corr100-seqs32`

SAND-032 Modal × vLLM specialist extract: **100 correspondence docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 64** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s7-corr100-seqs32` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=32 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16, 32], max_inputs=64 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 100 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `046a2c9bfc4e` |
| git | `b268ad4` |
| spec_hash | `d4c7647c373f6e7e23e7360369ed26c1acd000516cf20ba5960897dd8cb4dbe9` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **100 / 100** (errors 0) |
| **overall_extraction_score** | **0.2867** (sd 0.1946, min 0.0000, max 0.8095) |
| schema_valid_rate | 0.990 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 149.355 s |
| concurrency | 64 (32 per replica) |
| cold boot — deploy→engine ready (driver stamps) | 221.8 s |
| preflight probe (engine answering) | 218.755 s |
| latency p50 / p95 / max | 31.25 / 51.50 / 149.14 s |
| prompt / completion tokens | 226418 / 18630 |
| throughput | 1640.7 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 0.066380 |
| **$ per doc (busy)** | **0.000664** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.6 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 2 of 2** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790582397.24`: requests Δ 3 (cumulative 3), measured TTFT mean 1.808 s (vLLM histogram, cumulative), prefix-cache hit 27.0%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.
- replica `1790582397.97`: requests Δ 97 (cumulative 97), measured TTFT mean 16.175 s (vLLM histogram, cumulative), prefix-cache hit 50.8%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 3285.2 s over wall 149.4 s = **22.00×** effective parallelism at c64 (34% of the ideal 64×).
- **Tail:** slowest doc `DOC-a7d76cec54e46f1f` (email) 149.1 s = 100% of wall — p95/p50 = 1.65×.
- **Prompt length vs latency:** Pearson r = 0.20 across 100 docs (not prefill-dominated).
- **Decode budget:** mean completion 186 tok/doc, mean prompt 2264 tok/doc.
- **Subclass spread:** best `meeting_request` 0.482 (n=2), worst `email` 0.258 (n=54).
- **Field-level extraction:** 57/100 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.
- **Boot:** deploy→engine-ready 222 s (driver stamps); preflight probe measured 218.8 s once the engine answered.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s7-corr100-seqs32-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s7-corr100-seqs32-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| email | 54 | 0.2579 |
| memo | 11 | 0.2936 |
| letter | 9 | 0.2776 |
| demand | 9 | 0.3153 |
| notice | 8 | 0.3958 |
| press_release | 7 | 0.2933 |
| meeting_request | 2 | 0.4824 |
| **total** | **100** | **0.2867** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-16dfd03aed14e557` | email | 0.0000 | 0.0000 | ✓ | 13.6 | 1674 | 76 |  |
| 2 | `DOC-9d0aa39a8ac68936` | email | 0.0833 | 0.0000 | ✓ | 15.2 | 1671 | 92 |  |
| 3 | `DOC-20b4e31d9a4bf994` | email | 0.2359 | 0.0000 | ✓ | 16.0 | 1855 | 114 |  |
| 4 | `DOC-31c068618dba65f3` | letter | 0.3333 | 0.1333 | ✓ | 16.3 | 1813 | 116 |  |
| 5 | `DOC-c71d3ca0b727a0d4` | email | 0.0833 | 0.0000 | ✓ | 17.3 | 1779 | 134 |  |
| 6 | `DOC-84a9981be2435b55` | email | 0.0833 | 0.0000 | ✓ | 17.3 | 1847 | 127 |  |
| 7 | `DOC-38265bcc6ecfecc3` | email | 0.0784 | 0.0000 | ✓ | 17.9 | 1729 | 144 |  |
| 8 | `DOC-47647a5fdcd45666` | email | 0.3333 | 0.1250 | ✓ | 17.9 | 1916 | 136 |  |
| 9 | `DOC-553256644e7b4547` | email | 0.0952 | 0.0000 | ✓ | 18.5 | 1773 | 141 |  |
| 10 | `DOC-4eb0e9385b81cc4b` | email | 0.0303 | 0.0000 | ✓ | 18.6 | 1784 | 138 |  |
| 11 | `DOC-0ab974301d63024f` | letter | 0.5000 | 0.1428 | ✓ | 19.4 | 1752 | 143 |  |
| 12 | `DOC-44b1e5a60b363d3e` | letter | 0.0889 | 0.0000 | ✓ | 20.6 | 1996 | 152 |  |
| 13 | `DOC-99c7dacadccd6e78` | press_release | 0.5088 | 0.1250 | ✓ | 20.8 | 1796 | 153 |  |
| 14 | `DOC-f49b5cc25d9cb557` | letter | 0.2446 | 0.0000 | ✓ | 21.6 | 1996 | 160 |  |
| 15 | `DOC-eaeffa14c92e7cd8` | press_release | 0.1276 | 0.0000 | ✓ | 21.7 | 2512 | 155 |  |
| 16 | `DOC-d0c241ea24439be2` | email | 0.4689 | 0.1176 | ✓ | 22.1 | 1793 | 160 |  |
| 17 | `DOC-2aea82e94dba6438` | email | 0.2045 | 0.0000 | ✓ | 23.8 | 1911 | 170 |  |
| 18 | `DOC-314aa51db90c8c92` | memo | 0.4167 | 0.1112 | ✓ | 24.4 | 2541 | 178 |  |
| 19 | `DOC-c45ecc852b2cb0f4` | meeting_request | 0.5362 | 0.1176 | ✓ | 25.2 | 1823 | 196 |  |
| 20 | `DOC-8eed243667c985bd` | email | 0.7917 | 0.2105 | ✓ | 25.6 | 2149 | 198 |  |
| 21 | `DOC-cc6e6dece6a787c2` | demand | 0.4802 | 0.1112 | ✓ | 25.6 | 1790 | 201 |  |
| 22 | `DOC-4321eefceb0f4289` | letter | 0.3333 | 0.1176 | ✓ | 26.3 | 1920 | 207 |  |
| 23 | `DOC-556e41697352e63d` | demand | 0.0800 | 0.0000 | ✓ | 26.7 | 1876 | 199 |  |
| 24 | `DOC-522399c5514f180a` | memo | 0.2879 | 0.0000 | ✓ | 26.7 | 2443 | 207 |  |
| 25 | `DOC-b0055813bc08a29c` | meeting_request | 0.4286 | 0.1176 | ✓ | 26.7 | 2062 | 199 |  |
| 26 | `DOC-a763315b8f7cb96e` | email | 0.3667 | 0.1176 | ✓ | 28.9 | 2137 | 214 |  |
| 27 | `DOC-f36a37e1a9c1351e` | press_release | 0.1667 | 0.0000 | ✓ | 29.2 | 1707 | 109 |  |
| 28 | `DOC-1d5664e2c826ad07` | email | 0.3889 | 0.1428 | ✓ | 29.6 | 1685 | 115 |  |
| 29 | `DOC-32b1660fb702fd84` | memo | 0.1111 | 0.0000 | ✓ | 29.9 | 2158 | 231 |  |
| 30 | `DOC-c2826f69ed293da4` | memo | 0.1053 | 0.0000 | ✓ | 30.7 | 1698 | 111 |  |
| 31 | `DOC-228e51bba45b5c7d` | email | 0.2693 | 0.0000 | ✓ | 31.3 | 2506 | 178 |  |
| 32 | `DOC-19d9fd70a08d306b` | notice | 0.3333 | 0.1112 | ✓ | 31.9 | 2439 | 255 |  |
| 33 | `DOC-e72ff16f78525d0f` | email | 0.3140 | 0.0000 | ✓ | 32.8 | 2243 | 280 |  |
| 34 | `DOC-c4debd478f2c06e0` | email | 0.2045 | 0.0000 | ✓ | 33.2 | 1936 | 136 |  |
| 35 | `DOC-ab94c5d183e5f7ca` | notice | 0.0556 | 0.0000 | ✓ | 34.3 | 5639 | 142 |  |
| 36 | `DOC-bc3f4676ac0c2e16` | letter | 0.3333 | 0.1053 | ✓ | 34.6 | 3358 | 206 |  |
| 37 | `DOC-36b9a080db747f3d` | demand | 0.1468 | 0.0000 | ✓ | 35.2 | 2858 | 152 |  |
| 38 | `DOC-383b9badb01a1a00` | email | 0.1010 | 0.0000 | ✓ | 35.8 | 4829 | 157 |  |
| 39 | `DOC-4ab559dfb4d79b6d` | email | 0.6667 | 0.2667 | ✓ | 36.0 | 1757 | 138 |  |
| 40 | `DOC-cb4f8fb4ccb52f44` | email | 0.0833 | 0.0000 | ✓ | 36.0 | 1739 | 152 |  |
| 41 | `DOC-a318b50872273528` | email | 0.1167 | 0.0000 | ✓ | 36.2 | 2028 | 179 |  |
| 42 | `DOC-17ac4251c7d94cea` | email | 0.1111 | 0.0000 | ✓ | 5.3 | 1730 | 134 |  |
| 43 | `DOC-d3e421962da61b35` | notice | 0.7917 | 0.2222 | ✓ | 39.6 | 2129 | 181 |  |
| 44 | `DOC-379b182c302a6821` | email | 0.3333 | 0.1250 | ✓ | 39.6 | 1747 | 128 |  |
| 45 | `DOC-cd6877aeb3f2f7e4` | email | 0.0556 | 0.0000 | ✓ | 39.6 | 2263 | 183 |  |
| 46 | `DOC-f7af031d61f7d7f5` | email | 0.0800 | 0.0000 | ✓ | 7.1 | 3967 | 152 |  |
| 47 | `DOC-38c54645bf0e601a` | email | 0.3140 | 0.0000 | ✓ | 41.0 | 2025 | 198 |  |
| 48 | `DOC-91f5631a20c62dc5` | email | 0.6877 | 0.1176 | ✓ | 41.3 | 1922 | 214 |  |
| 49 | `DOC-fc6108235411ca8e` | demand | 0.3939 | 0.1112 | ✓ | 42.0 | 1934 | 191 |  |
| 50 | `DOC-690cb07fef21747b` | email | 0.5088 | 0.1333 | ✓ | 41.9 | 1954 | 148 |  |
| 51 | `DOC-b5d016f4b2abaa39` | email | 0.1212 | 0.0000 | ✓ | 43.2 | 1703 | 133 |  |
| 52 | `DOC-9ec94a2619e46dfb` | email | 0.4000 | 0.1176 | ✓ | 43.7 | 1742 | 168 |  |
| 53 | `DOC-2bdbf0be591edea6` | memo | 0.0800 | 0.0000 | ✓ | 44.2 | 1729 | 150 |  |
| 54 | `DOC-02dc4ab50ea271a4` | email | 0.4074 | 0.1176 | ✓ | 44.9 | 2038 | 184 |  |
| 55 | `DOC-f4b4c8c623ccb915` | press_release | 0.0800 | 0.0000 | ✓ | 45.2 | 4363 | 391 |  |
| 56 | `DOC-25958c023112a96e` | demand | 0.3333 | 0.1250 | ✓ | 46.1 | 1711 | 169 |  |
| 57 | `DOC-ba72bbffee783647` | email | 0.2722 | 0.0000 | ✓ | 46.7 | 1879 | 178 |  |
| 58 | `DOC-8754555168547e16` | email | 0.3458 | 0.0000 | ✓ | 47.4 | 2631 | 214 |  |
| 59 | `DOC-2431095adda97989` | memo | 0.1752 | 0.0000 | ✓ | 47.5 | 2075 | 270 |  |
| 60 | `DOC-a8efd6e4c4d49aaf` | email | 0.2451 | 0.0000 | ✓ | 35.8 | 1940 | 187 |  |
| 61 | `DOC-8c312283e2533866` | press_release | 0.5000 | 0.1112 | ✓ | 49.5 | 2068 | 446 |  |
| 62 | `DOC-edd0a288e32f0d3b` | notice | 0.6667 | 0.2222 | ✓ | 32.8 | 1976 | 152 |  |
| 63 | `DOC-9b2bc061621a56be` | email | 0.3523 | 0.0000 | ✓ | 32.8 | 2043 | 139 |  |
| 64 | `DOC-21460a9f6d7e6348` | memo | 0.7843 | 0.2354 | ✗ | 33.8 | 1806 | 150 |  |
| 65 | `DOC-1dcf4dfd5ec6defb` | email | 0.2744 | 0.0000 | ✓ | 51.5 | 3002 | 259 |  |
| 66 | `DOC-9d65887887fe53d2` | email | 0.3333 | 0.1176 | ✓ | 35.6 | 1812 | 176 |  |
| 67 | `DOC-9be315cbfa0fbd19` | email | 0.1605 | 0.0000 | ✓ | 52.8 | 3834 | 277 |  |
| 68 | `DOC-cfe8e8e7b9b3f38d` | email | 0.0303 | 0.0000 | ✓ | 52.8 | 2628 | 238 |  |
| 69 | `DOC-8c7847bfbb91d578` | demand | 0.0351 | 0.0000 | ✓ | 30.9 | 2724 | 134 |  |
| 70 | `DOC-9501118a02fe39b9` | email | 0.4178 | 0.1112 | ✓ | 34.5 | 1889 | 165 |  |
| 71 | `DOC-f6a9a00e53cc7973` | notice | 0.1333 | 0.0000 | ✓ | 35.5 | 6883 | 174 |  |
| 72 | `DOC-5adf644f3cb1d34e` | email | 0.0000 | 0.0000 | ✓ | 26.7 | 1668 | 84 |  |
| 73 | `DOC-2cde0c6d0c70b02b` | memo | 0.0909 | 0.0000 | ✓ | 38.3 | 2206 | 225 |  |
| 74 | `DOC-d3d85dc1b1514bec` | notice | 0.4359 | 0.1112 | ✓ | 37.6 | 1913 | 224 |  |
| 75 | `DOC-341d347babb3a19f` | email | 0.2213 | 0.0000 | ✓ | 33.2 | 1896 | 170 |  |
| 76 | `DOC-6f05af738f455d50` | email | 0.1437 | 0.0000 | ✓ | 33.1 | 2788 | 172 |  |
| 77 | `DOC-e624b1b9823e53f5` | memo | 0.4617 | 0.1112 | ✓ | 54.3 | 2386 | 265 |  |
| 78 | `DOC-d6e2bbd8c5e394a4` | demand | 0.8095 | 0.2222 | ✓ | 30.0 | 1732 | 164 |  |
| 79 | `DOC-5a424efe5df6ba6f` | demand | 0.4428 | 0.1250 | ✓ | 36.0 | 4103 | 206 |  |
| 80 | `DOC-c4074ed5b08f097e` | memo | 0.3827 | 0.1333 | ✓ | 28.1 | 1724 | 133 |  |
| 81 | `DOC-752a5e85c01ca6f0` | email | 0.3939 | 0.1053 | ✓ | 35.6 | 1866 | 200 |  |
| 82 | `DOC-6aa30fb5a4e67d76` | email | 0.2696 | 0.0000 | ✓ | 33.3 | 2681 | 188 |  |
| 83 | `DOC-595ab9fc19465909` | notice | 0.3333 | 0.1112 | ✓ | 29.8 | 1840 | 181 |  |
| 84 | `DOC-a6fff0ef0e406461` | email | 0.1346 | 0.0000 | ✓ | 29.9 | 1843 | 174 |  |
| 85 | `DOC-76375ebb4cd91de9` | letter | 0.1111 | 0.0000 | ✓ | 30.0 | 2516 | 200 |  |
| 86 | `DOC-c00ffce3272be5fd` | email | 0.2981 | 0.0000 | ✓ | 31.2 | 2384 | 220 |  |
| 87 | `DOC-ff15276697cdfbb2` | demand | 0.1162 | 0.0000 | ✓ | 29.8 | 2322 | 191 |  |
| 88 | `DOC-e25814bd08d418aa` | email | 0.2467 | 0.0000 | ✓ | 35.2 | 2022 | 247 |  |
| 89 | `DOC-1f3f868558fc4a6e` | email | 0.3810 | 0.1538 | ✓ | 23.4 | 1845 | 122 |  |
| 90 | `DOC-c01ab1c1c673f355` | letter | 0.4743 | 0.1333 | ✓ | 24.8 | 1863 | 132 |  |
| 91 | `DOC-95a872ee4ff237d5` | email | 0.0784 | 0.0000 | ✓ | 27.4 | 2179 | 154 |  |
| 92 | `DOC-8ce704cea54b1469` | press_release | 0.0800 | 0.0000 | ✓ | 28.1 | 2665 | 191 |  |
| 93 | `DOC-ee6bae4d269c1911` | memo | 0.3333 | 0.1112 | ✓ | 33.6 | 2830 | 268 |  |
| 94 | `DOC-96438076efc6cc7b` | email | 0.3333 | 0.1053 | ✓ | 26.8 | 1778 | 167 |  |
| 95 | `DOC-caaba1c5a3f9a41e` | email | 0.2800 | 0.0000 | ✓ | 57.5 | 3117 | 622 |  |
| 96 | `DOC-162babf552426b57` | letter | 0.0800 | 0.0000 | ✓ | 26.4 | 1813 | 177 |  |
| 97 | `DOC-5b63f9fe205d564b` | email | 0.5303 | 0.1250 | ✓ | 23.1 | 1894 | 154 |  |
| 98 | `DOC-f0e1241d461dd523` | notice | 0.4167 | 0.1053 | ✓ | 28.6 | 2058 | 194 |  |
| 99 | `DOC-9422c8775b387935` | press_release | 0.5901 | 0.1176 | ✓ | 28.6 | 2588 | 213 |  |
| 100 | `DOC-a7d76cec54e46f1f` | email | 0.1633 | 0.0000 | ✓ | 149.1 | 2833 | 458 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s7-corr100-seqs32.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s7-corr100-seqs32
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s7-corr100-seqs32.yaml` | run spec |
| `reports/serving/sand032-s7-corr100-seqs32.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s7-corr100-seqs32/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s7-corr100-seqs32/` | offline Braintrust-shaped rows — disposed after this report is committed |
