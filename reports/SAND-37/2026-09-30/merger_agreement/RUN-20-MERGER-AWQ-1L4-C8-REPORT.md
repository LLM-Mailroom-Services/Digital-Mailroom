# Run report — `grid-20-merger-specialist-awq-1l4-rerun`

Dated cell stem: `RUN-20-MERGER-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-20-merger-specialist-awq-1l4-rerun` |
| task / agent | `merger_agreement_specialist` |
| prompt | `merger_agreement_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **20** |
| profile | `modal-vllm` |
| spec_hash | `42a52cdf5f234f070d189f5c3149487d1afcecaff7a57153ccfe3c73554abc90` |
| dataset fingerprint | `7e2b12cc13df` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **18 / 2 / 20** |
| **overall_extraction_score** | **0.012932** |
| schema_valid_rate | 1.000000 |
| error_count | 2 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 316.142 |
| gpu_seconds | 316.677 |
| estimated GPU cost | 0.070373 |
| **GPU $/doc** | **0.00390961** |
| latency p50 / max (s) | 50.460262 / 113.307683 |
| prompt / completion tokens | 167210 / 15448 |
| concurrency speedup (Σlat/wall) | 3.08 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-52f9a5be69429299` | True | 0 | 44.1 | 9517 | 537 | None |
| 2 | `DOC-0a733ab86f2390ae` | True | 0 | 51.8 | 8841 | 673 | None |
| 3 | `DOC-d0495abfa5f3d8ee` | True | 0 | 58.7 | 9008 | 796 | None |
| 4 | `DOC-c1d57615929b483e` | True | 0.062500 | 58.7 | 9148 | 786 | None |
| 5 | `DOC-7430de65e5471741` | True | 0.052632 | 65.5 | 9060 | 838 | None |
| 6 | `DOC-d554890e66786170` | True | 0 | 66.1 | 10446 | 857 | None |
| 7 | `DOC-5fbb9ee2f4b4b114` | True | 0.058824 | 49.5 | 9027 | 814 | None |
| 8 | `DOC-5fa0ba13cf68b593` | True | 0 | 38.9 | 9125 | 628 | None |
| 9 | `DOC-30eda1e78a5f6fb5` | True | 0 | 49.4 | 9124 | 772 | None |
| 10 | `DOC-511062d64bc9afc6` | True | 0 | 45.6 | 9338 | 680 | None |
| 11 | `DOC-be8461dd68cfe458` | True | 0 | 113.3 | 9054 | 1661 | None |
| 12 | `DOC-f4e726a7f2c25494` | True | 0 | 51.4 | 9345 | 822 | None |
| 13 | `DOC-ecf69d7e102ef62a` | True | 0 | 57.6 | 9271 | 922 | None |
| 14 | `DOC-1e016055aa435e71` | True | 0 | 47.7 | 9148 | 814 | None |
| 15 | `DOC-63beb09b179ea4ee` | True | 0 | 46.9 | 9374 | 859 | None |
| 16 | `DOC-169bbcdc5d9e609c` | True | 0 | 35.1 | 9975 | 832 | None |
| 17 | `DOC-fcaddb5bdc94ce63` | True | 0.058824 | 39.2 | 9123 | 878 | None |
| 18 | `DOC-03712a2b0a99a314` | True | 0 | 55.4 | 9286 | 1279 | None |
| 19 | `DOC-4ab4ecd86ecf275d` | False | — | 320.2 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9590, total_tokens=17782, completion_tokens_details=None, prompt_tokens_details=None) |
| 20 | `DOC-8fe2855a2310cdbe` | False | — | 258.9 | — | — | LengthFinishReasonError: Could not parse response content as the length limit was reached - CompletionUsage(completion_tokens=8192, prompt_tokens=9249, total_tokens=17441, completion_tokens_details=None, prompt_tokens_details=None) |
