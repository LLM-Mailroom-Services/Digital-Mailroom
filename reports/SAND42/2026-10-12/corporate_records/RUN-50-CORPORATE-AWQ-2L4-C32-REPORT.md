# Run report — `sand42-50-corporate-records-specialist-awq-2l4-c32`

Dated cell stem: `RUN-50-CORPORATE-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-corporate-records-specialist-awq-2l4-c32` |
| task / agent | `corporate_records_specialist` |
| prompt | `corporate_records_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `4c3e1631dfa8dc7584a9fccf13250c79f4a07bbdbf8cb9147a38a44b5784108a` |
| dataset fingerprint | `76b083c7c46d` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.500214** |
| schema_valid_rate | 0.960000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 48.923 |
| gpu_seconds | 49.356 |
| estimated GPU cost | 0.021936 |
| **GPU $/doc** | **0.00043872** |
| latency p50 / max (s) | 16.831071 / 33.250321 |
| prompt / completion tokens | 197319 / 7995 |
| concurrency speedup (Σlat/wall) | 19.30 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-91f89b9c0d285ac7` | True | 0.666700 | 16.0 | 6902 | 126 | None |
| 2 | `DOC-9ca44c7926a47ede` | True | 0.502400 | 16.0 | 2292 | 130 | None |
| 3 | `DOC-020d77c0107d273d` | True | 0.474600 | 16.0 | 2302 | 116 | None |
| 4 | `DOC-a5fd7fe18b094f20` | True | 0.848500 | 16.0 | 5919 | 145 | None |
| 5 | `DOC-204c3c7c0ba021cd` | True | 0.474600 | 16.1 | 2226 | 152 | None |
| 6 | `DOC-0a262afc80c73247` | True | 0.113600 | 16.3 | 3124 | 153 | None |
| 7 | `DOC-81ae205a3b0bf16f` | True | 0.581300 | 16.3 | 2515 | 153 | None |
| 8 | `DOC-2819b889b134ea01` | True | 0.750000 | 16.5 | 5344 | 151 | None |
| 9 | `DOC-9376c6bfa6779d5e` | True | 0.482200 | 17.4 | 2200 | 131 | None |
| 10 | `DOC-e077f1f7e80e1e04` | True | 0.162400 | 17.8 | 4043 | 153 | None |
| 11 | `DOC-c4c9c37a96291975` | True | 0.081300 | 18.9 | 2424 | 136 | None |
| 12 | `DOC-a040ac19abb88fec` | True | 0.409700 | 19.6 | 2206 | 141 | None |
| 13 | `DOC-474a0002b4c03be1` | True | 0.820500 | 19.7 | 2938 | 150 | None |
| 14 | `DOC-2f19002c84083aa8` | True | 0.497800 | 19.8 | 5200 | 165 | None |
| 15 | `DOC-732b812b7d9d9653` | True | 0.888900 | 20.2 | 5572 | 165 | None |
| 16 | `DOC-e478fa89043a29e3` | True | 0.820500 | 20.2 | 2910 | 151 | None |
| 17 | `DOC-12a6d4cd092cf66d` | True | 0.502600 | 21.3 | 7710 | 157 | None |
| 18 | `DOC-f134b9491efc5c57` | True | 0.794900 | 22.4 | 2865 | 152 | None |
| 19 | `DOC-0f56fe8db6df01bd` | True | 0.063500 | 22.8 | 5368 | 168 | None |
| 20 | `DOC-b3ad98e5530dfeaf` | True | 0.282000 | 22.6 | 2521 | 182 | None |
| 21 | `DOC-fbcdd16e24f143ac` | True | 0.158200 | 23.9 | 2456 | 155 | None |
| 22 | `DOC-e545bbd5f5ea61b6` | True | 0.697000 | 23.9 | 2788 | 157 | None |
| 23 | `DOC-01054efd0980066b` | True | 0.822200 | 24.2 | 5122 | 159 | None |
| 24 | `DOC-9467462d9bb34f8e` | True | 0.541700 | 25.5 | 5345 | 156 | None |
| 25 | `DOC-4dc719baa790a79c` | True | 0.725500 | 27.4 | 2669 | 170 | None |
| 26 | `DOC-68d5a8753fcc3675` | True | 0.440500 | 27.9 | 5671 | 177 | None |
| 27 | `DOC-fc9f56d999bd7566` | True | 0.666700 | 28.6 | 2509 | 196 | None |
| 28 | `DOC-e6906e59f9bd74ca` | True | 0.620000 | 11.1 | 2978 | 160 | None |
| 29 | `DOC-00193d0c070747e6` | True | 0.714300 | 13.1 | 3225 | 173 | None |
| 30 | `DOC-dfe42f3747f299e6` | True | 0.750000 | 8.9 | 5870 | 158 | None |
| 31 | `DOC-606242f2919653a4` | True | 0.233200 | 9.5 | 5253 | 165 | None |
| 32 | `DOC-f21f3dadebb121e3` | True | 0.784300 | 13.2 | 3308 | 180 | None |
| 33 | `DOC-80e90a37bb750a3c` | True | 0.149500 | 13.0 | 2776 | 181 | None |
| 34 | `DOC-27bbad54b6fd107e` | True | 0.833300 | 7.1 | 2871 | 169 | None |
| 35 | `DOC-866139125545b36a` | True | 0.773300 | 10.2 | 5397 | 180 | None |
| 36 | `DOC-41b53ea487b84955` | True | 0.750000 | 29.8 | 4617 | 228 | None |
| 37 | `DOC-b832b5eaa2b4848c` | True | 0.106800 | 30.3 | 2762 | 95 | None |
| 38 | `DOC-a973ebf005e0e785` | True | 0.427800 | 14.8 | 6146 | 234 | None |
| 39 | `DOC-6790430ae2a6c724` | True | 0.184600 | 31.5 | 4477 | 142 | None |
| 40 | `DOC-2338d194d5250def` | True | 0.486700 | 12.2 | 5258 | 128 | None |
| 41 | `DOC-d015968793450753` | True | 0.805600 | 32.0 | 5082 | 171 | None |
| 42 | `DOC-ffb48271e0a5e812` | True | 0.666700 | 16.1 | 5344 | 142 | None |
| 43 | `DOC-bfa92eb6c72569ee` | True | 0.118400 | 16.6 | 3771 | 158 | None |
| 44 | `DOC-0a8eb16fff7e67ca` | True | 0.359000 | 16.5 | 5246 | 159 | None |
| 45 | `DOC-78f2456f571403a9` | True | 0.180900 | 15.3 | 2345 | 154 | None |
| 46 | `DOC-37152a33cfb70d37` | True | 0.410300 | 17.0 | 2902 | 175 | None |
| 47 | `DOC-842215e36884da89` | True | 0.246700 | 12.9 | 5226 | 161 | None |
| 48 | `DOC-d0aebe650be3e512` | True | 0.497600 | 11.9 | 2405 | 163 | None |
| 49 | `DOC-d4dfbfe8049d41f9` | True | 0.493400 | 14.4 | 3856 | 174 | None |
| 50 | `DOC-1e8e3ce47882ae71` | True | 0.148500 | 33.3 | 3063 | 198 | None |
