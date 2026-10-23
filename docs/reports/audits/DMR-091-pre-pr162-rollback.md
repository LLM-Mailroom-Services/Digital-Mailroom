# DMR-091 pre-PR162 recovery snapshot

Published 2026-10-23 UTC at the user's request, before PR #162 merges:
[pre-pr162-2026-10-23](https://github.com/LLM-Mailroom-Services/Digital-Mailroom/releases/tag/pre-pr162-2026-10-23).

- Exact canonical main commit: `d77c9db238bf7113e512e2fdcbd65f032a2a9c3b`.
- Tree: `ed1a8c2fc8e7c25e4a1f774e01017b7935d5e7ba`.
- Annotated tag object: `724afd54383d0b15a80f8fa39be5da503b8d445b`.
- Published GitHub prerelease; not latest. Stable release remains `v0.9.0`.
- Assets: source archive (93,741,734 bytes), snapshot manifest, SHA256SUMS.
- Archive SHA256: `0b1775ce03872c6673abdc1588f7a0507e8d9066a4e1ee3cc8a47f2ad91bb2da`.
- Manifest SHA256: `b43251ed6b0807e907bc7147b89246282d89d30c2c614bb849b15b8e7de8e942`.

Verification: remote tag peels to the exact commit; every one of 3,237 archived
tracked paths matches the Git blob and executable/symlink mode. Manifest includes
all seven declared package versions, cursors, package tree IDs and all tracked
vendor entries. Downloaded published assets pass SHA256SUMS. PR #162 was still
open and unmerged after publication. The release did not change main, package
contents, the lockfile or semantic release version.

Inspect the recovery point in a separate checkout:

```sh
git fetch origin tag pre-pr162-2026-10-23
git worktree add --detach ../Digital-Mailroom-pre-pr162 pre-pr162-2026-10-23
```

This captures committed repository state. It does not back up external data,
runtime databases, secrets, installed environments or deployed services. Never
force-update or delete this recovery tag. It is outside the normal semantic
release chain so preserving the exact main tree requires no release-cut commit.
