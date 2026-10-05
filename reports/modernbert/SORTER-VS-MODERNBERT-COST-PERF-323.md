## Sorter vs ModernBERT (classification)

| side | model | n | e2e (s) | $/doc |
| --- | --- | --- | --- | --- |
| sorter | Qwen/Qwen3-8B | 323 | 2.8 | 0.0001392 |
| modernbert | Lucius-Morningstar/mailroom-modernbert-classifier | 323 | 0.075 | 1e-06 |

### Quality
| metric | sorter | modernbert | Δ (sorter − modernbert) |
| --- | --- | --- | --- |
| accuracy | 0.98 | 0.8947 | 0.0853 |
| doc_type_accuracy | - | 0.8947 | - |
| exact_match | 0.98 | 0.8947 | 0.0853 |
| f1_macro | 0.9899 | - | - |
| subclass_accuracy | - | 0.526 | - |

---

## OpenRouter qwen/qwen3.7-flash (API $ proxy)

## Sorter vs ModernBERT (classification)

| side | model | n | e2e (s) | $/doc |
| --- | --- | --- | --- | --- |
| sorter | qwen/qwen3.7-flash | 323 | 0.9 | 0.00029453658536585364 |
| modernbert | Lucius-Morningstar/mailroom-modernbert-classifier | 323 | 0.075 | 1e-06 |

### Quality
| metric | sorter | modernbert | Δ (sorter − modernbert) |
| --- | --- | --- | --- |
| accuracy | 0.94 | 0.8947 | 0.0453 |
| doc_type_accuracy | - | 0.8947 | - |
| exact_match | - | 0.8947 | - |
| subclass_accuracy | - | 0.526 | - |

## Honest gaps

- ModernBERT accuracy: **measured** on all 323 held-out docs (`eval_run3_20260921.json`, run-3 weights).
- Sorter Modal accuracy: **run-50-modal-hf** on **n=50** (0.98 doc_type) — not the same 323-doc pass.
- Sorter costs: **fixture / ledger proxies**, linearly scaled to n=323; not a fresh sorter job.
- Live run-3 SSH training: **not evaluated** here; refresh when checkpoint lands.
