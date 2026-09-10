<div align="center">

# 📚 Monorepo Documentation

**The documentation hub for the Digital-Mailroom monorepo — architecture, contracts, audits, and wiki pages.**

</div>

---

## Structure

| Path | Contents |
|:---|:---|
| [`assets/`](assets/) | Shared documentation assets (images, diagrams) |
| [`reports/`](reports/) | Evaluation reports, audits, and analysis documents |
| [`reports/audits/`](reports/audits/) | Baseline audits and structural analysis |
| [`wiki/`](wiki/) | GitHub-wiki pages (synced via `sync-wiki.sh`) |

## Key Documents

| Document | Description |
|:---|:---|
| `../README.md` | Root monorepo README |
| `../docs/v7-taxonomy.md` | Canonical five-class taxonomy definition |
| `../docs/DOCCLASS_CONTRACT.md` | Dataset contract and versioning rules |
| `../docs/mailroom-corpus-plan.md` | Strategic plan for corpus development |

## Related Documentation

| Package | Docs |
|:---|:---|
| `llm-mailroom` | `packages/llm-mailroom/docs/` — full pipeline documentation |
| `llm-entity-extraction` | `packages/llm-entity-extraction/docs/` — experiment log, slides, memos |
| `mailroom-corpus-eda` | `packages/mailroom-corpus-eda/docs/` — dataset cards, source corpora |

## Wiki

The GitHub wiki is pushed from `wiki/` via `sync-wiki.sh`. Edit wiki-native pages directly in `wiki/`; mirror pages are generated from canonical sources at sync time.
