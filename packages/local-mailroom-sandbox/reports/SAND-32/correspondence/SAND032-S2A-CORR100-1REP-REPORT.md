# Run report — `sand032-s2a-corr100-1rep`

SAND-032 Modal × vLLM specialist extract: **100 correspondence docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 8** on **1×L4** (MIN=MAX=1 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s2a-corr100-1rep` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1× L4 (single replica) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=16 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16], max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 1/1, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 100 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `046a2c9bfc4e` |
| git | `e9550a1 (dirty)` |
| spec_hash | `9882ad19dcf3eb1072e9c45a82f8f91b88007efbe82a2058aa5f6622dd9d5254` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **100 / 100** (errors 0) |
| **overall_extraction_score** | **0.2886** (sd 0.1975, min 0.0000, max 0.8095) |
| schema_valid_rate | 1.000 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 94.984 s |
| concurrency | 8 (8 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.192 s |
| latency p50 / p95 / max | 6.86 / 11.59 / 26.79 s |
| prompt / completion tokens | 226418 / 18564 |
| throughput | 2579.2 tok/s |
| GPU $ over busy wall (×1 L4 @ $0.8/h) | 0.021108 |
| **$ per doc (busy)** | **0.000211** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.6 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 1 of 1** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790546353.94`: requests Δ 100 (cumulative 120), measured TTFT mean 0.689 s (vLLM histogram, cumulative), prefix-cache hit 57.3%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 742.7 s over wall 95.0 s = **7.82×** effective parallelism at c8 (98% of the ideal 8×).
- **Tail:** slowest doc `DOC-caaba1c5a3f9a41e` (email) 26.8 s = 28% of wall — p95/p50 = 1.69×.
- **Prompt length vs latency:** Pearson r = 0.38 across 100 docs (not prefill-dominated).
- **Decode budget:** mean completion 186 tok/doc, mean prompt 2264 tok/doc.
- **Subclass spread:** best `meeting_request` 0.482 (n=2), worst `email` 0.252 (n=54).
- **Field-level extraction:** 56/100 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s2a-corr100-1rep-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s2a-corr100-1rep-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| email | 54 | 0.2523 |
| memo | 11 | 0.3185 |
| demand | 9 | 0.3284 |
| letter | 9 | 0.2776 |
| notice | 8 | 0.3958 |
| press_release | 7 | 0.3069 |
| meeting_request | 2 | 0.4824 |
| **total** | **100** | **0.2886** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-c2826f69ed293da4` | memo | 0.1053 | 0.0000 | ✓ | 6.3 | 1698 | 103 |  |
| 2 | `DOC-383b9badb01a1a00` | email | 0.1010 | 0.0000 | ✓ | 7.8 | 4829 | 159 |  |
| 3 | `DOC-2aea82e94dba6438` | email | 0.2045 | 0.0000 | ✓ | 8.0 | 1911 | 171 |  |
| 4 | `DOC-02dc4ab50ea271a4` | email | 0.0741 | 0.0000 | ✓ | 8.9 | 2038 | 186 |  |
| 5 | `DOC-a318b50872273528` | email | 0.0889 | 0.0000 | ✓ | 9.0 | 2028 | 187 |  |
| 6 | `DOC-fc6108235411ca8e` | demand | 0.4133 | 0.1112 | ✓ | 11.6 | 1934 | 224 |  |
| 7 | `DOC-32b1660fb702fd84` | memo | 0.1111 | 0.0000 | ✓ | 12.5 | 2158 | 238 |  |
| 8 | `DOC-f49b5cc25d9cb557` | letter | 0.2446 | 0.0000 | ✓ | 8.1 | 1996 | 162 |  |
| 9 | `DOC-0ab974301d63024f` | letter | 0.5000 | 0.1538 | ✓ | 7.5 | 1752 | 133 |  |
| 10 | `DOC-1d5664e2c826ad07` | email | 0.3889 | 0.1428 | ✓ | 6.5 | 1685 | 115 |  |
| 11 | `DOC-eaeffa14c92e7cd8` | press_release | 0.1276 | 0.0000 | ✓ | 8.2 | 2512 | 150 |  |
| 12 | `DOC-ab94c5d183e5f7ca` | notice | 0.0556 | 0.0000 | ✓ | 8.2 | 5639 | 146 |  |
| 13 | `DOC-f36a37e1a9c1351e` | press_release | 0.1667 | 0.0000 | ✓ | 4.2 | 1707 | 107 |  |
| 14 | `DOC-8754555168547e16` | email | 0.3458 | 0.0000 | ✓ | 8.3 | 2631 | 215 |  |
| 15 | `DOC-a763315b8f7cb96e` | email | 0.3667 | 0.1176 | ✓ | 7.4 | 2137 | 214 |  |
| 16 | `DOC-9be315cbfa0fbd19` | email | 0.1605 | 0.0000 | ✓ | 11.3 | 3834 | 292 |  |
| 17 | `DOC-e624b1b9823e53f5` | memo | 0.4617 | 0.1112 | ✓ | 10.5 | 2386 | 269 |  |
| 18 | `DOC-caaba1c5a3f9a41e` | email | 0.2800 | 0.0000 | ✓ | 26.8 | 3117 | 624 |  |
| 19 | `DOC-553256644e7b4547` | email | 0.0952 | 0.0000 | ✓ | 5.1 | 1773 | 123 |  |
| 20 | `DOC-38c54645bf0e601a` | email | 0.3140 | 0.0000 | ✓ | 7.2 | 2025 | 200 |  |
| 21 | `DOC-e72ff16f78525d0f` | email | 0.3140 | 0.0000 | ✓ | 9.2 | 2243 | 252 |  |
| 22 | `DOC-c45ecc852b2cb0f4` | meeting_request | 0.5362 | 0.1176 | ✓ | 5.9 | 1823 | 189 |  |
| 23 | `DOC-a7d76cec54e46f1f` | email | 0.1633 | 0.0000 | ✓ | 15.3 | 2833 | 450 |  |
| 24 | `DOC-8c312283e2533866` | press_release | 0.5000 | 0.1112 | ✓ | 15.0 | 2068 | 446 |  |
| 25 | `DOC-c71d3ca0b727a0d4` | email | 0.0833 | 0.0000 | ✓ | 4.4 | 1779 | 134 |  |
| 26 | `DOC-ba72bbffee783647` | email | 0.1852 | 0.0000 | ✓ | 6.5 | 1879 | 181 |  |
| 27 | `DOC-b5d016f4b2abaa39` | email | 0.1212 | 0.0000 | ✓ | 4.8 | 1703 | 132 |  |
| 28 | `DOC-9ec94a2619e46dfb` | email | 0.4000 | 0.1176 | ✓ | 6.1 | 1742 | 168 |  |
| 29 | `DOC-f4b4c8c623ccb915` | press_release | 0.0800 | 0.0000 | ✓ | 14.2 | 4363 | 396 |  |
| 30 | `DOC-44b1e5a60b363d3e` | letter | 0.0889 | 0.0000 | ✓ | 5.8 | 1996 | 152 |  |
| 31 | `DOC-228e51bba45b5c7d` | email | 0.1768 | 0.0000 | ✓ | 7.3 | 2506 | 185 |  |
| 32 | `DOC-cb4f8fb4ccb52f44` | email | 0.0833 | 0.0000 | ✓ | 5.5 | 1739 | 152 |  |
| 33 | `DOC-25958c023112a96e` | demand | 0.3333 | 0.1250 | ✓ | 6.8 | 1711 | 170 |  |
| 34 | `DOC-2431095adda97989` | memo | 0.5086 | 0.1112 | ✓ | 10.4 | 2075 | 257 |  |
| 35 | `DOC-314aa51db90c8c92` | memo | 0.4167 | 0.1112 | ✓ | 7.2 | 2541 | 178 |  |
| 36 | `DOC-1dcf4dfd5ec6defb` | email | 0.2744 | 0.0000 | ✓ | 11.0 | 3002 | 266 |  |
| 37 | `DOC-31c068618dba65f3` | letter | 0.3333 | 0.1428 | ✓ | 5.7 | 1813 | 112 |  |
| 38 | `DOC-b0055813bc08a29c` | meeting_request | 0.4286 | 0.1176 | ✓ | 7.4 | 2062 | 169 |  |
| 39 | `DOC-8eed243667c985bd` | email | 0.7917 | 0.2105 | ✓ | 6.6 | 2149 | 176 |  |
| 40 | `DOC-19d9fd70a08d306b` | notice | 0.3333 | 0.1112 | ✓ | 10.1 | 2439 | 255 |  |
| 41 | `DOC-bc3f4676ac0c2e16` | letter | 0.3333 | 0.1053 | ✓ | 8.6 | 3358 | 213 |  |
| 42 | `DOC-522399c5514f180a` | memo | 0.2879 | 0.0000 | ✓ | 7.3 | 2443 | 205 |  |
| 43 | `DOC-99c7dacadccd6e78` | press_release | 0.5088 | 0.1250 | ✓ | 5.1 | 1796 | 153 |  |
| 44 | `DOC-cfe8e8e7b9b3f38d` | email | 0.0303 | 0.0000 | ✓ | 8.0 | 2628 | 225 |  |
| 45 | `DOC-2bdbf0be591edea6` | memo | 0.0800 | 0.0000 | ✓ | 5.3 | 1729 | 150 |  |
| 46 | `DOC-556e41697352e63d` | demand | 0.0800 | 0.0000 | ✓ | 6.8 | 1876 | 195 |  |
| 47 | `DOC-4eb0e9385b81cc4b` | email | 0.0303 | 0.0000 | ✓ | 5.3 | 1784 | 141 |  |
| 48 | `DOC-c4debd478f2c06e0` | email | 0.2045 | 0.0000 | ✓ | 4.9 | 1936 | 139 |  |
| 49 | `DOC-9d0aa39a8ac68936` | email | 0.0833 | 0.0000 | ✓ | 3.7 | 1671 | 92 |  |
| 50 | `DOC-91f5631a20c62dc5` | email | 0.6877 | 0.1176 | ✓ | 7.3 | 1922 | 197 |  |
| 51 | `DOC-690cb07fef21747b` | email | 0.5088 | 0.1333 | ✓ | 6.0 | 1954 | 159 |  |
| 52 | `DOC-36b9a080db747f3d` | demand | 0.1468 | 0.0000 | ✓ | 5.6 | 2858 | 148 |  |
| 53 | `DOC-379b182c302a6821` | email | 0.3333 | 0.1333 | ✓ | 5.4 | 1747 | 144 |  |
| 54 | `DOC-20b4e31d9a4bf994` | email | 0.2359 | 0.0000 | ✓ | 4.4 | 1855 | 114 |  |
| 55 | `DOC-47647a5fdcd45666` | email | 0.3333 | 0.1250 | ✓ | 5.2 | 1916 | 136 |  |
| 56 | `DOC-d3e421962da61b35` | notice | 0.7917 | 0.2222 | ✓ | 6.9 | 2129 | 186 |  |
| 57 | `DOC-cc6e6dece6a787c2` | demand | 0.4802 | 0.1112 | ✓ | 6.6 | 1790 | 185 |  |
| 58 | `DOC-84a9981be2435b55` | email | 0.0833 | 0.0000 | ✓ | 4.8 | 1847 | 138 |  |
| 59 | `DOC-38265bcc6ecfecc3` | email | 0.0784 | 0.0000 | ✓ | 5.9 | 1729 | 172 |  |
| 60 | `DOC-4ab559dfb4d79b6d` | email | 0.6667 | 0.2667 | ✓ | 4.5 | 1757 | 138 |  |
| 61 | `DOC-cd6877aeb3f2f7e4` | email | 0.0556 | 0.0000 | ✓ | 6.2 | 2263 | 183 |  |
| 62 | `DOC-16dfd03aed14e557` | email | 0.0784 | 0.0000 | ✓ | 3.3 | 1674 | 107 |  |
| 63 | `DOC-d0c241ea24439be2` | email | 0.4689 | 0.1250 | ✓ | 4.9 | 1793 | 164 |  |
| 64 | `DOC-4321eefceb0f4289` | letter | 0.3333 | 0.1176 | ✓ | 6.5 | 1920 | 207 |  |
| 65 | `DOC-a8efd6e4c4d49aaf` | email | 0.5308 | 0.1112 | ✓ | 7.3 | 1940 | 180 |  |
| 66 | `DOC-21460a9f6d7e6348` | memo | 0.7255 | 0.2499 | ✓ | 5.9 | 1806 | 129 |  |
| 67 | `DOC-edd0a288e32f0d3b` | notice | 0.6667 | 0.2354 | ✓ | 6.7 | 1976 | 150 |  |
| 68 | `DOC-9d65887887fe53d2` | email | 0.3333 | 0.1176 | ✓ | 6.8 | 1812 | 157 |  |
| 69 | `DOC-2cde0c6d0c70b02b` | memo | 0.0909 | 0.0000 | ✓ | 9.9 | 2206 | 225 |  |
| 70 | `DOC-9b2bc061621a56be` | email | 0.3523 | 0.0000 | ✓ | 8.0 | 2043 | 139 |  |
| 71 | `DOC-d3d85dc1b1514bec` | notice | 0.4359 | 0.1112 | ✓ | 10.3 | 1913 | 223 |  |
| 72 | `DOC-f6a9a00e53cc7973` | notice | 0.1333 | 0.0000 | ✓ | 9.6 | 6883 | 175 |  |
| 73 | `DOC-9501118a02fe39b9` | email | 0.4002 | 0.1112 | ✓ | 7.9 | 1889 | 166 |  |
| 74 | `DOC-5a424efe5df6ba6f` | demand | 0.5414 | 0.1250 | ✓ | 7.6 | 4103 | 143 |  |
| 75 | `DOC-341d347babb3a19f` | email | 0.2213 | 0.0000 | ✓ | 8.3 | 1896 | 163 |  |
| 76 | `DOC-6f05af738f455d50` | email | 0.1204 | 0.0000 | ✓ | 6.4 | 2788 | 143 |  |
| 77 | `DOC-752a5e85c01ca6f0` | email | 0.3939 | 0.1053 | ✓ | 9.9 | 1866 | 202 |  |
| 78 | `DOC-6aa30fb5a4e67d76` | email | 0.2696 | 0.0000 | ✓ | 7.6 | 2681 | 188 |  |
| 79 | `DOC-8c7847bfbb91d578` | demand | 0.0351 | 0.0000 | ✓ | 6.2 | 2724 | 139 |  |
| 80 | `DOC-e25814bd08d418aa` | email | 0.1633 | 0.0000 | ✓ | 9.5 | 2022 | 227 |  |
| 81 | `DOC-d6e2bbd8c5e394a4` | demand | 0.8095 | 0.2499 | ✓ | 5.9 | 1732 | 154 |  |
| 82 | `DOC-595ab9fc19465909` | notice | 0.3333 | 0.1112 | ✓ | 6.2 | 1840 | 181 |  |
| 83 | `DOC-a6fff0ef0e406461` | email | 0.1346 | 0.0000 | ✓ | 6.2 | 1843 | 175 |  |
| 84 | `DOC-c00ffce3272be5fd` | email | 0.2981 | 0.0000 | ✓ | 7.8 | 2384 | 221 |  |
| 85 | `DOC-5adf644f3cb1d34e` | email | 0.0000 | 0.0000 | ✓ | 2.9 | 1668 | 84 |  |
| 86 | `DOC-ee6bae4d269c1911` | memo | 0.3333 | 0.1112 | ✓ | 10.6 | 2830 | 269 |  |
| 87 | `DOC-c4074ed5b08f097e` | memo | 0.3827 | 0.1333 | ✓ | 5.2 | 1724 | 132 |  |
| 88 | `DOC-76375ebb4cd91de9` | letter | 0.1111 | 0.0000 | ✓ | 7.4 | 2516 | 182 |  |
| 89 | `DOC-ff15276697cdfbb2` | demand | 0.1162 | 0.0000 | ✓ | 7.5 | 2322 | 193 |  |
| 90 | `DOC-8ce704cea54b1469` | press_release | 0.1754 | 0.0000 | ✓ | 8.1 | 2665 | 191 |  |
| 91 | `DOC-95a872ee4ff237d5` | email | 0.0784 | 0.0000 | ✓ | 6.7 | 2179 | 154 |  |
| 92 | `DOC-96438076efc6cc7b` | email | 0.3333 | 0.1250 | ✓ | 5.6 | 1778 | 154 |  |
| 93 | `DOC-c01ab1c1c673f355` | letter | 0.4743 | 0.1333 | ✓ | 4.7 | 1863 | 132 |  |
| 94 | `DOC-162babf552426b57` | letter | 0.0800 | 0.0000 | ✓ | 6.4 | 1813 | 178 |  |
| 95 | `DOC-f0e1241d461dd523` | notice | 0.4167 | 0.1112 | ✓ | 8.5 | 2058 | 213 |  |
| 96 | `DOC-9422c8775b387935` | press_release | 0.5901 | 0.1053 | ✓ | 8.6 | 2588 | 224 |  |
| 97 | `DOC-f7af031d61f7d7f5` | email | 0.0800 | 0.0000 | ✓ | 7.1 | 3967 | 221 |  |
| 98 | `DOC-17ac4251c7d94cea` | email | 0.1111 | 0.0000 | ✓ | 3.6 | 1730 | 123 |  |
| 99 | `DOC-1f3f868558fc4a6e` | email | 0.3333 | 0.1112 | ✓ | 3.9 | 1845 | 136 |  |
| 100 | `DOC-5b63f9fe205d564b` | email | 0.5800 | 0.1250 | ✓ | 4.5 | 1894 | 169 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s2a-corr100-1rep.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s2a-corr100-1rep
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s2a-corr100-1rep.yaml` | run spec |
| `reports/serving/sand032-s2a-corr100-1rep.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s2a-corr100-1rep/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s2a-corr100-1rep/` | offline Braintrust-shaped rows — disposed after this report is committed |
