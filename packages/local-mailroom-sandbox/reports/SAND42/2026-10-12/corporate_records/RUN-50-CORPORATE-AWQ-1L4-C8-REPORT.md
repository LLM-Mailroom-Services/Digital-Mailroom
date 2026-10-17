# Run report — `sand42-50-corporate-records-specialist-awq-1l4-c8`

Dated cell stem: `RUN-50-CORPORATE-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-corporate-records-specialist-awq-1l4-c8` |
| task / agent | `corporate_records_specialist` |
| prompt | `corporate_records_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `4640639b77be18b6b293e54690edaabb31ed4fe2709ff68e36bff59dd277e2ef` |
| dataset fingerprint | `76b083c7c46d` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.493254** |
| schema_valid_rate | 0.960000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 88.403 |
| gpu_seconds | 88.712 |
| estimated GPU cost | 0.019714 |
| **GPU $/doc** | **0.00039428** |
| latency p50 / max (s) | 11.231984 / 16.472906 |
| prompt / completion tokens | 197319 / 7968 |
| concurrency speedup (Σlat/wall) | 6.36 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-020d77c0107d273d` | True | 0.474600 | 10.5 | 2302 | 107 | None |
| 2 | `DOC-9ca44c7926a47ede` | True | 0.502400 | 10.8 | 2292 | 130 | None |
| 3 | `DOC-6790430ae2a6c724` | True | 0.184600 | 11.0 | 4477 | 142 | None |
| 4 | `DOC-fbcdd16e24f143ac` | True | 0.158200 | 13.8 | 2456 | 154 | None |
| 5 | `DOC-e545bbd5f5ea61b6` | True | 0.697000 | 13.9 | 2788 | 157 | None |
| 6 | `DOC-81ae205a3b0bf16f` | True | 0.248000 | 13.9 | 2515 | 158 | None |
| 7 | `DOC-01054efd0980066b` | True | 0.822200 | 14.1 | 5122 | 159 | None |
| 8 | `DOC-12a6d4cd092cf66d` | True | 0.502600 | 14.2 | 7710 | 158 | None |
| 9 | `DOC-91f89b9c0d285ac7` | True | 0.666700 | 12.1 | 6902 | 127 | None |
| 10 | `DOC-c4c9c37a96291975` | True | 0.081300 | 12.5 | 2424 | 136 | None |
| 11 | `DOC-0a262afc80c73247` | True | 0.113600 | 12.3 | 3124 | 143 | None |
| 12 | `DOC-a040ac19abb88fec` | True | 0.409700 | 11.3 | 2206 | 141 | None |
| 13 | `DOC-732b812b7d9d9653` | True | 0.888900 | 12.5 | 5572 | 157 | None |
| 14 | `DOC-0f56fe8db6df01bd` | True | 0.063500 | 13.3 | 5368 | 163 | None |
| 15 | `DOC-2819b889b134ea01` | True | 0.750000 | 14.5 | 5344 | 178 | None |
| 16 | `DOC-68d5a8753fcc3675` | True | 0.440500 | 14.3 | 5671 | 177 | None |
| 17 | `DOC-9376c6bfa6779d5e` | True | 0.482200 | 7.7 | 2200 | 131 | None |
| 18 | `DOC-e077f1f7e80e1e04` | True | 0.162400 | 9.3 | 4043 | 160 | None |
| 19 | `DOC-f134b9491efc5c57` | True | 0.794900 | 6.7 | 2865 | 140 | None |
| 20 | `DOC-b3ad98e5530dfeaf` | True | 0.282000 | 10.5 | 2521 | 190 | None |
| 21 | `DOC-2f19002c84083aa8` | True | 0.497800 | 8.6 | 5200 | 165 | None |
| 22 | `DOC-1e8e3ce47882ae71` | True | 0.148500 | 11.4 | 3063 | 198 | None |
| 23 | `DOC-4dc719baa790a79c` | True | 0.666700 | 10.1 | 2669 | 163 | None |
| 24 | `DOC-fc9f56d999bd7566` | True | 0.666700 | 12.8 | 2509 | 204 | None |
| 25 | `DOC-e478fa89043a29e3` | True | 0.820500 | 10.7 | 2910 | 151 | None |
| 26 | `DOC-474a0002b4c03be1` | True | 0.820500 | 11.2 | 2938 | 150 | None |
| 27 | `DOC-a5fd7fe18b094f20` | True | 0.848500 | 11.1 | 5919 | 142 | None |
| 28 | `DOC-b832b5eaa2b4848c` | True | 0.106800 | 6.2 | 2762 | 95 | None |
| 29 | `DOC-d015968793450753` | True | 0.722200 | 11.8 | 5082 | 159 | None |
| 30 | `DOC-9467462d9bb34f8e` | True | 0.541700 | 11.2 | 5345 | 158 | None |
| 31 | `DOC-41b53ea487b84955` | True | 0.750000 | 16.5 | 4617 | 233 | None |
| 32 | `DOC-204c3c7c0ba021cd` | True | 0.474600 | 11.1 | 2226 | 152 | None |
| 33 | `DOC-bfa92eb6c72569ee` | True | 0.118400 | 11.2 | 3771 | 158 | None |
| 34 | `DOC-00193d0c070747e6` | True | 0.714300 | 11.4 | 3225 | 173 | None |
| 35 | `DOC-37152a33cfb70d37` | True | 0.410300 | 10.3 | 2902 | 152 | None |
| 36 | `DOC-0a8eb16fff7e67ca` | True | 0.692300 | 11.2 | 5246 | 166 | None |
| 37 | `DOC-a973ebf005e0e785` | True | 0.427800 | 14.3 | 6146 | 210 | None |
| 38 | `DOC-ffb48271e0a5e812` | True | 0.666700 | 9.7 | 5344 | 149 | None |
| 39 | `DOC-78f2456f571403a9` | True | 0.153100 | 9.6 | 2345 | 144 | None |
| 40 | `DOC-f21f3dadebb121e3` | True | 0.784300 | 12.4 | 3308 | 180 | None |
| 41 | `DOC-80e90a37bb750a3c` | True | 0.149500 | 10.6 | 2776 | 167 | None |
| 42 | `DOC-e6906e59f9bd74ca` | True | 0.620000 | 12.8 | 2978 | 160 | None |
| 43 | `DOC-d4dfbfe8049d41f9` | True | 0.493400 | 13.2 | 3856 | 175 | None |
| 44 | `DOC-866139125545b36a` | True | 0.773300 | 12.6 | 5397 | 180 | None |
| 45 | `DOC-2338d194d5250def` | True | 0.517000 | 10.3 | 5258 | 143 | None |
| 46 | `DOC-606242f2919653a4` | True | 0.233200 | 10.6 | 5253 | 161 | None |
| 47 | `DOC-842215e36884da89` | True | 0.246700 | 8.3 | 5226 | 163 | None |
| 48 | `DOC-d0aebe650be3e512` | True | 0.497600 | 7.9 | 2405 | 163 | None |
| 49 | `DOC-dfe42f3747f299e6` | True | 0.750000 | 8.4 | 5870 | 167 | None |
| 50 | `DOC-27bbad54b6fd107e` | True | 0.625000 | 5.3 | 2871 | 179 | None |
