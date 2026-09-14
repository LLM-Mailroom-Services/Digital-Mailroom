<div align="center">

# ⚙️ Claims Data EDA Scripts

**Utility scripts for the Claims Data EDA package.**

</div>

---

## Functional index

| Group | Script | Purpose |
|:---|:---|:---|
| **Acquire** | `acquire_synpuf.py` | Acquire the CMS 2008-2010 DE-SynPUF Sample 1 (all 5 file types / 8 ZIPs) |
| **Build** | `build_corpus_index.py` | Normalize the DE-SynPUF Sample-1 CSVs into unified JSONL indexes |
| | `build_pipeline_dump.py` | Build the pipeline-ready `insurance_claim` sample from the index |
| **Publish** | `publish_hf_dataset.py` | Publish the rendered insurance_claim corpus to the Hub |
| **Render** | `render_eob.py` | Deterministic EOB-style document renderer for claim events (**imported by llm-entity-extraction + corpus-eda build**) |
| | `render_samples.py` | Render real corpus documents as PDF samples |
| **QA** | `spot_check.py` | Draw a human-review sample → `reports/eda/spot_check.csv` |
| **EDA** | `eda/explore_cms.py` | CMS DE-SynPUF exploration |

> **Shared-renderer note:** `render_eob.py` is imported by
> `llm-entity-extraction` dataset publishers (`build_extra_claims.py`,
> `publish_docclass_v6.py`, `attach_original_files.py`) and by
> `mailroom-corpus-eda/src/mailroom_eda/v8_build.py`. Do not move or rename
> without updating those consumers.

## Usage

```bash
cd packages/claims-data-eda

# Typical pipeline: acquire → index → dump → render → publish
python scripts/acquire_synpuf.py
python scripts/build_corpus_index.py
python scripts/build_pipeline_dump.py
python scripts/render_samples.py
python scripts/publish_hf_dataset.py
```

## Related Files

- `reports/` — Generated reports and figures
- `tests/` — Test suites