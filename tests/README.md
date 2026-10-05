# Tests

The suite under this directory covers the sandbox CLI, local evaluation and data
flows, serving and job operations, reporting, and repository governance. The
default suite does not make live LLM calls; tests marked `local_llm` are skipped
unless `SANDBOX_LOCAL_LLM=1` is set.

## Run

From the repository root, install the development dependencies and run pytest:

```bash
pip install -e ".[dev]"
pytest -v
```

Useful focused commands:

```bash
pytest --collect-only -q       # list discovered tests without running them
pytest tests/test_eval.py -q    # run one test module
SANDBOX_LOCAL_LLM=1 pytest -m local_llm
```

Pytest is configured to discover tests from this directory and add `src/` to the
Python path; there is no need to change into a package subdirectory.

## Coverage Map

- **Agents, evaluation, and data:** agent and eval behavior (`test_agents`,
  `test_eval`, `test_overlay`); corpus, dataset, and fixture preparation
  (`test_corpus`, `test_datasets`, `test_prep`, `test_sampling`); LegalBench,
  extraction, and scoring (`test_legalbench`, `test_eval_environment_lineage`,
  `test_extraction_scope`, `test_cuad_scoring`, `test_maud_scoring`,
  `test_schema_adherence`, `test_sorter_isolated_shape`,
  `test_modernbert_feeder`, `test_qwen_flash_ledger`).
- **Prompts, providers, and tracing:** prompt loading, registry, provenance,
  injection, simplified-prompt sync, and provider credentials
  (`test_prompts`, `test_prompt_registry`, `test_prompt_provenance`,
  `test_prompt_injection`, `test_simplified_prompts`,
  `test_sync_specialist_prompts`, `test_provider_credentials`); live-or-loud
  behavior and timeouts (`test_live_or_loud`, `test_live_or_loud_sweep`,
  `test_llm_timeout`); tracing backends and offline behavior
  (`test_tracing_braintrust`, `test_tracing_mailroom_scores`, `test_bt_offline`).
- **Serving and deployment:** Compose, environment rendering, Modal/vLLM,
  serving parity and exports, specialist posture, and serving configurations
  (`test_compose`, `test_env`, `test_deploy_env`, `test_modal_vllm`,
  `test_modal_performance`, `test_serving_parity`, `test_serving_report`,
  `test_sand032_configs`, `test_specialist_posture`, `test_vllm_metrics`,
  `test_tunnel`).
- **Jobs and operator interfaces:** job specifications, execution, checkpointing,
  remote work, metrics, telemetry, and trace packs (`test_job_spec`,
  `test_job_runner`, `test_job_checkpoint`, `test_job_cli`, `test_job_remote`,
  `test_job_preflight`, `test_job_metrics`, `test_job_otel`,
  `test_job_trace_pack`); beacon and board, session/tray, and watch UI behavior
  (`test_beacon`, `test_board`, `test_mailroom_session`, `test_tray_context`,
  `test_watch`, `test_watch_demo`, `test_watch_web`, `test_watchdog`,
  `test_watch_screenshots`).
- **Reports, configuration, and project integrity:** report and chart outputs,
  grids, funding, and dated reports (`test_reports_hub`, `test_gpu_report`,
  `test_source_charts`, `test_grid_cards`, `test_grid_master`,
  `test_grid_reader`, `test_funding`, `test_dated_reports`); run suites and
  runbooks (`test_run_suite`, `test_runbooks`); CLI wiring, governance, skills,
  subagents, requirements, vendored files, and regression guards
  (`test_cli_wiring`, `test_governance_sand`, `test_skills`, `test_subagents`,
  `test_requirements`, `test_vendor`, `test_vendor_drift`,
  `test_regression_guards`).

`conftest.py` provides shared pytest fixtures and hooks.
