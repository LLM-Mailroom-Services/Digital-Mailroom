# Run report — `grid-50-correspondence-specialist-awq-1l4`

Dated cell stem: `RUN-50-CORRESPONDENCE-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-50-correspondence-specialist-awq-1l4` |
| task / agent | `correspondence_specialist` |
| prompt | `correspondence_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `c20ff843a924966e50728d1083a844c88d8593f70eb54b925da4ae279125e55e` |
| dataset fingerprint | `8e4572ae7fba` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.344648** |
| schema_valid_rate | 1.000000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 40.559 |
| gpu_seconds | 40.892 |
| estimated GPU cost | 0.009087 |
| **GPU $/doc** | **0.00018174** |
| latency p50 / max (s) | 6.601969 / 19.762077 |
| prompt / completion tokens | 134797 / 8084 |
| concurrency speedup (Σlat/wall) | 8.98 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-1d5664e2c826ad07` | True | 0.388900 | 6.9 | 2216 | 101 | None |
| 2 | `DOC-f36a37e1a9c1351e` | True | 0.083300 | 6.9 | 2238 | 105 | None |
| 3 | `DOC-c2826f69ed293da4` | True | 0.049400 | 6.9 | 2229 | 105 | None |
| 4 | `DOC-38c54645bf0e601a` | True | 0.181300 | 9.0 | 2556 | 139 | None |
| 5 | `DOC-a318b50872273528` | True | 0.348500 | 9.7 | 2559 | 164 | None |
| 6 | `DOC-383b9badb01a1a00` | True | 0.333300 | 10.5 | 4778 | 181 | None |
| 7 | `DOC-e624b1b9823e53f5` | True | 0.542500 | 11.6 | 2917 | 218 | None |
| 8 | `DOC-8754555168547e16` | True | 0.264100 | 11.7 | 3162 | 221 | None |
| 9 | `DOC-553256644e7b4547` | True | 0.333300 | 6.3 | 2304 | 118 | None |
| 10 | `DOC-c71d3ca0b727a0d4` | True | 0.333300 | 5.0 | 2310 | 128 | None |
| 11 | `DOC-c45ecc852b2cb0f4` | True | 0.536200 | 8.5 | 2354 | 165 | None |
| 12 | `DOC-9ec94a2619e46dfb` | True | 0.400000 | 6.7 | 2273 | 154 | None |
| 13 | `DOC-44b1e5a60b363d3e` | True | 0.333300 | 5.9 | 2527 | 127 | None |
| 14 | `DOC-cb4f8fb4ccb52f44` | True | 0.333300 | 5.0 | 2270 | 118 | None |
| 15 | `DOC-228e51bba45b5c7d` | True | 0.258200 | 7.4 | 3037 | 175 | None |
| 16 | `DOC-314aa51db90c8c92` | True | 0.416700 | 6.0 | 3072 | 163 | None |
| 17 | `DOC-2431095adda97989` | True | 0.175200 | 11.2 | 2606 | 298 | None |
| 18 | `DOC-2bdbf0be591edea6` | True | 0.080000 | 4.1 | 2260 | 117 | None |
| 19 | `DOC-8eed243667c985bd` | True | 0.791700 | 7.1 | 2680 | 192 | None |
| 20 | `DOC-4eb0e9385b81cc4b` | True | 0.228100 | 5.5 | 2315 | 139 | None |
| 21 | `DOC-f4b4c8c623ccb915` | True | 0.106700 | 17.6 | 4894 | 433 | None |
| 22 | `DOC-91f5631a20c62dc5` | True | 0.384700 | 6.8 | 2453 | 176 | None |
| 23 | `DOC-47647a5fdcd45666` | True | 0.333300 | 5.0 | 2447 | 126 | None |
| 24 | `DOC-c4debd478f2c06e0` | True | 0.511900 | 5.4 | 2467 | 137 | None |
| 25 | `DOC-690cb07fef21747b` | True | 0.083300 | 5.3 | 2485 | 139 | None |
| 26 | `DOC-20b4e31d9a4bf994` | True | 0.284400 | 5.0 | 2386 | 117 | None |
| 27 | `DOC-d0c241ea24439be2` | True | 0.510100 | 4.7 | 2324 | 102 | None |
| 28 | `DOC-16dfd03aed14e557` | True | 0 | 3.6 | 2205 | 76 | None |
| 29 | `DOC-38265bcc6ecfecc3` | True | 0.121200 | 5.1 | 2260 | 112 | None |
| 30 | `DOC-1dcf4dfd5ec6defb` | True | 0.245700 | 19.8 | 3533 | 463 | None |
| 31 | `DOC-edd0a288e32f0d3b` | True | 0.666700 | 6.8 | 2507 | 134 | None |
| 32 | `DOC-21460a9f6d7e6348` | True | 0.745100 | 6.0 | 2337 | 115 | None |
| 33 | `DOC-a8efd6e4c4d49aaf` | True | 0.219000 | 8.8 | 2471 | 176 | None |
| 34 | `DOC-d3d85dc1b1514bec` | True | 0.820500 | 8.5 | 2444 | 175 | None |
| 35 | `DOC-2cde0c6d0c70b02b` | True | 0.078400 | 9.3 | 2737 | 185 | None |
| 36 | `DOC-f6a9a00e53cc7973` | True | 0.333300 | 8.1 | 6379 | 143 | None |
| 37 | `DOC-9b2bc061621a56be` | True | 0.527800 | 9.6 | 2574 | 191 | None |
| 38 | `DOC-d6e2bbd8c5e394a4` | True | 0.809500 | 5.5 | 2263 | 124 | None |
| 39 | `DOC-595ab9fc19465909` | True | 0.333300 | 6.5 | 2371 | 150 | None |
| 40 | `DOC-5adf644f3cb1d34e` | True | 0 | 3.0 | 2199 | 76 | None |
| 41 | `DOC-a6fff0ef0e406461` | True | 0.381000 | 7.1 | 2374 | 162 | None |
| 42 | `DOC-ff15276697cdfbb2` | True | 0.116200 | 6.3 | 2853 | 165 | None |
| 43 | `DOC-c4074ed5b08f097e` | True | 0.382700 | 4.9 | 2255 | 132 | None |
| 44 | `DOC-ee6bae4d269c1911` | True | 0.333300 | 10.6 | 3361 | 265 | None |
| 45 | `DOC-76375ebb4cd91de9` | True | 0.111100 | 8.2 | 3047 | 199 | None |
| 46 | `DOC-17ac4251c7d94cea` | True | 0.121200 | 4.0 | 2261 | 112 | None |
| 47 | `DOC-9422c8775b387935` | True | 0.800000 | 5.7 | 3119 | 156 | None |
| 48 | `DOC-96438076efc6cc7b` | True | 0.333300 | 5.2 | 2309 | 144 | None |
| 49 | `DOC-5b63f9fe205d564b` | True | 0.621200 | 4.6 | 2425 | 146 | None |
| 50 | `DOC-c01ab1c1c673f355` | True | 0.506900 | 5.6 | 2394 | 125 | None |
