# Run report — `grid-50-corporate-records-specialist-awq-1l4`

Dated cell stem: `RUN-50-CORPORATE-AWQ-1L4-C8`. Written automatically under the local-date specialist tree.

| | |
| --- | --- |
| run_id | `grid-50-corporate-records-specialist-awq-1l4` |
| task / agent | `corporate_records_specialist` |
| prompt | `corporate_records_specialist_v1` |
| engine | `Qwen/Qwen3-8B-AWQ` |
| GPU shape | **1×L4** |
| concurrency | **8** |
| n | **50** |
| profile | `modal-vllm` |
| spec_hash | `95c64a5863b63278b5b1f4faa71342163a7c5abd3a744acb36dcdd001c590f3d` |
| dataset fingerprint | `d3139c5e07c1` |

## Headline results

| metric | value |
| --- | --- |
| docs ok / failed / total | **50 / 0 / 50** |
| **overall_extraction_score** | **0.449218** |
| schema_valid_rate | 0.940000 |
| error_count | 0 |

## Serving / cost (see sibling `-SERVING.md`)

| metric | value |
| --- | --- |
| wall_seconds | 71.152 |
| gpu_seconds | 71.437 |
| estimated GPU cost | 0.015875 |
| **GPU $/doc** | **0.0003175** |
| latency p50 / max (s) | 13.187200 / 22.254661 |
| prompt / completion tokens | 223160 / 8360 |
| concurrency speedup (Σlat/wall) | 9.22 |

## Per-document scores

| # | doc id | ok | overall | latency s | prompt tok | compl tok | error |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `DOC-e42fbaa25765ec5f` | True | 0.132500 | 13.3 | 2249 | 97 | None |
| 2 | `DOC-5dc965bfd05b8bf5` | True | 0.185900 | 14.7 | 5308 | 154 | None |
| 3 | `DOC-42999d0d46a55578` | True | 0.743600 | 14.7 | 4943 | 153 | None |
| 4 | `DOC-7ca9eefc5f17d24f` | True | 0.140100 | 14.9 | 2456 | 155 | None |
| 5 | `DOC-34077127acc64d5e` | True | 0.551500 | 15.1 | 5910 | 160 | None |
| 6 | `DOC-a14783cfd27c88c1` | True | 0.596200 | 19.8 | 4571 | 182 | None |
| 7 | `DOC-263580addaac6d20` | True | 0.805600 | 21.9 | 5241 | 239 | None |
| 8 | `DOC-bda69bc956881bab` | True | 0.666700 | 22.3 | 7261 | 247 | None |
| 9 | `DOC-0d9dd64d13b1c270` | True | 0.114600 | 12.5 | 2512 | 161 | None |
| 10 | `DOC-1e0470c03b023106` | True | 0.794900 | 13.3 | 5338 | 159 | None |
| 11 | `DOC-c9fa372f38de2b5e` | True | 0.357100 | 13.2 | 3160 | 163 | None |
| 12 | `DOC-c40a11ac7f2c7b5b` | True | 0.058000 | 10.6 | 2656 | 157 | None |
| 13 | `DOC-e366f6c8f425cd09` | True | 0.694400 | 16.0 | 4797 | 193 | None |
| 14 | `DOC-4a77d0b316e1cc01` | True | 0.697000 | 18.8 | 5497 | 204 | None |
| 15 | `DOC-732b812b7d9d9653` | True | 0.888900 | 13.3 | 5572 | 165 | None |
| 16 | `DOC-3c328f7374a079a9` | True | 0.733300 | 14.0 | 4845 | 191 | None |
| 17 | `DOC-9cd96711a8928ec5` | True | 0.359000 | 11.4 | 4953 | 169 | None |
| 18 | `DOC-db84eb3d59faee66` | True | 0.081300 | 11.3 | 2644 | 159 | None |
| 19 | `DOC-51092450a52e256c` | True | 0.442300 | 13.2 | 5466 | 174 | None |
| 20 | `DOC-4042dc3ecd9ac9b4` | True | 0.149900 | 11.1 | 5283 | 156 | None |
| 21 | `DOC-e12f100d091e15b5` | True | 0.468200 | 8.1 | 2310 | 137 | None |
| 22 | `DOC-417996c5cc3d91f5` | True | 0.440200 | 6.5 | 2232 | 97 | None |
| 23 | `DOC-85c7b49cdac19586` | True | 0.695300 | 15.3 | 5388 | 196 | None |
| 24 | `DOC-9bdcc670eb06437b` | True | 0.440200 | 12.1 | 2446 | 125 | None |
| 25 | `DOC-9523246260be90e0` | True | 0.833300 | 13.5 | 5812 | 168 | None |
| 26 | `DOC-1578b671836c78e9` | True | 0.820500 | 13.5 | 5810 | 167 | None |
| 27 | `DOC-0d28ca4c116b9f53` | True | 0.487200 | 11.8 | 3334 | 158 | None |
| 28 | `DOC-08829e0f817f1211` | True | 0.452400 | 12.0 | 2947 | 167 | None |
| 29 | `DOC-cdc3f9c110996846` | True | 0.141900 | 12.2 | 4257 | 166 | None |
| 30 | `DOC-d8a8d7c000ae6495` | True | 0.100000 | 9.8 | 2687 | 147 | None |
| 31 | `DOC-ef2f0660ed8b6f24` | True | 0.449700 | 18.3 | 6125 | 237 | None |
| 32 | `DOC-a973ebf005e0e785` | True | 0.427800 | 16.3 | 6146 | 234 | None |
| 33 | `DOC-087da9fdf781f7db` | True | 0.333300 | 11.3 | 5240 | 137 | None |
| 34 | `DOC-ffb48271e0a5e812` | True | 0.666700 | 11.0 | 5344 | 144 | None |
| 35 | `DOC-30ce0f05432fc57f` | True | 0.440500 | 12.0 | 2647 | 159 | None |
| 36 | `DOC-e12651c80e736fb8` | True | 0.467900 | 13.4 | 2760 | 176 | None |
| 37 | `DOC-2aa6196b22606d9c` | True | 0.442300 | 16.2 | 5877 | 214 | None |
| 38 | `DOC-b7680bb9f72c5e65` | True | 0.287800 | 12.7 | 5257 | 165 | None |
| 39 | `DOC-8018aaaf98b8597e` | True | 0.787900 | 10.4 | 5234 | 147 | None |
| 40 | `DOC-0636dbc980a43715` | True | 0.141300 | 8.5 | 2250 | 116 | None |
| 41 | `DOC-5c087a08edcb4a91` | True | 0.508800 | 13.0 | 5096 | 197 | None |
| 42 | `DOC-b28a8210ab812830` | True | 0.097600 | 13.2 | 2515 | 160 | None |
| 43 | `DOC-30fe9f6e442b9df3` | True | 0.262400 | 13.5 | 4047 | 163 | None |
| 44 | `DOC-36df577431fb1032` | True | 0.267900 | 13.6 | 5485 | 157 | None |
| 45 | `DOC-a2110b2cebe63cb7` | True | 0.755600 | 13.8 | 5308 | 166 | None |
| 46 | `DOC-a52b3ad21666d339` | True | 0.166700 | 11.2 | 3538 | 168 | None |
| 47 | `DOC-69ffaec3ba2b2cde` | True | 0.154700 | 10.5 | 5230 | 160 | None |
| 48 | `DOC-dfe42f3747f299e6` | True | 0.750000 | 10.3 | 5870 | 162 | None |
| 49 | `DOC-5cc2960a21fca151` | True | 0.246700 | 10.6 | 5228 | 172 | None |
| 50 | `DOC-b865a8f75657643a` | True | 0.733300 | 6.2 | 6078 | 160 | None |
