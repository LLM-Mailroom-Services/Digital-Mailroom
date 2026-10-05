# Run report — `grid-50-correspondence-specialist-awq-2l4`

Dated cell stem: `RUN-50-CORRESPONDENCE-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-50-correspondence-specialist-awq-2l4` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `a6e93f6358b9f97bcf0a52077980ef0e17e4ed0da5929ed2489f74ff0a0b8c32` |
| dataset fingerprint | `8e4572ae7fba` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.333968** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 13.956 |
| gpu_seconds | 14.253 |
| estimated GPU cost | 0.006335 |
| **GPU $/doc** | **0.0001267** |
| latency p50 / max (s) | 10.732824 / 22.278216 |
| prompt / completion tokens | 134797 / 8106 |
| concurrency speedup (Σlat/wall) | 39.89 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-16dfd03aed14e557` | True | 0 | 8.2 | 2205 | 76 | None |
| 2 | `DOC-1d5664e2c826ad07` | True | 0.388900 | 9.7 | 2216 | 104 | None |
| 3 | `DOC-f36a37e1a9c1351e` | True | 0.083300 | 9.7 | 2238 | 105 | None |
| 4 | `DOC-d0c241ea24439be2` | True | 0.510100 | 9.6 | 2324 | 111 | None |
| 5 | `DOC-cb4f8fb4ccb52f44` | True | 0.333300 | 9.8 | 2270 | 118 | None |
| 6 | `DOC-20b4e31d9a4bf994` | True | 0.284400 | 9.9 | 2386 | 123 | None |
| 7 | `DOC-c2826f69ed293da4` | True | 0.049400 | 10.3 | 2229 | 105 | None |
| 8 | `DOC-2bdbf0be591edea6` | True | 0.051300 | 10.7 | 2260 | 116 | None |
| 9 | `DOC-38265bcc6ecfecc3` | True | 0.121200 | 10.7 | 2260 | 114 | None |
| 10 | `DOC-44b1e5a60b363d3e` | True | 0.333300 | 11.9 | 2527 | 127 | None |
| 11 | `DOC-553256644e7b4547` | True | 0.333300 | 11.9 | 2304 | 127 | None |
| 12 | `DOC-c71d3ca0b727a0d4` | True | 0.333300 | 12.6 | 2310 | 128 | None |
| 13 | `DOC-38c54645bf0e601a` | True | 0.370400 | 12.6 | 2556 | 128 | None |
| 14 | `DOC-9ec94a2619e46dfb` | True | 0.400000 | 12.7 | 2273 | 133 | None |
| 15 | `DOC-4eb0e9385b81cc4b` | True | 0.228100 | 12.6 | 2315 | 138 | None |
| 16 | `DOC-c4debd478f2c06e0` | True | 0.511900 | 13.5 | 2467 | 137 | None |
| 17 | `DOC-690cb07fef21747b` | True | 0.083300 | 13.7 | 2485 | 140 | None |
| 18 | `DOC-314aa51db90c8c92` | True | 0.416700 | 13.8 | 3072 | 156 | None |
| 19 | `DOC-8eed243667c985bd` | True | 0.333300 | 14.0 | 2680 | 159 | None |
| 20 | `DOC-a318b50872273528` | True | 0.348500 | 14.3 | 2559 | 157 | None |
| 21 | `DOC-c45ecc852b2cb0f4` | True | 0.536200 | 14.5 | 2354 | 166 | None |
| 22 | `DOC-91f5631a20c62dc5` | True | 0.354400 | 14.5 | 2453 | 168 | None |
| 23 | `DOC-228e51bba45b5c7d` | True | 0.258200 | 15.0 | 3037 | 175 | None |
| 24 | `DOC-a8efd6e4c4d49aaf` | True | 0.219000 | 14.9 | 2471 | 176 | None |
| 25 | `DOC-2cde0c6d0c70b02b` | True | 0.078400 | 15.0 | 2737 | 180 | None |
| 26 | `DOC-383b9badb01a1a00` | True | 0.333300 | 15.2 | 4778 | 181 | None |
| 27 | `DOC-47647a5fdcd45666` | True | 0.333300 | 16.0 | 2447 | 130 | None |
| 28 | `DOC-5adf644f3cb1d34e` | True | 0 | 3.6 | 2199 | 76 | None |
| 29 | `DOC-8754555168547e16` | True | 0.264100 | 16.9 | 3162 | 232 | None |
| 30 | `DOC-21460a9f6d7e6348` | True | 0.862700 | 7.4 | 2337 | 137 | None |
| 31 | `DOC-d6e2bbd8c5e394a4` | True | 0.809500 | 6.7 | 2263 | 123 | None |
| 32 | `DOC-edd0a288e32f0d3b` | True | 0.666700 | 7.5 | 2507 | 134 | None |
| 33 | `DOC-f6a9a00e53cc7973` | True | 0.333300 | 7.7 | 6379 | 144 | None |
| 34 | `DOC-d3d85dc1b1514bec` | True | 0.538400 | 9.3 | 2444 | 169 | None |
| 35 | `DOC-595ab9fc19465909` | True | 0.333300 | 6.9 | 2371 | 152 | None |
| 36 | `DOC-96438076efc6cc7b` | True | 0.333300 | 5.2 | 2309 | 144 | None |
| 37 | `DOC-a6fff0ef0e406461` | True | 0.381000 | 7.2 | 2374 | 163 | None |
| 38 | `DOC-c4074ed5b08f097e` | True | 0.382700 | 5.5 | 2255 | 128 | None |
| 39 | `DOC-e624b1b9823e53f5` | True | 0.542500 | 18.1 | 2917 | 280 | None |
| 40 | `DOC-ff15276697cdfbb2` | True | 0.116200 | 6.3 | 2853 | 165 | None |
| 41 | `DOC-17ac4251c7d94cea` | True | 0.121200 | 4.7 | 2261 | 112 | None |
| 42 | `DOC-c01ab1c1c673f355` | True | 0.506900 | 4.9 | 2394 | 126 | None |
| 43 | `DOC-2431095adda97989` | True | 0.175200 | 18.5 | 2606 | 296 | None |
| 44 | `DOC-5b63f9fe205d564b` | True | 0.580000 | 4.7 | 2425 | 146 | None |
| 45 | `DOC-9b2bc061621a56be` | True | 0.527800 | 8.9 | 2574 | 191 | None |
| 46 | `DOC-76375ebb4cd91de9` | True | 0.111100 | 7.5 | 3047 | 190 | None |
| 47 | `DOC-9422c8775b387935` | True | 0.800000 | 6.7 | 3119 | 158 | None |
| 48 | `DOC-ee6bae4d269c1911` | True | 0.333300 | 11.0 | 3361 | 281 | None |
| 49 | `DOC-1dcf4dfd5ec6defb` | True | 0.245700 | 22.1 | 3533 | 438 | None |
| 50 | `DOC-f4b4c8c623ccb915` | True | 0.106700 | 22.3 | 4894 | 443 | None |
