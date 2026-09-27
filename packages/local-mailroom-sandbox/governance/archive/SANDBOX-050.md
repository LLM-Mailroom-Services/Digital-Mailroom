# Archive — SANDBOX-050 mission (superseded by SAND-010)

Historical mission board for the 50-subclass Modal+vLLM sorter run
(2026-09-16). Card IDs used the legacy `SANDBOX-050-*` scheme.

**Superseded by:** epic **`SAND-010`** (+ sub-cards `SAND-010-k`) on
[`../TASKS.md`](../TASKS.md). Prefix for all new sandbox-isolated work is
**`SAND`**, not `SANDBOX` and not `DMR`.

| Legacy ID | SAND ID | Title | Last status |
| --- | --- | --- | --- |
| SANDBOX-050-1 | SAND-010-1 | Verify stratified 50-subclass sample | done |
| SANDBOX-050-2 | SAND-010-2 | Amend run spec to GPU cap + lock | done |
| SANDBOX-050-3 | SAND-010-3 | Preflight + guards loud | in_progress |
| SANDBOX-050-4 | SAND-010-4 | Deploy sandbox-vllm + verify | done |
| SANDBOX-050-5 | SAND-010-5 | Run start → watch → completion | in_progress |
| SANDBOX-050-6 | SAND-010-6 | Teardown | todo |
| SANDBOX-050-7 | SAND-010-7 | Interpret | todo |
| SANDBOX-050-8 | SAND-010-8 | Monorepo sync + board close | todo |

Original mission brief (abridged): real Modal+vLLM run of the
subclass-stratified 50-row sorter eval; GPU hard cap 2; teardown after;
monorepo sync last. Binding specs were `config/runs/run-50-subclass.yaml`
/ `run-50-five-types.yaml`, `deploy/README.md`, `docs/jobs.md`.
