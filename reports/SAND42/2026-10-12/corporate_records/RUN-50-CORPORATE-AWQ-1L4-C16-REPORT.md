# Run report — `sand42-50-corporate-records-specialist-awq-1l4-c16`

Dated cell stem: `RUN-50-CORPORATE-AWQ-1L4-C16`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-corporate-records-specialist-awq-1l4-c16` |
| task / agent | `corporate_records_specialist` |
| prompt | `corporate_records_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **16** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `94320a5e877feebf05f31ede8c7846ed8f7e31aea5ddcceaa822f7cde5a2f5ec` |
| dataset fingerprint | `76b083c7c46d` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.494264** |
| schema_valid_rate | 0.960000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 76.489 |
| gpu_seconds | 76.955 |
| estimated GPU cost | 0.017101 |
| **GPU $/doc** | **0.00034202** |
| latency p50 / max (s) | 19.520060 / 32.010122 |
| prompt / completion tokens | 197319 / 8075 |
| concurrency speedup (Σlat/wall) | 12.46 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-020d77c0107d273d` | True | 0.474600 | 19.5 | 2302 | 116 | None |
| 2 | `DOC-9ca44c7926a47ede` | True | 0.502400 | 19.6 | 2292 | 130 | None |
| 3 | `DOC-c4c9c37a96291975` | True | 0.081300 | 19.9 | 2424 | 136 | None |
| 4 | `DOC-91f89b9c0d285ac7` | True | 0.666700 | 20.0 | 6902 | 126 | None |
| 5 | `DOC-0a262afc80c73247` | True | 0.113600 | 23.1 | 3124 | 147 | None |
| 6 | `DOC-a040ac19abb88fec` | True | 0.409700 | 23.1 | 2206 | 141 | None |
| 7 | `DOC-e545bbd5f5ea61b6` | True | 0.363600 | 23.1 | 2788 | 156 | None |
| 8 | `DOC-6790430ae2a6c724` | True | 0.184600 | 23.2 | 4477 | 143 | None |
| 9 | `DOC-0f56fe8db6df01bd` | True | 0.063500 | 23.3 | 5368 | 161 | None |
| 10 | `DOC-fbcdd16e24f143ac` | True | 0.158200 | 23.3 | 2456 | 155 | None |
| 11 | `DOC-12a6d4cd092cf66d` | True | 0.502600 | 23.5 | 7710 | 158 | None |
| 12 | `DOC-81ae205a3b0bf16f` | True | 0.248000 | 27.2 | 2515 | 158 | None |
| 13 | `DOC-732b812b7d9d9653` | True | 0.888900 | 27.3 | 5572 | 165 | None |
| 14 | `DOC-01054efd0980066b` | True | 0.822200 | 27.3 | 5122 | 158 | None |
| 15 | `DOC-2819b889b134ea01` | True | 0.750000 | 27.7 | 5344 | 171 | None |
| 16 | `DOC-68d5a8753fcc3675` | True | 0.440500 | 32.0 | 5671 | 189 | None |
| 17 | `DOC-9376c6bfa6779d5e` | True | 0.482200 | 14.8 | 2200 | 124 | None |
| 18 | `DOC-e077f1f7e80e1e04` | True | 0.162400 | 17.4 | 4043 | 160 | None |
| 19 | `DOC-f134b9491efc5c57` | True | 0.794900 | 14.1 | 2865 | 141 | None |
| 20 | `DOC-2f19002c84083aa8` | True | 0.495100 | 18.3 | 5200 | 170 | None |
| 21 | `DOC-474a0002b4c03be1` | True | 0.820500 | 15.2 | 2938 | 149 | None |
| 22 | `DOC-e478fa89043a29e3` | True | 0.820500 | 15.3 | 2910 | 151 | None |
| 23 | `DOC-a5fd7fe18b094f20` | True | 0.757600 | 13.6 | 5919 | 139 | None |
| 24 | `DOC-b3ad98e5530dfeaf` | True | 0.282000 | 23.4 | 2521 | 190 | None |
| 25 | `DOC-4dc719baa790a79c` | True | 0.666700 | 21.0 | 2669 | 170 | None |
| 26 | `DOC-d015968793450753` | True | 0.805600 | 20.8 | 5082 | 170 | None |
| 27 | `DOC-b832b5eaa2b4848c` | True | 0.106800 | 16.8 | 2762 | 157 | None |
| 28 | `DOC-9467462d9bb34f8e` | True | 0.541700 | 17.1 | 5345 | 158 | None |
| 29 | `DOC-204c3c7c0ba021cd` | True | 0.474600 | 15.3 | 2226 | 152 | None |
| 30 | `DOC-1e8e3ce47882ae71` | True | 0.148500 | 24.7 | 3063 | 198 | None |
| 31 | `DOC-fc9f56d999bd7566` | True | 0.666700 | 24.7 | 2509 | 196 | None |
| 32 | `DOC-41b53ea487b84955` | True | 0.750000 | 26.5 | 4617 | 239 | None |
| 33 | `DOC-bfa92eb6c72569ee` | True | 0.451800 | 19.3 | 3771 | 160 | None |
| 34 | `DOC-37152a33cfb70d37` | True | 0.410300 | 20.0 | 2902 | 161 | None |
| 35 | `DOC-ffb48271e0a5e812` | True | 0.666700 | 18.7 | 5344 | 144 | None |
| 36 | `DOC-00193d0c070747e6` | True | 0.714300 | 21.5 | 3225 | 181 | None |
| 37 | `DOC-0a8eb16fff7e67ca` | True | 0.692300 | 19.9 | 5246 | 165 | None |
| 38 | `DOC-78f2456f571403a9` | True | 0.153100 | 14.3 | 2345 | 144 | None |
| 39 | `DOC-2338d194d5250def` | True | 0.577700 | 11.4 | 5258 | 136 | None |
| 40 | `DOC-f21f3dadebb121e3` | True | 0.784300 | 18.1 | 3308 | 180 | None |
| 41 | `DOC-e6906e59f9bd74ca` | True | 0.620000 | 14.8 | 2978 | 160 | None |
| 42 | `DOC-80e90a37bb750a3c` | True | 0.149500 | 16.2 | 2776 | 183 | None |
| 43 | `DOC-606242f2919653a4` | True | 0.233200 | 11.9 | 5253 | 160 | None |
| 44 | `DOC-842215e36884da89` | True | 0.246700 | 12.0 | 5226 | 161 | None |
| 45 | `DOC-d4dfbfe8049d41f9` | True | 0.493400 | 15.3 | 3856 | 180 | None |
| 46 | `DOC-866139125545b36a` | True | 0.773300 | 15.3 | 5397 | 179 | None |
| 47 | `DOC-a973ebf005e0e785` | True | 0.427800 | 21.8 | 6146 | 212 | None |
| 48 | `DOC-dfe42f3747f299e6` | True | 0.750000 | 7.6 | 5870 | 161 | None |
| 49 | `DOC-d0aebe650be3e512` | True | 0.497600 | 7.3 | 2405 | 163 | None |
| 50 | `DOC-27bbad54b6fd107e` | True | 0.625000 | 5.4 | 2871 | 171 | None |
