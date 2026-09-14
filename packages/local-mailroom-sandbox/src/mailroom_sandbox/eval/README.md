<div align="center">

# 🧪 Evaluation Utilities

**Evaluation runners, scoring, matrix, and tracing for the sandbox.**

</div>

---

## Purpose

Drive evaluations against the sandbox pipeline — vendored mailroom agents
through the provider seam, with deterministic scoring and honest mock
labelling.

## Surface

```python
from mailroom_sandbox.eval import runners, scoring, matrix, tracing

# per-agent isolated eval (sorter / contracts / specialists)
runners.run_isolated_eval(agent="sorter", model="mock/mock-...", ...)
# scoring helpers
scoring.accuracy(...)
scoring.exact_match(...)
scoring.compare_local_vs_api(...)
```

There is no top-level `run_evaluation` symbol — the entrypoints live in
`runners`. See `docs/evals.md` for the full eval-task surface and the
`AgentSpec` extension point.

## Related Files

- `../` — Package root
- `../../tests/` — Test suites
- `../../docs/evals.md` — Eval task reference