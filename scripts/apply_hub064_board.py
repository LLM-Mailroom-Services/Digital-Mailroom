#!/usr/bin/env python3
"""Apply HUB-043 archive + HUB-064 spawn to governance/TASKS.md (idempotent)."""
from pathlib import Path
import sys
path = Path("governance/TASKS.md")
text = path.read_text()
if "| HUB-064 |" in text and "**HUB-043** (done 2026-09-08)" in text and "| HUB-043 |" not in "\n".join(l for l in text.splitlines() if l.startswith("| HUB-")):
    print("already applied")
    sys.exit(0)
lines = text.splitlines(keepends=True)
# remove open HUB-043 row
lines = [l for l in lines if not l.startswith("| HUB-043 |")]
hub064 = (
"| HUB-064 | `assigned` | **Gmail triage team → production-ready (edge cases, debugging, configurations)** — spawned at HUB-043 close. Scope: live/hermetic re-send provenance operator proof + runbook; production `.env`/secrets matrix; pathway edge cases (multi-attach, capability handoffs, allowlist, echo/reaction, `watcher.lock`, Space durability); debugging harness (triage I/O, smoke `--real` gates, Langfuse/Phoenix `gmail-triage` checklist); mailroom-corpus sample fixtures for Gmail pilots. Out of scope: reopening HUB-043 unless regression proven. | unclaimed | [#43](https://github.com/Exios66/mailroom-dev/issues/43) | opened 2026-09-08 by CoS / human close of HUB-043 |\n"
)
if "| HUB-064 |" not in "".join(lines):
    rules = next(i for i,l in enumerate(lines) if l.startswith("## Rules that keep the board honest"))
    insert = next(i for i in range(rules-1,-1,-1) if lines[i].startswith("| HUB-")) + 1
    lines.insert(insert, hub064)
arch = (
"- **HUB-043** (done 2026-09-08) — **Watcher filename-only dedup silently drops re-sent Gmail documents (live pilot bug)** — human report 2026-09-04; intake-provenance-aware `_is_already_processed` (`message_id`/`upload_id`) + `test_watcher_dedup.py` on `main`. **CLOSED by human/CoS directive 2026-09-08:** system considered operational; live Gmail re-send proof deferred (credentials not handy / producer not reachable from CoS). GitHub issue https://github.com/Exios66/mailroom-dev/issues/29 closed `completed` + `stage/done`. Follow-up spawned: **HUB-064** ([#43](https://github.com/Exios66/mailroom-dev/issues/43)). Evidence: code on main; CoS close comment on #29; board archive this commit.\n"
)
if "**HUB-043** (done 2026-09-08)" not in "".join(lines):
    ai = next(i for i,l in enumerate(lines) if l.startswith("## Archive"))
    j = ai + 1
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    lines.insert(j, arch)
path.write_text("".join(lines))
print("applied", path)
