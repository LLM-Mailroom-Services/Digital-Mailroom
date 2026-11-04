# Run report — `sand032-s9-corporate50-bal`

SAND-032 Modal × vLLM specialist extract: **50 corporate_record docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 64** on **2×L4** (MIN=MAX=2 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s9-corporate50-bal` |
| task / agent | `corporate_records_specialist` |
| prompt | `corporate_records_specialist_simplified` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 2× L4 (data-parallel replicas) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=32 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16, 32], max_inputs=32 |
| modal | `sandbox-vllm-sand032`, max/min containers 2/2, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 50 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `d3139c5e07c1` |
| git | `37e5f98 (dirty)` |
| spec_hash | `5219221416312471322cac41daf1b6c82d4398c4631faf4f2fb8eab277b40c30` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **50 / 50** (errors 0) |
| **overall_extraction_score** | **0.4386** (sd 0.2496, min 0.0580, max 0.8889) |
| schema_valid_rate | 0.940 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 48.646 s |
| concurrency | 64 (32 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.332 s |
| latency p50 / p95 / max | 45.21 / 47.21 / 48.46 s |
| prompt / completion tokens | 255944 / 8243 |
| throughput | 5430.8 tok/s |
| GPU $ over busy wall (×2 L4 @ $0.8/h) | 0.021620 |
| **$ per doc (busy)** | **0.000432** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.7 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 2 of 2** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790582921.77`: requests Δ 17 (cumulative 93), measured TTFT mean 6.854 s (vLLM histogram, cumulative), prefix-cache hit 43.1%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.
- replica `1790582929.28`: requests Δ 33 (cumulative 107), measured TTFT mean 9.291 s (vLLM histogram, cumulative), prefix-cache hit 42.9%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 2029.7 s over wall 48.6 s = **41.72×** effective parallelism at c64 (65% of the ideal 64×).
- **Tail:** slowest doc `DOC-b865a8f75657643a` (articles_of_incorporation) 48.5 s = 100% of wall — p95/p50 = 1.04×.
- **Prompt length vs latency:** Pearson r = -0.07 across 50 docs (not prefill-dominated).
- **Decode budget:** mean completion 165 tok/doc, mean prompt 5119 tok/doc.
- **Subclass spread:** best `articles_of_incorporation` 0.761 (n=5), worst `board_resolution` 0.117 (n=4).
- **Field-level extraction:** 17/50 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s9-corporate50-bal-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s9-corporate50-bal-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| charter_amendment | 8 | 0.4486 |
| indenture | 7 | 0.4765 |
| subsidiary_list | 6 | 0.2801 |
| rights_instrument | 6 | 0.4277 |
| bylaws | 6 | 0.6784 |
| officer_certificate | 6 | 0.2067 |
| articles_of_incorporation | 5 | 0.7609 |
| board_resolution | 4 | 0.1167 |
| powers_of_attorney | 2 | 0.5877 |
| **total** | **50** | **0.4386** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-9bdcc670eb06437b` | subsidiary_list | 0.4402 | 0.1538 | ✗ | 28.3 | 2446 | 124 |  |
| 2 | `DOC-d8a8d7c000ae6495` | rights_instrument | 0.1000 | 0.0000 | ✓ | 29.2 | 2687 | 143 |  |
| 3 | `DOC-8018aaaf98b8597e` | bylaws | 0.6667 | 0.2223 | ✓ | 29.3 | 6615 | 145 |  |
| 4 | `DOC-087da9fdf781f7db` | bylaws | 0.3333 | 0.1111 | ✓ | 29.6 | 6603 | 138 |  |
| 5 | `DOC-08829e0f817f1211` | charter_amendment | 0.4524 | 0.1111 | ✓ | 29.6 | 2947 | 163 |  |
| 6 | `DOC-c9fa372f38de2b5e` | charter_amendment | 0.3571 | 0.1111 | ✓ | 29.9 | 3160 | 163 |  |
| 7 | `DOC-69ffaec3ba2b2cde` | officer_certificate | 0.1547 | 0.0000 | ✓ | 29.9 | 6545 | 158 |  |
| 8 | `DOC-30ce0f05432fc57f` | rights_instrument | 0.4405 | 0.1176 | ✓ | 30.0 | 2647 | 159 |  |
| 9 | `DOC-dfe42f3747f299e6` | bylaws | 0.7500 | 0.2352 | ✓ | 30.4 | 7237 | 160 |  |
| 10 | `DOC-36df577431fb1032` | officer_certificate | 0.1389 | 0.0000 | ✓ | 30.5 | 6001 | 150 |  |
| 11 | `DOC-9cd96711a8928ec5` | charter_amendment | 0.3590 | 0.1053 | ✓ | 30.7 | 4953 | 171 |  |
| 12 | `DOC-a2110b2cebe63cb7` | rights_instrument | 0.7556 | 0.2000 | ✓ | 30.6 | 6718 | 166 |  |
| 13 | `DOC-a14783cfd27c88c1` | indenture | 0.5795 | 0.1176 | ✓ | 31.6 | 5858 | 197 |  |
| 14 | `DOC-4a77d0b316e1cc01` | charter_amendment | 0.3636 | 0.1053 | ✓ | 31.7 | 5713 | 217 |  |
| 15 | `DOC-bda69bc956881bab` | powers_of_attorney | 0.6667 | 0.2223 | ✓ | 31.9 | 9395 | 222 |  |
| 16 | `DOC-a973ebf005e0e785` | indenture | 0.4278 | 0.1176 | ✓ | 31.9 | 7583 | 200 |  |
| 17 | `DOC-ef2f0660ed8b6f24` | indenture | 0.4497 | 0.1176 | ✓ | 32.5 | 7923 | 227 |  |
| 18 | `DOC-e42fbaa25765ec5f` | subsidiary_list | 0.1325 | 0.0000 | ✗ | 38.8 | 2249 | 97 |  |
| 19 | `DOC-417996c5cc3d91f5` | subsidiary_list | 0.4402 | 0.2222 | ✗ | 42.5 | 2232 | 97 |  |
| 20 | `DOC-0636dbc980a43715` | subsidiary_list | 0.1413 | 0.0000 | ✓ | 44.0 | 2250 | 120 |  |
| 21 | `DOC-e12f100d091e15b5` | subsidiary_list | 0.4682 | 0.1250 | ✓ | 44.0 | 2310 | 152 |  |
| 22 | `DOC-ffb48271e0a5e812` | bylaws | 0.6667 | 0.2352 | ✓ | 44.4 | 6741 | 136 |  |
| 23 | `DOC-c40a11ac7f2c7b5b` | subsidiary_list | 0.0580 | 0.0000 | ✓ | 44.9 | 2656 | 157 |  |
| 24 | `DOC-42999d0d46a55578` | articles_of_incorporation | 0.7436 | 0.2223 | ✓ | 45.1 | 4943 | 157 |  |
| 25 | `DOC-263580addaac6d20` | articles_of_incorporation | 0.8056 | 0.2223 | ✓ | 45.2 | 5557 | 162 |  |
| 26 | `DOC-30fe9f6e442b9df3` | officer_certificate | 0.2624 | 0.0000 | ✓ | 45.2 | 4047 | 163 |  |
| 27 | `DOC-732b812b7d9d9653` | rights_instrument | 0.8889 | 0.2105 | ✓ | 45.5 | 7045 | 157 |  |
| 28 | `DOC-34077127acc64d5e` | indenture | 0.5515 | 0.1111 | ✓ | 45.5 | 7235 | 168 |  |
| 29 | `DOC-7ca9eefc5f17d24f` | board_resolution | 0.1401 | 0.0000 | ✓ | 45.6 | 2456 | 154 |  |
| 30 | `DOC-db84eb3d59faee66` | board_resolution | 0.0813 | 0.0000 | ✓ | 45.6 | 2644 | 181 |  |
| 31 | `DOC-5dc965bfd05b8bf5` | rights_instrument | 0.2115 | 0.0000 | ✓ | 45.8 | 5481 | 179 |  |
| 32 | `DOC-1e0470c03b023106` | articles_of_incorporation | 0.7949 | 0.2105 | ✓ | 46.0 | 6754 | 157 |  |
| 33 | `DOC-b7680bb9f72c5e65` | officer_certificate | 0.2878 | 0.0000 | ✓ | 46.1 | 6557 | 157 |  |
| 34 | `DOC-e366f6c8f425cd09` | charter_amendment | 0.3611 | 0.1053 | ✓ | 46.4 | 4797 | 189 |  |
| 35 | `DOC-9523246260be90e0` | bylaws | 0.8333 | 0.2105 | ✓ | 46.5 | 7196 | 163 |  |
| 36 | `DOC-1578b671836c78e9` | bylaws | 0.8205 | 0.2105 | ✓ | 46.6 | 7197 | 151 |  |
| 37 | `DOC-4042dc3ecd9ac9b4` | officer_certificate | 0.1499 | 0.0000 | ✓ | 46.6 | 6599 | 159 |  |
| 38 | `DOC-cdc3f9c110996846` | charter_amendment | 0.1419 | 0.0000 | ✓ | 46.6 | 4257 | 165 |  |
| 39 | `DOC-0d9dd64d13b1c270` | board_resolution | 0.1480 | 0.0000 | ✓ | 46.8 | 2512 | 167 |  |
| 40 | `DOC-3c328f7374a079a9` | charter_amendment | 0.7333 | 0.2105 | ✓ | 46.7 | 4845 | 191 |  |
| 41 | `DOC-5cc2960a21fca151` | officer_certificate | 0.2467 | 0.0000 | ✓ | 46.8 | 6533 | 163 |  |
| 42 | `DOC-e12651c80e736fb8` | indenture | 0.4423 | 0.1176 | ✓ | 46.8 | 2760 | 165 |  |
| 43 | `DOC-51092450a52e256c` | indenture | 0.4423 | 0.1176 | ✓ | 46.9 | 6933 | 168 |  |
| 44 | `DOC-b28a8210ab812830` | board_resolution | 0.0976 | 0.0000 | ✓ | 46.9 | 2515 | 163 |  |
| 45 | `DOC-5c087a08edcb4a91` | powers_of_attorney | 0.5088 | 0.1250 | ✓ | 47.0 | 6451 | 196 |  |
| 46 | `DOC-a52b3ad21666d339` | rights_instrument | 0.1694 | 0.0000 | ✓ | 47.0 | 3538 | 169 |  |
| 47 | `DOC-0d28ca4c116b9f53` | charter_amendment | 0.8205 | 0.2105 | ✓ | 47.1 | 3334 | 166 |  |
| 48 | `DOC-85c7b49cdac19586` | articles_of_incorporation | 0.6602 | 0.1176 | ✓ | 47.2 | 6825 | 194 |  |
| 49 | `DOC-2aa6196b22606d9c` | indenture | 0.4423 | 0.1111 | ✓ | 47.6 | 5877 | 214 |  |
| 50 | `DOC-b865a8f75657643a` | articles_of_incorporation | 0.8000 | 0.2223 | ✓ | 48.5 | 7587 | 163 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s9-corporate50-bal.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s9-corporate50-bal
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s9-corporate50-bal.yaml` | run spec |
| `reports/serving/sand032-s9-corporate50-bal.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s9-corporate50-bal/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s9-corporate50-bal/` | offline Braintrust-shaped rows — disposed after this report is committed |
