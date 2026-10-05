# Run report — `sand032-s2b-corr100-2rep`

SAND-032 Modal × vLLM specialist extract: **100 correspondence docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 16** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s2b-corr100-2rep` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_production` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=16 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16], max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 100 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `046a2c9bfc4e` |
| git | `76d11cc (dirty)` |
| spec_hash | `d20d182c0363e3b10217fb96b4f077a5b595810ee9a38b64170349e85e298ac1` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **100 / 100** (errors 0) |
| **overall_extraction_score** | **0.2966** (sd 0.2019, min 0.0000, max 0.8095) |
| schema_valid_rate | 1.000 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 46.135 s |
| concurrency | 16 (8 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.164 s |
| latency p50 / p95 / max | 5.70 / 14.41 / 31.11 s |
| prompt / completion tokens | 226418 / 18484 |
| throughput | 5308.4 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 0.020504 |
| **$ per doc (busy)** | **0.000205** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.6 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 2 of 2** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790546353.94`: requests Δ 49 (cumulative 169), measured TTFT mean 0.513 s (vLLM histogram, cumulative), prefix-cache hit 70.0%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.
- replica `1790546749.43`: requests Δ 51 (cumulative 51), measured TTFT mean 1.259 s (vLLM histogram, cumulative), prefix-cache hit 50.4%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 705.4 s over wall 46.1 s = **15.29×** effective parallelism at c16 (96% of the ideal 16×).
- **Tail:** slowest doc `DOC-caaba1c5a3f9a41e` (email) 31.1 s = 67% of wall — p95/p50 = 2.53×.
- **Prompt length vs latency:** Pearson r = 0.21 across 100 docs (not prefill-dominated).
- **Decode budget:** mean completion 185 tok/doc, mean prompt 2264 tok/doc.
- **Subclass spread:** best `meeting_request` 0.482 (n=2), worst `email` 0.263 (n=54).
- **Field-level extraction:** 55/100 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s2b-corr100-2rep-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s2b-corr100-2rep-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| email | 54 | 0.2627 |
| memo | 11 | 0.3185 |
| demand | 9 | 0.3655 |
| letter | 9 | 0.2776 |
| notice | 8 | 0.3958 |
| press_release | 7 | 0.2933 |
| meeting_request | 2 | 0.4824 |
| **total** | **100** | **0.2966** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-c2826f69ed293da4` | memo | 0.1053 | 0.0000 | ✓ | 3.7 | 1698 | 106 |  |
| 2 | `DOC-1d5664e2c826ad07` | email | 0.3889 | 0.1428 | ✓ | 3.7 | 1685 | 115 |  |
| 3 | `DOC-ab94c5d183e5f7ca` | notice | 0.0556 | 0.0000 | ✓ | 4.4 | 5639 | 146 |  |
| 4 | `DOC-eaeffa14c92e7cd8` | press_release | 0.1276 | 0.0000 | ✓ | 4.4 | 2512 | 154 |  |
| 5 | `DOC-a318b50872273528` | email | 0.0889 | 0.0000 | ✓ | 5.3 | 2028 | 187 |  |
| 6 | `DOC-fc6108235411ca8e` | demand | 0.4133 | 0.1112 | ✓ | 5.6 | 1934 | 204 |  |
| 7 | `DOC-f36a37e1a9c1351e` | press_release | 0.1667 | 0.0000 | ✓ | 2.8 | 1707 | 107 |  |
| 8 | `DOC-0ab974301d63024f` | letter | 0.5000 | 0.1428 | ✓ | 11.2 | 1752 | 141 |  |
| 9 | `DOC-e72ff16f78525d0f` | email | 0.3140 | 0.0000 | ✓ | 6.2 | 2243 | 249 |  |
| 10 | `DOC-383b9badb01a1a00` | email | 0.1010 | 0.0000 | ✓ | 12.1 | 4829 | 159 |  |
| 11 | `DOC-f49b5cc25d9cb557` | letter | 0.2446 | 0.0000 | ✓ | 12.2 | 1996 | 162 |  |
| 12 | `DOC-2aea82e94dba6438` | email | 0.2045 | 0.0000 | ✓ | 12.4 | 1911 | 170 |  |
| 13 | `DOC-02dc4ab50ea271a4` | email | 0.0741 | 0.0000 | ✓ | 13.3 | 2038 | 186 |  |
| 14 | `DOC-38c54645bf0e601a` | email | 0.3140 | 0.0000 | ✓ | 8.1 | 2025 | 200 |  |
| 15 | `DOC-a763315b8f7cb96e` | email | 0.3667 | 0.1176 | ✓ | 10.7 | 2137 | 214 |  |
| 16 | `DOC-8754555168547e16` | email | 0.3458 | 0.0000 | ✓ | 14.4 | 2631 | 220 |  |
| 17 | `DOC-32b1660fb702fd84` | memo | 0.1111 | 0.0000 | ✓ | 15.1 | 2158 | 227 |  |
| 18 | `DOC-a7d76cec54e46f1f` | email | 0.1633 | 0.0000 | ✓ | 11.2 | 2833 | 452 |  |
| 19 | `DOC-c71d3ca0b727a0d4` | email | 0.0833 | 0.0000 | ✓ | 3.6 | 1779 | 134 |  |
| 20 | `DOC-e624b1b9823e53f5` | memo | 0.4617 | 0.1112 | ✓ | 16.2 | 2386 | 265 |  |
| 21 | `DOC-9be315cbfa0fbd19` | email | 0.1605 | 0.0000 | ✓ | 16.4 | 3834 | 268 |  |
| 22 | `DOC-c45ecc852b2cb0f4` | meeting_request | 0.5362 | 0.1176 | ✓ | 4.9 | 1823 | 189 |  |
| 23 | `DOC-f4b4c8c623ccb915` | press_release | 0.0800 | 0.0000 | ✓ | 10.1 | 4363 | 399 |  |
| 24 | `DOC-553256644e7b4547` | email | 0.0952 | 0.0000 | ✓ | 5.5 | 1773 | 138 |  |
| 25 | `DOC-b5d016f4b2abaa39` | email | 0.1212 | 0.0000 | ✓ | 3.5 | 1703 | 132 |  |
| 26 | `DOC-44b1e5a60b363d3e` | letter | 0.0889 | 0.0000 | ✓ | 4.0 | 1996 | 152 |  |
| 27 | `DOC-9ec94a2619e46dfb` | email | 0.4000 | 0.1112 | ✓ | 7.1 | 1742 | 166 |  |
| 28 | `DOC-ba72bbffee783647` | email | 0.1852 | 0.0000 | ✓ | 7.6 | 1879 | 177 |  |
| 29 | `DOC-31c068618dba65f3` | letter | 0.3333 | 0.1333 | ✓ | 3.5 | 1813 | 116 |  |
| 30 | `DOC-25958c023112a96e` | demand | 0.6667 | 0.2105 | ✓ | 5.8 | 1711 | 180 |  |
| 31 | `DOC-1dcf4dfd5ec6defb` | email | 0.2744 | 0.0000 | ✓ | 6.7 | 3002 | 262 |  |
| 32 | `DOC-b0055813bc08a29c` | meeting_request | 0.4286 | 0.1176 | ✓ | 5.6 | 2062 | 199 |  |
| 33 | `DOC-228e51bba45b5c7d` | email | 0.2693 | 0.0000 | ✓ | 7.7 | 2506 | 177 |  |
| 34 | `DOC-cb4f8fb4ccb52f44` | email | 0.0833 | 0.0000 | ✓ | 6.7 | 1739 | 152 |  |
| 35 | `DOC-19d9fd70a08d306b` | notice | 0.3333 | 0.1112 | ✓ | 7.0 | 2439 | 256 |  |
| 36 | `DOC-522399c5514f180a` | memo | 0.2879 | 0.0000 | ✓ | 5.3 | 2443 | 205 |  |
| 37 | `DOC-99c7dacadccd6e78` | press_release | 0.5088 | 0.1250 | ✓ | 4.0 | 1796 | 153 |  |
| 38 | `DOC-8c312283e2533866` | press_release | 0.5000 | 0.1112 | ✓ | 19.5 | 2068 | 446 |  |
| 39 | `DOC-2431095adda97989` | memo | 0.5086 | 0.1112 | ✓ | 10.9 | 2075 | 258 |  |
| 40 | `DOC-314aa51db90c8c92` | memo | 0.4167 | 0.1112 | ✓ | 8.7 | 2541 | 178 |  |
| 41 | `DOC-8eed243667c985bd` | email | 0.7917 | 0.2105 | ✓ | 8.1 | 2149 | 178 |  |
| 42 | `DOC-2bdbf0be591edea6` | memo | 0.0800 | 0.0000 | ✓ | 3.9 | 1729 | 153 |  |
| 43 | `DOC-bc3f4676ac0c2e16` | letter | 0.3333 | 0.1053 | ✓ | 9.4 | 3358 | 207 |  |
| 44 | `DOC-690cb07fef21747b` | email | 0.5088 | 0.1333 | ✓ | 4.1 | 1954 | 159 |  |
| 45 | `DOC-91f5631a20c62dc5` | email | 0.6877 | 0.1176 | ✓ | 4.9 | 1922 | 191 |  |
| 46 | `DOC-9d0aa39a8ac68936` | email | 0.0833 | 0.0000 | ✓ | 4.0 | 1671 | 92 |  |
| 47 | `DOC-4eb0e9385b81cc4b` | email | 0.0303 | 0.0000 | ✓ | 5.8 | 1784 | 139 |  |
| 48 | `DOC-36b9a080db747f3d` | demand | 0.1468 | 0.0000 | ✓ | 3.9 | 2858 | 153 |  |
| 49 | `DOC-c4debd478f2c06e0` | email | 0.5379 | 0.1333 | ✓ | 5.5 | 1936 | 137 |  |
| 50 | `DOC-556e41697352e63d` | demand | 0.0800 | 0.0000 | ✓ | 7.6 | 1876 | 197 |  |
| 51 | `DOC-d3e421962da61b35` | notice | 0.7917 | 0.2222 | ✓ | 4.7 | 2129 | 184 |  |
| 52 | `DOC-cfe8e8e7b9b3f38d` | email | 0.0303 | 0.0000 | ✓ | 9.2 | 2628 | 225 |  |
| 53 | `DOC-379b182c302a6821` | email | 0.3333 | 0.1250 | ✓ | 5.6 | 1747 | 133 |  |
| 54 | `DOC-cc6e6dece6a787c2` | demand | 0.4802 | 0.1112 | ✓ | 4.8 | 1790 | 185 |  |
| 55 | `DOC-84a9981be2435b55` | email | 0.1786 | 0.0000 | ✓ | 3.4 | 1847 | 129 |  |
| 56 | `DOC-20b4e31d9a4bf994` | email | 0.2359 | 0.0000 | ✓ | 4.9 | 1855 | 114 |  |
| 57 | `DOC-38265bcc6ecfecc3` | email | 0.0784 | 0.0000 | ✓ | 4.4 | 1729 | 172 |  |
| 58 | `DOC-16dfd03aed14e557` | email | 0.0784 | 0.0000 | ✓ | 3.0 | 1674 | 107 |  |
| 59 | `DOC-47647a5fdcd45666` | email | 0.3333 | 0.1250 | ✓ | 6.1 | 1916 | 136 |  |
| 60 | `DOC-caaba1c5a3f9a41e` | email | 0.2800 | 0.0000 | ✓ | 31.1 | 3117 | 624 |  |
| 61 | `DOC-4ab559dfb4d79b6d` | email | 0.6667 | 0.2667 | ✓ | 5.6 | 1757 | 138 |  |
| 62 | `DOC-4321eefceb0f4289` | letter | 0.3333 | 0.1176 | ✓ | 5.5 | 1920 | 205 |  |
| 63 | `DOC-9d65887887fe53d2` | email | 0.3333 | 0.1176 | ✓ | 4.4 | 1812 | 163 |  |
| 64 | `DOC-21460a9f6d7e6348` | memo | 0.7255 | 0.2499 | ✓ | 3.6 | 1806 | 129 |  |
| 65 | `DOC-2cde0c6d0c70b02b` | memo | 0.0909 | 0.0000 | ✓ | 6.0 | 2206 | 225 |  |
| 66 | `DOC-5a424efe5df6ba6f` | demand | 0.5414 | 0.1250 | ✓ | 4.0 | 4103 | 143 |  |
| 67 | `DOC-cd6877aeb3f2f7e4` | email | 0.0556 | 0.0000 | ✓ | 8.6 | 2263 | 183 |  |
| 68 | `DOC-f6a9a00e53cc7973` | notice | 0.1333 | 0.0000 | ✓ | 4.9 | 6883 | 177 |  |
| 69 | `DOC-341d347babb3a19f` | email | 0.2213 | 0.0000 | ✓ | 4.2 | 1896 | 149 |  |
| 70 | `DOC-d0c241ea24439be2` | email | 0.4689 | 0.1250 | ✓ | 7.8 | 1793 | 159 |  |
| 71 | `DOC-a8efd6e4c4d49aaf` | email | 0.5308 | 0.1112 | ✓ | 8.5 | 1940 | 180 |  |
| 72 | `DOC-9b2bc061621a56be` | email | 0.3523 | 0.0000 | ✓ | 7.0 | 2043 | 140 |  |
| 73 | `DOC-edd0a288e32f0d3b` | notice | 0.6667 | 0.2222 | ✓ | 7.6 | 1976 | 154 |  |
| 74 | `DOC-8c7847bfbb91d578` | demand | 0.0351 | 0.0000 | ✓ | 3.7 | 2724 | 139 |  |
| 75 | `DOC-9501118a02fe39b9` | email | 0.4178 | 0.1112 | ✓ | 7.6 | 1889 | 164 |  |
| 76 | `DOC-d3d85dc1b1514bec` | notice | 0.4359 | 0.1112 | ✓ | 10.0 | 1913 | 220 |  |
| 77 | `DOC-d6e2bbd8c5e394a4` | demand | 0.8095 | 0.2499 | ✓ | 4.0 | 1732 | 156 |  |
| 78 | `DOC-e25814bd08d418aa` | email | 0.1633 | 0.0000 | ✓ | 5.9 | 2022 | 227 |  |
| 79 | `DOC-595ab9fc19465909` | notice | 0.3333 | 0.1112 | ✓ | 4.6 | 1840 | 181 |  |
| 80 | `DOC-6f05af738f455d50` | email | 0.1437 | 0.0000 | ✓ | 7.3 | 2788 | 134 |  |
| 81 | `DOC-76375ebb4cd91de9` | letter | 0.1111 | 0.0000 | ✓ | 4.6 | 2516 | 181 |  |
| 82 | `DOC-c4074ed5b08f097e` | memo | 0.3827 | 0.1333 | ✓ | 3.8 | 1724 | 147 |  |
| 83 | `DOC-752a5e85c01ca6f0` | email | 0.3939 | 0.1053 | ✓ | 10.1 | 1866 | 207 |  |
| 84 | `DOC-5adf644f3cb1d34e` | email | 0.0000 | 0.0000 | ✓ | 4.7 | 1668 | 87 |  |
| 85 | `DOC-8ce704cea54b1469` | press_release | 0.0800 | 0.0000 | ✓ | 4.8 | 2665 | 190 |  |
| 86 | `DOC-6aa30fb5a4e67d76` | email | 0.2696 | 0.0000 | ✓ | 9.2 | 2681 | 183 |  |
| 87 | `DOC-95a872ee4ff237d5` | email | 0.0784 | 0.0000 | ✓ | 3.9 | 2179 | 154 |  |
| 88 | `DOC-96438076efc6cc7b` | email | 0.3333 | 0.1176 | ✓ | 4.0 | 1778 | 159 |  |
| 89 | `DOC-a6fff0ef0e406461` | email | 0.1346 | 0.0000 | ✓ | 7.7 | 1843 | 175 |  |
| 90 | `DOC-c01ab1c1c673f355` | letter | 0.4743 | 0.1333 | ✓ | 3.4 | 1863 | 132 |  |
| 91 | `DOC-1f3f868558fc4a6e` | email | 0.3333 | 0.1112 | ✓ | 3.4 | 1845 | 136 |  |
| 92 | `DOC-c00ffce3272be5fd` | email | 0.2981 | 0.0000 | ✓ | 9.3 | 2384 | 222 |  |
| 93 | `DOC-ff15276697cdfbb2` | demand | 0.1162 | 0.0000 | ✓ | 7.9 | 2322 | 191 |  |
| 94 | `DOC-ee6bae4d269c1911` | memo | 0.3333 | 0.1112 | ✓ | 11.1 | 2830 | 269 |  |
| 95 | `DOC-17ac4251c7d94cea` | email | 0.1111 | 0.0000 | ✓ | 4.2 | 1730 | 141 |  |
| 96 | `DOC-f7af031d61f7d7f5` | email | 0.0800 | 0.0000 | ✓ | 5.4 | 3967 | 152 |  |
| 97 | `DOC-f0e1241d461dd523` | notice | 0.4167 | 0.1112 | ✓ | 7.9 | 2058 | 216 |  |
| 98 | `DOC-162babf552426b57` | letter | 0.0800 | 0.0000 | ✓ | 6.2 | 1813 | 179 |  |
| 99 | `DOC-5b63f9fe205d564b` | email | 0.5800 | 0.1250 | ✓ | 4.1 | 1894 | 168 |  |
| 100 | `DOC-9422c8775b387935` | press_release | 0.5901 | 0.1176 | ✓ | 7.5 | 2588 | 213 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s2b-corr100-2rep.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s2b-corr100-2rep
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s2b-corr100-2rep.yaml` | run spec |
| `reports/serving/sand032-s2b-corr100-2rep.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s2b-corr100-2rep/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s2b-corr100-2rep/` | offline Braintrust-shaped rows — disposed after this report is committed |
