# Run report — `grid-20-contracts-specialist-awq-1l4`

Dated cell stem: `RUN-20-CONTRACTS-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-20-contracts-specialist-awq-1l4` |
| task / agent | `contracts_specialist` |
| prompt | `contracts_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **20** |
| profile | `modal-vllm` |
| spec_hash | `bab8851282caa60d3c4435646222baa04b3fd315f400e4062c86fdccc8d81c39` |
| dataset fingerprint | `704bac6c015d` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **19 / 1 / 20** |
| **overall_extraction_score** | **0.531137** |
| schema_valid_rate | 1.000000 |
| error_count | 1 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 299.295 |
| gpu_seconds | 299.716 |
| estimated GPU cost | 0.066604 |
| **GPU $/doc** | **0.00350547** |
| latency p50 / max (s) | 65.780504 / 187.841582 |
| prompt / completion tokens | 123139 / 31915 |
| concurrency speedup (Σlat/wall) | 4.31 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-98ff556893f1a98f` | True | 0.750000 | 33.7 | 3200 | 654 | None |
| 2 | `DOC-9696c5996f24d85d` | True | — | 64.1 | 4377 | 1422 | None |
| 3 | `DOC-c30c293d38a2cd8b` | True | 0.545500 | 37.3 | 9794 | 911 | None |
| 4 | `DOC-6712aa595cfe3e2c` | True | 0.470600 | 74.5 | 7666 | 1680 | None |
| 5 | `DOC-adad5ef793c0e409` | True | 0.461500 | 76.2 | 8247 | 1701 | None |
| 6 | `DOC-5892b6dc609c8d0f` | True | — | 79.7 | 7606 | 1790 | None |
| 7 | `DOC-ba6d7a0ea5100bbb` | True | 0.631600 | 80.3 | 7887 | 1807 | None |
| 8 | `DOC-440a54573c24b918` | True | 1.000000 | 26.5 | 3493 | 627 | None |
| 9 | `DOC-9e063c6e3baf1233` | True | 0.545500 | 104.9 | 7486 | 2442 | None |
| 10 | `DOC-ade03c57c5f78e21` | True | 0.705900 | 49.9 | 4093 | 1278 | None |
| 11 | `DOC-c68a4dd90660c113` | True | 0.615400 | 49.8 | 7851 | 1302 | None |
| 12 | `DOC-55df050fcb737129` | True | 0.500000 | 63.4 | 5461 | 1639 | None |
| 13 | `DOC-99ca00712a84f039` | True | 0.666700 | 78.7 | 5337 | 2002 | None |
| 14 | `DOC-fca31a55b1d526ea` | True | 0.833300 | 80.1 | 5459 | 2068 | None |
| 15 | `DOC-f9b36fee351217c2` | True | 0.500000 | 65.8 | 7931 | 1719 | None |
| 16 | `DOC-a2ce7adbf6f5cb8d` | True | 0.555600 | 39.2 | 6729 | 1080 | None |
| 17 | `DOC-d1c45d175a8abeb5` | True | 0.560000 | 27.1 | 6851 | 775 | None |
| 18 | `DOC-2ca7b08d2d439f1e` | True | — | 187.8 | 7616 | 4860 | None |
| 19 | `DOC-dfa5c8eb1e7b837c` | True | 0.750000 | 71.8 | 6055 | 2158 | None |
| 20 | `DOC-06229aa6571f9d46` | False | — | 228.1 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=6154, total_tokens=14346, completion_tokens_details=None, prompt_tokens_details=None) |
