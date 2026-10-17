# Run report — `sand42-50-correspondence-specialist-awq-2l4-c16`

Dated cell stem: `RUN-50-CORRESPONDENCE-AWQ-2L4-C16`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand42-50-correspondence-specialist-awq-2l4-c16` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **16** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `49141e5933d1dbdec8fd77c63445503cf515eb2661ca18846c10616d49e352f5` |
| dataset fingerprint | `a00ba5dc0159` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.389918** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 40.760 |
| gpu_seconds | 41.075 |
| estimated GPU cost | 0.018256 |
| **GPU $/doc** | **0.00036512** |
| latency p50 / max (s) | 6.899983 / 13.466672 |
| prompt / completion tokens | 129444 / 7845 |
| concurrency speedup (Σlat/wall) | 9.62 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-bcc74152bde91996` | True | 0.809500 | 4.7 | 2211 | 121 | None |
| 2 | `DOC-2a7acfac00e67bac` | True | 0.027800 | 10.0 | 2256 | 120 | None |
| 3 | `DOC-3433644b29e318b3` | True | 0.496700 | 10.0 | 2311 | 123 | None |
| 4 | `DOC-c71d3ca0b727a0d4` | True | 0.333300 | 10.2 | 2310 | 128 | None |
| 5 | `DOC-a21b03af9a6afc21` | True | 0.824600 | 10.2 | 2412 | 130 | None |
| 6 | `DOC-3c85eb56a4145e0c` | True | 0.714300 | 10.3 | 2357 | 134 | None |
| 7 | `DOC-6bdc0c7c153547b6` | True | 0.614700 | 5.7 | 2480 | 224 | None |
| 8 | `DOC-fcab49d5955c76c0` | True | 0.060600 | 10.6 | 2332 | 136 | None |
| 9 | `DOC-275198e372250586` | True | 0.158700 | 11.6 | 2880 | 151 | None |
| 10 | `DOC-8ca6802d3a0f5d1a` | True | 0.814800 | 11.7 | 3289 | 153 | None |
| 11 | `DOC-1de496e8c9350155` | True | 0.369600 | 11.8 | 2314 | 153 | None |
| 12 | `DOC-0dfd9710f2380220` | True | 0.205000 | 12.3 | 2367 | 169 | None |
| 13 | `DOC-d9937f535b7c22f3` | True | 0.333300 | 12.5 | 2447 | 173 | None |
| 14 | `DOC-b7f699fd18d0f80c` | True | 0.518500 | 13.2 | 2731 | 189 | None |
| 15 | `DOC-fc6108235411ca8e` | True | 0.060600 | 13.3 | 2465 | 198 | None |
| 16 | `DOC-3a21b2695c19d388` | True | 0.095200 | 13.4 | 2766 | 199 | None |
| 17 | `DOC-af2b2b54e31214cc` | True | 0.363600 | 13.5 | 2822 | 202 | None |
| 18 | `DOC-e7b6158bfb232964` | True | 0.500000 | 4.8 | 2246 | 115 | None |
| 19 | `DOC-ede2172372d1f296` | True | 0.111100 | 5.6 | 2282 | 140 | None |
| 20 | `DOC-4fa7aa63b169fea8` | True | 0.333300 | 5.3 | 2523 | 142 | None |
| 21 | `DOC-5cdfee2b0ef0a218` | True | 0.536200 | 6.4 | 2263 | 156 | None |
| 22 | `DOC-8674660f9ccc8243` | True | 0.536200 | 5.3 | 2377 | 142 | None |
| 23 | `DOC-bdf1d75db5874068` | True | 0.777800 | 6.8 | 2839 | 167 | None |
| 24 | `DOC-25958c023112a96e` | True | 0.666700 | 6.9 | 2242 | 172 | None |
| 25 | `DOC-ba3217c0524a9577` | True | 0.666700 | 4.8 | 2368 | 132 | None |
| 26 | `DOC-4ea9a8cde42f450b` | True | 0.466700 | 6.2 | 2309 | 152 | None |
| 27 | `DOC-5cef7d1205cc37d5` | True | 0.194500 | 6.2 | 2581 | 150 | None |
| 28 | `DOC-b78953fa896bdeb9` | True | 0.575400 | 6.9 | 2441 | 172 | None |
| 29 | `DOC-38a7cb4be93dbecd` | True | 0.740700 | 8.8 | 2625 | 231 | None |
| 30 | `DOC-9417d989cb45b287` | True | 0.055600 | 3.8 | 2212 | 89 | None |
| 31 | `DOC-3fd5fb2e4b505b04` | True | 0.764700 | 6.9 | 2584 | 184 | None |
| 32 | `DOC-80c4ee15e95f8cc6` | True | 0.049400 | 7.0 | 2631 | 166 | None |
| 33 | `DOC-8b2609c15d1d37af` | True | 0.428600 | 7.4 | 2604 | 204 | None |
| 34 | `DOC-44dd971367dd458a` | True | 0.622200 | 4.5 | 2298 | 113 | None |
| 35 | `DOC-a7e5e24fade86aae` | True | 0.454500 | 6.4 | 3230 | 158 | None |
| 36 | `DOC-315b7ca63910e311` | True | 0.193900 | 10.2 | 2607 | 223 | None |
| 37 | `DOC-65c30d7452215c4b` | True | 0.133300 | 7.1 | 2272 | 131 | None |
| 38 | `DOC-f64e409a607594bb` | True | 0.176800 | 3.8 | 2264 | 104 | None |
| 39 | `DOC-537e1f953940c39c` | True | 0.233300 | 8.7 | 2600 | 181 | None |
| 40 | `DOC-fe0e62a4596a649b` | True | 0.060600 | 6.9 | 2255 | 132 | None |
| 41 | `DOC-5feb4a34e13ce77a` | True | 0.100000 | 6.3 | 2415 | 182 | None |
| 42 | `DOC-aff14c55ba2c4d16` | True | 0.076900 | 7.4 | 3394 | 148 | None |
| 43 | `DOC-62d410af6bdd29f8` | True | 0.228600 | 6.1 | 2520 | 182 | None |
| 44 | `DOC-c4074ed5b08f097e` | True | 0.382700 | 5.6 | 2255 | 132 | None |
| 45 | `DOC-20dc95a39ec83250` | True | 0.191100 | 7.7 | 2422 | 167 | None |
| 46 | `DOC-851611e86c9e36d0` | True | 0.514600 | 4.5 | 2806 | 141 | None |
| 47 | `DOC-90326221a1667d50` | True | 0.333300 | 6.6 | 3495 | 153 | None |
| 48 | `DOC-6823b2f649cf1d0a` | True | 0.407400 | 5.8 | 4888 | 144 | None |
| 49 | `DOC-f8fb6b01de0fc173` | True | 0.861100 | 5.3 | 3169 | 156 | None |
| 50 | `DOC-e1e0cc74e784a403` | True | 0.321200 | 5.1 | 2677 | 181 | None |
