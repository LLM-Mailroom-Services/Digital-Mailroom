# Run report — `grid-20-merger-specialist-awq-1l4-retry`

Dated cell stem: `RUN-20-MERGER-AWQ-1L4-C8-RETRY`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-20-merger-specialist-awq-1l4-retry` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **20** |
| profile | `modal-vllm` |
| spec_hash | `8821719fd9c52cab73caca437d80dda3e99e4ca4fae7dbf3420535dc120a271a` |
| dataset fingerprint | `53cb996f5b48` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **17 / 3 / 20** |
| **overall_extraction_score** | **0.016917** |
| schema_valid_rate | 1.000000 |
| error_count | 3 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 992.915 |
| gpu_seconds | 992.915 |
| estimated GPU cost | 0.220648 |
| **GPU $/doc** | **0.012979** |
| latency p50 / max (s) | 86.672966 / 119.679299 |
| prompt / completion tokens | 156468 / 17546 |
| concurrency speedup (Σlat/wall) | 1.44 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-d4b1a7a2b981fbf4` | True | 0 | 64.2 | 9342 | 689 | None |
| 2 | `DOC-4f23b571c261a708` | True | 0 | 64.7 | 9004 | 683 | None |
| 3 | `DOC-be8461dd68cfe458` | True | 0 | 75.3 | 8983 | 799 | None |
| 4 | `DOC-d9157f4ad78024e5` | True | 0 | 86.7 | 9179 | 927 | None |
| 5 | `DOC-d01014aed8ad8824` | True | 0 | 92.4 | 9317 | 988 | None |
| 6 | `DOC-cea6dc327188d9da` | True | 0 | 99.3 | 9418 | 1063 | None |
| 7 | `DOC-62456d43b50f73fa` | True | 0 | 119.7 | 9629 | 1340 | None |
| 8 | `DOC-4e57aa1ce9cc283b` | True | 0.117647 | 55.1 | 9143 | 756 | None |
| 9 | `DOC-0534799ed39ca0db` | True | 0.055556 | 76.3 | 9106 | 972 | None |
| 10 | `DOC-8a0bdfe3d16c33b2` | True | 0.058824 | 108.5 | 9304 | 1363 | None |
| 11 | `DOC-158ec6b697211e14` | True | 0 | 111.7 | 8933 | 1377 | None |
| 12 | `DOC-297745a521cd1e8c` | True | 0 | 105.8 | 9095 | 1354 | None |
| 13 | `DOC-9d34581755c603a3` | True | 0 | 94.5 | 8792 | 1247 | None |
| 14 | `DOC-5d30efc302f3c431` | True | 0 | 76.2 | 9218 | 1051 | None |
| 15 | `DOC-ff3ceb691481f1bd` | True | 0 | 56.7 | 9174 | 789 | None |
| 16 | `DOC-7128ff7c2ed51cd6` | True | 0.055556 | 45.3 | 8913 | 721 | None |
| 17 | `DOC-169bbcdc5d9e609c` | True | 0 | 97.6 | 9918 | 1427 | None |
| 18 | `DOC-4cab0ae6bfeaa370` | False | — | 958.3 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=16384, prompt_tokens=9107, total_tokens=25491, completion_tokens_details=None, prompt_tokens_details=None) |
| 19 | `DOC-f9870e3b8fd141b0` | False | — | 913.3 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=16384, prompt_tokens=9363, total_tokens=25747, completion_tokens_details=None, prompt_tokens_details=None) |
| 20 | `DOC-681bc6115b882191` | False | — | 880.8 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=16384, prompt_tokens=9172, total_tokens=25556, completion_tokens_details=None, prompt_tokens_details=None) |
