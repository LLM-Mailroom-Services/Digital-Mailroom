# Feeder resync bundle (2026-09-27)

Commit `dc5eeb1d`: sync **llm-mailroom** `@ddfe6ba` and **local-mailroom-sandbox** `@500eeee` into the monorepo, refresh vendor snapshots, advance `packages_sync.json`.

The verified git bundle lives in **Exios66/llm-dojo-scoring** on branch `cursor/feeder-bundle-host-d595` under `tools/digital-mailroom-feeder-resync/` (avoids multi-megabyte commits on this repo).

After merging the workflow PR, **Apply feeder resync bundle** runs on `main` (or use **workflow_dispatch**) and fast-forwards `main` to `dc5eeb1d`.
