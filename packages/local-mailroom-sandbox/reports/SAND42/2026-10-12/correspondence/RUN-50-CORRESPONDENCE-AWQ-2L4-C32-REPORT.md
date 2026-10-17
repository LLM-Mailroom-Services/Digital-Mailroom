# Run report — `sand42-50-correspondence-specialist-awq-2l4-c32`

Dated cell stem: `RUN-50-CORRESPONDENCE-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-correspondence-specialist-awq-2l4-c32` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `6309643e22df187b496a257b0042a8e592ac73b485b57b53480b986af4503580` |
| dataset fingerprint | `a00ba5dc0159` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.373316** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 37.657 |
| gpu_seconds | 37.986 |
| estimated GPU cost | 0.016883 |
| **GPU $/doc** | **0.00033766** |
| latency p50 / max (s) | 10.686197 / 20.445487 |
| prompt / completion tokens | 129444 / 7767 |
| concurrency speedup (Σlat/wall) | 14.63 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-2a7acfac00e67bac` | True | 0.027800 | 8.3 | 2256 | 120 | None |
| 2 | `DOC-3433644b29e318b3` | True | 0.496700 | 8.3 | 2311 | 123 | None |
| 3 | `DOC-25958c023112a96e` | True | 0.333300 | 8.1 | 2242 | 125 | None |
| 4 | `DOC-1de496e8c9350155` | True | 0.369600 | 8.3 | 2314 | 131 | None |
| 5 | `DOC-a21b03af9a6afc21` | True | 0.824600 | 8.3 | 2412 | 130 | None |
| 6 | `DOC-fcab49d5955c76c0` | True | 0.060600 | 8.4 | 2332 | 136 | None |
| 7 | `DOC-ede2172372d1f296` | True | 0.111100 | 8.2 | 2282 | 140 | None |
| 8 | `DOC-4fa7aa63b169fea8` | True | 0.333300 | 8.3 | 2523 | 142 | None |
| 9 | `DOC-8ca6802d3a0f5d1a` | True | 0.814800 | 9.3 | 3289 | 163 | None |
| 10 | `DOC-0dfd9710f2380220` | True | 0.205000 | 9.5 | 2367 | 169 | None |
| 11 | `DOC-b7f699fd18d0f80c` | True | 0.518500 | 9.8 | 2731 | 179 | None |
| 12 | `DOC-e7b6158bfb232964` | True | 0.500000 | 10.2 | 2246 | 117 | None |
| 13 | `DOC-ba3217c0524a9577` | True | 0.333300 | 10.6 | 2368 | 124 | None |
| 14 | `DOC-5cef7d1205cc37d5` | True | 0.234100 | 11.2 | 2581 | 141 | None |
| 15 | `DOC-8674660f9ccc8243` | True | 0.536200 | 11.3 | 2377 | 142 | None |
| 16 | `DOC-6bdc0c7c153547b6` | True | 0.745100 | 11.5 | 2480 | 225 | None |
| 17 | `DOC-3c85eb56a4145e0c` | True | 0.714300 | 11.8 | 2357 | 138 | None |
| 18 | `DOC-5cdfee2b0ef0a218` | True | 0.536200 | 12.1 | 2263 | 146 | None |
| 19 | `DOC-275198e372250586` | True | 0.158700 | 13.0 | 2880 | 150 | None |
| 20 | `DOC-4ea9a8cde42f450b` | True | 0.466700 | 13.8 | 2309 | 160 | None |
| 21 | `DOC-b78953fa896bdeb9` | True | 0.575400 | 14.1 | 2441 | 169 | None |
| 22 | `DOC-af2b2b54e31214cc` | True | 0.363600 | 14.7 | 2822 | 177 | None |
| 23 | `DOC-65c30d7452215c4b` | True | 0.133300 | 6.4 | 2272 | 132 | None |
| 24 | `DOC-fe0e62a4596a649b` | True | 0.060600 | 6.2 | 2255 | 132 | None |
| 25 | `DOC-d9937f535b7c22f3` | True | 0.333300 | 14.8 | 2447 | 173 | None |
| 26 | `DOC-bdf1d75db5874068` | True | 0.777800 | 14.5 | 2839 | 287 | None |
| 27 | `DOC-38a7cb4be93dbecd` | True | 0.740700 | 15.0 | 2625 | 178 | None |
| 28 | `DOC-3fd5fb2e4b505b04` | True | 0.764700 | 15.5 | 2584 | 184 | None |
| 29 | `DOC-c4074ed5b08f097e` | True | 0.382700 | 5.4 | 2255 | 132 | None |
| 30 | `DOC-90326221a1667d50` | True | 0.333300 | 6.5 | 3495 | 153 | None |
| 31 | `DOC-3a21b2695c19d388` | True | 0.095200 | 16.3 | 2766 | 199 | None |
| 32 | `DOC-20dc95a39ec83250` | True | 0.191100 | 6.9 | 2422 | 168 | None |
| 33 | `DOC-fc6108235411ca8e` | True | 0.060600 | 16.7 | 2465 | 198 | None |
| 34 | `DOC-6823b2f649cf1d0a` | True | 0.407400 | 5.5 | 4888 | 143 | None |
| 35 | `DOC-f8fb6b01de0fc173` | True | 0.527800 | 5.2 | 3169 | 142 | None |
| 36 | `DOC-315b7ca63910e311` | True | 0.193900 | 17.0 | 2607 | 214 | None |
| 37 | `DOC-9417d989cb45b287` | True | 0.055600 | 9.3 | 2212 | 89 | None |
| 38 | `DOC-bcc74152bde91996` | True | 0.809500 | 17.9 | 2211 | 121 | None |
| 39 | `DOC-c71d3ca0b727a0d4` | True | 0.333300 | 18.0 | 2310 | 128 | None |
| 40 | `DOC-f64e409a607594bb` | True | 0.176800 | 7.8 | 2264 | 108 | None |
| 41 | `DOC-44dd971367dd458a` | True | 0.622200 | 10.8 | 2298 | 113 | None |
| 42 | `DOC-aff14c55ba2c4d16` | True | 0.076900 | 11.1 | 3394 | 150 | None |
| 43 | `DOC-80c4ee15e95f8cc6` | True | 0.049400 | 11.3 | 2631 | 160 | None |
| 44 | `DOC-a7e5e24fade86aae` | True | 0.454500 | 11.3 | 3230 | 152 | None |
| 45 | `DOC-851611e86c9e36d0` | True | 0.514600 | 8.6 | 2806 | 141 | None |
| 46 | `DOC-537e1f953940c39c` | True | 0.233300 | 12.3 | 2600 | 181 | None |
| 47 | `DOC-8b2609c15d1d37af` | True | 0.428600 | 20.4 | 2604 | 204 | None |
| 48 | `DOC-5feb4a34e13ce77a` | True | 0.100000 | 11.3 | 2415 | 176 | None |
| 49 | `DOC-62d410af6bdd29f8` | True | 0.228600 | 10.5 | 2520 | 181 | None |
| 50 | `DOC-e1e0cc74e784a403` | True | 0.321200 | 9.1 | 2677 | 181 | None |
