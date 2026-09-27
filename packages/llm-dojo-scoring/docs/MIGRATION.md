# Migrating llm-entity-extraction / llm-mailroom to llm-dojo-scoring

> **Release checklist:** every `release_chain` cut must bump the
> `__version__` **fallback** in `llm_dojo_scoring/__init__.py` to the new
> release number (the importable value derives from installed metadata via
> `importlib.metadata`; the hardcoded fallback only serves uninstalled
> checkouts, so it must track the cut). Sweep the README badge/pins and the
> `docs/*.md` header stamps in the same commit.

The scoring code that lives in the pipeline projects is now consolidated in
`llm-dojo-scoring`. Migrating is a drop-in import swap — every public name is
kept (same signatures, same return shapes) so the eval runners, Braintrust
scorers, and reporting scripts keep working with minimal edits.

## 4. Verification

After the swap, run the suite and re-export — numbers must be unchanged:

```bash
python -m pytest                                # pipeline's own tests
python scripts/eval/run_subtype_eval.py --dry-run
dojo-export --task all --log reports/experiment_log.jsonl
```

The regenerated `Sorter_Experiment_Results.xlsx` must match the previous
artifact row-for-row (the reference artifacts were produced by this exact
logic).