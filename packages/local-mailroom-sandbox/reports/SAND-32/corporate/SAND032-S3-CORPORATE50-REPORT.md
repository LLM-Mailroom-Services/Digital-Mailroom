# Run report — `sand032-s3-corporate50`

SAND-032 Modal × vLLM specialist extract: **50 corporate_record docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 32** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s3-corporate50` |
| task / agent | `corporate_records_specialist` |
| prompt | `corporate_records_specialist_simplified` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=16 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16], max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 50 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `d3139c5e07c1` |
| git | `b9d2832 (dirty)` |
| spec_hash | `6738cdc253d639d11fef0eeac26bec8c5350149c0ab4fb1f1c561c00d1300865` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **50 / 50** (errors 0) |
| **overall_extraction_score** | **0.4583** (sd 0.2512, min 0.0580, max 0.8889) |
| schema_valid_rate | 0.940 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 56.293 s |
| concurrency | 32 (16 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.194 s |
| latency p50 / p95 / max | 28.94 / 55.07 / 55.53 s |
| prompt / completion tokens | 255944 / 8188 |
| throughput | 4692.1 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 0.025019 |
| **$ per doc (busy)** | **0.000500** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.7 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 2 of 2** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790546353.94`: requests Δ 21 (cumulative 248), measured TTFT mean 1.155 s (vLLM histogram, cumulative), prefix-cache hit 66.0%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.
- replica `1790546749.43`: requests Δ 29 (cumulative 122), measured TTFT mean 5.653 s (vLLM histogram, cumulative), prefix-cache hit 43.9%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 1452.0 s over wall 56.3 s = **25.79×** effective parallelism at c32 (81% of the ideal 32×).
- **Tail:** slowest doc `DOC-bda69bc956881bab` (powers_of_attorney) 55.5 s = 99% of wall — p95/p50 = 1.90×.
- **Prompt length vs latency:** Pearson r = 0.36 across 50 docs (not prefill-dominated).
- **Decode budget:** mean completion 164 tok/doc, mean prompt 5119 tok/doc.
- **Subclass spread:** best `articles_of_incorporation` 0.761 (n=5), worst `board_resolution` 0.108 (n=4).
- **Field-level extraction:** 16/50 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s3-corporate50-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s3-corporate50-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| charter_amendment | 8 | 0.6089 |
| indenture | 7 | 0.4765 |
| subsidiary_list | 6 | 0.2801 |
| rights_instrument | 6 | 0.4277 |
| bylaws | 6 | 0.6271 |
| officer_certificate | 6 | 0.2144 |
| articles_of_incorporation | 5 | 0.7609 |
| board_resolution | 4 | 0.1084 |
| powers_of_attorney | 2 | 0.5877 |
| **total** | **50** | **0.4583** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-e42fbaa25765ec5f` | subsidiary_list | 0.1325 | 0.0000 | ✗ | 13.4 | 2249 | 97 |  |
| 2 | `DOC-417996c5cc3d91f5` | subsidiary_list | 0.4402 | 0.2222 | ✗ | 13.4 | 2232 | 97 |  |
| 3 | `DOC-9bdcc670eb06437b` | subsidiary_list | 0.4402 | 0.1538 | ✗ | 14.7 | 2446 | 125 |  |
| 4 | `DOC-0d9dd64d13b1c270` | board_resolution | 0.1146 | 0.0000 | ✓ | 17.3 | 2512 | 159 |  |
| 5 | `DOC-c40a11ac7f2c7b5b` | subsidiary_list | 0.0580 | 0.0000 | ✓ | 17.4 | 2656 | 157 |  |
| 6 | `DOC-c9fa372f38de2b5e` | charter_amendment | 0.3571 | 0.1111 | ✓ | 17.4 | 3160 | 163 |  |
| 7 | `DOC-cdc3f9c110996846` | charter_amendment | 0.3939 | 0.1053 | ✓ | 17.4 | 4257 | 164 |  |
| 8 | `DOC-732b812b7d9d9653` | rights_instrument | 0.8889 | 0.2105 | ✓ | 17.4 | 7045 | 160 |  |
| 9 | `DOC-9523246260be90e0` | bylaws | 0.8333 | 0.2105 | ✓ | 19.2 | 7196 | 166 |  |
| 10 | `DOC-9cd96711a8928ec5` | charter_amendment | 0.6923 | 0.2105 | ✓ | 19.8 | 4953 | 170 |  |
| 11 | `DOC-0d28ca4c116b9f53` | charter_amendment | 0.8205 | 0.2105 | ✓ | 20.5 | 3334 | 166 |  |
| 12 | `DOC-e366f6c8f425cd09` | charter_amendment | 0.6944 | 0.2000 | ✓ | 22.1 | 4797 | 193 |  |
| 13 | `DOC-30ce0f05432fc57f` | rights_instrument | 0.4405 | 0.1176 | ✓ | 11.0 | 2647 | 159 |  |
| 14 | `DOC-0636dbc980a43715` | subsidiary_list | 0.1413 | 0.0000 | ✓ | 7.3 | 2250 | 121 |  |
| 15 | `DOC-087da9fdf781f7db` | bylaws | 0.3590 | 0.1053 | ✓ | 11.8 | 6603 | 151 |  |
| 16 | `DOC-d8a8d7c000ae6495` | rights_instrument | 0.1000 | 0.0000 | ✓ | 26.8 | 2687 | 142 |  |
| 17 | `DOC-8018aaaf98b8597e` | bylaws | 0.6667 | 0.2223 | ✓ | 11.4 | 6615 | 145 |  |
| 18 | `DOC-e12f100d091e15b5` | subsidiary_list | 0.4682 | 0.1333 | ✓ | 29.1 | 2310 | 137 |  |
| 19 | `DOC-b7680bb9f72c5e65` | officer_certificate | 0.2878 | 0.0000 | ✓ | 11.7 | 6557 | 157 |  |
| 20 | `DOC-b28a8210ab812830` | board_resolution | 0.0976 | 0.0000 | ✓ | 10.8 | 2515 | 164 |  |
| 21 | `DOC-1e0470c03b023106` | articles_of_incorporation | 0.7949 | 0.2105 | ✓ | 32.4 | 6754 | 157 |  |
| 22 | `DOC-42999d0d46a55578` | articles_of_incorporation | 0.7436 | 0.2223 | ✓ | 33.9 | 4943 | 150 |  |
| 23 | `DOC-36df577431fb1032` | officer_certificate | 0.1846 | 0.0000 | ✓ | 9.5 | 6001 | 152 |  |
| 24 | `DOC-4042dc3ecd9ac9b4` | officer_certificate | 0.1499 | 0.0000 | ✓ | 34.7 | 6599 | 159 |  |
| 25 | `DOC-69ffaec3ba2b2cde` | officer_certificate | 0.1547 | 0.0000 | ✓ | 8.2 | 6545 | 157 |  |
| 26 | `DOC-dfe42f3747f299e6` | bylaws | 0.7500 | 0.2352 | ✓ | 6.6 | 7237 | 163 |  |
| 27 | `DOC-7ca9eefc5f17d24f` | board_resolution | 0.1401 | 0.0000 | ✓ | 36.1 | 2456 | 155 |  |
| 28 | `DOC-08829e0f817f1211` | charter_amendment | 0.4524 | 0.1111 | ✓ | 37.5 | 2947 | 168 |  |
| 29 | `DOC-db84eb3d59faee66` | board_resolution | 0.0813 | 0.0000 | ✓ | 37.5 | 2644 | 162 |  |
| 30 | `DOC-34077127acc64d5e` | indenture | 0.5515 | 0.1111 | ✓ | 37.5 | 7235 | 168 |  |
| 31 | `DOC-5dc965bfd05b8bf5` | rights_instrument | 0.2115 | 0.0000 | ✓ | 40.3 | 5481 | 179 |  |
| 32 | `DOC-51092450a52e256c` | indenture | 0.4423 | 0.1176 | ✓ | 42.6 | 6933 | 170 |  |
| 33 | `DOC-1578b671836c78e9` | bylaws | 0.8205 | 0.2000 | ✓ | 44.4 | 7197 | 166 |  |
| 34 | `DOC-85c7b49cdac19586` | articles_of_incorporation | 0.6602 | 0.1176 | ✓ | 46.6 | 6825 | 194 |  |
| 35 | `DOC-ef2f0660ed8b6f24` | indenture | 0.4497 | 0.1176 | ✓ | 49.1 | 7923 | 185 |  |
| 36 | `DOC-a14783cfd27c88c1` | indenture | 0.5795 | 0.1250 | ✓ | 49.2 | 5858 | 194 |  |
| 37 | `DOC-4a77d0b316e1cc01` | charter_amendment | 0.7273 | 0.2105 | ✓ | 49.2 | 5713 | 216 |  |
| 38 | `DOC-ffb48271e0a5e812` | bylaws | 0.3333 | 0.1176 | ✓ | 36.7 | 6741 | 144 |  |
| 39 | `DOC-e12651c80e736fb8` | indenture | 0.4423 | 0.1250 | ✓ | 36.7 | 2760 | 151 |  |
| 40 | `DOC-263580addaac6d20` | articles_of_incorporation | 0.8056 | 0.2223 | ✓ | 54.4 | 5557 | 162 |  |
| 41 | `DOC-30fe9f6e442b9df3` | officer_certificate | 0.2624 | 0.0000 | ✓ | 35.2 | 4047 | 163 |  |
| 42 | `DOC-a973ebf005e0e785` | indenture | 0.4278 | 0.1176 | ✓ | 55.1 | 7583 | 198 |  |
| 43 | `DOC-3c328f7374a079a9` | charter_amendment | 0.7333 | 0.2105 | ✓ | 55.1 | 4845 | 189 |  |
| 44 | `DOC-5cc2960a21fca151` | officer_certificate | 0.2467 | 0.0000 | ✓ | 28.4 | 6533 | 163 |  |
| 45 | `DOC-a2110b2cebe63cb7` | rights_instrument | 0.7556 | 0.2000 | ✓ | 33.1 | 6718 | 169 |  |
| 46 | `DOC-a52b3ad21666d339` | rights_instrument | 0.1694 | 0.0000 | ✓ | 28.8 | 3538 | 172 |  |
| 47 | `DOC-bda69bc956881bab` | powers_of_attorney | 0.6667 | 0.2223 | ✓ | 55.5 | 9395 | 217 |  |
| 48 | `DOC-b865a8f75657643a` | articles_of_incorporation | 0.8000 | 0.2223 | ✓ | 26.5 | 7587 | 163 |  |
| 49 | `DOC-5c087a08edcb4a91` | powers_of_attorney | 0.5088 | 0.1250 | ✓ | 38.4 | 6451 | 194 |  |
| 50 | `DOC-2aa6196b22606d9c` | indenture | 0.4423 | 0.1111 | ✓ | 42.8 | 5877 | 215 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s3-corporate50.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s3-corporate50
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s3-corporate50.yaml` | run spec |
| `reports/serving/sand032-s3-corporate50.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s3-corporate50/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s3-corporate50/` | offline Braintrust-shaped rows — disposed after this report is committed |
