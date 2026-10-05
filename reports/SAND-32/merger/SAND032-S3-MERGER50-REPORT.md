# Run report — `sand032-s3-merger50`

SAND-032 Modal × vLLM specialist extract: **50 merger_agreement docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 32** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s3-merger50` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_simplified` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=16 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16], max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 50 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `23c90708536e` |
| git | `d2bb4ef` |
| spec_hash | `7f13f615baa1e9feeffe2b00bac7f929ca876e27f4a8ecaccff21cf75a242c06` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **44 / 50** (errors 6) |
| **overall_extraction_score** | **0.0396** (sd 0.0505, min 0.0000, max 0.2000) |
| schema_valid_rate | 1.000 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 342.375 s |
| concurrency | 32 (16 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.176 s |
| latency p50 / p95 / max | 119.00 / 211.41 / 217.85 s |
| prompt / completion tokens | 465554 / 40242 |
| throughput | 1477.3 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 0.152167 |
| **$ per doc (busy)** | **0.003458** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $1.4 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 2 of 2** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790546353.94`: requests Δ 30 (cumulative 278), measured TTFT mean 6.948 s (vLLM histogram, cumulative), prefix-cache hit 50.4%, preemptions 0, length-capped finishes 5, KV usage at scrape 0%.
- replica `1790546749.43`: requests Δ 20 (cumulative 142), measured TTFT mean 6.335 s (vLLM histogram, cumulative), prefix-cache hit 35.4%, preemptions 0, length-capped finishes 1, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 5118.6 s over wall 342.4 s = **14.95×** effective parallelism at c32 (47% of the ideal 32×).
- **Tail:** slowest doc `DOC-74a69c5b3cdf1afc` (all_stock) 217.8 s = 64% of wall — p95/p50 = 1.78×.
- **Prompt length vs latency:** Pearson r = 0.25 across 44 docs (not prefill-dominated).
- **Decode budget:** mean completion 915 tok/doc, mean prompt 10581 tok/doc.
- **Subclass spread:** best `all_cash` 0.049 (n=18), worst `mixed_cash_stock` 0.021 (n=3).
- **Field-level extraction:** 44/44 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Scoring method — MAUD answer accuracy

The pinned Hub merger rows carry ground truth only as `maud_clause_labels` (LegalBench MAUD question → answer). The suite field map scores document_name/parties/…, which those rows never populate, so field F1 is 0 by construction. The headline here is **per-question MAUD accuracy** (`src/mailroom_sandbox/eval/maud_scoring.py`); an unanswered question counts as wrong.

| metric | value |
| --- | --- |
| labeled MAUD questions | 717 |
| answered | 159 (22.2% coverage) |
| correct | 29 → **micro accuracy 4.0%** |
| precision on answered | 18.2% |
| clean subset (single MAUD sub-question per name) | 14/306 = 4.6% |

**Dataset caveat:** the corpus collapses several MAUD sub-questions under one name (e.g. `No-Shop` answers include `Yes`, `Strict liability`, `Reasonable standard`), so a per-doc target on those names is ambiguous; the clean subset excludes them.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s3-merger50-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s3-merger50-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| all_cash | 18 | 0.0487 |
| other | 12 | 0.0235 |
| all_stock | 11 | 0.0476 |
| mixed_cash_stock | 3 | 0.0208 |
| **total** | **44** | **0.0396** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-c96b9c7e12f91576` | other | 0.0000 | 0.0000 | ✓ | 65.5 | 10784 | 669 |  |
| 2 | `DOC-1252fb5690e17c7b` | all_cash | 0.0556 | 0.0000 | ✓ | 69.6 | 10533 | 692 |  |
| 3 | `DOC-be8461dd68cfe458` | all_stock | 0.0000 | 0.0000 | ✓ | 75.7 | 10400 | 797 |  |
| 4 | `DOC-15f85636d1eb6b77` | all_cash | 0.0667 | 0.0000 | ✓ | 79.4 | 10758 | 851 |  |
| 5 | `DOC-fc07b37a0f0d1234` | mixed_cash_stock | 0.0625 | 0.0000 | ✓ | 79.5 | 10382 | 847 |  |
| 6 | `DOC-5fbb9ee2f4b4b114` | other | 0.1176 | 0.0000 | ✓ | 82.9 | 10427 | 837 |  |
| 7 | `DOC-45f801408be08af6` | all_stock | 0.2000 | 0.0000 | ✓ | 87.5 | 11412 | 965 |  |
| 8 | `DOC-30eda1e78a5f6fb5` | all_stock | 0.0000 | 0.0000 | ✓ | 97.1 | 10358 | 1111 |  |
| 9 | `DOC-5fa0ba13cf68b593` | other | 0.0000 | 0.0000 | ✓ | 97.6 | 10443 | 683 |  |
| 10 | `DOC-8f599c800d19fd92` | all_cash | 0.0000 | 0.0000 | ✓ | 107.9 | 10320 | 750 |  |
| 11 | `DOC-ecf69d7e102ef62a` | other | 0.0000 | 0.0000 | ✓ | 108.8 | 10495 | 764 |  |
| 12 | `DOC-1e016055aa435e71` | other | 0.0000 | 0.0000 | ✓ | 53.4 | 10295 | 795 |  |
| 13 | `DOC-f4e726a7f2c25494` | all_stock | 0.0000 | 0.0000 | ✓ | 119.1 | 10718 | 844 |  |
| 14 | `DOC-c1d57615929b483e` | mixed_cash_stock | 0.0000 | 0.0000 | ✓ | 124.2 | 10370 | 840 |  |
| 15 | `DOC-038a485469f83c9a` | all_stock | 0.1250 | 0.0000 | ✓ | 128.7 | 10500 | 895 |  |
| 16 | `DOC-7430de65e5471741` | all_cash | 0.0526 | 0.0000 | ✓ | 128.9 | 10251 | 1552 |  |
| 17 | `DOC-d01014aed8ad8824` | other | 0.0000 | 0.0000 | ✓ | 132.9 | 10725 | 875 |  |
| 18 | `DOC-63beb09b179ea4ee` | all_cash | 0.0000 | 0.0000 | ✓ | 61.1 | 10611 | 846 |  |
| 19 | `DOC-52f9a5be69429299` | mixed_cash_stock | 0.0000 | 0.0000 | ✓ | 137.5 | 10715 | 889 |  |
| 20 | `DOC-3927f91bc3daffc3` | all_cash | 0.0000 | 0.0000 | ✓ | 138.2 | 11001 | 1695 |  |
| 21 | `DOC-eac7882cff200545` | other | 0.0588 | 0.0000 | ✓ | 142.2 | 10659 | 941 |  |
| 22 | `DOC-d5c4f12f934de48e` | other | 0.1053 | 0.0000 | ✓ | 62.9 | 10716 | 890 |  |
| 23 | `DOC-882fabf7aba36941` | other | 0.0000 | 0.0000 | ✓ | 151.5 | 10790 | 1028 |  |
| 24 | `DOC-03712a2b0a99a314` | all_stock | 0.0588 | 0.0000 | ✓ | 49.2 | 10586 | 787 |  |
| 25 | `DOC-8c661a1693d4655b` | other | 0.0000 | 0.0000 | ✓ | 159.3 | 10586 | 1056 |  |
| 26 | `DOC-f099c5c73d56631e` | other | 0.0000 | 0.0000 | ✓ | 72.8 | 11308 | 1207 |  |
| 27 | `DOC-fd6090e354177e5b` | all_cash | 0.0000 | 0.0000 | ✓ | 43.2 | 10139 | 745 |  |
| 28 | `DOC-ab735131c00271bc` | all_cash | 0.0556 | 0.0000 | ✓ | 39.0 | 10018 | 821 |  |
| 29 | `DOC-d1e355800bff0425` | other | 0.0000 | 0.0000 | ✓ | 45.4 | 10375 | 915 |  |
| 30 | `DOC-37026835107f9684` | all_stock | 0.0000 | 0.0000 | ✓ | 172.5 | 10669 | 1217 |  |
| 31 | `DOC-b866e2b4f5059213` | all_cash | 0.0556 | 0.0000 | ✓ | 39.2 | 10358 | 978 |  |
| 32 | `DOC-d554890e66786170` | all_cash | 0.1250 | 0.0000 | ✓ | 201.9 | 11752 | 750 |  |
| 33 | `DOC-2f9cf3ce009aaaf0` | all_cash | 0.0588 | 0.0000 | ✓ | 126.6 | 10215 | 683 |  |
| 34 | `DOC-0a733ab86f2390ae` | all_cash | 0.0667 | 0.0000 | ✓ | 206.2 | 10048 | 840 |  |
| 35 | `DOC-8a0bdfe3d16c33b2` | all_cash | 0.0000 | 0.0000 | ✓ | 210.1 | 10574 | 853 |  |
| 36 | `DOC-4ab4ecd86ecf275d` | all_stock | 0.0625 | 0.0000 | ✓ | 211.4 | 10904 | 758 |  |
| 37 | `DOC-d0495abfa5f3d8ee` | all_stock | 0.0000 | 0.0000 | ✓ | 214.0 | 10241 | 824 |  |
| 38 | `DOC-74a69c5b3cdf1afc` | all_stock | 0.0000 | 0.0000 | ✓ | 217.8 | 11554 | 1074 |  |
| 39 | `DOC-2b9f668ab6cb8901` | all_cash | 0.0526 | 0.0000 | ✓ | 140.5 | 10143 | 898 |  |
| 40 | `DOC-5c44797b6add60e4` | all_cash | 0.0000 | 0.0000 | ✓ | 137.2 | 10523 | 1016 |  |
| 41 | `DOC-fcaddb5bdc94ce63` | all_cash | 0.0588 | 0.0000 | ✓ | 118.9 | 10394 | 873 |  |
| 42 | `DOC-8fe2855a2310cdbe` | mixed_cash_stock | — | — | ✗ | 144.3 | None | None | LengthFinishReasonError: Could not parse response content as |
| 43 | `DOC-169bbcdc5d9e609c` | all_stock | 0.0769 | 0.0000 | ✓ | 114.3 | 11218 | 628 |  |
| 44 | `DOC-26fa94f698c37fc5` | all_cash | 0.1765 | 0.0000 | ✓ | 142.7 | 10267 | 1317 |  |
| 45 | `DOC-f546c7d6cf2e77e2` | all_cash | 0.0526 | 0.0000 | ✓ | 124.1 | 10019 | 946 |  |
| 46 | `DOC-f90cc5fb2ceac154` | mixed_cash_stock | — | — | ✗ | 318.1 | None | None | LengthFinishReasonError: Could not parse response content as |
| 47 | `DOC-eb2b56fe30dc35f4` | all_cash | — | — | ✗ | 319.6 | None | None | LengthFinishReasonError: Could not parse response content as |
| 48 | `DOC-62456d43b50f73fa` | all_stock | — | — | ✗ | 319.8 | None | None | LengthFinishReasonError: Could not parse response content as |
| 49 | `DOC-511062d64bc9afc6` | other | — | — | ✗ | 319.7 | None | None | LengthFinishReasonError: Could not parse response content as |
| 50 | `DOC-bec74557186e9409` | other | — | — | ✗ | 272.5 | None | None | LengthFinishReasonError: Could not parse response content as |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s3-merger50.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s3-merger50
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s3-merger50.yaml` | run spec |
| `reports/serving/sand032-s3-merger50.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s3-merger50/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s3-merger50/` | offline Braintrust-shaped rows — disposed after this report is committed |
