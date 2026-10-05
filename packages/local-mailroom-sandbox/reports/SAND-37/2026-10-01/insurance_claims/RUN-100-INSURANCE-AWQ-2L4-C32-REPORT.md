# Run report — `sand40-100-insurance-claims-specialist-awq-2l4`

Dated cell stem: `RUN-100-INSURANCE-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand40-100-insurance-claims-specialist-awq-2l4` |
| task / agent | `insurance_claims_specialist` |
| prompt | `insurance_claims_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **100** |
| profile | `modal-vllm` |
| spec_hash | `a21e118a35b8a7903077cee32a6e3bfdcb0d12446c21762236b3c24e8c100317` |
| dataset fingerprint | `d78a97b685ab` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **100 / 0 / 100** |
| **overall_extraction_score** | **0.671539** |
| schema_valid_rate | 0.230000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 81.502 |
| gpu_seconds | 81.791 |
| estimated GPU cost | 0.036352 |
| **GPU $/doc** | **0.00036352** |
| latency p50 / max (s) | 20.420715 / 58.460930 |
| prompt / completion tokens | 327213 / 41631 |
| concurrency speedup (Σlat/wall) | 27.07 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-8cf0d471d8ec695d` | True | 0.796700 | 15.5 | 2830 | 343 | None |
| 2 | `DOC-fa698a867428a0ed` | True | 0.638700 | 15.3 | 3016 | 341 | None |
| 3 | `DOC-edc5811634a19b7a` | True | 0.805600 | 15.5 | 2835 | 341 | None |
| 4 | `DOC-dcb4333f78bfe249` | True | 0.636300 | 15.5 | 2934 | 338 | None |
| 5 | `DOC-28295fb236ac02ca` | True | 0.634100 | 15.3 | 2959 | 331 | None |
| 6 | `DOC-884dc887726dcfa5` | True | 0.737500 | 15.5 | 2833 | 350 | None |
| 7 | `DOC-4fd4cf5db3cfdb47` | True | 0.630900 | 15.6 | 2940 | 359 | None |
| 8 | `DOC-b1fad3c1c6ab0f6a` | True | 0.644200 | 15.7 | 2949 | 358 | None |
| 9 | `DOC-e818dc7448fea142` | True | 0.800000 | 15.7 | 2835 | 357 | None |
| 10 | `DOC-3ddb0ec69ce4f93f` | True | 0.648700 | 15.7 | 2949 | 361 | None |
| 11 | `DOC-8dcc97d49f2004f5` | True | 0.790800 | 17.3 | 2835 | 311 | None |
| 12 | `DOC-89dbe9bbd1ae3838` | True | 0.644200 | 17.6 | 2972 | 366 | None |
| 13 | `DOC-ee3512878a0003b7` | True | 0.793000 | 18.2 | 2831 | 332 | None |
| 14 | `DOC-2d2ec2092b012662` | True | 0.800000 | 18.9 | 2831 | 340 | None |
| 15 | `DOC-e7bc347246615526` | True | 0.629800 | 18.8 | 2949 | 338 | None |
| 16 | `DOC-c89c9134db9e8f1e` | True | 0.639800 | 19.6 | 3002 | 344 | None |
| 17 | `DOC-1e95a2ae82adc61c` | True | 0.681700 | 19.8 | 3143 | 392 | None |
| 18 | `DOC-c0e145a5a0a0d4bd` | True | 0.793000 | 20.3 | 2833 | 342 | None |
| 19 | `DOC-2d574972cb7a2f63` | True | 0.639600 | 20.6 | 2980 | 350 | None |
| 20 | `DOC-bce319dabbc42e89` | True | 0.799100 | 21.0 | 2831 | 350 | None |
| 21 | `DOC-4cd6ca1171e8885e` | True | 0.772900 | 21.5 | 2832 | 355 | None |
| 22 | `DOC-9f75d0ce11867685` | True | 0.634500 | 21.4 | 3044 | 352 | None |
| 23 | `DOC-d5e1b8ed3350fb36` | True | 0.629000 | 22.3 | 2969 | 363 | None |
| 24 | `DOC-d3d2943dbe2d4ef9` | True | 0.636800 | 23.0 | 2991 | 369 | None |
| 25 | `DOC-4dda6e74e78edd70` | True | 0.642800 | 23.3 | 2949 | 375 | None |
| 26 | `DOC-85e8bca0769880bf` | True | 0.697800 | 24.2 | 3141 | 389 | None |
| 27 | `DOC-a1a2afde18ded42d` | True | 0.688500 | 24.8 | 3086 | 399 | None |
| 28 | `DOC-576c9233159914e3` | True | 0.682500 | 26.5 | 3080 | 448 | None |
| 29 | `DOC-e0c3e056397d7806` | True | 0.637500 | 12.7 | 2812 | 278 | None |
| 30 | `DOC-b3be1f4b2b6142ed` | True | 0.695500 | 14.7 | 2815 | 289 | None |
| 31 | `DOC-63692b8a349be3ad` | True | 0.623700 | 12.7 | 2808 | 294 | None |
| 32 | `DOC-89fc7bbb8ccef92c` | True | 0.713300 | 15.6 | 3052 | 306 | None |
| 33 | `DOC-ed19a2628827f390` | True | 0.702900 | 12.3 | 2811 | 298 | None |
| 34 | `DOC-c0d9bf1e6be4ad51` | True | 0.701500 | 16.5 | 2808 | 314 | None |
| 35 | `DOC-df5ebe3e7263b6c6` | True | 0.705100 | 12.1 | 2815 | 286 | None |
| 36 | `DOC-4d04bd1e2f23c81b` | True | 0.713200 | 12.8 | 2799 | 299 | None |
| 37 | `DOC-1898a0fbb779070c` | True | 0.684200 | 17.4 | 3068 | 340 | None |
| 38 | `DOC-0ed0eb663781836b` | True | 0.696900 | 15.6 | 2806 | 280 | None |
| 39 | `DOC-7eb9512b93dd2f13` | True | 0.615400 | 18.2 | 2807 | 290 | None |
| 40 | `DOC-826b2ac305c2b791` | True | 0.695500 | 12.4 | 2810 | 283 | None |
| 41 | `DOC-db1d2b3ea4d2d24f` | True | 0.741700 | 14.0 | 2804 | 281 | None |
| 42 | `DOC-a0be2aba09a3f580` | True | 0.691300 | 19.1 | 3095 | 362 | None |
| 43 | `DOC-21ffbe92b56f949c` | True | 0.682100 | 13.9 | 2806 | 277 | None |
| 44 | `DOC-d6d57b7a18431923` | True | 0.695900 | 13.5 | 2803 | 276 | None |
| 45 | `DOC-b6993f654cb64a38` | True | 0.682100 | 13.4 | 2810 | 290 | None |
| 46 | `DOC-7a128ee6e786bd0e` | True | 0.702400 | 20.0 | 2808 | 303 | None |
| 47 | `DOC-596b1f881ecf4a8a` | True | 0.649600 | 17.0 | 2806 | 297 | None |
| 48 | `DOC-b28fe495a873ca59` | True | 0.689500 | 16.8 | 2807 | 300 | None |
| 49 | `DOC-35939293b668a1b0` | True | 0.689500 | 14.1 | 2808 | 270 | None |
| 50 | `DOC-e572745d557c7fbf` | True | 0.689400 | 22.0 | 3125 | 413 | None |
| 51 | `DOC-89236fcc6aa82a3d` | True | 0.800000 | 37.6 | 2834 | 352 | None |
| 52 | `DOC-bf5c2cc12aca8aad` | True | 0.793500 | 38.4 | 2834 | 345 | None |
| 53 | `DOC-dc33a3e5a8cf5b6b` | True | 0.801200 | 38.5 | 2832 | 345 | None |
| 54 | `DOC-17abdc452037b6eb` | True | 0.704100 | 23.3 | 3129 | 433 | None |
| 55 | `DOC-aacaf03452045b89` | True | 0.613100 | 17.8 | 2981 | 385 | None |
| 56 | `DOC-85e24caa52979f50` | True | 0.683600 | 26.1 | 3121 | 377 | None |
| 57 | `DOC-8bb9c14eb11704f2` | True | 0.622000 | 19.9 | 3003 | 365 | None |
| 58 | `DOC-c7f433bb70f6ab0e` | True | 0.615200 | 19.5 | 2986 | 331 | None |
| 59 | `DOC-1bc5f212af3bd4c2` | True | 0.645400 | 21.5 | 2990 | 439 | None |
| 60 | `DOC-2435c398b95844bc` | True | 0.679500 | 47.9 | 3080 | 485 | None |
| 61 | `DOC-c6339c641d801de5` | True | 0.615200 | 16.6 | 3023 | 312 | None |
| 62 | `DOC-79244cf752911808` | True | 0.617600 | 17.9 | 2969 | 331 | None |
| 63 | `DOC-4348717727f6d6b4` | True | 0.645600 | 20.8 | 3004 | 391 | None |
| 64 | `DOC-fc5aa23171d955cf` | True | 0.626500 | 19.9 | 2972 | 372 | None |
| 65 | `DOC-ab3b194998a42322` | True | 0.613100 | 21.9 | 3016 | 378 | None |
| 66 | `DOC-a0c5db2835e31ef6` | True | 0.601000 | 18.6 | 2871 | 334 | None |
| 67 | `DOC-d52f175e739a5f5f` | True | 0.626500 | 22.7 | 2974 | 325 | None |
| 68 | `DOC-1f15cce85d6c9f8f` | True | 0.613800 | 22.2 | 3012 | 373 | None |
| 69 | `DOC-13597dd5f0ca00c4` | True | 0.579600 | 20.6 | 2888 | 345 | None |
| 70 | `DOC-01f1577c446c646d` | True | 0.599300 | 21.8 | 2868 | 330 | None |
| 71 | `DOC-f80fe4950664c6e0` | True | 0.591000 | 20.1 | 2884 | 344 | None |
| 72 | `DOC-0596b6ff5f3f7028` | True | 0.595700 | 21.7 | 2912 | 375 | None |
| 73 | `DOC-56b5ff2db7cab57f` | True | 0.610500 | 23.5 | 3019 | 411 | None |
| 74 | `DOC-4e21681f375a247d` | True | 0.641100 | 24.8 | 2985 | 347 | None |
| 75 | `DOC-fa4420dfb29b9410` | True | 0.581000 | 21.2 | 2908 | 389 | None |
| 76 | `DOC-9178d6cdb14bfac9` | True | 0.601000 | 23.1 | 2872 | 344 | None |
| 77 | `DOC-804fbeed2ab25ae8` | True | 0.580900 | 24.0 | 2873 | 349 | None |
| 78 | `DOC-5b455f179d11b3d3` | True | 0.591000 | 21.3 | 2903 | 398 | None |
| 79 | `DOC-27b23fd94cc70d9d` | True | 0.605200 | 26.5 | 2890 | 362 | None |
| 80 | `DOC-ec76076167291255` | True | 0.613100 | 30.3 | 2974 | 384 | None |
| 81 | `DOC-b199013b1823372d` | True | 0.582700 | 24.0 | 2882 | 343 | None |
| 82 | `DOC-2bb9b262e943bc89` | True | 0.626500 | 28.0 | 3056 | 384 | None |
| 83 | `DOC-ffc9528cf71610fc` | True | 0.613800 | 29.3 | 2986 | 390 | None |
| 84 | `DOC-d62e0d8ac987119d` | True | 0.626500 | 32.1 | 3031 | 417 | None |
| 85 | `DOC-66a4bc121141fe7a` | True | 0.689400 | 26.4 | 5690 | 436 | None |
| 86 | `DOC-0bdda3ecc67bae80` | True | 0.666300 | 16.1 | 4998 | 435 | None |
| 87 | `DOC-cdd4f26b4f9db00c` | True | 0.777900 | 19.5 | 4789 | 495 | None |
| 88 | `DOC-91fe413a7105d6fc` | True | 0.688000 | 23.7 | 5106 | 503 | None |
| 89 | `DOC-65bd322c23c62250` | True | 0.700400 | 26.4 | 4621 | 554 | None |
| 90 | `DOC-81a444ef841aea5f` | True | 0.616400 | 33.9 | 4887 | 635 | None |
| 91 | `DOC-009ee40e247a0a6e` | True | 0.608300 | 18.7 | 4688 | 568 | None |
| 92 | `DOC-e08d7fd014fde496` | True | 0.608700 | 26.5 | 4487 | 531 | None |
| 93 | `DOC-06844413e427f8c2` | True | 0.764900 | 22.2 | 5336 | 511 | None |
| 94 | `DOC-db02c129ee1d5261` | True | 0.692600 | 24.4 | 5515 | 539 | None |
| 95 | `DOC-0966e6d5a9e7bd71` | True | 0.753200 | 34.2 | 4683 | 956 | None |
| 96 | `DOC-d3f320a3ba9c105b` | True | 0.597600 | 30.3 | 5234 | 697 | None |
| 97 | `DOC-4df9e8f7fd1c31c3` | True | 0.615400 | 31.9 | 4883 | 937 | None |
| 98 | `DOC-02f77aa77391a8c2` | True | 0.753100 | 44.2 | 5091 | 1299 | None |
| 99 | `DOC-46870fd360755337` | True | 0.673200 | 55.0 | 5424 | 1683 | None |
| 100 | `DOC-da50072c19e4223c` | True | 0.726000 | 58.5 | 5957 | 1647 | None |
