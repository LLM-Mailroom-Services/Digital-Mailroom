<div align="center">

# 📚 Monorepo Documentation

**The documentation hub for the Digital-Mailroom monorepo — architecture, contracts, audits, and wiki pages.**

</div>

---

## Structure

| Path | Contents |
| :--- | :--- |
| [`assets/`](assets/) | Shared documentation assets (images, diagrams) |
| [`reports/`](reports/) | Evaluation reports, audits, and analysis documents |
| [`reports/audits/`](reports/audits/) | Corpus baseline audits plus DMR-009/091/092/093 branch, import and release audits |
| [`wiki/`](wiki/) | GitHub-wiki pages (synced via `sync-wiki.sh`) |

## Key Documents

| Document | Description |
| :--- | :--- |
| `../README.md` | Root monorepo README |
| `../CONTRIBUTING.md` | Contributor guide: repo routing, card workflow, testing, commits, PRs |
| `../SECURITY.md` | Vulnerability reporting, secrets and data handling |
| `TESTING.md` | Test tiers, per-package commands and the change-type → required-suite matrix |
| `COMMIT_MESSAGES.md` | Shared commit-message template and examples (`.gitmessage`) |
| `v7-taxonomy.md` | Canonical five-class taxonomy definition |
| `DOCCLASS_CONTRACT.md` | Dataset contract and versioning rules |
| `docclass-merged-plan.md` | Strategic plan for corpus development |

## Related Documentation

| Package | Docs |
| :--- | :--- |
| `llm-mailroom` | `packages/llm-mailroom/docs/` — full pipeline documentation |
| `local-mailroom-sandbox` | `packages/local-mailroom-sandbox/docs/` — sandbox, Modal and vLLM guides |
| `mailroom-corpus-eda` | `packages/mailroom-corpus-eda/docs/` — dataset cards, source corpora |

## Wiki

The GitHub wiki is pushed from `wiki/` via `sync-wiki.sh`. Edit wiki-native pages directly in `wiki/`; mirror pages are generated from canonical sources at sync time.
