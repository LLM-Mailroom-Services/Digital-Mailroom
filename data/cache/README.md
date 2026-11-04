# Dataset cache

Gitignored Hub materialization for [Lucius-Morningstar/mailroom-dataset](https://huggingface.co/datasets/Lucius-Morningstar/mailroom-dataset/viewer/ground_truth) at the family pin (`FAMILY_HF_REVISION`). Pytest never reads this directory.

```bash
sandbox datasets pull
# → data/cache/Lucius-Morningstar__mailroom-dataset__ed7576b67634/ground_truth_all.jsonl
#    3,302 rows (train+test): contract 600, corporate_record 450,
#    correspondence 1,000, insurance_claim 1,100, merger_agreement 152

sandbox datasets sample --per-class 20   # or 40 / 100 (merger cap is 152)
# → …/ground_truth_all_perclass20.jsonl
```

`split: all` is required for 40/100-per-class Modal draws — the Hub `test` split is only ~323 rows (~17 mergers). Point a run spec at the sampled JSONL with `dataset.local_path` (offline after the first pull) or keep `provider: huggingface` / `split: all` and let preflight hit the Hub parquet cache under `data/cache/hf`.
