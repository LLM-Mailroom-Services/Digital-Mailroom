# Run report — `sand40-100-correspondence-specialist-awq-2l4`

Dated cell stem: `RUN-100-CORRESPONDENCE-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand40-100-correspondence-specialist-awq-2l4` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **100** |
| profile | `modal-vllm` |
| spec_hash | `9aabe1bcab7b2cf3e3765b8223dca30209d3449a5d76465aabe509f9c9dd2c89` |
| dataset fingerprint | `046a2c9bfc4e` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **100 / 0 / 100** |
| **overall_extraction_score** | **0.341261** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 27.519 |
| gpu_seconds | 28.150 |
| estimated GPU cost | 0.012511 |
| **GPU $/doc** | **0.00012511** |
| latency p50 / max (s) | 10.299583 / 37.861527 |
| prompt / completion tokens | 277062 / 17014 |
| concurrency speedup (Σlat/wall) | 41.88 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-b5d016f4b2abaa39` | True | 0.333300 | 10.7 | 2234 | 104 | None |
| 2 | `DOC-1d5664e2c826ad07` | True | 0.388900 | 10.8 | 2216 | 104 | None |
| 3 | `DOC-c2826f69ed293da4` | True | 0.049400 | 10.8 | 2229 | 105 | None |
| 4 | `DOC-f36a37e1a9c1351e` | True | 0.083300 | 10.8 | 2238 | 104 | None |
| 5 | `DOC-f49b5cc25d9cb557` | True | 0.153500 | 10.8 | 2527 | 125 | None |
| 6 | `DOC-9ec94a2619e46dfb` | True | 0.400000 | 11.7 | 2273 | 143 | None |
| 7 | `DOC-553256644e7b4547` | True | 0.333300 | 11.9 | 2304 | 118 | None |
| 8 | `DOC-c71d3ca0b727a0d4` | True | 0.333300 | 12.2 | 2310 | 129 | None |
| 9 | `DOC-44b1e5a60b363d3e` | True | 0.333300 | 12.3 | 2527 | 127 | None |
| 10 | `DOC-02dc4ab50ea271a4` | True | 0.333300 | 12.7 | 2569 | 145 | None |
| 11 | `DOC-38c54645bf0e601a` | True | 0.370400 | 13.0 | 2556 | 132 | None |
| 12 | `DOC-c45ecc852b2cb0f4` | True | 0.666700 | 13.2 | 2354 | 157 | None |
| 13 | `DOC-0ab974301d63024f` | True | 0.500000 | 13.9 | 2283 | 132 | None |
| 14 | `DOC-228e51bba45b5c7d` | True | 0.258200 | 14.4 | 3037 | 175 | None |
| 15 | `DOC-ab94c5d183e5f7ca` | True | 0.106700 | 15.0 | 5331 | 157 | None |
| 16 | `DOC-fc6108235411ca8e` | True | 0.393900 | 15.2 | 2465 | 197 | None |
| 17 | `DOC-a318b50872273528` | True | 0.215200 | 15.2 | 2559 | 157 | None |
| 18 | `DOC-2aea82e94dba6438` | True | 0.204500 | 15.7 | 2442 | 165 | None |
| 19 | `DOC-383b9badb01a1a00` | True | 0.333300 | 16.2 | 4778 | 181 | None |
| 20 | `DOC-ba72bbffee783647` | True | 0.518500 | 16.2 | 2410 | 175 | None |
| 21 | `DOC-a763315b8f7cb96e` | True | 0.500000 | 16.7 | 2668 | 189 | None |
| 22 | `DOC-8754555168547e16` | True | 0.264100 | 16.8 | 3162 | 221 | None |
| 23 | `DOC-e72ff16f78525d0f` | True | 0.444400 | 17.0 | 2774 | 232 | None |
| 24 | `DOC-32b1660fb702fd84` | True | 0.111100 | 17.2 | 2689 | 239 | None |
| 25 | `DOC-31c068618dba65f3` | True | 0.333300 | 6.2 | 2344 | 108 | None |
| 26 | `DOC-2431095adda97989` | True | 0.175200 | 18.4 | 2606 | 269 | None |
| 27 | `DOC-e624b1b9823e53f5` | True | 0.542500 | 18.6 | 2917 | 217 | None |
| 28 | `DOC-9be315cbfa0fbd19` | True | 0.814800 | 19.0 | 4365 | 269 | None |
| 29 | `DOC-cb4f8fb4ccb52f44` | True | 0.333300 | 8.6 | 2270 | 118 | None |
| 30 | `DOC-eaeffa14c92e7cd8` | True | 0.381000 | 20.3 | 3043 | 160 | None |
| 31 | `DOC-314aa51db90c8c92` | True | 0.416700 | 9.8 | 3072 | 156 | None |
| 32 | `DOC-8eed243667c985bd` | True | 0.333300 | 8.3 | 2680 | 159 | None |
| 33 | `DOC-b0055813bc08a29c` | True | 0.055600 | 9.2 | 2593 | 143 | None |
| 34 | `DOC-9d0aa39a8ac68936` | True | 0.333300 | 4.8 | 2202 | 97 | None |
| 35 | `DOC-2bdbf0be591edea6` | True | 0.051300 | 6.9 | 2260 | 116 | None |
| 36 | `DOC-25958c023112a96e` | True | 0.666700 | 10.7 | 2242 | 155 | None |
| 37 | `DOC-4eb0e9385b81cc4b` | True | 0.228100 | 7.3 | 2315 | 138 | None |
| 38 | `DOC-99c7dacadccd6e78` | True | 0.508800 | 9.1 | 2327 | 138 | None |
| 39 | `DOC-c4debd478f2c06e0` | True | 0.511900 | 7.3 | 2467 | 137 | None |
| 40 | `DOC-bc3f4676ac0c2e16` | True | 0.333300 | 10.3 | 3889 | 169 | None |
| 41 | `DOC-522399c5514f180a` | True | 0.500000 | 10.1 | 2974 | 171 | None |
| 42 | `DOC-690cb07fef21747b` | True | 0.083300 | 8.2 | 2485 | 140 | None |
| 43 | `DOC-d3e421962da61b35` | True | 0.791700 | 7.2 | 2660 | 135 | None |
| 44 | `DOC-36b9a080db747f3d` | True | 0.066700 | 8.0 | 3389 | 147 | None |
| 45 | `DOC-91f5631a20c62dc5` | True | 0.354400 | 9.1 | 2453 | 168 | None |
| 46 | `DOC-379b182c302a6821` | True | 0.333300 | 8.0 | 2278 | 119 | None |
| 47 | `DOC-16dfd03aed14e557` | True | 0 | 4.7 | 2205 | 76 | None |
| 48 | `DOC-38265bcc6ecfecc3` | True | 0.121200 | 6.9 | 2260 | 109 | None |
| 49 | `DOC-556e41697352e63d` | True | 0.080000 | 12.1 | 2407 | 189 | None |
| 50 | `DOC-19d9fd70a08d306b` | True | 0.333300 | 15.7 | 2970 | 230 | None |
| 51 | `DOC-47647a5fdcd45666` | True | 0.333300 | 10.1 | 2447 | 143 | None |
| 52 | `DOC-84a9981be2435b55` | True | 0.428600 | 8.5 | 2378 | 120 | None |
| 53 | `DOC-cc6e6dece6a787c2` | True | 0.445200 | 10.3 | 2321 | 163 | None |
| 54 | `DOC-20b4e31d9a4bf994` | True | 0.284400 | 9.8 | 2386 | 123 | None |
| 55 | `DOC-cfe8e8e7b9b3f38d` | True | 0.333300 | 15.3 | 3159 | 234 | None |
| 56 | `DOC-4321eefceb0f4289` | True | 0.333300 | 8.3 | 2451 | 131 | None |
| 57 | `DOC-4ab559dfb4d79b6d` | True | 0.333300 | 9.8 | 2288 | 128 | None |
| 58 | `DOC-cd6877aeb3f2f7e4` | True | 0.156900 | 11.2 | 2794 | 147 | None |
| 59 | `DOC-8c312283e2533866` | True | 0.508800 | 29.7 | 2599 | 423 | None |
| 60 | `DOC-21460a9f6d7e6348` | True | 0.803900 | 7.7 | 2337 | 123 | None |
| 61 | `DOC-d0c241ea24439be2` | True | 0.510100 | 10.1 | 2324 | 111 | None |
| 62 | `DOC-f4b4c8c623ccb915` | True | 0.106700 | 31.3 | 4894 | 443 | None |
| 63 | `DOC-a7d76cec54e46f1f` | True | 0.163300 | 31.5 | 3364 | 454 | None |
| 64 | `DOC-9d65887887fe53d2` | True | 0.375000 | 10.4 | 2343 | 167 | None |
| 65 | `DOC-d3d85dc1b1514bec` | True | 0.538400 | 10.8 | 2444 | 169 | None |
| 66 | `DOC-6f05af738f455d50` | True | 0.132300 | 8.3 | 3319 | 135 | None |
| 67 | `DOC-9501118a02fe39b9` | True | 0.400200 | 9.8 | 2420 | 165 | None |
| 68 | `DOC-752a5e85c01ca6f0` | True | 0.393900 | 8.8 | 2397 | 144 | None |
| 69 | `DOC-edd0a288e32f0d3b` | True | 0.666700 | 10.6 | 2507 | 134 | None |
| 70 | `DOC-f6a9a00e53cc7973` | True | 0.333300 | 11.0 | 6379 | 144 | None |
| 71 | `DOC-341d347babb3a19f` | True | 0.222900 | 9.9 | 2427 | 143 | None |
| 72 | `DOC-2cde0c6d0c70b02b` | True | 0.078400 | 13.2 | 2737 | 180 | None |
| 73 | `DOC-8c7847bfbb91d578` | True | 0.333300 | 8.8 | 3255 | 134 | None |
| 74 | `DOC-5a424efe5df6ba6f` | True | 0.547100 | 10.4 | 4634 | 148 | None |
| 75 | `DOC-5adf644f3cb1d34e` | True | 0 | 5.1 | 2199 | 76 | None |
| 76 | `DOC-a8efd6e4c4d49aaf` | True | 0.219000 | 13.4 | 2471 | 176 | None |
| 77 | `DOC-9b2bc061621a56be` | True | 0.527800 | 12.0 | 2574 | 192 | None |
| 78 | `DOC-d6e2bbd8c5e394a4` | True | 0.809500 | 8.2 | 2263 | 126 | None |
| 79 | `DOC-c4074ed5b08f097e` | True | 0.382700 | 7.0 | 2255 | 128 | None |
| 80 | `DOC-1dcf4dfd5ec6defb` | True | 0.245700 | 25.0 | 3533 | 417 | None |
| 81 | `DOC-6aa30fb5a4e67d76` | True | 0.336200 | 10.6 | 3212 | 179 | None |
| 82 | `DOC-95a872ee4ff237d5` | True | 0.203400 | 5.9 | 2710 | 131 | None |
| 83 | `DOC-a6fff0ef0e406461` | True | 0.381000 | 8.6 | 2374 | 167 | None |
| 84 | `DOC-595ab9fc19465909` | True | 0.333300 | 8.7 | 2371 | 172 | None |
| 85 | `DOC-c00ffce3272be5fd` | True | 0.345800 | 9.2 | 2915 | 182 | None |
| 86 | `DOC-ff15276697cdfbb2` | True | 0.116200 | 8.1 | 2853 | 165 | None |
| 87 | `DOC-e25814bd08d418aa` | True | 0.246700 | 11.7 | 2553 | 211 | None |
| 88 | `DOC-f0e1241d461dd523` | True | 0.416700 | 6.9 | 2589 | 166 | None |
| 89 | `DOC-96438076efc6cc7b` | True | 0.333300 | 5.6 | 2309 | 144 | None |
| 90 | `DOC-c01ab1c1c673f355` | True | 0.506900 | 5.2 | 2394 | 124 | None |
| 91 | `DOC-17ac4251c7d94cea` | True | 0.121200 | 4.5 | 2261 | 112 | None |
| 92 | `DOC-76375ebb4cd91de9` | True | 0.111100 | 9.3 | 3047 | 196 | None |
| 93 | `DOC-1f3f868558fc4a6e` | True | 0.381000 | 4.6 | 2376 | 113 | None |
| 94 | `DOC-9422c8775b387935` | True | 0.800000 | 6.7 | 3119 | 157 | None |
| 95 | `DOC-8ce704cea54b1469` | True | 0.333300 | 7.7 | 3196 | 174 | None |
| 96 | `DOC-162babf552426b57` | True | 0.080000 | 6.1 | 2344 | 157 | None |
| 97 | `DOC-caaba1c5a3f9a41e` | True | 0.533300 | 37.9 | 3648 | 621 | None |
| 98 | `DOC-ee6bae4d269c1911` | True | 0.333300 | 12.0 | 3361 | 265 | None |
| 99 | `DOC-f7af031d61f7d7f5` | True | 0.333300 | 6.1 | 4498 | 158 | None |
| 100 | `DOC-5b63f9fe205d564b` | True | 0.621200 | 5.5 | 2425 | 153 | None |
