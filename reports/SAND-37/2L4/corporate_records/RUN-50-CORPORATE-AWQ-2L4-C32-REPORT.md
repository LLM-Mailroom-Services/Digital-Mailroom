# Run report — `grid-50-corporate-records-specialist-awq-2l4`

Dated cell stem: `RUN-50-CORPORATE-AWQ-2L4-C32`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-50-corporate-records-specialist-awq-2l4` |
| task / agent | `corporate_records_specialist` |
| prompt | `corporate_records_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **2×L4** |
| concurrency | **32** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `ae7a4401dc43ff2f54b6c9162029a1ab2724a8d6e85835c87f35155ecce4fd47` |
| dataset fingerprint | `d3139c5e07c1` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.452042** |
| schema_valid_rate | 0.940000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 21.173 |
| gpu_seconds | 21.481 |
| estimated GPU cost | 0.009547 |
| **GPU $/doc** | **0.00019094** |
| latency p50 / max (s) | 24.065056 / 36.481023 |
| prompt / completion tokens | 223160 / 8354 |
| concurrency speedup (Σlat/wall) | 52.98 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-417996c5cc3d91f5` | True | 0.440200 | 16.9 | 2232 | 97 | None |
| 2 | `DOC-e42fbaa25765ec5f` | True | 0.132500 | 18.0 | 2249 | 97 | None |
| 3 | `DOC-9bdcc670eb06437b` | True | 0.440200 | 20.2 | 2446 | 125 | None |
| 4 | `DOC-db84eb3d59faee66` | True | 0.081300 | 22.4 | 2644 | 147 | None |
| 5 | `DOC-d8a8d7c000ae6495` | True | 0.102700 | 22.5 | 2687 | 151 | None |
| 6 | `DOC-4042dc3ecd9ac9b4` | True | 0.149900 | 22.7 | 5283 | 157 | None |
| 7 | `DOC-e12f100d091e15b5` | True | 0.465800 | 23.8 | 2310 | 150 | None |
| 8 | `DOC-5dc965bfd05b8bf5` | True | 0.211500 | 24.4 | 5308 | 154 | None |
| 9 | `DOC-7ca9eefc5f17d24f` | True | 0.140100 | 24.4 | 2456 | 155 | None |
| 10 | `DOC-cdc3f9c110996846` | True | 0.393900 | 24.4 | 4257 | 164 | None |
| 11 | `DOC-1e0470c03b023106` | True | 0.794900 | 25.7 | 5338 | 159 | None |
| 12 | `DOC-c9fa372f38de2b5e` | True | 0.357100 | 25.9 | 3160 | 163 | None |
| 13 | `DOC-34077127acc64d5e` | True | 0.551500 | 26.3 | 5910 | 160 | None |
| 14 | `DOC-0d28ca4c116b9f53` | True | 0.487200 | 26.2 | 3334 | 158 | None |
| 15 | `DOC-9cd96711a8928ec5` | True | 0.359000 | 28.1 | 4953 | 170 | None |
| 16 | `DOC-08829e0f817f1211` | True | 0.452400 | 28.0 | 2947 | 163 | None |
| 17 | `DOC-1578b671836c78e9` | True | 0.743600 | 28.5 | 5810 | 152 | None |
| 18 | `DOC-51092450a52e256c` | True | 0.442300 | 28.5 | 5466 | 174 | None |
| 19 | `DOC-0d9dd64d13b1c270` | True | 0.148000 | 30.0 | 2512 | 171 | None |
| 20 | `DOC-732b812b7d9d9653` | True | 0.888900 | 31.3 | 5572 | 165 | None |
| 21 | `DOC-42999d0d46a55578` | True | 0.743600 | 31.4 | 4943 | 158 | None |
| 22 | `DOC-c40a11ac7f2c7b5b` | True | 0.388900 | 31.4 | 2656 | 182 | None |
| 23 | `DOC-e366f6c8f425cd09` | True | 0.361100 | 31.5 | 4797 | 189 | None |
| 24 | `DOC-4a77d0b316e1cc01` | True | 0.697000 | 32.4 | 5497 | 206 | None |
| 25 | `DOC-a14783cfd27c88c1` | True | 0.596200 | 33.2 | 4571 | 181 | None |
| 26 | `DOC-3c328f7374a079a9` | True | 0.733300 | 33.2 | 4845 | 188 | None |
| 27 | `DOC-ef2f0660ed8b6f24` | True | 0.449700 | 33.5 | 6125 | 233 | None |
| 28 | `DOC-30ce0f05432fc57f` | True | 0.440500 | 15.7 | 2647 | 171 | None |
| 29 | `DOC-9523246260be90e0` | True | 0.833300 | 33.9 | 5812 | 188 | None |
| 30 | `DOC-85c7b49cdac19586` | True | 0.695300 | 33.9 | 5388 | 200 | None |
| 31 | `DOC-087da9fdf781f7db` | True | 0.333300 | 14.3 | 5240 | 137 | None |
| 32 | `DOC-a973ebf005e0e785` | True | 0.427800 | 34.6 | 6146 | 211 | None |
| 33 | `DOC-ffb48271e0a5e812` | True | 0.666700 | 13.1 | 5344 | 145 | None |
| 34 | `DOC-bda69bc956881bab` | True | 0.666700 | 35.7 | 7261 | 247 | None |
| 35 | `DOC-8018aaaf98b8597e` | True | 0.787900 | 11.5 | 5234 | 147 | None |
| 36 | `DOC-2aa6196b22606d9c` | True | 0.442300 | 19.0 | 5877 | 214 | None |
| 37 | `DOC-b28a8210ab812830` | True | 0.097600 | 10.5 | 2515 | 158 | None |
| 38 | `DOC-0636dbc980a43715` | True | 0.141300 | 11.9 | 2250 | 116 | None |
| 39 | `DOC-263580addaac6d20` | True | 0.805600 | 36.5 | 5241 | 238 | None |
| 40 | `DOC-a52b3ad21666d339` | True | 0.169400 | 10.2 | 3538 | 169 | None |
| 41 | `DOC-5cc2960a21fca151` | True | 0.246700 | 8.7 | 5228 | 163 | None |
| 42 | `DOC-b865a8f75657643a` | True | 0.733300 | 8.3 | 6078 | 161 | None |
| 43 | `DOC-5c087a08edcb4a91` | True | 0.508800 | 13.2 | 5096 | 192 | None |
| 44 | `DOC-b7680bb9f72c5e65` | True | 0.287800 | 14.6 | 5257 | 157 | None |
| 45 | `DOC-30fe9f6e442b9df3` | True | 0.168900 | 13.0 | 4047 | 150 | None |
| 46 | `DOC-e12651c80e736fb8` | True | 0.467900 | 15.4 | 2760 | 176 | None |
| 47 | `DOC-36df577431fb1032` | True | 0.267900 | 11.5 | 5485 | 158 | None |
| 48 | `DOC-a2110b2cebe63cb7` | True | 0.755600 | 12.0 | 5308 | 166 | None |
| 49 | `DOC-69ffaec3ba2b2cde` | True | 0.154700 | 10.0 | 5230 | 160 | None |
| 50 | `DOC-dfe42f3747f299e6` | True | 0.750000 | 9.6 | 5870 | 161 | None |
