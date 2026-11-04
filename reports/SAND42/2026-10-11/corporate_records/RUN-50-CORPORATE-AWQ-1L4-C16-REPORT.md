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
| **overall_extraction_score** | **0.483984** |
| schema_valid_rate | 0.960000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 41.691 |
| gpu_seconds | 42.007 |
| estimated GPU cost | 0.009335 |
| **GPU $/doc** | **0.0001867** |
| latency p50 / max (s) | 19.581422 / 31.462880 |
| prompt / completion tokens | 197319 / 8000 |
| concurrency speedup (Σlat/wall) | 22.34 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-91f89b9c0d285ac7` | True | 0.666700 | 19.6 | 6902 | 128 | None |
| 2 | `DOC-9ca44c7926a47ede` | True | 0.502400 | 19.6 | 2292 | 130 | None |
| 3 | `DOC-020d77c0107d273d` | True | 0.474600 | 19.6 | 2302 | 116 | None |
| 4 | `DOC-c4c9c37a96291975` | True | 0.081300 | 20.7 | 2424 | 136 | None |
| 5 | `DOC-a040ac19abb88fec` | True | 0.412100 | 21.3 | 2206 | 141 | None |
| 6 | `DOC-6790430ae2a6c724` | True | 0.184600 | 22.6 | 4477 | 142 | None |
| 7 | `DOC-e545bbd5f5ea61b6` | True | 0.363600 | 23.8 | 2788 | 154 | None |
| 8 | `DOC-12a6d4cd092cf66d` | True | 0.502600 | 23.8 | 7710 | 158 | None |
| 9 | `DOC-0a262afc80c73247` | True | 0.113600 | 23.9 | 3124 | 153 | None |
| 10 | `DOC-81ae205a3b0bf16f` | True | 0.248000 | 23.9 | 2515 | 158 | None |
| 11 | `DOC-01054efd0980066b` | True | 0.822200 | 23.9 | 5122 | 160 | None |
| 12 | `DOC-fbcdd16e24f143ac` | True | 0.158200 | 23.9 | 2456 | 155 | None |
| 13 | `DOC-2819b889b134ea01` | True | 0.750000 | 24.2 | 5344 | 169 | None |
| 14 | `DOC-732b812b7d9d9653` | True | 0.888900 | 24.2 | 5572 | 165 | None |
| 15 | `DOC-0f56fe8db6df01bd` | True | 0.063500 | 24.2 | 5368 | 161 | None |
| 16 | `DOC-68d5a8753fcc3675` | True | 0.440500 | 31.5 | 5671 | 177 | None |
| 17 | `DOC-b832b5eaa2b4848c` | True | 0.106800 | 10.6 | 2762 | 95 | None |
| 18 | `DOC-9376c6bfa6779d5e` | True | 0.482200 | 15.2 | 2200 | 131 | None |
| 19 | `DOC-f134b9491efc5c57` | True | 0.794900 | 13.8 | 2865 | 140 | None |
| 20 | `DOC-e077f1f7e80e1e04` | True | 0.162400 | 17.4 | 4043 | 151 | None |
| 21 | `DOC-2f19002c84083aa8` | True | 0.497800 | 16.9 | 5200 | 165 | None |
| 22 | `DOC-a5fd7fe18b094f20` | True | 0.757600 | 16.6 | 5919 | 143 | None |
| 23 | `DOC-474a0002b4c03be1` | True | 0.820500 | 16.7 | 2938 | 149 | None |
| 24 | `DOC-e478fa89043a29e3` | True | 0.820500 | 16.9 | 2910 | 151 | None |
| 25 | `DOC-b3ad98e5530dfeaf` | True | 0.282000 | 21.2 | 2521 | 182 | None |
| 26 | `DOC-9467462d9bb34f8e` | True | 0.541700 | 19.5 | 5345 | 158 | None |
| 27 | `DOC-d015968793450753` | True | 0.805600 | 19.8 | 5082 | 166 | None |
| 28 | `DOC-1e8e3ce47882ae71` | True | 0.148500 | 21.3 | 3063 | 198 | None |
| 29 | `DOC-204c3c7c0ba021cd` | True | 0.474600 | 13.8 | 2226 | 152 | None |
| 30 | `DOC-4dc719baa790a79c` | True | 0.666700 | 24.2 | 2669 | 193 | None |
| 31 | `DOC-fc9f56d999bd7566` | True | 0.666700 | 24.3 | 2509 | 196 | None |
| 32 | `DOC-41b53ea487b84955` | True | 0.750000 | 27.8 | 4617 | 228 | None |
| 33 | `DOC-bfa92eb6c72569ee` | True | 0.118400 | 20.1 | 3771 | 158 | None |
| 34 | `DOC-37152a33cfb70d37` | True | 0.410300 | 20.0 | 2902 | 161 | None |
| 35 | `DOC-00193d0c070747e6` | True | 0.714300 | 21.6 | 3225 | 181 | None |
| 36 | `DOC-ffb48271e0a5e812` | True | 0.666700 | 15.9 | 5344 | 141 | None |
| 37 | `DOC-0a8eb16fff7e67ca` | True | 0.359000 | 19.0 | 5246 | 159 | None |
| 38 | `DOC-78f2456f571403a9` | True | 0.153100 | 15.9 | 2345 | 144 | None |
| 39 | `DOC-2338d194d5250def` | True | 0.517000 | 12.0 | 5258 | 138 | None |
| 40 | `DOC-80e90a37bb750a3c` | True | 0.149500 | 16.7 | 2776 | 167 | None |
| 41 | `DOC-f21f3dadebb121e3` | True | 0.784300 | 17.2 | 3308 | 180 | None |
| 42 | `DOC-e6906e59f9bd74ca` | True | 0.620000 | 14.2 | 2978 | 160 | None |
| 43 | `DOC-d4dfbfe8049d41f9` | True | 0.493400 | 14.7 | 3856 | 175 | None |
| 44 | `DOC-866139125545b36a` | True | 0.773300 | 14.7 | 5397 | 179 | None |
| 45 | `DOC-842215e36884da89` | True | 0.246700 | 10.5 | 5226 | 158 | None |
| 46 | `DOC-606242f2919653a4` | True | 0.233200 | 10.7 | 5253 | 161 | None |
| 47 | `DOC-a973ebf005e0e785` | True | 0.427800 | 22.0 | 6146 | 234 | None |
| 48 | `DOC-dfe42f3747f299e6` | True | 0.750000 | 7.7 | 5870 | 158 | None |
| 49 | `DOC-d0aebe650be3e512` | True | 0.497600 | 5.7 | 2405 | 163 | None |
| 50 | `DOC-27bbad54b6fd107e` | True | 0.833300 | 6.2 | 2871 | 182 | None |
