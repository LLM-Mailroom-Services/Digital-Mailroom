# DMR-092 v0.9.1 pre-PR162 rollback release

Published [v0.9.1](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/releases/tag/v0.9.1)
on 2026-10-23 UTC from merged main `f3c56ec56eb38cbb79c590a8f59ffa012a0efd04`
(release preparation [PR164](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/pull/164)).
PR162 remained open, draft and unmerged throughout publication and verification.

All seven package trees and runtime sources match pre-integration main
`d77c9db238bf7113e512e2fdcbd65f032a2a9c3b` exactly. Only CHANGELOG.md,
root pyproject.toml, uv.lock and governance/TASKS.md differ. Both root version
and virtual lock package are 0.9.1; the lock has no dependency/marker changes.
The generated footer's mislabeled old-version comparison link was corrected.

The remote annotated tag peels to that merged-main commit. The release is
published, stable and latest. Its source archive was verified against every
tracked blob and executable/symlink mode; downloaded assets pass SHA256SUMS.

- Tagged Git tree: `3ca79e5eaf560f519ed309648216a9797629d45d`.
- Verified tracked archive paths: 3,237.
- Source archive SHA256: `9c8c29a70877c1a50d831f50f6ff720cef7322d1ca7e02055155f2e158026e2d`.
- Manifest SHA256: `2018a66e40b95ce5d963a487d2bbe04b5cdb88ccf0f625b8198fe4e24dab88ba`.

Independent GPT-6.1-Sol **xhigh** audit confirmed the runtime setting, complete
package tree identity and release-only import origins. Baseline suites:
**5152 passed, 63 skipped, 3 failed**. Two failures reproduce documented
pipeline storage concurrency defects; one is external mailroom-ml missing
its evaluation entrypoint. This recovery release preserves that state and
does not claim those defects repaired. Root tooling: 62 tests; board API:
23 checks. Lock, release-chain, vendor and taxonomy gates pass; five historical
board reference errors remain. Required `ci` references a deleted workflow
(DMR-080); PR164 used the documented administrative merge path, disclosed
before execution. Branch protection was not changed and no substitute green
status was fabricated.

Inspect the recovery source in a separate checkout:

```sh
git fetch origin tag v0.9.1
git worktree add --detach ../Digital-Mailroom-v0.9.1 v0.9.1
```

The earlier exact-main `pre-pr162-2026-10-23` recovery snapshot remains intact.
External data, runtime databases, secrets, installed environments and deployed
services are outside both source backups.
