# Run report — `sand42-50-corporate-records-specialist-awq-2l4-c16`

Dated cell stem: `RUN-50-CORPORATE-AWQ-2L4-C16`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-corporate-records-specialist-awq-2l4-c16` |
| task / agent | `corporate_records_specialist` |
| prompt | `corporate_records_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **16** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `7d4a833c7b5b92d4bba6419c2121b40b9e58a2f18b759fc882b7526be9ccbe73` |
| dataset fingerprint | `76b083c7c46d` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.487960** |
| schema_valid_rate | 0.960000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 58.447 |
| gpu_seconds | 58.676 |
| estimated GPU cost | 0.026078 |
| **GPU $/doc** | **0.00052156** |
| latency p50 / max (s) | 12.514542 / 25.570402 |
| prompt / completion tokens | 197319 / 8021 |
| concurrency speedup (Σlat/wall) | 11.43 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-732b812b7d9d9653` | True | 0.888900 | 8.4 | 5572 | 165 | None |
| 2 | `DOC-68d5a8753fcc3675` | True | 0.440500 | 8.4 | 5671 | 178 | None |
| 3 | `DOC-b3ad98e5530dfeaf` | True | 0.282000 | 5.2 | 2521 | 190 | None |
| 4 | `DOC-9376c6bfa6779d5e` | True | 0.482200 | 3.6 | 2200 | 131 | None |
| 5 | `DOC-020d77c0107d273d` | True | 0.474600 | 17.4 | 2302 | 116 | None |
| 6 | `DOC-91f89b9c0d285ac7` | True | 0.666700 | 17.5 | 6902 | 126 | None |
| 7 | `DOC-9ca44c7926a47ede` | True | 0.502400 | 17.5 | 2292 | 131 | None |
| 8 | `DOC-c4c9c37a96291975` | True | 0.081300 | 19.0 | 2424 | 136 | None |
| 9 | `DOC-0a262afc80c73247` | True | 0.113600 | 20.0 | 3124 | 143 | None |
| 10 | `DOC-a040ac19abb88fec` | True | 0.412100 | 20.3 | 2206 | 141 | None |
| 11 | `DOC-6790430ae2a6c724` | True | 0.184600 | 20.4 | 4477 | 142 | None |
| 12 | `DOC-fbcdd16e24f143ac` | True | 0.158200 | 20.4 | 2456 | 155 | None |
| 13 | `DOC-e545bbd5f5ea61b6` | True | 0.363600 | 20.5 | 2788 | 158 | None |
| 14 | `DOC-81ae205a3b0bf16f` | True | 0.248000 | 20.5 | 2515 | 158 | None |
| 15 | `DOC-12a6d4cd092cf66d` | True | 0.502600 | 21.9 | 7710 | 158 | None |
| 16 | `DOC-e077f1f7e80e1e04` | True | 0.162400 | 14.0 | 4043 | 151 | None |
| 17 | `DOC-f134b9491efc5c57` | True | 0.794900 | 6.6 | 2865 | 152 | None |
| 18 | `DOC-0f56fe8db6df01bd` | True | 0.063500 | 25.3 | 5368 | 161 | None |
| 19 | `DOC-01054efd0980066b` | True | 0.822200 | 25.3 | 5122 | 159 | None |
| 20 | `DOC-2819b889b134ea01` | True | 0.750000 | 25.6 | 5344 | 171 | None |
| 21 | `DOC-fc9f56d999bd7566` | True | 0.666700 | 8.1 | 2509 | 188 | None |
| 22 | `DOC-e478fa89043a29e3` | True | 0.820500 | 8.5 | 2910 | 151 | None |
| 23 | `DOC-d015968793450753` | True | 0.805600 | 8.6 | 5082 | 166 | None |
| 24 | `DOC-b832b5eaa2b4848c` | True | 0.106800 | 7.2 | 2762 | 158 | None |
| 25 | `DOC-bfa92eb6c72569ee` | True | 0.118400 | 7.4 | 3771 | 158 | None |
| 26 | `DOC-0a8eb16fff7e67ca` | True | 0.692300 | 6.5 | 5246 | 150 | None |
| 27 | `DOC-37152a33cfb70d37` | True | 0.410300 | 6.9 | 2902 | 160 | None |
| 28 | `DOC-2f19002c84083aa8` | True | 0.497800 | 16.4 | 5200 | 165 | None |
| 29 | `DOC-4dc719baa790a79c` | True | 0.666700 | 14.8 | 2669 | 163 | None |
| 30 | `DOC-204c3c7c0ba021cd` | True | 0.474600 | 11.2 | 2226 | 133 | None |
| 31 | `DOC-a5fd7fe18b094f20` | True | 0.848500 | 13.6 | 5919 | 145 | None |
| 32 | `DOC-474a0002b4c03be1` | True | 0.820500 | 13.8 | 2938 | 149 | None |
| 33 | `DOC-f21f3dadebb121e3` | True | 0.784300 | 8.8 | 3308 | 180 | None |
| 34 | `DOC-9467462d9bb34f8e` | True | 0.541700 | 18.2 | 5345 | 157 | None |
| 35 | `DOC-78f2456f571403a9` | True | 0.153100 | 7.4 | 2345 | 144 | None |
| 36 | `DOC-1e8e3ce47882ae71` | True | 0.148500 | 21.5 | 3063 | 198 | None |
| 37 | `DOC-2338d194d5250def` | True | 0.486700 | 6.2 | 5258 | 128 | None |
| 38 | `DOC-00193d0c070747e6` | True | 0.714300 | 14.9 | 3225 | 173 | None |
| 39 | `DOC-ffb48271e0a5e812` | True | 0.666700 | 11.8 | 5344 | 139 | None |
| 40 | `DOC-d4dfbfe8049d41f9` | True | 0.490700 | 8.2 | 3856 | 179 | None |
| 41 | `DOC-842215e36884da89` | True | 0.246700 | 6.7 | 5226 | 158 | None |
| 42 | `DOC-41b53ea487b84955` | True | 0.750000 | 21.3 | 4617 | 239 | None |
| 43 | `DOC-a973ebf005e0e785` | True | 0.427800 | 16.8 | 6146 | 234 | None |
| 44 | `DOC-80e90a37bb750a3c` | True | 0.165400 | 13.2 | 2776 | 201 | None |
| 45 | `DOC-e6906e59f9bd74ca` | True | 0.620000 | 10.5 | 2978 | 160 | None |
| 46 | `DOC-866139125545b36a` | True | 0.773300 | 10.1 | 5397 | 161 | None |
| 47 | `DOC-606242f2919653a4` | True | 0.233200 | 10.0 | 5253 | 160 | None |
| 48 | `DOC-d0aebe650be3e512` | True | 0.497600 | 6.1 | 2405 | 163 | None |
| 49 | `DOC-dfe42f3747f299e6` | True | 0.750000 | 9.9 | 5870 | 168 | None |
| 50 | `DOC-27bbad54b6fd107e` | True | 0.625000 | 5.7 | 2871 | 171 | None |
