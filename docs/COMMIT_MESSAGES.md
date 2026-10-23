# Commit messages

A reviewer should understand the problem, resulting behavior and evidence
without reading the conversation. Every commit needs a concrete subject and
an explanatory body. Use the existing `DMR-0NN:` routing prefix for hub work;
follow the owning standalone repository's routing rules for package changes.

Enable the shared template once per clone:

```sh
git config --local commit.template "$(git rev-parse --show-toplevel)/.gitmessage"
```

Then use `git commit` to open it in your editor. Commands using `-m` or `-F`
bypass the editor; their messages must still meet the same standard. The
template contains comments only, so accepting it unchanged produces an empty
message instead of a commit full of placeholders.

## Write the subject around behavior

Use an active verb and the outcome: `prevent`, `preserve`, `reject`, `delegate`,
`restore`, or another precise verb. Name the affected behavior or component.
Keep the subject readable in a one-line history; put detail in the body.

| Avoid | Prefer |
| --- | --- |
| `DMR-091: address CodeAnt comments` | `DMR-091: reject unsupported labels before scoring equivalence` |
| `DMR-091: sync packages` | `DMR-091: import released scoring engines and refresh pinned vendors` |
| `DMR-093: update docs` | `DMR-093: describe the five-package core and preserved feeder branches` |

## Explain the change and its limits

For a small change, one or two paragraphs plus validation can be enough. For
a major or cross-package change, use the template's sections:

- **Problem:** the trigger, prior behavior and practical impact.
- **Changes:** the paths changed, what each group does and why it is needed.
- **Validation:** the commands or named gates, results, and material skips or
  failures. Bug fixes name the regression demonstrated red before the fix and
  green afterward. Separate independent review from tests run by the author.
- **Compatibility and provenance:** changed public behavior, preserved
  contracts and known limits. Source imports name the owner PR, merged SHA or
  immutable release, generation command, exact-byte verification and retained
  overlays. State when a gate or downstream adoption is still pending.
- **References:** the card, issue, PR and durable evidence that help review.

Do not paste the work log, abandoned approaches or a review bot's prompt.
Do not claim a full suite passed when only a focused selection ran. Distinguish
new failures from demonstrated baseline or environment failures.

## Example: a source-owned bug fix

```text
DMR-091: keep private warehouse rows off publicly readable temporary inodes

Problem
A reader could open an empty temporary before chmod and retain access to
private rows written later, including after a failed publication.

Changes
src/storage/warehouse.py creates payload inodes private from the outset.
A separate always-empty probe captures kernel-applied publication permissions.
src/tests/test_runtime_review_objections.py covers retained descriptors,
successful and failed writes, and existing target modes.

Validation
The four retained-descriptor regressions fail on the parent and pass after
the repair. The focused runtime gate passes 73 cases. Independent review
confirms Parquet/JSON failure cleanup, fsync ordering and atomic replacement.
The final full-suite result is recorded separately before merge.

Compatibility and provenance
Existing target permissions and umask-derived first-publication permissions
are preserved. This source-owned repair must merge before the hub imports it.
```

The example records evidence from that specific repair. It is not permission
to reuse those counts for another commit. Write new results for each change.

Review the staged diff before composing the final message. Stage explicit
paths, check that each belongs to the card, use UTC for evidence timestamps,
and verify that the body describes the final diff. Improve future commits
without rewriting published history unless the user explicitly requests it.
