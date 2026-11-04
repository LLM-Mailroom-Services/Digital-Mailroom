# Run report — `sand40-100-corporate-records-specialist-awq-2l4`

Dated cell stem: `RUN-100-CORPORATE-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `sand40-100-corporate-records-specialist-awq-2l4` |
| task / agent | `corporate_records_specialist` |
| prompt | `corporate_records_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **100** |
| profile | `modal-vllm` |
| spec_hash | `770b562a3fd86f6c444909bf78cb8ce47da965c571ec1fcdebeab449cd58a9d5` |
| dataset fingerprint | `76d8a17658f7` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **100 / 0 / 100** |
| **overall_extraction_score** | **0.475484** |
| schema_valid_rate | 0.970000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 48.108 |
| gpu_seconds | 48.441 |
| estimated GPU cost | 0.021529 |
| **GPU $/doc** | **0.00021529** |
| latency p50 / max (s) | 19.920200 / 40.398858 |
| prompt / completion tokens | 421101 / 16622 |
| concurrency speedup (Σlat/wall) | 42.65 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-4d8e8b87f161d432` | True | 0.416700 | 19.0 | 2565 | 120 | None |
| 2 | `DOC-c2304ee259662c25` | True | 0.529200 | 19.0 | 5297 | 121 | None |
| 3 | `DOC-a1bf2ddf032e38ea` | True | 0.462700 | 19.1 | 2245 | 120 | None |
| 4 | `DOC-6d17fda455311945` | True | 0.805600 | 19.4 | 7276 | 135 | None |
| 5 | `DOC-e42fbaa25765ec5f` | True | 0.465800 | 20.0 | 2249 | 133 | None |
| 6 | `DOC-e545bbd5f5ea61b6` | True | 0.697000 | 20.9 | 2788 | 155 | None |
| 7 | `DOC-5dc965bfd05b8bf5` | True | 0.185900 | 20.9 | 5308 | 150 | None |
| 8 | `DOC-7ca9eefc5f17d24f` | True | 0.140100 | 21.2 | 2456 | 154 | None |
| 9 | `DOC-d50133030490ea0a` | True | 0.105100 | 21.9 | 3035 | 147 | None |
| 10 | `DOC-732b812b7d9d9653` | True | 0.888900 | 22.6 | 5572 | 156 | None |
| 11 | `DOC-3e20fef7d0be1ab6` | True | 0.794900 | 23.1 | 5219 | 153 | None |
| 12 | `DOC-0a262afc80c73247` | True | 0.113600 | 23.3 | 3124 | 147 | None |
| 13 | `DOC-1e0470c03b023106` | True | 0.794900 | 23.3 | 5338 | 159 | None |
| 14 | `DOC-cc3d181a639616d7` | True | 0.113600 | 23.8 | 3196 | 155 | None |
| 15 | `DOC-42999d0d46a55578` | True | 0.743600 | 24.3 | 4943 | 158 | None |
| 16 | `DOC-34077127acc64d5e` | True | 0.551500 | 24.3 | 5910 | 160 | None |
| 17 | `DOC-3c328f7374a079a9` | True | 0.733300 | 24.8 | 4845 | 169 | None |
| 18 | `DOC-1b024f18a5882a8e` | True | 0.447000 | 25.2 | 5644 | 166 | None |
| 19 | `DOC-ec57149494f0c9a0` | True | 0.785700 | 26.3 | 3177 | 173 | None |
| 20 | `DOC-a14783cfd27c88c1` | True | 0.596200 | 27.1 | 4571 | 190 | None |
| 21 | `DOC-c40a11ac7f2c7b5b` | True | 0.388900 | 27.3 | 2656 | 182 | None |
| 22 | `DOC-d2969f9629acc901` | True | 0.148800 | 28.3 | 2466 | 162 | None |
| 23 | `DOC-c9fa372f38de2b5e` | True | 0.357100 | 28.2 | 3160 | 163 | None |
| 24 | `DOC-74e0f47369572741` | True | 0.154700 | 28.6 | 5271 | 189 | None |
| 25 | `DOC-7294152c69239b1e` | True | 0.447100 | 29.5 | 4613 | 199 | None |
| 26 | `DOC-e366f6c8f425cd09` | True | 0.694400 | 31.6 | 4797 | 187 | None |
| 27 | `DOC-b7be4de1447c8a24` | True | 0.145800 | 31.8 | 3656 | 232 | None |
| 28 | `DOC-4a77d0b316e1cc01` | True | 0.727300 | 32.8 | 5497 | 209 | None |
| 29 | `DOC-263580addaac6d20` | True | 0.805600 | 33.6 | 5241 | 238 | None |
| 30 | `DOC-bda69bc956881bab` | True | 0.666700 | 35.2 | 7261 | 250 | None |
| 31 | `DOC-020d77c0107d273d` | True | 0.472200 | 36.2 | 2302 | 116 | None |
| 32 | `DOC-345450f6677c2a8a` | True | 0.154700 | 18.1 | 5362 | 150 | None |
| 33 | `DOC-cb828c5701c751f3` | True | 0.154700 | 19.0 | 2952 | 153 | None |
| 34 | `DOC-310fa993e212a342` | True | 0.181300 | 17.5 | 2453 | 161 | None |
| 35 | `DOC-417996c5cc3d91f5` | True | 0.440200 | 14.1 | 2232 | 97 | None |
| 36 | `DOC-51092450a52e256c` | True | 0.442300 | 19.8 | 5466 | 167 | None |
| 37 | `DOC-0d9dd64d13b1c270` | True | 0.114600 | 40.4 | 2512 | 161 | None |
| 38 | `DOC-db84eb3d59faee66` | True | 0.081300 | 19.9 | 2644 | 146 | None |
| 39 | `DOC-c80ef83120793a69` | True | 0.517100 | 16.6 | 2267 | 150 | None |
| 40 | `DOC-b856ca94d75a431a` | True | 0.692300 | 22.4 | 2808 | 162 | None |
| 41 | `DOC-e12f100d091e15b5` | True | 0.465800 | 18.4 | 2310 | 137 | None |
| 42 | `DOC-5052ed547d53cfbf` | True | 0.871800 | 19.1 | 3886 | 150 | None |
| 43 | `DOC-9bdcc670eb06437b` | True | 0.440200 | 15.5 | 2446 | 124 | None |
| 44 | `DOC-9cd96711a8928ec5` | True | 0.359000 | 23.5 | 4953 | 171 | None |
| 45 | `DOC-4042dc3ecd9ac9b4` | True | 0.149900 | 20.1 | 5283 | 160 | None |
| 46 | `DOC-f70b11ab7f823e2d` | True | 0.761900 | 18.4 | 3138 | 157 | None |
| 47 | `DOC-9467462d9bb34f8e` | True | 0.541700 | 18.2 | 5345 | 161 | None |
| 48 | `DOC-325f25ad3bf7d458` | True | 0.282000 | 22.7 | 2519 | 181 | None |
| 49 | `DOC-0d28ca4c116b9f53` | True | 0.487200 | 15.8 | 3334 | 158 | None |
| 50 | `DOC-f1e8af2071cb17fa` | True | 0.416700 | 22.0 | 5083 | 169 | None |
| 51 | `DOC-b73c5e5708c43511` | True | 0.227100 | 18.6 | 5157 | 165 | None |
| 52 | `DOC-9523246260be90e0` | True | 0.833300 | 20.3 | 5812 | 186 | None |
| 53 | `DOC-08829e0f817f1211` | True | 0.523800 | 15.9 | 2947 | 161 | None |
| 54 | `DOC-cde69e0ba4db2419` | True | 0.282000 | 26.6 | 2523 | 184 | None |
| 55 | `DOC-85c7b49cdac19586` | True | 0.660200 | 24.7 | 5388 | 200 | None |
| 56 | `DOC-1578b671836c78e9` | True | 0.743600 | 21.5 | 5810 | 153 | None |
| 57 | `DOC-feab935f7db4b9cf` | True | 0.846200 | 22.2 | 5253 | 151 | None |
| 58 | `DOC-1853b495e0848fca` | True | 0.769200 | 21.0 | 5266 | 152 | None |
| 59 | `DOC-0636dbc980a43715` | True | 0.141300 | 7.4 | 2250 | 116 | None |
| 60 | `DOC-087da9fdf781f7db` | True | 0.333300 | 14.0 | 5240 | 137 | None |
| 61 | `DOC-a195b29d1b417e2f` | True | 0.443200 | 19.4 | 4801 | 216 | None |
| 62 | `DOC-d8a8d7c000ae6495` | True | 0.102700 | 14.9 | 2687 | 144 | None |
| 63 | `DOC-cdc3f9c110996846` | True | 0.727300 | 21.8 | 4257 | 164 | None |
| 64 | `DOC-d361e5631ac2bebb` | True | 0.461500 | 30.4 | 5060 | 237 | None |
| 65 | `DOC-6993b10b8f79da64` | True | 0.357100 | 16.8 | 2924 | 144 | None |
| 66 | `DOC-bb25adbf606096a4` | True | 0.442300 | 21.6 | 3698 | 191 | None |
| 67 | `DOC-674588a5b4c8d642` | True | 0.410300 | 15.7 | 3264 | 159 | None |
| 68 | `DOC-78f2456f571403a9` | True | 0.153100 | 15.7 | 2345 | 153 | None |
| 69 | `DOC-30ce0f05432fc57f` | True | 0.440500 | 20.9 | 2647 | 171 | None |
| 70 | `DOC-ffb48271e0a5e812` | True | 0.666700 | 18.4 | 5344 | 144 | None |
| 71 | `DOC-8e3fa7aa97eda92a` | True | 0.785700 | 19.7 | 5261 | 175 | None |
| 72 | `DOC-5c087a08edcb4a91` | True | 0.508800 | 16.9 | 5096 | 163 | None |
| 73 | `DOC-e54512dab9fa64a4` | True | 0.500000 | 19.2 | 3048 | 172 | None |
| 74 | `DOC-7a7b8110d33a84be` | True | 0.623100 | 14.8 | 2642 | 154 | None |
| 75 | `DOC-e1e86caf042eb7b9` | True | 0.620000 | 14.9 | 3067 | 156 | None |
| 76 | `DOC-8018aaaf98b8597e` | True | 0.666700 | 17.4 | 5234 | 150 | None |
| 77 | `DOC-30fe9f6e442b9df3` | True | 0.168900 | 16.1 | 4047 | 150 | None |
| 78 | `DOC-b7680bb9f72c5e65` | True | 0.287800 | 20.5 | 5257 | 161 | None |
| 79 | `DOC-e12651c80e736fb8` | True | 0.467900 | 22.1 | 2760 | 176 | None |
| 80 | `DOC-8663fca594565055` | True | 0.755600 | 18.5 | 3440 | 159 | None |
| 81 | `DOC-0db97c4753dcbaea` | True | 0.761900 | 22.5 | 4209 | 229 | None |
| 82 | `DOC-2aa6196b22606d9c` | True | 0.442300 | 25.0 | 5877 | 235 | None |
| 83 | `DOC-ef2f0660ed8b6f24` | True | 0.449700 | 28.3 | 6125 | 233 | None |
| 84 | `DOC-571cffbc7867e8ef` | True | 0.132600 | 21.1 | 2538 | 185 | None |
| 85 | `DOC-a973ebf005e0e785` | True | 0.427800 | 26.1 | 6146 | 234 | None |
| 86 | `DOC-a2110b2cebe63cb7` | True | 0.755600 | 14.4 | 5308 | 166 | None |
| 87 | `DOC-b28a8210ab812830` | True | 0.097600 | 16.6 | 2515 | 158 | None |
| 88 | `DOC-63fffca0c0a261ec` | True | 0.843100 | 17.4 | 5135 | 165 | None |
| 89 | `DOC-36df577431fb1032` | True | 0.184600 | 12.6 | 5485 | 154 | None |
| 90 | `DOC-5cc2960a21fca151` | True | 0.246700 | 12.7 | 5228 | 163 | None |
| 91 | `DOC-dfe42f3747f299e6` | True | 0.750000 | 10.1 | 5870 | 158 | None |
| 92 | `DOC-478a8974f4909fc3` | True | 0.733300 | 8.1 | 6078 | 154 | None |
| 93 | `DOC-20e622adc7603fc5` | True | 0.857100 | 15.2 | 5201 | 183 | None |
| 94 | `DOC-69ffaec3ba2b2cde` | True | 0.154700 | 13.4 | 5230 | 160 | None |
| 95 | `DOC-a52b3ad21666d339` | True | 0.169400 | 13.5 | 3538 | 170 | None |
| 96 | `DOC-d564c7cabec90e84` | True | 0.246700 | 11.9 | 5206 | 164 | None |
| 97 | `DOC-c85fadd4401ec219` | True | 0.717900 | 7.7 | 5693 | 179 | None |
| 98 | `DOC-e646013a1cfd084b` | True | 0.805600 | 13.9 | 3122 | 214 | None |
| 99 | `DOC-ffb94478e4033b99` | True | 0.154700 | 9.9 | 5323 | 157 | None |
| 100 | `DOC-b865a8f75657643a` | True | 0.733300 | 8.9 | 6078 | 154 | None |
