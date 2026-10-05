# Run report — `sand032-s10-corporate75-v2`

SAND-032 Modal × vLLM specialist extract: **75 corporate_record docs** on **Qwen/Qwen3-8B-AWQ** at **concurrency 8** on **1×L4** (MIN=MAX=1 pinned, dedicated app `sandbox-vllm-sand032`). Public HF `mailroom-dataset` only.

| | |
| --- | --- |
| run_id | `sand032-s10-corporate75-v2` |
| task / agent | `corporate_records_specialist` |
| prompt | `corporate_records_specialist_v2_evalenv` (local pin) |
| engine | `Qwen/Qwen3-8B-AWQ`, vLLM `v0.29.0`, 1× L4 (single replica) |
| context / quant | `max_model_len=32768`, quant=`awq_marlin`, gpu_util=0.9, max_num_seqs=16 |
| engine flags | prefix_caching=on, enforce_eager=off, kv_cache_dtype=`fp8`, thinking=off, cudagraph sizes=[1, 2, 4, 8, 16], max_inputs=16 |
| modal | `sandbox-vllm-sand032`, max/min containers 1/1, scaledown 120 s, profile `exios66` |
| dataset | mailroom-dataset `ground_truth`, split=all, rev `ed7576b6`, seed 42 |
| draw | 75 docs, single-class bucket (nested 20 ⊂ 50 ⊂ 100); dataset sha `ea36c90aa6b2` |
| git | `02954ee (dirty)` |
| spec_hash | `a8b80797a7939f8d192018fe101affa28608e67c5037730efd3c7249c963e0cd` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / total | **75 / 75** (errors 0) |
| **overall_extraction_score** | **0.4689** (sd 0.2429, min 0.0580, max 0.8718) |
| schema_valid_rate | 0.960 |
| parse errors | 0 |

## Serving / cost metrics

| metric | value |
| --- | --- |
| wall (runner busy interval) | 132.717 s |
| concurrency | 8 (8 per replica) |
| cold boot — deploy→engine ready (driver stamps) | — |
| preflight probe (engine answering) | 0.516 s |
| latency p50 / p95 / max | 13.41 / 17.91 / 25.24 s |
| prompt / completion tokens | 368364 / 12166 |
| throughput | 2867.2 tok/s |
| GPU $ over busy wall (×1 L4 @ $0.8/h) | 0.029493 |
| **$ per doc (busy)** | **0.000393** |
| fleet window deploy→stop (upper est.) | — → — USD |
| cost cap | $0.2 (config) |

## Engine observations (vLLM `/metrics`, measured — never inferred)

- `/metrics` coverage after the run: **replicas observed: 1 of 1** (sampled through the Modal router; replica = vLLM process start time).
- replica `1790586975.98`: requests Δ 75 (cumulative 225), measured TTFT mean 1.463 s (vLLM histogram, cumulative), prefix-cache hit 46.4%, preemptions 0, length-capped finishes 0, KV usage at scrape 0%.

## Analyst insights & findings

- **Concurrency efficiency:** Σ latency 1042.6 s over wall 132.7 s = **7.86×** effective parallelism at c8 (98% of the ideal 8×).
- **Tail:** slowest doc `DOC-bda69bc956881bab` (powers_of_attorney) 25.2 s = 19% of wall — p95/p50 = 1.34×.
- **Prompt length vs latency:** Pearson r = 0.39 across 75 docs (not prefill-dominated).
- **Decode budget:** mean completion 162 tok/doc, mean prompt 4912 tok/doc.
- **Subclass spread:** best `articles_of_incorporation` 0.785 (n=9), worst `board_resolution` 0.135 (n=8).
- **Field-level extraction:** 22/75 docs have extraction_f1 = 0 — the overall score is carried by entity/structure components, not exact field values.

## Figures

![Per-document latency, slowest first, with p50/p95 reference lines](figures/sand032-s10-corporate75-v2-latency.svg)

![Mean overall extraction score by subclass](figures/sand032-s10-corporate75-v2-subclass.svg)

_Table views of both figures: **Per-document scores** and **Strata** below._

## Strata (subclass)

| subclass | n | mean overall |
| --- | --- | --- |
| charter_amendment | 12 | 0.5147 |
| indenture | 11 | 0.4758 |
| articles_of_incorporation | 9 | 0.7847 |
| rights_instrument | 9 | 0.4991 |
| officer_certificate | 9 | 0.2167 |
| subsidiary_list | 8 | 0.4054 |
| board_resolution | 8 | 0.1353 |
| bylaws | 6 | 0.6656 |
| powers_of_attorney | 3 | 0.6458 |
| **total** | **75** | **0.4689** |

## Per-document scores

| # | doc id | subclass | overall | extraction_f1 | schema | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-a1bf2ddf032e38ea` | subsidiary_list | 0.5580 | 0.1819 | ✓ | 14.8 | 2259 | 115 |  |
| 2 | `DOC-e42fbaa25765ec5f` | subsidiary_list | 0.4658 | 0.1538 | ✗ | 15.0 | 2263 | 133 |  |
| 3 | `DOC-263580addaac6d20` | articles_of_incorporation | 0.8056 | 0.2223 | ✓ | 17.3 | 5571 | 162 |  |
| 4 | `DOC-42999d0d46a55578` | articles_of_incorporation | 0.7436 | 0.2223 | ✓ | 17.3 | 4957 | 153 |  |
| 5 | `DOC-3e20fef7d0be1ab6` | articles_of_incorporation | 0.7949 | 0.2105 | ✓ | 17.5 | 5260 | 159 |  |
| 6 | `DOC-34077127acc64d5e` | indenture | 0.5515 | 0.1111 | ✓ | 17.8 | 7249 | 169 |  |
| 7 | `DOC-5dc965bfd05b8bf5` | rights_instrument | 0.2115 | 0.0000 | ✓ | 22.4 | 5495 | 180 |  |
| 8 | `DOC-bda69bc956881bab` | powers_of_attorney | 0.6667 | 0.2223 | ✓ | 25.2 | 9409 | 235 |  |
| 9 | `DOC-7ca9eefc5f17d24f` | board_resolution | 0.1401 | 0.0000 | ✓ | 13.4 | 2470 | 155 |  |
| 10 | `DOC-6d17fda455311945` | articles_of_incorporation | 0.8056 | 0.2223 | ✓ | 11.1 | 10144 | 135 |  |
| 11 | `DOC-0d9dd64d13b1c270` | board_resolution | 0.1146 | 0.0000 | ✓ | 11.8 | 2526 | 144 |  |
| 12 | `DOC-d2969f9629acc901` | board_resolution | 0.1488 | 0.0000 | ✓ | 13.4 | 2480 | 154 |  |
| 13 | `DOC-a14783cfd27c88c1` | indenture | 0.5962 | 0.1176 | ✓ | 17.4 | 5872 | 196 |  |
| 14 | `DOC-4a77d0b316e1cc01` | charter_amendment | 0.7273 | 0.2105 | ✓ | 15.3 | 5727 | 185 |  |
| 15 | `DOC-e366f6c8f425cd09` | charter_amendment | 0.3611 | 0.1053 | ✓ | 10.5 | 4811 | 174 |  |
| 16 | `DOC-4d8e8b87f161d432` | subsidiary_list | 0.4191 | 0.1667 | ✓ | 11.2 | 2579 | 119 |  |
| 17 | `DOC-7294152c69239b1e` | indenture | 0.4471 | 0.1111 | ✓ | 14.5 | 4627 | 196 |  |
| 18 | `DOC-c40a11ac7f2c7b5b` | subsidiary_list | 0.0580 | 0.0000 | ✓ | 12.9 | 2670 | 151 |  |
| 19 | `DOC-1e0470c03b023106` | articles_of_incorporation | 0.7949 | 0.2105 | ✓ | 14.9 | 6768 | 157 |  |
| 20 | `DOC-c9fa372f38de2b5e` | charter_amendment | 0.3571 | 0.1111 | ✓ | 14.9 | 3174 | 163 |  |
| 21 | `DOC-732b812b7d9d9653` | rights_instrument | 0.8222 | 0.2223 | ✓ | 13.2 | 7059 | 151 |  |
| 22 | `DOC-74e0f47369572741` | officer_certificate | 0.1547 | 0.0000 | ✓ | 12.8 | 6479 | 150 |  |
| 23 | `DOC-3c328f7374a079a9` | charter_amendment | 0.4000 | 0.1053 | ✓ | 15.8 | 4859 | 189 |  |
| 24 | `DOC-9cd96711a8928ec5` | charter_amendment | 0.3590 | 0.1053 | ✓ | 13.0 | 4967 | 171 |  |
| 25 | `DOC-51092450a52e256c` | indenture | 0.4423 | 0.1176 | ✓ | 12.7 | 6947 | 170 |  |
| 26 | `DOC-310fa993e212a342` | board_resolution | 0.2146 | 0.0000 | ✓ | 11.9 | 2467 | 159 |  |
| 27 | `DOC-db84eb3d59faee66` | board_resolution | 0.0813 | 0.0000 | ✓ | 11.7 | 2658 | 157 |  |
| 28 | `DOC-b856ca94d75a431a` | charter_amendment | 0.6923 | 0.2352 | ✓ | 12.1 | 2822 | 162 |  |
| 29 | `DOC-4042dc3ecd9ac9b4` | officer_certificate | 0.1499 | 0.0000 | ✓ | 11.7 | 6613 | 155 |  |
| 30 | `DOC-cde69e0ba4db2419` | officer_certificate | 0.2820 | 0.0000 | ✓ | 12.2 | 2537 | 170 |  |
| 31 | `DOC-417996c5cc3d91f5` | subsidiary_list | 0.6923 | 0.4000 | ✗ | 6.1 | 2246 | 93 |  |
| 32 | `DOC-85c7b49cdac19586` | articles_of_incorporation | 0.6602 | 0.1176 | ✓ | 13.1 | 6839 | 195 |  |
| 33 | `DOC-5052ed547d53cfbf` | articles_of_incorporation | 0.8718 | 0.2105 | ✓ | 12.0 | 3900 | 150 |  |
| 34 | `DOC-f1e8af2071cb17fa` | rights_instrument | 0.4167 | 0.1111 | ✓ | 15.5 | 6439 | 163 |  |
| 35 | `DOC-e12f100d091e15b5` | subsidiary_list | 0.4682 | 0.1111 | ✓ | 13.0 | 2324 | 158 |  |
| 36 | `DOC-9bdcc670eb06437b` | subsidiary_list | 0.4402 | 0.1538 | ✗ | 12.1 | 2460 | 124 |  |
| 37 | `DOC-9467462d9bb34f8e` | indenture | 0.5208 | 0.1176 | ✓ | 12.9 | 6964 | 142 |  |
| 38 | `DOC-f70b11ab7f823e2d` | charter_amendment | 0.7619 | 0.2105 | ✓ | 15.5 | 3152 | 186 |  |
| 39 | `DOC-1578b671836c78e9` | bylaws | 0.7436 | 0.1111 | ✓ | 16.0 | 7211 | 171 |  |
| 40 | `DOC-9523246260be90e0` | bylaws | 0.8333 | 0.2105 | ✓ | 16.1 | 7210 | 170 |  |
| 41 | `DOC-b73c5e5708c43511` | officer_certificate | 0.2271 | 0.0000 | ✓ | 13.4 | 5958 | 174 |  |
| 42 | `DOC-0d28ca4c116b9f53` | charter_amendment | 0.4872 | 0.1053 | ✓ | 12.4 | 3348 | 159 |  |
| 43 | `DOC-08829e0f817f1211` | charter_amendment | 0.5238 | 0.1111 | ✓ | 13.0 | 2961 | 160 |  |
| 44 | `DOC-cdc3f9c110996846` | charter_amendment | 0.3939 | 0.1053 | ✓ | 14.3 | 4271 | 164 |  |
| 45 | `DOC-a195b29d1b417e2f` | indenture | 0.4432 | 0.1111 | ✓ | 15.0 | 4815 | 184 |  |
| 46 | `DOC-ef2f0660ed8b6f24` | indenture | 0.4497 | 0.1176 | ✓ | 15.7 | 7937 | 183 |  |
| 47 | `DOC-d8a8d7c000ae6495` | rights_instrument | 0.1027 | 0.0000 | ✓ | 12.5 | 2701 | 148 |  |
| 48 | `DOC-bb25adbf606096a4` | indenture | 0.4423 | 0.1111 | ✓ | 13.0 | 3712 | 168 |  |
| 49 | `DOC-30ce0f05432fc57f` | rights_instrument | 0.4405 | 0.1176 | ✓ | 9.3 | 2661 | 159 |  |
| 50 | `DOC-087da9fdf781f7db` | bylaws | 0.3333 | 0.1176 | ✓ | 11.2 | 6617 | 135 |  |
| 51 | `DOC-a973ebf005e0e785` | indenture | 0.4278 | 0.1176 | ✓ | 17.9 | 7597 | 202 |  |
| 52 | `DOC-6993b10b8f79da64` | charter_amendment | 0.3571 | 0.1053 | ✓ | 10.5 | 2938 | 153 |  |
| 53 | `DOC-2aa6196b22606d9c` | indenture | 0.4450 | 0.1111 | ✓ | 17.8 | 5891 | 215 |  |
| 54 | `DOC-0db97c4753dcbaea` | powers_of_attorney | 0.7619 | 0.2105 | ✓ | 14.7 | 4223 | 228 |  |
| 55 | `DOC-ffb48271e0a5e812` | bylaws | 0.6667 | 0.2352 | ✓ | 10.9 | 6755 | 139 |  |
| 56 | `DOC-e12651c80e736fb8` | indenture | 0.4679 | 0.1250 | ✓ | 13.4 | 2774 | 170 |  |
| 57 | `DOC-8e3fa7aa97eda92a` | articles_of_incorporation | 0.7857 | 0.2105 | ✓ | 13.6 | 6658 | 167 |  |
| 58 | `DOC-571cffbc7867e8ef` | board_resolution | 0.1326 | 0.0000 | ✓ | 11.4 | 2552 | 145 |  |
| 59 | `DOC-78f2456f571403a9` | board_resolution | 0.1531 | 0.0000 | ✓ | 11.2 | 2359 | 144 |  |
| 60 | `DOC-b7680bb9f72c5e65` | officer_certificate | 0.2878 | 0.0000 | ✓ | 12.1 | 6571 | 157 |  |
| 61 | `DOC-8663fca594565055` | charter_amendment | 0.7556 | 0.2223 | ✓ | 13.5 | 3454 | 161 |  |
| 62 | `DOC-0636dbc980a43715` | subsidiary_list | 0.1413 | 0.0000 | ✓ | 10.7 | 2264 | 95 |  |
| 63 | `DOC-8018aaaf98b8597e` | bylaws | 0.6667 | 0.2223 | ✓ | 15.6 | 6629 | 141 |  |
| 64 | `DOC-30fe9f6e442b9df3` | officer_certificate | 0.2624 | 0.0000 | ✓ | 14.3 | 4061 | 163 |  |
| 65 | `DOC-b28a8210ab812830` | board_resolution | 0.0976 | 0.0000 | ✓ | 12.1 | 2529 | 145 |  |
| 66 | `DOC-5c087a08edcb4a91` | powers_of_attorney | 0.5088 | 0.1111 | ✓ | 17.7 | 6465 | 187 |  |
| 67 | `DOC-a2110b2cebe63cb7` | rights_instrument | 0.7556 | 0.1904 | ✓ | 17.7 | 6732 | 162 |  |
| 68 | `DOC-63fffca0c0a261ec` | rights_instrument | 0.8431 | 0.1904 | ✓ | 18.7 | 6443 | 183 |  |
| 69 | `DOC-36df577431fb1032` | officer_certificate | 0.1846 | 0.0000 | ✓ | 14.7 | 6015 | 152 |  |
| 70 | `DOC-20e622adc7603fc5` | rights_instrument | 0.7857 | 0.2223 | ✓ | 17.5 | 6499 | 193 |  |
| 71 | `DOC-a52b3ad21666d339` | rights_instrument | 0.1138 | 0.0000 | ✓ | 13.7 | 3552 | 172 |  |
| 72 | `DOC-69ffaec3ba2b2cde` | officer_certificate | 0.1547 | 0.0000 | ✓ | 12.5 | 6559 | 153 |  |
| 73 | `DOC-dfe42f3747f299e6` | bylaws | 0.7500 | 0.2352 | ✓ | 12.3 | 7251 | 155 |  |
| 74 | `DOC-5cc2960a21fca151` | officer_certificate | 0.2467 | 0.0000 | ✓ | 12.6 | 6547 | 166 |  |
| 75 | `DOC-b865a8f75657643a` | articles_of_incorporation | 0.8000 | 0.2223 | ✓ | 7.5 | 7601 | 163 |  |

## Reproduce

```bash
modal profile activate exios66
scripts/sand032/run_one.sh config/runs/sand032-s10-corporate75-v2.yaml deploy stop   # or: warm (reuse fleet)
scripts/mailroom-tui score sand032-s10-corporate75-v2
```

## Artifacts

| path | role |
| --- | --- |
| `config/runs/sand032-s10-corporate75-v2.yaml` | run spec |
| `reports/serving/sand032-s10-corporate75-v2.serving.json` | serving record (busy wall, tokens, p50/p95, run-span lower bound) |
| `data/runtime/runs/sand032-s10-corporate75-v2/` | run store (lock, dataset, items, /metrics before/after) — gitignored |
| `data/runtime/bt_experiments/sand032-s10-corporate75-v2/` | offline Braintrust-shaped rows — disposed after this report is committed |
