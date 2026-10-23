# Vendored llm-mailroom

Authoritative source: https://github.com/Exios66/llm-mailroom

- Source ref: `main`
- Exact source commit: `c529d3f3e4c10865b90f7d7d4675dbb2b8fbae5e`
- Snapshot layout: src/ minus tests/ and runtime/build artifacts.

Changes originate in the standalone repository, are committed and reviewed
there, then consumed here. Never patch this snapshot or export hub changes
back into the owning repository. The hub workspace and this snapshot must
match after importing this same revision.

Dojo owns scoring; llm-mailroom owns the pipeline. Production corporate v6
and sandbox evaluation v7 remain separate intentional prompt catalogs.
