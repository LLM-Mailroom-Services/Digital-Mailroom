<!-- Generated from config/runbooks/catalog.yaml. Edit the catalog, then: sandbox runbook write -->

# Sandbox Modal + vLLM operator runbooks

1. Change serving pins, variants, or a runbook's steps / configs here.
2. Run `sandbox runbook check` — it must stay green against deploy defaults,
   config/models.yaml, and the cited run YAMLs.
3. Run `sandbox runbook write` so docs/runbooks/ matches the renderer.
4. Commit the catalog + generated docs together.

```bash
sandbox runbook list
sandbox runbook show l4-qwen3-8b          # singular 1×L4 / 1-container Qwen3-8B
sandbox runbook show l4-qwen3-8b-track-a  # Operator A
sandbox runbook show improved-awq-c8      # improved config
sandbox runbook check                     # catalog vs live pins
sandbox runbook write                     # regenerate this directory
```

Source of truth: [`config/runbooks/catalog.yaml`](../../config/runbooks/catalog.yaml).

## Singular L4 / 1-container Qwen3-8B

- [`l4-qwen3-8b`](l4-qwen3-8b.md) — Singular 1×L4 / 1-container Qwen3-8B (full 5×30)
- [`l4-qwen3-8b-track-a`](l4-qwen3-8b-track-a.md) — Operator A — 1×L4 Qwen3-8B (contracts → corporate → correspondence)
- [`l4-qwen3-8b-track-b`](l4-qwen3-8b-track-b.md) — Operator B — 1×L4 Qwen3-8B (merger → insurance)
- [`l4-qwen3-8b-n20`](l4-qwen3-8b-n20.md) — Singular 1×L4 Qwen3-8B — 20-contract probe

## Improved run configurations

- [`improved-awq`](improved-awq.md) — AWQ on 1×L4 (Qwen3-8B-AWQ, contracts N=20)
- [`improved-awq-c8`](improved-awq-c8.md) — AWQ + 32768 + concurrency 8 (contracts N=20)
- [`improved-correspondence-awq`](improved-correspondence-awq.md) — AWQ 32768 correspondence N=20 (concurrency 5)
- [`improved-correspondence-awq-c8`](improved-correspondence-awq-c8.md) — AWQ 32768 correspondence N=20 (concurrency 8)
- [`improved-correspondence-fp16-c8`](improved-correspondence-fp16-c8.md) — FP16 isolation twin of correspondence AWQ-c8 — **BLOCKED**
- [`improved-granite-fp8`](improved-granite-fp8.md) — Granite 4.2-8B FP8 on 1×L4 (SAND-027 Leg A swap-in)
- [`improved-second-l4`](improved-second-l4.md) — Second L4 — data parallel (still 1 GPU / container)
- [`improved-scale-matrix`](improved-scale-matrix.md) — L4 scale-matrix cells (not the singular 1-container path)

## Anti-patterns

| Anti-pattern | Cost | Instead |
| --- | --- | --- |
| Independent sandbox run start per config | a cold boot per run | sandbox run suite (or a catalog runbook with warm-once steps) |
| modal deploy --strategy recreate between classes | image + weight reload | deploy once per matrix / track |
| Concurrency 3–4 on light classes after a c8 probe | leftover continuous-batching headroom | re-derive per class (keep ≤ replicas × max_num_seqs) |
| scaledown 600 while iterating attended | container dies mid-matrix, re-pay boot | 120 attended / 600 overnight only |
| H100 for n≤100 specialist docs | ~4.9× $/hr without a matching wall cut | stay on 1×L4 |
