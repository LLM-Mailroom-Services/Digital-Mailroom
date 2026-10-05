# Modal L4 Qwen benchmark kit

Operator runbooks live in **one catalog**:
[`config/runbooks/catalog.yaml`](../../config/runbooks/catalog.yaml).

Do not copy serving numbers into this file. Edit the catalog, then:

```bash
sandbox runbook list
sandbox runbook show l4-qwen3-8b          # singular 1×L4 / 1-container Qwen3-8B
sandbox runbook show l4-qwen3-8b-track-a  # Operator A
sandbox runbook show l4-qwen3-8b-track-b  # Operator B
sandbox runbook show improved-awq-c8      # improved configs
sandbox runbook check                     # catalog vs live pins
sandbox runbook write                     # regenerate docs/runbooks/
```

Generated cards:

| Path | Contents |
| --- | --- |
| [`docs/runbooks/README.md`](../runbooks/README.md) | Index + anti-patterns |
| [`docs/runbooks/archived-experiments/qwen/STALE/l4-qwen3-8b.md`](../runbooks/archived-experiments/qwen/STALE/l4-qwen3-8b.md) | Full 5×30 on one L4 / one container |
| [`docs/runbooks/archived-experiments/qwen/STALE/baseline.md`](../runbooks/archived-experiments/qwen/STALE/baseline.md) | Family rollup (tracks + N=20) |
| [`docs/runbooks/specialists/contracts/improved.md`](../runbooks/specialists/contracts/improved.md) | AWQ / c8 / Granite / second L4 / scale-matrix |

Live numeric pins (model, GPU, `max_containers=1`, `max_model_len=16384`, …)
are declared in `serving.baseline` and tested against `deploy/modal_vllm.py`,
`config/models.yaml`, and `config/runs/run-30-*-specialist.yaml`. Per-class
concurrency and cost caps stay in `src/mailroom_sandbox/job/specialist_posture.py`.
Suite order stays in `config/runs/suites/`.

Related: [`modal-serving-ops.md`](modal-serving-ops.md) (warm-once doctrine),
[`scale-matrix.md`](../scale-matrix.md) (4×L4 cells — not the singular path),
[`jobs.md`](../jobs.md) (spec / preflight / resume).
