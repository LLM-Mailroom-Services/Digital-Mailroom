# Operator runbook catalog

**Edit this directory, not the generated markdown.**

| Path | Role |
| --- | --- |
| [`catalog.yaml`](catalog.yaml) | Source of truth for operator runbooks |
| [`../runs/`](../runs/) | Live run specs (engine / dataset / job pins) |
| [`../runs/suites/`](../runs/suites/) | Track A / B / full order |
| [`../models.yaml`](../models.yaml) | Modal model matrix rows |
| [`../../src/mailroom_sandbox/job/specialist_posture.py`](../../src/mailroom_sandbox/job/specialist_posture.py) | Per-class concurrency / caps |
| [`../../docs/runbooks/`](../../docs/runbooks/) | Generated cards (`sandbox runbook write`) |

```bash
sandbox runbook list
sandbox runbook show l4-qwen3-8b          # singular 1×L4 / 1-container Qwen3-8B
sandbox runbook show improved-awq-c8      # improved config
sandbox runbook check
sandbox runbook write                     # refresh docs/runbooks/
```

`sandbox runbook check` fails if catalog serving pins drift from
`deploy/modal_vllm.py`, `config/models.yaml`, or the cited run YAMLs.
