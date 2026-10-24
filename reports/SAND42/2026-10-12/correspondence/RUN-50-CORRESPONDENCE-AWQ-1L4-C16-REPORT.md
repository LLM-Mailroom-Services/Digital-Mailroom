# Run report — `sand42-50-correspondence-specialist-awq-1l4-c16`

Dated cell stem: `RUN-50-CORRESPONDENCE-AWQ-1L4-C16`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-correspondence-specialist-awq-1l4-c16` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **16** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `6424743b9c169c02a993c7a77cbdc619dbae92c306b6110ce54cfe559e89236b` |
| dataset fingerprint | `a00ba5dc0159` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.378846** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 47.200 |
| gpu_seconds | 47.464 |
| estimated GPU cost | 0.010548 |
| **GPU $/doc** | **0.00021096** |
| latency p50 / max (s) | 9.629865 / 17.194573 |
| prompt / completion tokens | 129444 / 7783 |
| concurrency speedup (Σlat/wall) | 10.33 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-c71d3ca0b727a0d4` | True | 0.333300 | 9.6 | 2310 | 128 | None |
| 2 | `DOC-1de496e8c9350155` | True | 0.369600 | 9.6 | 2314 | 131 | None |
| 3 | `DOC-3433644b29e318b3` | True | 0.496700 | 9.6 | 2311 | 123 | None |
| 4 | `DOC-fcab49d5955c76c0` | True | 0.060600 | 9.6 | 2332 | 136 | None |
| 5 | `DOC-2a7acfac00e67bac` | True | 0.027800 | 9.6 | 2256 | 120 | None |
| 6 | `DOC-a21b03af9a6afc21` | True | 0.736800 | 9.6 | 2412 | 118 | None |
| 7 | `DOC-bcc74152bde91996` | True | 0.809500 | 9.6 | 2211 | 121 | None |
| 8 | `DOC-3c85eb56a4145e0c` | True | 0.714300 | 9.6 | 2357 | 129 | None |
| 9 | `DOC-275198e372250586` | True | 0.158700 | 9.9 | 2880 | 150 | None |
| 10 | `DOC-8ca6802d3a0f5d1a` | True | 0.814800 | 9.9 | 3289 | 153 | None |
| 11 | `DOC-0dfd9710f2380220` | True | 0.205000 | 10.1 | 2367 | 156 | None |
| 12 | `DOC-d9937f535b7c22f3` | True | 0.333300 | 12.8 | 2447 | 170 | None |
| 13 | `DOC-af2b2b54e31214cc` | True | 0.363600 | 13.0 | 2822 | 177 | None |
| 14 | `DOC-b7f699fd18d0f80c` | True | 0.518500 | 13.3 | 2731 | 189 | None |
| 15 | `DOC-fc6108235411ca8e` | True | 0.060600 | 14.4 | 2465 | 198 | None |
| 16 | `DOC-3a21b2695c19d388` | True | 0.095200 | 14.5 | 2766 | 198 | None |
| 17 | `DOC-e7b6158bfb232964` | True | 0.500000 | 7.6 | 2246 | 115 | None |
| 18 | `DOC-ede2172372d1f296` | True | 0.111100 | 8.7 | 2282 | 140 | None |
| 19 | `DOC-8674660f9ccc8243` | True | 0.536200 | 8.5 | 2377 | 142 | None |
| 20 | `DOC-4fa7aa63b169fea8` | True | 0.333300 | 8.8 | 2523 | 147 | None |
| 21 | `DOC-4ea9a8cde42f450b` | True | 0.466700 | 8.8 | 2309 | 152 | None |
| 22 | `DOC-ba3217c0524a9577` | True | 0.333300 | 6.2 | 2368 | 124 | None |
| 23 | `DOC-5cdfee2b0ef0a218` | True | 0.536200 | 10.0 | 2263 | 156 | None |
| 24 | `DOC-38a7cb4be93dbecd` | True | 0.777800 | 11.0 | 2625 | 159 | None |
| 25 | `DOC-25958c023112a96e` | True | 0.666700 | 11.4 | 2242 | 172 | None |
| 26 | `DOC-b78953fa896bdeb9` | True | 0.608800 | 11.3 | 2441 | 174 | None |
| 27 | `DOC-5cef7d1205cc37d5` | True | 0.194500 | 9.0 | 2581 | 156 | None |
| 28 | `DOC-3fd5fb2e4b505b04` | True | 0.764700 | 10.2 | 2584 | 184 | None |
| 29 | `DOC-6bdc0c7c153547b6` | True | 0.745100 | 14.1 | 2480 | 225 | None |
| 30 | `DOC-9417d989cb45b287` | True | 0.055600 | 6.4 | 2212 | 89 | None |
| 31 | `DOC-8b2609c15d1d37af` | True | 0.428600 | 10.7 | 2604 | 204 | None |
| 32 | `DOC-bdf1d75db5874068` | True | 0.777800 | 17.2 | 2839 | 271 | None |
| 33 | `DOC-44dd971367dd458a` | True | 0.622200 | 7.2 | 2298 | 113 | None |
| 34 | `DOC-315b7ca63910e311` | True | 0.193900 | 12.5 | 2607 | 223 | None |
| 35 | `DOC-80c4ee15e95f8cc6` | True | 0.049400 | 10.3 | 2631 | 155 | None |
| 36 | `DOC-65c30d7452215c4b` | True | 0.133300 | 9.8 | 2272 | 131 | None |
| 37 | `DOC-fe0e62a4596a649b` | True | 0.060600 | 8.3 | 2255 | 132 | None |
| 38 | `DOC-aff14c55ba2c4d16` | True | 0.076900 | 10.1 | 3394 | 150 | None |
| 39 | `DOC-a7e5e24fade86aae` | True | 0.454500 | 10.9 | 3230 | 158 | None |
| 40 | `DOC-537e1f953940c39c` | True | 0.233300 | 11.3 | 2600 | 172 | None |
| 41 | `DOC-20dc95a39ec83250` | True | 0.191100 | 9.3 | 2422 | 167 | None |
| 42 | `DOC-90326221a1667d50` | True | 0.333300 | 8.5 | 3495 | 157 | None |
| 43 | `DOC-c4074ed5b08f097e` | True | 0.382700 | 6.9 | 2255 | 132 | None |
| 44 | `DOC-5feb4a34e13ce77a` | True | 0.100000 | 9.4 | 2415 | 180 | None |
| 45 | `DOC-f64e409a607594bb` | True | 0.176800 | 6.2 | 2264 | 120 | None |
| 46 | `DOC-6823b2f649cf1d0a` | True | 0.407400 | 6.6 | 4888 | 140 | None |
| 47 | `DOC-62d410af6bdd29f8` | True | 0.228600 | 8.4 | 2520 | 182 | None |
| 48 | `DOC-851611e86c9e36d0` | True | 0.514600 | 5.4 | 2806 | 141 | None |
| 49 | `DOC-f8fb6b01de0fc173` | True | 0.527800 | 5.4 | 3169 | 142 | None |
| 50 | `DOC-e1e0cc74e784a403` | True | 0.321200 | 6.2 | 2677 | 181 | None |
