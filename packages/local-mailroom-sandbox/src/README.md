<div align="center">

# 🐍 Sandbox Source

**Source code for the local-mailroom-sandbox package.**

</div>

---

## Structure

| Path | Contents |
|:---|:---|
| [`mailroom_sandbox/`](mailroom_sandbox/) | Main package (CLI, runtime, providers, eval) |
| `mailroom_sandbox/eval/` | Evaluation utilities (runners, scoring, matrix, tracing) |

## Package surface

```python
import mailroom_sandbox

mailroom_sandbox.activate()            # put the vendored family srcs on sys.path
mailroom_sandbox.vendored_mailroom_src()  # Path | None — vendor/llm-mailroom/src
mailroom_sandbox.vendored_dojo_src()      # Path | None — vendor/llm-dojo-scoring
```

The full CLI is `sandbox` (see `src/mailroom_sandbox/cli.py` and
`docs/SANDBOX-GUIDE.md`). Evaluations are driven through
`mailroom_sandbox.eval.runners` (e.g. `run_isolated_eval`, the per-agent
`run_*` entrypoints) — there is no top-level `run_evaluation` symbol.

## Related Files

- `tests/` — Test suites
- `config/` — Configuration (taxonomy base/overlay, models, profiles, runs)
- `data/` — Test data