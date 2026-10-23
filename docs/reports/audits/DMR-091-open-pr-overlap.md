# DMR-091 open hub PR overlap disposition

2026-10-23 UTC; frozen heads are listed below. This records review decisions, not new source-main adoption.

| PR / frozen head | Disposition |
| --- | --- |
| [#152](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/152) `c0173ecee90e5f1e90ea8e734ff40de4b75d71f2` | Closed; paired-length fixes are now source-owned in merged Dojo PR58/59 and imported from main. Do not replay the older hub patch. |
| [#153](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/153) `a2695d480f95fcb4f775d57c625866754d9bca63` | Closed; storage/schema concurrency fixes are source-owned in merged pipeline PR115. The retained regression covers actual concurrent writes. |
| [#154](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/154) `2250a55a43e4a57b4d236a0e42bed7c27e6ebe82` | Closed; input-contract docstrings are retained in merged source Dojo revisions. The old hub documentation patch must not overwrite later source behavior. |
| [#156](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/156) `b4c7fa67b39d7ceac6506e689aa9a358949c12e3` | Open, separate hub CI tooling. No package implementation overlap; AGENTS/README/TESTING/board overlap requires a normal content merge. It is not evidence of a currently produced ci status and must not be replaced by a stub green status. |
| [#157](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/157) `05fe21ef0f160e9b11a36f8c31fb1734bc881281` | Open, separate branch-audit/governance scope. Preserve its audit history; merge board/STATE changes by content, not a whole-file override. |
| [#159](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/159) `30ae291cd1c7d59daf704d8f3ea90120c292b21f` | Open/conflicted. Changes pipeline dataset pin to v9.2 and explicitly proposes pushing the hub change back upstream. Current standalone pipeline still pins v9.1; keep this adoption separate and source-first. Do not merge/replay it over the imported pipeline or silently promote dataset revisions. |
| [#160](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/160) `f96552050b5caad4a150dd328af67ec8200b428a` | Open, two additional hub governance tests only. Their suite inventory derives workspace members dynamically and is compatible with the five-member target. Existing-card task markers are historical audit assertions; any later card close should retain history. No scoring/storage/vendor implementation to import. |

PR162 remains the reconciliation unit; PR167 is the separate five-core pruning stack. Neither PR should export package implementation back to a standalone repository. Final imports must recheck source heads and open PR overlap before ready-for-review.

The older reconciliation report is explicitly marked historical; its initial upstream-absence and zero-vendor-drift claims are superseded by the source-first audits.
