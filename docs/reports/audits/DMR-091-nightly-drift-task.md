# DMR-091 daily source and vendor drift audit

Verified enabled at 2026-10-23T04:25:37Z. Schedule: **23:00 America/Chicago every day**, using the host wall-clock timezone (`/etc/localtime` resolves to America/Chicago). The October 22 trigger dispatched at 2026-10-23T04:00:01Z and its audit turn is queued behind the active reconciliation turn. Scheduler status `succeeded` confirms dispatch, not a completed or clean drift audit. Next trigger: **2026-10-24T04:00:00Z**, October 23 at 23:00 CDT. The first queued audit has not yet produced its required result artifacts.

Task ID: `scheduled-task:command:mcp:cfd57e87-0e5c-421a-b0f9-5d1e2618755b:schedule-task:dmr091-nightly-feeder-vendor-audit-2300-chicago-v1`.

The coordinator must delegate to GPT-6.1-Sol with explicit `reasoningEffort: xhigh` and verify the injected runtime. A missing configuration or network/authentication failure is a failed check, never a clean result.

Each run inspects current canonical `origin/main` in an isolated clone and discovers active packages from `scripts/packages_sync.json`. It compares recorded cursors, immutable standalone tips and complete hub package trees, including additions, deletions, contents and modes. It checks both vendor snapshots independently, runs `sync_vendor.py --check`, and compares open hub PR content with advancing source work to report duplicated or superseded changes. Pending PR coverage must be verified against its current head.

The active manifest governs the audit before and after the separate five-core pruning PR lands. Feature-branch feeder archives preserve history and are not active imports. Source ownership remains standalone-first. No automated edits, imports, commits, pushes, merges, releases, dataset publishing or external messages are authorized.

Timestamped JSON and Markdown results go to `~/.local/state/digital-mailroom/drift-audits/` outside repositories. The task reports in the owning thread and avoids overlapping runs. Corporate live v6 and evaluation v7 remain independent; the audit never regenerates prompts.
