# Run report — `sand032-s9-corr100-bal`

SAND-032 Modal × vLLM specialist extract: **100 correspondence docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 64** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s9-corr100-bal` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=32 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16, 32], max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 100 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `046a2c9bfc4e` |
| git | `37e5f98 (dirty)` |
| spec_hash | `711094888e32fe1f897745120beaed2d291b340b7b9d6ea566d4088a43e99f76` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **100 / 100** (errors 0) |
| **overall_extraction_score** | **0.2872** (sd 0.1955, min 0.0000, max 0.8095) |
| schema_valid_rate | 0.990 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 38.972 s |
| concurrency | 64 (32 per replica) |
| cold boot — deploy→engine ready (driver stamps) | 181.3 s |
| preflight probe (engine answering) | 178.543 s |
| latency p50 / p95 / max | 21.19 / 30.35 / 38.90 s |
| prompt / completion tokens | 226418 / 18414 |
| throughput | 6282.2 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 0.017321 |
| **$ per doc (busy)** | **0.000173** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.6 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 2 of 2** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790582921.77`: requests Δ 51 (cumulative 51), measured TTFT mean 5.508 s (vLLM histogram, cumulative), prefix-cache hit 49.2%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.
- replica `1790582929.28`: requests Δ 49 (cumulative 49), measured TTFT mean 5.460 s (vLLM histogram, cumulative), prefix-cache hit 50.5%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 1971.4 s over wall 39.0 s = **50.59×** effective parallelism at c64 (79% of the ideal 64×).
- **Tail:** slowest doc `DOC-caaba1c5a3f9a41e` (email) 38.9 s = 100% of wall — p95/p50 = 1.43×.
- **Prompt length vs latency:** Pearson r = 0.10 across 100 docs (not prefill-dominated).
- **Decode budget:** mean completion 184 tok/doc, mean prompt 2264 tok/doc.
- **Subclass spread:** best `meeting_request` 0.482 (n=2), worst `email` 0.252 (n=54).
- **Field-level extraction:** 57/100 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.
- **Boot:** deploy→engine-ready 181 s (driver stamps); preflight probe measured 178.5 s once the engine answered.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s9-corr100-bal-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s9-corr100-bal-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| email | 54 | 0.2523 |
| memo | 11 | 0.2900 |
| letter | 9 | 0.2776 |
| demand | 9 | 0.3633 |
| notice | 8 | 0.3958 |
| press_release | 7 | 0.2870 |
| meeting_request | 2 | 0.4824 |
| **total** | **100** | **0.2872** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-9d0aa39a8ac68936` | email | 0.0833 | 0.0000 | ✓ | 17.0 | 1671 | 92 |  |
| 2 | `DOC-f36a37e1a9c1351e` | press_release | 0.1667 | 0.0000 | ✓ | 17.4 | 1707 | 106 |  |
| 3 | `DOC-c2826f69ed293da4` | memo | 0.1053 | 0.0000 | ✓ | 17.6 | 1698 | 106 |  |
| 4 | `DOC-16dfd03aed14e557` | email | 0.0784 | 0.0000 | ✓ | 17.7 | 1674 | 107 |  |
| 5 | `DOC-20b4e31d9a4bf994` | email | 0.2359 | 0.0000 | ✓ | 18.1 | 1855 | 114 |  |
| 6 | `DOC-84a9981be2435b55` | email | 0.0833 | 0.0000 | ✓ | 18.2 | 1847 | 127 |  |
| 7 | `DOC-1d5664e2c826ad07` | email | 0.3889 | 0.1428 | ✓ | 18.5 | 1685 | 115 |  |
| 8 | `DOC-31c068618dba65f3` | letter | 0.3333 | 0.1428 | ✓ | 18.7 | 1813 | 113 |  |
| 9 | `DOC-379b182c302a6821` | email | 0.3333 | 0.1250 | ✓ | 19.4 | 1747 | 127 |  |
| 10 | `DOC-4eb0e9385b81cc4b` | email | 0.0303 | 0.0000 | ✓ | 19.8 | 1784 | 141 |  |
| 11 | `DOC-b5d016f4b2abaa39` | email | 0.1212 | 0.0000 | ✓ | 19.9 | 1703 | 137 |  |
| 12 | `DOC-0ab974301d63024f` | letter | 0.5000 | 0.1428 | ✓ | 20.4 | 1752 | 143 |  |
| 13 | `DOC-553256644e7b4547` | email | 0.0952 | 0.0000 | ✓ | 20.4 | 1773 | 140 |  |
| 14 | `DOC-c4debd478f2c06e0` | email | 0.2045 | 0.0000 | ✓ | 21.2 | 1936 | 134 |  |
| 15 | `DOC-c71d3ca0b727a0d4` | email | 0.0833 | 0.0000 | ✓ | 21.2 | 1779 | 134 |  |
| 16 | `DOC-38265bcc6ecfecc3` | email | 0.1340 | 0.0000 | ✓ | 21.4 | 1729 | 137 |  |
| 17 | `DOC-47647a5fdcd45666` | email | 0.3333 | 0.1250 | ✓ | 21.5 | 1916 | 136 |  |
| 18 | `DOC-4ab559dfb4d79b6d` | email | 0.3333 | 0.1428 | ✓ | 21.5 | 1757 | 136 |  |
| 19 | `DOC-ab94c5d183e5f7ca` | notice | 0.0556 | 0.0000 | ✓ | 21.8 | 5639 | 147 |  |
| 20 | `DOC-2bdbf0be591edea6` | memo | 0.0800 | 0.0000 | ✓ | 22.0 | 1729 | 150 |  |
| 21 | `DOC-99c7dacadccd6e78` | press_release | 0.5088 | 0.1250 | ✓ | 22.1 | 1796 | 154 |  |
| 22 | `DOC-f49b5cc25d9cb557` | letter | 0.2446 | 0.0000 | ✓ | 22.5 | 1996 | 162 |  |
| 23 | `DOC-383b9badb01a1a00` | email | 0.1010 | 0.0000 | ✓ | 22.6 | 4829 | 159 |  |
| 24 | `DOC-690cb07fef21747b` | email | 0.5088 | 0.1333 | ✓ | 22.7 | 1954 | 148 |  |
| 25 | `DOC-eaeffa14c92e7cd8` | press_release | 0.1276 | 0.0000 | ✓ | 23.1 | 2512 | 159 |  |
| 26 | `DOC-36b9a080db747f3d` | demand | 0.1468 | 0.0000 | ✓ | 22.9 | 2858 | 163 |  |
| 27 | `DOC-d0c241ea24439be2` | email | 0.4689 | 0.1176 | ✓ | 22.9 | 1793 | 162 |  |
| 28 | `DOC-cb4f8fb4ccb52f44` | email | 0.0833 | 0.0000 | ✓ | 24.3 | 1739 | 154 |  |
| 29 | `DOC-44b1e5a60b363d3e` | letter | 0.0889 | 0.0000 | ✓ | 24.8 | 1996 | 151 |  |
| 30 | `DOC-25958c023112a96e` | demand | 0.6667 | 0.2105 | ✓ | 24.8 | 1711 | 180 |  |
| 31 | `DOC-2aea82e94dba6438` | email | 0.2045 | 0.0000 | ✓ | 25.0 | 1911 | 172 |  |
| 32 | `DOC-cd6877aeb3f2f7e4` | email | 0.0556 | 0.0000 | ✓ | 25.0 | 2263 | 183 |  |
| 33 | `DOC-38c54645bf0e601a` | email | 0.3140 | 0.0000 | ✓ | 25.5 | 2025 | 197 |  |
| 34 | `DOC-fc6108235411ca8e` | demand | 0.3939 | 0.1112 | ✓ | 25.7 | 1934 | 191 |  |
| 35 | `DOC-9ec94a2619e46dfb` | email | 0.4000 | 0.1176 | ✓ | 25.8 | 1742 | 168 |  |
| 36 | `DOC-c45ecc852b2cb0f4` | meeting_request | 0.5362 | 0.1176 | ✓ | 25.8 | 1823 | 190 |  |
| 37 | `DOC-b0055813bc08a29c` | meeting_request | 0.4286 | 0.1176 | ✓ | 25.9 | 2062 | 169 |  |
| 38 | `DOC-a318b50872273528` | email | 0.1167 | 0.0000 | ✓ | 26.1 | 2028 | 178 |  |
| 39 | `DOC-02dc4ab50ea271a4` | email | 0.0741 | 0.0000 | ✓ | 26.3 | 2038 | 186 |  |
| 40 | `DOC-ba72bbffee783647` | email | 0.2722 | 0.0000 | ✓ | 26.3 | 1879 | 188 |  |
| 41 | `DOC-d3e421962da61b35` | notice | 0.7917 | 0.2222 | ✓ | 26.8 | 2129 | 181 |  |
| 42 | `DOC-228e51bba45b5c7d` | email | 0.2693 | 0.0000 | ✓ | 26.8 | 2506 | 178 |  |
| 43 | `DOC-cc6e6dece6a787c2` | demand | 0.4802 | 0.1112 | ✓ | 26.9 | 1790 | 186 |  |
| 44 | `DOC-91f5631a20c62dc5` | email | 0.6877 | 0.1176 | ✓ | 27.0 | 1922 | 194 |  |
| 45 | `DOC-556e41697352e63d` | demand | 0.0800 | 0.0000 | ✓ | 27.3 | 1876 | 203 |  |
| 46 | `DOC-4321eefceb0f4289` | letter | 0.3333 | 0.1176 | ✓ | 27.2 | 1920 | 205 |  |
| 47 | `DOC-bc3f4676ac0c2e16` | letter | 0.3333 | 0.1053 | ✓ | 27.7 | 3358 | 213 |  |
| 48 | `DOC-8754555168547e16` | email | 0.3458 | 0.0000 | ✓ | 28.0 | 2631 | 214 |  |
| 49 | `DOC-8eed243667c985bd` | email | 0.7917 | 0.2105 | ✓ | 27.9 | 2149 | 195 |  |
| 50 | `DOC-522399c5514f180a` | memo | 0.2879 | 0.0000 | ✓ | 28.1 | 2443 | 205 |  |
| 51 | `DOC-a763315b8f7cb96e` | email | 0.3667 | 0.1176 | ✓ | 28.2 | 2137 | 214 |  |
| 52 | `DOC-cfe8e8e7b9b3f38d` | email | 0.0303 | 0.0000 | ✓ | 28.5 | 2628 | 214 |  |
| 53 | `DOC-e72ff16f78525d0f` | email | 0.3140 | 0.0000 | ✓ | 28.9 | 2243 | 252 |  |
| 54 | `DOC-32b1660fb702fd84` | memo | 0.1111 | 0.0000 | ✓ | 29.5 | 2158 | 239 |  |
| 55 | `DOC-21460a9f6d7e6348` | memo | 0.7255 | 0.2354 | ✗ | 11.1 | 1806 | 129 |  |
| 56 | `DOC-314aa51db90c8c92` | memo | 0.4167 | 0.1112 | ✓ | 29.8 | 2541 | 178 |  |
| 57 | `DOC-5adf644f3cb1d34e` | email | 0.0000 | 0.0000 | ✓ | 7.0 | 1668 | 84 |  |
| 58 | `DOC-edd0a288e32f0d3b` | notice | 0.6667 | 0.2222 | ✓ | 12.0 | 1976 | 152 |  |
| 59 | `DOC-19d9fd70a08d306b` | notice | 0.3333 | 0.1112 | ✓ | 30.2 | 2439 | 254 |  |
| 60 | `DOC-9d65887887fe53d2` | email | 0.3333 | 0.1176 | ✓ | 12.5 | 1812 | 157 |  |
| 61 | `DOC-e624b1b9823e53f5` | memo | 0.4813 | 0.1112 | ✓ | 30.4 | 2386 | 270 |  |
| 62 | `DOC-2431095adda97989` | memo | 0.1752 | 0.0000 | ✓ | 30.3 | 2075 | 257 |  |
| 63 | `DOC-1dcf4dfd5ec6defb` | email | 0.2744 | 0.0000 | ✓ | 30.3 | 3002 | 266 |  |
| 64 | `DOC-c4074ed5b08f097e` | memo | 0.3827 | 0.1333 | ✓ | 7.6 | 1724 | 133 |  |
| 65 | `DOC-9b2bc061621a56be` | email | 0.3523 | 0.0000 | ✓ | 12.2 | 2043 | 137 |  |
| 66 | `DOC-8c7847bfbb91d578` | demand | 0.0351 | 0.0000 | ✓ | 9.2 | 2724 | 144 |  |
| 67 | `DOC-9be315cbfa0fbd19` | email | 0.1605 | 0.0000 | ✓ | 31.2 | 3834 | 285 |  |
| 68 | `DOC-f6a9a00e53cc7973` | notice | 0.1333 | 0.0000 | ✓ | 12.3 | 6883 | 175 |  |
| 69 | `DOC-6f05af738f455d50` | email | 0.1437 | 0.0000 | ✓ | 10.7 | 2788 | 133 |  |
| 70 | `DOC-d6e2bbd8c5e394a4` | demand | 0.8095 | 0.2222 | ✓ | 9.5 | 1732 | 156 |  |
| 71 | `DOC-96438076efc6cc7b` | email | 0.3333 | 0.1250 | ✓ | 6.3 | 1778 | 147 |  |
| 72 | `DOC-a8efd6e4c4d49aaf` | email | 0.5308 | 0.1112 | ✓ | 14.2 | 1940 | 180 |  |
| 73 | `DOC-95a872ee4ff237d5` | email | 0.0784 | 0.0000 | ✓ | 6.9 | 2179 | 154 |  |
| 74 | `DOC-5a424efe5df6ba6f` | demand | 0.5414 | 0.1250 | ✓ | 11.5 | 4103 | 142 |  |
| 75 | `DOC-a6fff0ef0e406461` | email | 0.1346 | 0.0000 | ✓ | 9.5 | 1843 | 175 |  |
| 76 | `DOC-6aa30fb5a4e67d76` | email | 0.2696 | 0.0000 | ✓ | 10.5 | 2681 | 184 |  |
| 77 | `DOC-595ab9fc19465909` | notice | 0.3333 | 0.1112 | ✓ | 9.7 | 1840 | 181 |  |
| 78 | `DOC-9501118a02fe39b9` | email | 0.4002 | 0.1112 | ✓ | 12.4 | 1889 | 166 |  |
| 79 | `DOC-c00ffce3272be5fd` | email | 0.2981 | 0.0000 | ✓ | 10.5 | 2384 | 198 |  |
| 80 | `DOC-341d347babb3a19f` | email | 0.2213 | 0.0000 | ✓ | 12.0 | 1896 | 171 |  |
| 81 | `DOC-5b63f9fe205d564b` | email | 0.5800 | 0.1250 | ✓ | 6.5 | 1894 | 169 |  |
| 82 | `DOC-1f3f868558fc4a6e` | email | 0.3810 | 0.1333 | ✓ | 6.9 | 1845 | 129 |  |
| 83 | `DOC-c01ab1c1c673f355` | letter | 0.4743 | 0.1333 | ✓ | 7.4 | 1863 | 132 |  |
| 84 | `DOC-2cde0c6d0c70b02b` | memo | 0.0909 | 0.0000 | ✓ | 15.3 | 2206 | 225 |  |
| 85 | `DOC-d3d85dc1b1514bec` | notice | 0.4359 | 0.1112 | ✓ | 15.3 | 1913 | 223 |  |
| 86 | `DOC-17ac4251c7d94cea` | email | 0.1111 | 0.0000 | ✓ | 7.1 | 1730 | 141 |  |
| 87 | `DOC-e25814bd08d418aa` | email | 0.1633 | 0.0000 | ✓ | 11.8 | 2022 | 231 |  |
| 88 | `DOC-752a5e85c01ca6f0` | email | 0.3939 | 0.1053 | ✓ | 13.3 | 1866 | 202 |  |
| 89 | `DOC-f7af031d61f7d7f5` | email | 0.0800 | 0.0000 | ✓ | 7.8 | 3967 | 155 |  |
| 90 | `DOC-ff15276697cdfbb2` | demand | 0.1162 | 0.0000 | ✓ | 11.1 | 2322 | 192 |  |
| 91 | `DOC-8ce704cea54b1469` | press_release | 0.0800 | 0.0000 | ✓ | 10.6 | 2665 | 190 |  |
| 92 | `DOC-76375ebb4cd91de9` | letter | 0.1111 | 0.0000 | ✓ | 11.2 | 2516 | 198 |  |
| 93 | `DOC-f0e1241d461dd523` | notice | 0.4167 | 0.1053 | ✓ | 10.6 | 2058 | 194 |  |
| 94 | `DOC-162babf552426b57` | letter | 0.0800 | 0.0000 | ✓ | 8.8 | 1813 | 177 |  |
| 95 | `DOC-f4b4c8c623ccb915` | press_release | 0.0800 | 0.0000 | ✓ | 33.7 | 4363 | 381 |  |
| 96 | `DOC-ee6bae4d269c1911` | memo | 0.3333 | 0.1112 | ✓ | 12.5 | 2830 | 275 |  |
| 97 | `DOC-9422c8775b387935` | press_release | 0.5457 | 0.1112 | ✓ | 9.8 | 2588 | 217 |  |
| 98 | `DOC-a7d76cec54e46f1f` | email | 0.1633 | 0.0000 | ✓ | 34.9 | 2833 | 456 |  |
| 99 | `DOC-8c312283e2533866` | press_release | 0.5000 | 0.1112 | ✓ | 35.4 | 2068 | 446 |  |
| 100 | `DOC-caaba1c5a3f9a41e` | email | 0.2800 | 0.0000 | ✓ | 38.9 | 3117 | 624 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s9-corr100-bal.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s9-corr100-bal
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s9-corr100-bal.yaml` | run spec |
| `reports/serving/sand032-s9-corr100-bal.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s9-corr100-bal/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s9-corr100-bal/` | offline Braintrust-shaped rows — disposed after this report is committed |
