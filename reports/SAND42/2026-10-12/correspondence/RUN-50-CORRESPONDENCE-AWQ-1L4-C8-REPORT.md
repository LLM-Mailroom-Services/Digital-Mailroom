# Run report — `sand42-50-correspondence-specialist-awq-1l4-c8`

Dated cell stem: `RUN-50-CORRESPONDENCE-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-correspondence-specialist-awq-1l4-c8` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `b0650f19a4c7b96a337163c44a5a36a5bc5fc41416cbf7bce8830a3d60207ceb` |
| dataset fingerprint | `a00ba5dc0159` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.388156** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 60.161 |
| gpu_seconds | 60.488 |
| estimated GPU cost | 0.013442 |
| **GPU $/doc** | **0.00026884** |
| latency p50 / max (s) | 6.732835 / 10.120394 |
| prompt / completion tokens | 129444 / 7664 |
| concurrency speedup (Σlat/wall) | 5.64 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-2a7acfac00e67bac` | True | 0.027800 | 6.9 | 2256 | 120 | None |
| 2 | `DOC-a21b03af9a6afc21` | True | 0.824600 | 6.9 | 2412 | 130 | None |
| 3 | `DOC-3c85eb56a4145e0c` | True | 0.714300 | 6.9 | 2357 | 129 | None |
| 4 | `DOC-fcab49d5955c76c0` | True | 0.060600 | 6.9 | 2332 | 136 | None |
| 5 | `DOC-0dfd9710f2380220` | True | 0.205000 | 8.7 | 2367 | 166 | None |
| 6 | `DOC-d9937f535b7c22f3` | True | 0.333300 | 8.9 | 2447 | 172 | None |
| 7 | `DOC-fc6108235411ca8e` | True | 0.060600 | 10.1 | 2465 | 198 | None |
| 8 | `DOC-3a21b2695c19d388` | True | 0.095200 | 10.1 | 2766 | 199 | None |
| 9 | `DOC-3433644b29e318b3` | True | 0.496700 | 6.0 | 2311 | 123 | None |
| 10 | `DOC-1de496e8c9350155` | True | 0.369600 | 6.2 | 2314 | 131 | None |
| 11 | `DOC-c71d3ca0b727a0d4` | True | 0.333300 | 5.3 | 2310 | 128 | None |
| 12 | `DOC-af2b2b54e31214cc` | True | 0.363600 | 7.8 | 2822 | 175 | None |
| 13 | `DOC-275198e372250586` | True | 0.158700 | 6.0 | 2880 | 150 | None |
| 14 | `DOC-bcc74152bde91996` | True | 0.809500 | 4.9 | 2211 | 121 | None |
| 15 | `DOC-b7f699fd18d0f80c` | True | 0.518500 | 8.4 | 2731 | 189 | None |
| 16 | `DOC-8ca6802d3a0f5d1a` | True | 0.814800 | 7.0 | 3289 | 163 | None |
| 17 | `DOC-5cdfee2b0ef0a218` | True | 0.536200 | 6.0 | 2263 | 146 | None |
| 18 | `DOC-e7b6158bfb232964` | True | 0.500000 | 4.1 | 2246 | 115 | None |
| 19 | `DOC-ede2172372d1f296` | True | 0.111100 | 5.8 | 2282 | 140 | None |
| 20 | `DOC-38a7cb4be93dbecd` | True | 0.777800 | 6.1 | 2625 | 159 | None |
| 21 | `DOC-bdf1d75db5874068` | True | 0.777800 | 6.6 | 2839 | 167 | None |
| 22 | `DOC-25958c023112a96e` | True | 0.666700 | 6.8 | 2242 | 172 | None |
| 23 | `DOC-6bdc0c7c153547b6` | True | 0.745100 | 8.8 | 2480 | 225 | None |
| 24 | `DOC-4fa7aa63b169fea8` | True | 0.333300 | 6.1 | 2523 | 143 | None |
| 25 | `DOC-8674660f9ccc8243` | True | 0.536200 | 6.0 | 2377 | 142 | None |
| 26 | `DOC-4ea9a8cde42f450b` | True | 0.466700 | 6.4 | 2309 | 152 | None |
| 27 | `DOC-ba3217c0524a9577` | True | 0.333300 | 5.7 | 2368 | 124 | None |
| 28 | `DOC-b78953fa896bdeb9` | True | 0.575400 | 7.1 | 2441 | 174 | None |
| 29 | `DOC-5cef7d1205cc37d5` | True | 0.472200 | 5.9 | 2581 | 137 | None |
| 30 | `DOC-3fd5fb2e4b505b04` | True | 0.764700 | 7.6 | 2584 | 174 | None |
| 31 | `DOC-315b7ca63910e311` | True | 0.193900 | 8.9 | 2607 | 210 | None |
| 32 | `DOC-9417d989cb45b287` | True | 0.055600 | 4.2 | 2212 | 89 | None |
| 33 | `DOC-8b2609c15d1d37af` | True | 0.428600 | 8.3 | 2604 | 204 | None |
| 34 | `DOC-80c4ee15e95f8cc6` | True | 0.049400 | 6.9 | 2631 | 152 | None |
| 35 | `DOC-65c30d7452215c4b` | True | 0.133300 | 5.5 | 2272 | 131 | None |
| 36 | `DOC-537e1f953940c39c` | True | 0.233300 | 8.5 | 2600 | 181 | None |
| 37 | `DOC-a7e5e24fade86aae` | True | 0.454500 | 7.3 | 3230 | 156 | None |
| 38 | `DOC-aff14c55ba2c4d16` | True | 0.076900 | 6.7 | 3394 | 150 | None |
| 39 | `DOC-44dd971367dd458a` | True | 0.900000 | 5.7 | 2298 | 130 | None |
| 40 | `DOC-fe0e62a4596a649b` | True | 0.060600 | 6.7 | 2255 | 132 | None |
| 41 | `DOC-20dc95a39ec83250` | True | 0.191100 | 7.9 | 2422 | 168 | None |
| 42 | `DOC-90326221a1667d50` | True | 0.333300 | 7.0 | 3495 | 152 | None |
| 43 | `DOC-c4074ed5b08f097e` | True | 0.382700 | 5.7 | 2255 | 128 | None |
| 44 | `DOC-5feb4a34e13ce77a` | True | 0.100000 | 8.6 | 2415 | 176 | None |
| 45 | `DOC-f64e409a607594bb` | True | 0.176800 | 6.1 | 2264 | 125 | None |
| 46 | `DOC-62d410af6bdd29f8` | True | 0.228600 | 8.0 | 2520 | 182 | None |
| 47 | `DOC-6823b2f649cf1d0a` | True | 0.407400 | 6.4 | 4888 | 142 | None |
| 48 | `DOC-851611e86c9e36d0` | True | 0.514600 | 5.2 | 2806 | 141 | None |
| 49 | `DOC-f8fb6b01de0fc173` | True | 0.527800 | 4.7 | 3169 | 142 | None |
| 50 | `DOC-e1e0cc74e784a403` | True | 0.176800 | 5.2 | 2677 | 173 | None |
