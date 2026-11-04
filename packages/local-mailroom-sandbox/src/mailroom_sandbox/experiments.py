"""Guided experimental designs composed from existing locked sandbox runs.

Create and review never deploy. Launch prepares every dataset/prompt first, obtains
initials, then deploys one cell at a time, smoke-tests a separate locked subset,
runs its jobs, and tears down that exact app even on failure.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import statistics
import sys
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from mailroom_sandbox.job import preflight
from mailroom_sandbox.job.checkpoint import RunStore, _atomic_write
from mailroom_sandbox.job.deploy_env import spec_env
from mailroom_sandbox.job.grid_cards import collect_card
from mailroom_sandbox.job.metrics import infer_wall_seconds_from_store
from mailroom_sandbox.job.otel import pipeline_provider
from mailroom_sandbox.job.sand42_cards import _summary as sand42_summary, paired_delta
from mailroom_sandbox.job.spec import DatasetSpec, FAMILY_HF_REVISION, ReviewerSpec, RunSpec, load_run_spec, run_dir
from mailroom_sandbox.job.spend import authorize, review_settings
from mailroom_sandbox.paths import repo_root
from mailroom_sandbox.services._exec import ServiceError, ToolFailed, stream_tool
from mailroom_sandbox.services._redact import redact_urls

CLASSES = {
    'contract': 'contracts-specialist', 'corporate_record': 'corporate-records-specialist',
    'correspondence': 'correspondence-specialist', 'insurance_claim': 'insurance-claims-specialist',
    'merger_agreement': 'merger-specialist',
}
DESIGNS = {'single': [(1, 8)], 'sand42': [(1, 8), (1, 16), (2, 8), (2, 16)]}


class Plan(BaseModel):
    model_config = ConfigDict(extra='forbid')
    schema_name: str = Field(default='sandbox.experiment/v1', alias='schema')
    study: str
    design: str
    runs: list[str] = Field(min_length=1)
    smoke_rows: int = Field(default=1, ge=1, le=5)
    smoke_cost_cap_usd: float = Field(default=0.10, gt=0, allow_inf_nan=False)
    smoke_wall_seconds: int = Field(default=120, ge=60)


def _load(path: str | Path) -> tuple[Path, Plan, list[tuple[Path, RunSpec]]]:
    path = Path(path).resolve()
    try:
        plan = Plan.model_validate(yaml.safe_load(path.read_text()))
        if plan.schema_name != 'sandbox.experiment/v1':
            raise ValueError('unsupported experiment schema')
        runs = [(path.parent / name, load_run_spec(path.parent / name)) for name in plan.runs]
        ids = [spec.run_id for _, spec in runs]
        if any(not name for name in ids) or len(set(ids)) != len(ids):
            raise ValueError('every run needs a distinct run_id')
        if any(spec.job.mode != 'endpoint' for _, spec in runs):
            raise ValueError('experiment launch currently requires job.mode: endpoint')
        if len({spec.job.mock for _, spec in runs}) != 1:
            raise ValueError('a design cannot mix mock and paid runs')
        return path, plan, runs
    except (ValueError, OSError, yaml.YAMLError) as exc:
        raise ServiceError(f'cannot load experiment: {exc}') from exc


def _quotas(buckets: list[dict], count: int) -> list[dict]:
    """Rescale published subclass quotas exactly, preserving each stratum when possible."""
    if count == sum(bucket['count'] for bucket in buckets):
        return copy.deepcopy(buckets)
    ordered = sorted(enumerate(buckets), key=lambda pair: (-pair[1]['count'], pair[0]))
    if count < len(buckets):
        return [{**bucket, 'count': 1} for _, bucket in ordered[:count]]
    weights = [bucket['count'] for bucket in buckets]
    available = count - len(buckets)
    raw = [available * weight / sum(weights) for weight in weights]
    counts = [1 + math.floor(value) for value in raw]
    for index in sorted(range(len(raw)), key=lambda i: (-(raw[i] % 1), i))[:count-sum(counts)]:
        counts[index] += 1
    return [{**bucket, 'count': n} for bucket, n in zip(buckets, counts)]


def _set(data: dict, assignment: str) -> None:
    name, sep, value = assignment.partition('=')
    if not sep:
        raise ServiceError('--set needs PATH=YAML_VALUE')
    parts = name.split('.')
    if parts[0] not in {'engine', 'job', 'trace', 'dataset', 'prompt', 'agent_knobs'}:
        raise ServiceError(f'unsupported setting {name!r}')
    target = data
    for part in parts[:-1]:
        if part not in target or not isinstance(target[part], dict):
            raise ServiceError(f'unknown configuration path {name!r}')
        target = target[part]
    if parts[-1] not in target:
        raise ServiceError(f'unknown configuration path {name!r}')
    try:
        target[parts[-1]] = yaml.safe_load(value)
    except yaml.YAMLError as exc:
        raise ServiceError(f'invalid YAML value for {name}: {exc}') from exc


def _reviewer_settings(reviewer: str | None, classes: list[str] | None) -> dict | None:
    """The frozen decision reviewer from ``BACKEND:MODEL`` and ``CLASS=CUTOFF`` flags (None when unset)."""
    if not reviewer and not classes:
        return None
    if not reviewer or not classes:
        raise ServiceError('--decision-reviewer and --decision-class must be given together')
    backend, sep, model = reviewer.partition(':')
    if not sep or not backend or not model:
        raise ServiceError('--decision-reviewer must be BACKEND:MODEL, e.g. decisions:openai/gpt-6-luna-decisions, jev:jev-1.13.0 or local:Org/Model')
    from mailroom_sandbox.overlay import live_doc_classes

    live = live_doc_classes()
    cutoffs = {}
    for item in classes:
        name, equals, raw = item.partition('=')
        try:
            cutoff = float(raw)
        except ValueError:
            cutoff = None
        if not name or not equals or cutoff is None:
            raise ServiceError(f'--decision-class must be CLASS=CUTOFF, got {item!r}')
        if name not in live:
            raise ServiceError(f'--decision-class {name!r} is not a live taxonomy class; valid: {sorted(live)}')
        if name in cutoffs:
            raise ServiceError(f'--decision-class {name!r} given more than once')
        cutoffs[name] = cutoff
    try:
        extra = {}
        if backend == 'decisions':
            from mailroom_sandbox.decision_backends import frontrunner_question_set

            extra['questions'] = frontrunner_question_set()
        return ReviewerSpec(backend=backend, model=model, classes=cutoffs, **extra).model_dump()
    except ValueError as exc:
        raise ServiceError(f'invalid decision reviewer: {exc}') from exc
def _local_strata(path: Path) -> dict[str, list[str]]:
    """Subclasses of the scoreable rows per doc class in a local JSONL.

    Rows are read as the corpus loader keys them and kept only when they carry
    the task ground truth the generated specs require (``require_task_gt``).
    """
    from mailroom_sandbox.corpus import _has_task_gt

    out: dict[str, list[str]] = defaultdict(list)
    try:
        text = path.read_text(encoding='utf-8')
    except OSError as exc:
        raise ServiceError(f'cannot read --local-dataset {path}: {exc}') from exc
    for line in text.split('\n'):  # JSONL records end at \n only; strings may hold U+2028
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        doc_class = row.get('expected') or row.get('expected_doc_class') or row.get('doc_type')
        fields = row.get('expected_fields') if row.get('expected_fields') is not None else row.get('gt_fields')
        if isinstance(fields, str):
            try:
                fields = json.loads(fields or '{}')
            except ValueError:
                fields = {}
        if doc_class and _has_task_gt({'expected_doc_class': doc_class, 'expected_fields': fields or {}}):
            out[str(doc_class)].append(str(row.get('expected_subclass') or ''))
    return dict(out)


def _fills(local: dict[str, list[str]], doc_class: str, quota: dict) -> bool:
    """Whether the local rows can fill one subclass quota, matched as the sampler matches."""
    from mailroom_sandbox.corpus import _subclass_matches

    have = sum(_subclass_matches({'expected_doc_class': doc_class, 'expected_subclass': sub}, quota['subclass'])
               for sub in local.get(doc_class, []))
    return have >= quota['count']


def _create(args) -> int:
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,23}', args.study):
        raise ServiceError('study must be 1–24 lowercase letters/digits/hyphens')
    if args.max_tokens < 1 or not math.isfinite(args.temperature) or not 0 <= args.temperature <= 2:
        raise ServiceError('max tokens must be positive; temperature must be finite in [0, 2]')
    if args.samples < 1:
        raise ServiceError('sample size must be positive')
    for flag, value in (('--cost-cap-usd', args.cost_cap_usd), ('--api-cost-cap-usd', args.api_cost_cap_usd)):
        if value is not None and (not math.isfinite(value) or value <= 0):
            raise ServiceError(f'{flag} must be a finite positive number (omit it to use the recommendation)')
    if args.max_wall_seconds is not None and args.max_wall_seconds < 60:
        raise ServiceError('--max-wall-seconds must be >= 60 (omit it to use the recommendation)')
    if not re.fullmatch(r'[a-fA-F0-9]{40}', args.revision):
        raise ServiceError('pin --revision to a full Hugging Face commit SHA')
    root = Path(args.output or repo_root() / 'config' / 'experiments' / args.study).resolve()
    if root.exists():
        raise ServiceError(f'{root} already exists; choose a new study/output (nothing overwritten)')
    cells = DESIGNS[args.design]
    local = _local_strata(Path(args.local_dataset)) if args.local_dataset else None
    if local is not None:
        from mailroom_sandbox.corpus import _subclass_matches

        for name in args.doc_class or list(CLASSES):
            # Count only rows the subclass filter can retain.
            subclasses = local.get(name, [])
            have = sum(
                not args.subclass or any(
                    _subclass_matches({'expected_doc_class': name, 'expected_subclass': sub}, requested)
                    for requested in args.subclass
                )
                for sub in subclasses
            )
            if have < args.samples:
                raise ServiceError(f'--local-dataset has {have} scoreable {name} row(s); lower --samples to '
                                   f'{max(have, 1)} or drop that class with --doc-class')
    if args.design == 'sand42' and (args.replicas is not None or args.concurrency is not None):
        raise ServiceError('sand42 fixes replica/concurrency axes at {1,2} × {8,16}; use single for custom values')
    selected = args.doc_class or list(CLASSES)
    generated = []
    from mailroom_sandbox.agent_routes import (critical_route, known_agents, live_specialists, parse_routes,
                                               specialist_tier)
    routes = parse_routes(args.agent_routes)
    from mailroom_sandbox.overlay import parse_agent_models
    try:
        agent_models = parse_agent_models(getattr(args, 'agent_models', None))
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc
    reviewer = _reviewer_settings(getattr(args, 'decision_reviewer', None), getattr(args, 'decision_class', None))

    def scoped(route):
        # One app per tier model per study, so the judge and `full` specialists share it.
        route = route.model_copy(deep=True)
        route.modal.app = f"sandbox-vllm-{args.study}-{route.modal.app.removeprefix('sandbox-vllm-critical-')}"
        return route

    # SAND-078: on Modal the judge runs a larger sibling of the base model on its
    # own app. OpenRouter keeps the profile's judge; an explicit judge pin wins.
    if (args.provider == 'modal-vllm' and args.design != 'sand42' and args.task == 'pipeline'
            and 'judge' not in routes and 'judge' not in agent_models and (judge := critical_route('judge'))):
        routes['judge'] = scoped(judge)
    # SAND-079: move the specialists to the mid or full tier; explicit pins win.
    if args.specialist_tier != 'base':
        if args.design == 'sand42' or args.task == 'sorter':
            raise ServiceError('--specialist-tier applies to specialists/pipeline experiments, not sand42 or sorter')
        tier = specialist_tier(args.specialist_tier, args.provider)
        for name in live_specialists():
            if name in routes or name in agent_models:
                continue
            if isinstance(tier, str):
                agent_models[name] = tier
            else:
                routes[name] = scoped(tier)
    if args.design == 'sand42':  # frozen study: keeps its AWQ / champion pair
        default_model = 'Qwen/Qwen3-8B-AWQ' if args.provider == 'modal-vllm' else 'qwen/qwen3.7-flash'
    else:  # SAND-077: Qwen3.5-9B on Modal, the same weights on OpenRouter
        default_model = 'Qwen/Qwen3.5-9B' if args.provider == 'modal-vllm' else 'qwen/qwen3.5-9b'
    chosen_model = args.model or default_model
    for cell_index, (replicas, concurrency) in enumerate(cells):
        for doc_class in (selected if args.task == 'specialists' else [selected[0]]):
            template = repo_root() / 'config' / 'runs' / f'sand42-50-{CLASSES[doc_class]}-awq-1l4-c8.yaml'
            spec = load_run_spec(template)
            data = spec.model_dump(by_alias=True)
            label = f'{replicas}r-c{args.concurrency or concurrency}'
            data['run_id'] = f'{args.study}-{CLASSES[doc_class] if args.task == "specialists" else args.task}-{label}'
            data['runbook_id'] = None
            data['note'] = f'{args.design} design; paired class draws, seed {args.seed}; cell {cell_index+1}'
            data['profile'] = args.provider
            data['engine']['kind'] = args.provider
            data['engine']['model'] = chosen_model
            if args.provider == 'modal-vllm' and chosen_model != spec.engine.model:
                from mailroom_sandbox.modal_matrix import resolve_modal_row
                try:
                    row = resolve_modal_row(chosen_model, gpu_override=args.gpu)
                except (KeyError, ValueError) as exc:
                    raise ServiceError(str(exc)) from exc
                data['engine']['vllm'].update(max_model_len=int(row['env']['MODAL_VLLM_MAX_MODEL_LEN']), quantization=row['env']['MODAL_VLLM_QUANTIZATION'])
            if args.provider == 'modal-vllm':
                data['engine']['modal'].update(app=f'sandbox-vllm-{args.study}-{label}', gpu=args.gpu,
                    min_containers=0, max_containers=args.replicas or replicas, named_image=args.named_image)
            else:
                data['engine']['modal'] = None
            # None = fill from the design-informed recommendation once the spec is complete.
            data['job'].update(mock=args.mock, mode='endpoint', concurrency=args.concurrency or concurrency,
                               cost_cap_usd=args.cost_cap_usd, max_wall_seconds=args.max_wall_seconds,
                               api_cost_cap_usd=args.api_cost_cap_usd)
            ds = data['dataset']
            ds.update(repo=args.dataset, config=args.dataset_config, split=args.split, revision=args.revision,
                      limit=args.samples, sample_seed=args.seed, require_task_gt=True)
            bucket = ds['strata']['buckets'][0]
            bucket['count'] = args.samples
            if bucket.get('sub_buckets'):
                bucket['sub_buckets'] = _quotas(bucket['sub_buckets'], args.samples)
                # The published quotas name Hub subclasses; a local file may hold others.
                if local is not None and not all(_fills(local, doc_class, sb) for sb in bucket['sub_buckets']):
                    del bucket['sub_buckets']
            if args.task != 'specialists':
                data['task'] = args.task
                ds['strata'] = {'buckets': [{'doc_class': name, 'count': args.samples} for name in selected]}
                ds['limit'] = args.samples * len(selected)
                data['prompt']['agents'] = {}
                for name in selected:
                    template_spec = load_run_spec(repo_root() / 'config' / 'runs' / f'sand42-50-{CLASSES[name]}-awq-1l4-c8.yaml')
                    data['prompt']['agents'].update(template_spec.prompt.get('agents', {}))
            if args.subclass:
                ds['strata'] = {'expected': selected if args.task != 'specialists' else [doc_class], 'expected_subclass': args.subclass}
            if args.local_dataset:
                ds.update(provider='file', local_path=str(Path(args.local_dataset).resolve()))
            data['job']['task'] = data['task']
            data['trace'].update(sink=args.trace_sink, otlp=args.trace_sink != 'none', endpoint=args.trace_endpoint,
                                 environment=args.study, tags=['sandbox', 'experiment', args.study, label])
            data['agent_knobs'] = {name: {'max_tokens': args.max_tokens, 'temperature': args.temperature} for name in (known_agents() if args.task == 'pipeline' else [data['task']])}
            data['agent_models'] = dict(agent_models)
            data['reviewer'] = reviewer
            data['agent_routes'] = {name: route.model_dump() for name, route in routes.items()}
            for name, route in data['agent_routes'].items():
                if route['provider'] == 'modal-vllm':
                    route['modal']['named_image'] = args.named_image
                if route['provider'] == 'modal-vllm' and route['modal']['app'].startswith('sandbox-vllm-route-'):
                    route_key = hashlib.sha256(json.dumps({'model': route['model'], 'gpu': args.gpu, 'vllm': route['vllm']}, sort_keys=True).encode()).hexdigest()[:8]
                    route['modal'].update(app=f'sandbox-vllm-{args.study}-{route_key}-{label}', gpu=args.gpu,
                                          max_containers=args.replicas or replicas)
                elif route['provider'] == 'modal-vllm' and args.design == 'sand42':
                    route['modal']['max_containers'] = replicas
                if name in data['agent_models']:
                    route['model'] = data['agent_models'][name]
            for setting in args.settings:
                _set(data, setting)
            try:
                # Unknown parameter names must fail rather than silently disappear.
                for section, model in [('engine', spec.engine), ('job', spec.job), ('trace', spec.trace), ('dataset', spec.dataset)]:
                    if set(data[section]) - set(type(model).model_fields):
                        raise ValueError(f'unknown {section} fields')
                result = _with_recommended_budget(RunSpec.model_validate(data))
                if result.job.mode != 'endpoint':
                    raise ValueError('experiment launch requires endpoint mode')
            except ValueError as exc:
                raise ServiceError(f'invalid experiment settings: {exc}') from exc
            generated.append(result)
    ids = [spec.run_id for spec in generated]
    if len(set(ids)) != len(ids):
        raise ServiceError('selected axes produce duplicate runs; remove --concurrency for the sand42 grid')
    try:
        plan = Plan(study=args.study, design=args.design, runs=[f'runs/{spec.run_id}.yaml' for spec in generated],
                    smoke_rows=args.smoke_rows, smoke_cost_cap_usd=args.smoke_cost_cap_usd)
    except ValueError as exc:
        raise ServiceError(f'invalid smoke settings: {exc}') from exc
    root.mkdir(parents=True)
    (root / 'runs').mkdir()
    for name, spec in zip(plan.runs, generated):
        (root / name).write_text(yaml.safe_dump(spec.model_dump(by_alias=True), sort_keys=False))
    manifest = root / 'experiment.yaml'
    manifest.write_text(yaml.safe_dump(plan.model_dump(by_alias=True), sort_keys=False))
    print(f'Created {manifest} ({len(generated)} runs; no downloads or paid actions).')
    _print_budget(generated)
    print(f'Next: sandbox experiment preflight --config {manifest}')
    return 0


def _with_recommended_budget(spec: RunSpec) -> RunSpec:
    """Fill every unset ceiling from the design-informed recommendation (SAND-089).

    Flags and --set values win; a GPU cap is only filled for runs that warm a Modal
    GPU, an API cap only for runs that bill API tokens.
    """
    from mailroom_sandbox.job.budget_advice import recommend

    advice = recommend(spec)
    job = spec.job.model_dump()
    if job['cost_cap_usd'] is None:
        job['cost_cap_usd'] = advice['gpu_cost_cap_usd']
    if job['max_wall_seconds'] is None:
        job['max_wall_seconds'] = advice['max_wall_seconds']
    if job['api_cost_cap_usd'] is None:
        job['api_cost_cap_usd'] = advice['api_cost_cap_usd']
    data = spec.model_dump(by_alias=True)
    data['job'] = job
    return RunSpec.model_validate(data)


def _budget_rows(specs) -> list[dict]:
    from mailroom_sandbox.job.budget_advice import compare, recommend

    rows = []
    for spec in specs:
        advice = recommend(spec)
        rows.append({'run_id': spec.run_id,
                     'configured': {'cost_cap_usd': spec.job.cost_cap_usd, 'max_wall_seconds': spec.job.max_wall_seconds,
                                    'api_cost_cap_usd': spec.job.api_cost_cap_usd},
                     'recommended': {'cost_cap_usd': advice['gpu_cost_cap_usd'],
                                     'max_wall_seconds': advice['max_wall_seconds'],
                                     'api_cost_cap_usd': advice['api_cost_cap_usd']},
                     'basis': advice['basis'], 'warnings': compare(spec, advice)})
    return rows


def _print_budget(specs) -> None:
    def money(value):
        return '-' if value is None else f'${value:.2f}'

    print('Budget ceilings (configured / recommended from the design; GPU = Modal time, API = tokens):')
    for row in _budget_rows(specs):
        have, want = row['configured'], row['recommended']
        print(f"  {row['run_id']}: GPU {money(have['cost_cap_usd'])} / {money(want['cost_cap_usd'])}  "
              f"wall {have['max_wall_seconds']}s / {want['max_wall_seconds']}s  "
              f"API {money(have['api_cost_cap_usd'])} / {money(want['api_cost_cap_usd'])}")
        for warning in row['warnings']:
            print(f'    warning: {warning}')


@contextmanager
def _environment(spec: RunSpec):
    """Use only reviewed deploy/model settings; restore the caller environment on exit."""
    overrides = spec_env(spec) if spec.engine.kind == 'modal-vllm' else {}
    overrides['VLLM_MODEL'] = spec.engine.model
    overrides['OBSERVABILITY_PROVIDER'] = pipeline_provider(spec.trace.sink)
    overrides['OBSERVABILITY_ENVIRONMENT'] = spec.trace.environment
    if spec.engine.kind == 'modal-vllm' and os.environ.get('MODAL_VLLM_API_TOKEN'):
        overrides['VLLM_API_KEY'] = os.environ['MODAL_VLLM_API_TOKEN']
    if spec.engine.kind == 'modal-vllm' and spec.engine.modal:
        workspace = os.environ.get('MODAL_WORKSPACE', '').strip()
        if workspace:
            overrides['VLLM_BASE_URL'] = f'https://{workspace}--{spec.engine.modal.app}-serve.modal.run/v1'
    saved = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            if value:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _prepare(path: Path, plan: Plan, runs: list[tuple[Path, RunSpec]]) -> list[RunStore]:
    from mailroom_sandbox.runtime import load_env_file
    load_env_file()
    stores = []
    paired = {}
    for config, spec in runs:
        with _environment(spec):
            report = preflight.preflight(spec, config_path=config, offline=spec.job.mock, live=False)
        if report.get('status') != 'prepared':
            raise ServiceError(f"preflight refused {spec.run_id}: {redact_urls(json.dumps(report))}")
        store = RunStore(run_dir(report['run_id']))
        lock = store.verify_generation()
        rows = store.dataset_rows()
        if not rows or (spec.dataset.limit and len(rows) != spec.dataset.limit):
            raise ServiceError(f'{spec.run_id}: requested {spec.dataset.limit} rows, prepared {len(rows)}; no spend authorized')
        fingerprint = hashlib.sha256(store.dataset_path.read_bytes()).hexdigest()
        if spec.task in paired and paired[spec.task] != fingerprint:
            raise ServiceError(f'{spec.task}: cells have different dataset bytes; paired comparison refused')
        paired[spec.task] = fingerprint
        if not spec.job.mock:
            from mailroom_sandbox.agent_routes import validate
            validate(spec.agent_routes, credentials=True)
            from mailroom_sandbox.job.spend import require_budget
            require_budget(lock)
            if _uses_default(spec) and spec.engine.kind == 'openrouter' and not os.environ.get('OPENROUTER_API_KEY', '').strip():
                raise ServiceError('set OPENROUTER_API_KEY before preparing an API experiment')
            if _uses_default(spec) and spec.engine.kind == 'modal-vllm' and not os.environ.get('MODAL_WORKSPACE', '').strip():
                raise ServiceError('experiment launch needs MODAL_WORKSPACE to address each scoped cell app')
            if spec.trace.sink != 'none':
                try:
                    from opentelemetry.sdk.trace import TracerProvider  # noqa: F401 - availability probe
                    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # noqa: F401 - availability probe
                except ImportError as exc:
                    raise ServiceError('selected trace sink requires pip install -e ".[observability]"') from exc
        _deployments(spec)
        stores.append(store)
    return stores


def _review(path: Path, plan: Plan, runs, stores=None) -> dict:
    rows = []
    for index, (config, spec) in enumerate(runs):
        with _environment(spec):
            settings = review_settings(stores[index]) if stores else spec.model_dump(by_alias=True)
        rows.append({'config': str(config), 'review': settings})
        rows[-1]['managed_deployments'] = [{'model': item.engine.model, 'modal': item.engine.modal.model_dump(),
            'vllm': item.engine.vllm.model_dump(), 'environment': spec_env(item)} for item in _deployments(spec)]
    for row, budget in zip(rows, _budget_rows([spec for _, spec in runs])):
        row['budget'] = budget
    return {'study': plan.study, 'design': plan.design, 'runs': rows,
            'smoke_rows_per_run': plan.smoke_rows, 'smoke_cost_cap_usd': plan.smoke_cost_cap_usd,
            'smoke_wall_seconds': plan.smoke_wall_seconds,
            'sum_run_and_smoke_caps_usd': sum(float(spec.job.cost_cap_usd or 0) + plan.smoke_cost_cap_usd for _, spec in runs),
            'sum_api_caps_usd': sum(float(spec.job.api_cost_cap_usd or 0) for _, spec in runs),
            'spend': 'mock; no provider calls' if all(spec.job.mock for _, spec in runs) else 'Modal/OpenRouter: initials required before paid actions',
            'observer': f'sandbox experiment watch --config {path}',
            'reports': f'sandbox experiment report --config {path}'}


def _cmd_review(args) -> int:
    path, plan, runs = _load(args.config)
    print(redact_urls(json.dumps(_review(path, plan, runs), indent=2)))
    return 0


def _cmd_preflight(args) -> int:
    path, plan, runs = _load(args.config)
    stores = _prepare(path, plan, runs)
    print(redact_urls(json.dumps(_review(path, plan, runs, stores), indent=2)))
    print('Preflight prepared all locked datasets/prompts. No provider/deploy request made. Next: sandbox experiment launch --config ' + str(path))
    return 0


def _execute(store: RunStore) -> dict:
    from mailroom_sandbox import cli
    result = cli._run_endpoint(store, argparse.Namespace(watch=False, max_items=None))
    _atomic_write(store.dir / 'experiment-result.json', json.dumps({'generation_id': store.read_lock().get('generation_id'),
        'scores': result.get('scores', {}), 'summary': store.summary()}, default=str, indent=2))
    return result


def _smoke(spec: RunSpec, store: RunStore, plan: Plan) -> None:
    source = store.dir / 'smoke-input.jsonl'
    rows = store.dataset_rows()[:plan.smoke_rows]
    if spec.task == 'pipeline':
        counts = defaultdict(int)
        rows = []
        for row in store.dataset_rows():
            doc_class = row.get('expected_doc_class')
            if counts[doc_class] < plan.smoke_rows:
                rows.append(row)
                counts[doc_class] += 1
    _atomic_write(source, ''.join(json.dumps(row) + '\n' for row in rows))
    smoke = spec.model_copy(deep=True)
    smoke.run_id = spec.run_id[:53] + '-s' + hashlib.sha256(spec.run_id.encode()).hexdigest()[:8]
    smoke.dataset = DatasetSpec(provider='file', local_path=str(source), limit=len(rows))
    smoke.job.concurrency = min(spec.job.concurrency, len(rows))
    smoke.job.cost_cap_usd = min(float(spec.job.cost_cap_usd or plan.smoke_cost_cap_usd), plan.smoke_cost_cap_usd)
    smoke.job.max_wall_seconds = min(spec.job.max_wall_seconds or plan.smoke_wall_seconds, plan.smoke_wall_seconds)
    if spec.job.api_cost_cap_usd is not None:
        smoke.job.api_cost_cap_usd = min(float(spec.job.api_cost_cap_usd), plan.smoke_cost_cap_usd)
    smoke.agent_knobs = copy.deepcopy((store.read_lock() or {}).get('agent_knobs') or {})
    report = preflight.preflight(smoke, offline=smoke.job.mock, live=False)
    if report.get('status') != 'prepared':
        raise ServiceError(f'smoke preflight refused: {report}')
    smoke_store = RunStore(run_dir(smoke.run_id))
    _execute(smoke_store)
    result = smoke_store.summary()
    # Whole-run summaries historically called every processed row successful;
    # the persisted per-document evidence is the authoritative smoke gate.
    if result.get('state') != 'done' or result.get('ok') != len(rows) or result.get('errors'):
        raise ServiceError(f'smoke failed for {spec.run_id}: {result}; full run was not started')
    store.append_event('experiment_smoke_passed', 'info', smoke_run_id=smoke.run_id, rows=len(rows))


def _route_model_ids(name: str, route, base: str, headers: dict[str, str], spec: RunSpec) -> list[str]:
    """Read ``/models`` for a route, waiting out a scale-to-zero boot.

    A managed Modal route holds the request open (minutes) while its container
    boots, so the old single 60 s GET failed verification and tore down a
    healthy app. Reuse the preflight boot budget; a refused connection still
    means a dead/wrong endpoint and fails fast.
    """
    import time

    import httpx

    budget_spec = spec.model_copy(deep=True)
    if route.provider == 'modal-vllm':
        budget_spec.engine.kind = 'modal-vllm'
    budget = preflight.probe_timeout_seconds(budget_spec)
    deadline = time.monotonic() + budget
    last_error: Exception | None = None
    while True:
        timeout = max(1.0, deadline - time.monotonic())
        try:
            models = httpx.get(base + '/models', headers=headers, timeout=timeout)
            models.raise_for_status()
            return [row.get('id') for row in models.json().get('data', [])]
        except httpx.ConnectError:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
        if time.monotonic() >= deadline:
            raise ServiceError(
                f'{name}: no /models response within the {budget:.0f}s probe budget: '
                + redact_urls(str(last_error))
            )
        time.sleep(1.0)


def _probe(spec: RunSpec) -> None:
    from mailroom_sandbox.health import probe_chat
    from mailroom_sandbox.overlay import load_profile
    if _uses_default(spec) and spec.engine.kind == 'modal-vllm':
        result = preflight.probe_engine(spec)
        if not result.get('ok'):
            raise ServiceError('engine verification failed: ' + redact_urls(json.dumps(result)))
    profile = load_profile(spec.profile)
    profile['default_model'] = spec.engine.model
    if _uses_default(spec):
        result = probe_chat(profile, timeout=60)
        if not result.ok:
            raise ServiceError('chat smoke failed: ' + redact_urls(result.detail))


    if spec.agent_routes:
        import httpx
        from mailroom_sandbox.agent_routes import endpoint, credential_env
        for name, route in spec.agent_routes.items():
            route = route.model_copy(deep=True)
            route.model = spec.agent_models.get(name) or route.model
            base = endpoint(route)
            key = os.environ.get(credential_env(route), '')
            headers = {'Authorization': f'Bearer {key}'} if key else {}
            try:
                if route.provider in {'modal-vllm', 'vllm'}:
                    ids = _route_model_ids(name, route, base, headers, spec)
                    if route.model not in ids:
                        raise ServiceError(f'{name}: endpoint does not serve {route.model}')
                response = httpx.post(base + '/chat/completions', headers=headers, timeout=60,
                    json={'model': route.model, 'messages': [{'role': 'user', 'content': 'Reply OK.'}], 'max_tokens': 8})
                response.raise_for_status()
                if not response.json().get('choices'):
                    raise ServiceError(f'{name}: chat smoke returned no choices')
            except (httpx.HTTPError, ValueError) as exc:
                raise ServiceError(f'{name}: route verification failed: {redact_urls(str(exc))}') from exc


def _uses_default(spec: RunSpec) -> bool:
    from mailroom_sandbox.agent_routes import known_agents
    agents = known_agents() if spec.task == 'pipeline' else {spec.task}
    return bool(agents - set(spec.agent_routes))


def _deployments(spec: RunSpec) -> list[RunSpec]:
    """Distinct managed engines in this cell, including per-agent Modal routes."""
    engines = []
    if _uses_default(spec) and spec.engine.kind == 'modal-vllm':
        engines.append(spec.model_copy(deep=True))
    for name, route in spec.agent_routes.items():
        if route.provider != 'modal-vllm':
            continue
        deployment = spec.model_copy(deep=True)
        deployment.profile = 'modal-vllm'
        deployment.engine.kind = 'modal-vllm'
        deployment.engine.model = (spec.agent_models or {}).get(name) or route.model
        deployment.engine.modal = route.modal.model_copy(deep=True)
        deployment.engine.vllm = route.vllm.model_copy(deep=True)
        engines.append(deployment)
    by_app = {}
    for engine in engines:
        app = engine.engine.modal.app
        if not app.startswith('sandbox-vllm-'):
            raise ServiceError('experiment apps must use a sandbox-vllm- scoped name')
        if app in by_app and spec_env(by_app[app]) != spec_env(engine):
            raise ServiceError(f'{app}: agents request incompatible models/parameters on one app')
        by_app[app] = engine
    return list(by_app.values())


def _deploy(spec: RunSpec) -> None:
    from mailroom_sandbox.services.modal_cli import INSTALL_HINT, PINNED_SDK
    from mailroom_sandbox.services._exec import run_tool
    result = run_tool(['modal', '--version'], hint=INSTALL_HINT)
    if not re.search(rf'(?<![\d.]){re.escape(PINNED_SDK)}(?![\d.])', result.stdout or ''):
        raise ServiceError(f'install verified Modal SDK {PINNED_SDK} before launching')
    commands = []
    if spec.engine.modal.prewarm:
        commands.append(['modal', 'run', 'deploy/modal_vllm.py::download_model'])
    commands.append(['modal', 'deploy', 'deploy/modal_vllm.py'])
    for command in commands:
        rc = stream_tool(command, cwd=repo_root(), hint=INSTALL_HINT)
        if rc:
            raise ToolFailed(command, rc)


def _teardown(spec: RunSpec) -> None:
    from mailroom_sandbox.services.modal_cli import _cmd_stop
    _cmd_stop(argparse.Namespace(app=spec.engine.modal.app, dry_run=False, no_verify=False))


def _cmd_launch(args) -> int:
    import fcntl
    from itertools import groupby
    from mailroom_sandbox.runtime import load_env_file
    load_env_file()
    path, plan, runs = _load(args.config)
    # Prevent two local launchers from spending against the same campaign.
    with (path.parent / '.launch.lock').open('a') as guard:
        try:
            fcntl.flock(guard, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ServiceError('this experiment already has an active launcher') from exc
        stores = _prepare(path, plan, runs)
        review = _review(path, plan, runs, stores)
        workflow = {'plan_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'configs': {str(config): hashlib.sha256(config.read_bytes()).hexdigest() for config, _ in runs},
                    'smoke_rows': plan.smoke_rows, 'smoke_cost_cap_usd': plan.smoke_cost_cap_usd,
                    'smoke_wall_seconds': plan.smoke_wall_seconds}
        print(redact_urls(json.dumps(review, indent=2)), file=sys.stderr)
        if not all(spec.job.mock for _, spec in runs):
            initials = args.initials
            if initials is None:
                if not sys.stdin.isatty():
                    raise ServiceError('review every setting above and sign --initials YOUR_INITIALS; no paid action started')
                try:
                    initials = input('I reviewed ALL cells, samples, settings, caps and smoke costs and authorize Modal/OpenRouter spend. Sign initials (blank cancels): ')
                except (EOFError, KeyboardInterrupt) as exc:
                    raise ServiceError('authorization cancelled; no paid action started') from exc
            for (_, spec), store in zip(runs, stores):
                with _environment(spec):
                    authorize(store, initials=initials, extra=workflow)
        marker = path.parent / 'current-run'
        def group_key(pair):
            _, spec = pair[0]
            return json.dumps([spec_env(item) for item in _deployments(spec)], sort_keys=True)
        try:
            for _, group in groupby(zip(runs, stores), key=group_key):
                group = list(group)
                pending = []
                for entry in group:
                    store = entry[1]
                    status = store.summary()
                    if status.get('state') == 'done':
                        if status.get('errors') or status.get('ok') != len(store.dataset_rows()):
                            raise ServiceError(f'{store.run_id}: terminal evidence is incomplete; investigate before resetting/retrying')
                    else:
                        pending.append(entry)
                if not pending:
                    continue
                group = pending
                first = group[0][0][1]
                with _environment(first):
                    owned = []
                    try:
                        if not first.job.mock:
                            from mailroom_sandbox.services.modal_cli import _is_deployed
                            for deployment in _deployments(first):
                                if _is_deployed(deployment.engine.modal.app):
                                    raise ServiceError(f'{deployment.engine.modal.app} already deployed; no ownership taken')
                                owned.append(deployment)
                                with _environment(deployment):
                                    _deploy(deployment)
                        for (_, spec), store in group:
                            _atomic_write(marker, store.run_id + '\n')
                            if store.summary().get('state') == 'done':
                                continue
                            if not spec.job.mock:
                                _probe(spec)
                            _smoke(spec, store, plan)
                            _execute(store)
                            summary = store.summary()
                            if summary.get('state') != 'done' or summary.get('errors') or summary.get('ok') != len(store.dataset_rows()):
                                raise ServiceError(f'{spec.run_id} incomplete or failed: {summary}; later jobs were not started')
                    finally:
                        failures = []
                        for deployment in reversed(owned):
                            try:
                                with _environment(deployment):
                                    _teardown(deployment)
                            except Exception as exc:
                                failures.append(str(exc))
                        if failures:
                            cause = sys.exc_info()[1]
                            prefix = f'{cause}; ' if cause else ''
                            raise ServiceError(prefix + 'teardown failed: ' + '; '.join(failures))
        finally:
            _write_report(path, plan, runs)
    return 0


# The class-native headline each specialist is judged on, first match wins.
_TASK_METRICS = ('cuad_presence_f1', 'maud_accuracy', 'extraction_f1', 'doc_type_accuracy', 'accuracy')


def _task_metric(values: dict) -> tuple[str | None, float | None]:
    for name in _TASK_METRICS:
        if values.get(name) is not None:
            return name, values[name]
    return None, None


def _fmt_score(value) -> str:
    return '—' if value is None else f'{value:.3f}'


def _fmt_delta(value) -> str:
    return '—' if value is None else f'{value:+.3f}'


def _usage(items: list[dict]) -> dict:
    """Token totals and median latency over successful items; None when not reported."""
    ok = [item for item in items if item.get('ok')]
    prompt = [item['prompt_tokens'] for item in ok if isinstance(item.get('prompt_tokens'), int)]
    completion = [item['completion_tokens'] for item in ok if isinstance(item.get('completion_tokens'), int)]
    latency = [item['latency_ms'] for item in ok if isinstance(item.get('latency_ms'), (int, float))]
    return {'prompt_tokens': sum(prompt) if prompt else None,
            'completion_tokens': sum(completion) if completion else None,
            'p50_latency_ms': statistics.median(latency) if latency else None}


def _sand42_row(run_id: str, metrics: dict) -> str:
    def number(value, spec='.2f'):
        return '—' if value is None else format(value, spec)

    def interval(mean, low, high):
        return '—' if mean is None else f'{mean:.3f} [{number(low, ".3f")}, {number(high, ".3f")}]'

    rel, quality, cost, goodput = metrics['reliability'], metrics['quality'], metrics['cost'], metrics['goodput']
    latency, tokens, pipeline = metrics['latency'], metrics['tokens'], metrics.get('pipeline') or {}
    ok_ci = rel.get('ok_rate_ci') or (None, None)
    return (f"| {run_id} | {interval(rel.get('ok_rate'), *ok_ci)} | "
            f"{interval(quality.get('mean'), quality.get('ci_low'), quality.get('ci_high'))} | "
            f"{_fmt_score(rel.get('schema_valid_rate'))} | {number(cost.get('usd_per_1k_ok'))} | "
            f"{number(goodput.get('documents_per_minute_per_gpu'))} | "
            f"{number(goodput.get('goodput_documents_per_minute_per_gpu'))} | "
            f"{number(latency.get('p50'), '.1f')} / {number(latency.get('p95'), '.1f')} | "
            f"{number(tokens.get('prompt'), ',')} / {number(tokens.get('completion'), ',')} | "
            f"{_fmt_score(pipeline.get('review_rate'))} |")


def _clear_gpu_metrics(metrics: dict, card: dict | None) -> None:
    """No GPU was billed (mock, or API-only): the card's L4 × 1 is a default, not a measurement."""
    metrics['cost'] = {}
    metrics['goodput'] = {}
    if card:
        card['cost'] = {}
        card['conditions'] = {**(card.get('conditions') or {}), 'gpu': None, 'gpu_usd_per_hour': None, 'replicas': None}


def _write_report(path: Path, plan: Plan, runs) -> dict:
    rows = []
    cards = {}
    paired = defaultdict(list)
    for config, spec in runs:
        store = RunStore(run_dir(spec.run_id))
        if not store.read_lock():
            rows.append({'run_id': spec.run_id, 'state': 'not prepared', 'expected': spec.dataset.limit})
            continue
        store.verify_generation()
        summary = store.summary()
        summary['expected'] = len(store.dataset_rows())
        summary['task'] = spec.task
        summary['mock'] = spec.job.mock
        summary['config'] = str(config)
        summary['model'] = spec.engine.model
        summary['gpu'] = spec.engine.modal.gpu if spec.engine.modal else None
        summary['replicas'] = spec.engine.modal.max_containers if spec.engine.modal else None
        summary['concurrency'] = spec.job.concurrency
        summary['dataset_sha256'] = hashlib.sha256(store.dataset_path.read_bytes()).hexdigest()
        saved = store.dir / 'experiment-result.json'
        if saved.is_file():
            result = json.loads(saved.read_text())
            if result.get('generation_id') == store.read_lock().get('generation_id'):
                summary['scorer_aggregates'] = result.get('scores', {})
        # Summarize existing scorer outputs, without defining a new scoring engine.
        scores = defaultdict(list)
        for item in store.load_items():
            for key, value in (item.get('score') or {}).items():
                if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
                    scores[key].append(value)
        summary['stored_score_means'] = {key: sum(values)/len(values) for key, values in scores.items()}
        summary['usage'] = _usage(store.load_items())
        # A run stopped before its first document has nothing to measure.
        card = collect_card(store, wall_seconds=infer_wall_seconds_from_store(store)) if store.load_items() else None
        summary['sand42'] = sand42_summary(spec.run_id, card, spec.task)
        lock = store.read_lock() or {}
        from mailroom_sandbox.job.api_budget import spend_estimate, usage_records
        from mailroom_sandbox.job.spend import bills_gpu
        if spec.job.mock or not bills_gpu(lock):
            _clear_gpu_metrics(summary['sand42'], card)
        if not spec.job.mock and (api_spend := spend_estimate(lock, usage_records(store))):
            summary['sand42']['api_cost'] = api_spend  # SAND-089: token spend, reported apart from GPU
        if card:
            cards[spec.run_id] = card
            (path.parent / 'cards').mkdir(exist_ok=True)
            _atomic_write(path.parent / 'cards' / f'{spec.run_id}.card.json',
                          json.dumps(card, indent=2, sort_keys=True, default=str))
        rows.append(summary)
        paired[spec.task].append(hashlib.sha256(store.dataset_path.read_bytes()).hexdigest())
    complete = all(row.get('state') == 'done' and row.get('ok') == row.get('expected') and not row.get('errors') for row in rows)
    report = {'schema': 'sandbox.experiment-report/v1', 'study': plan.study, 'complete': complete,
              'paired_dataset_bytes': all(len(set(values)) == 1 for values in paired.values()), 'runs': rows}
    comparisons = []
    baseline = {}
    for row in rows:
        if row.get('state') != 'done' or row.get('ok') != row.get('expected') or row.get('errors'):
            continue
        key = row.get('task')
        if key not in baseline:
            baseline[key] = row
            continue
        ref = baseline[key]
        if ref['dataset_sha256'] != row['dataset_sha256']:
            continue
        comparisons.append({'reference': ref['run_id'], 'run': row['run_id'], 'paired_n': row['ok'],
            'paired_quality': paired_delta(cards[ref['run_id']], cards[row['run_id']]),
            'stored_score_mean_deltas': {metric: value-ref['stored_score_means'][metric]
                for metric, value in row['stored_score_means'].items() if metric in ref['stored_score_means']}})
    report['comparisons'] = comparisons
    _atomic_write(path.parent / 'report.json', json.dumps(report, indent=2, sort_keys=True))
    lines = [f'# {plan.study}', '', f'Complete: {complete}; paired dataset bytes: {report["paired_dataset_bytes"]}.', '',
             '| Run | State | Successful / expected | Errors |', '| --- | --- | --- | --- |']
    for row in rows:
        lines.append(f'| {row["run_id"]} | {row["state"]} | {row.get("ok", 0)} / {row.get("expected")} | {row.get("errors", 0)} |')
    scored = [row for row in rows if row.get('stored_score_means')]
    if scored:
        lines += ['', '## Quality', '', 'Means over successful documents, from the Dojo scorers stored with each item.', '',
                  '| Run | Model | n | Headline | Task metric | Schema adherence | Tokens (in / out) | p50 latency |',
                  '| --- | --- | --- | --- | --- | --- | --- | --- |']
        for row in scored:
            means = row['stored_score_means']
            name, value = _task_metric(means)
            usage = row.get('usage') or {}
            tokens = ' / '.join('—' if usage.get(key) is None else f'{usage[key]:,}'
                                for key in ('prompt_tokens', 'completion_tokens'))
            tokens = 'not reported' if tokens == '— / —' else tokens
            p50 = f"{usage['p50_latency_ms']:.0f} ms" if usage.get('p50_latency_ms') is not None else '—'
            lines.append(f"| {row['run_id']} | {row.get('model')} | {row.get('ok', 0)} | "
                         f"{_fmt_score(means.get('overall_extraction_score'))} | "
                         f"{name + ' ' + _fmt_score(value) if name else '—'} | "
                         f"{_fmt_score(means.get('schema_adherence'))} | {tokens} | {p50} |")
    measured = [row for row in rows if (row.get('sand42') or {}).get('reported')]
    if measured:
        lines += ['', '## Sand42 metrics', '', 'The card contract of docs/SAND42-EXPERIMENT-DESIGN.md section 5; each run\'s card is under cards/.', '',
                  '| Run | Ok rate (95% CI) | Quality (95% CI) | Schema valid | $/1k ok | Docs/min/GPU | Goodput at SLO | p50 / p95 s | Tokens in / out | Review rate |',
                  '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
        lines += [_sand42_row(row['run_id'], row['sand42']) for row in measured]
    routed = [row for row in measured if row['sand42'].get('pipeline')]
    if routed:
        lines += ['', '## Pipeline routing', '',
                  'A class with no decision reviewer has no disagreement check: its LLM reviewer only runs on medium-confidence sorter results.', '',
                  '| Run | Class | Reviewer | Documents | Stages | Review rate | Class correct | Stage correct |',
                  '| --- | --- | --- | --- | --- | --- | --- | --- |']
        for row in routed:
            block = row['sand42']['pipeline']
            for name, part in {'all': block, **block['by_class']}.items():
                stages = ', '.join(f'{stage} {count}' for stage, count in sorted(part['stages'].items()))
                reviewer = part.get('reviewer')
                reviewer = '' if name == 'all' else f"{reviewer} at {part['reviewer_cutoff']}" if reviewer else 'none'
                lines.append(f"| {row['run_id']} | {name} | {reviewer} | {part['documents']} | {stages} | {_fmt_score(part['review_rate'])} | "
                             f"{_fmt_score(part['class_correct'])} | {_fmt_score(part['stage_correct'])} |")
            causes = ', '.join(f'{cause} {count}' for cause, count in block['review_causes'].items())
            lines.append(f"\nReview causes in {row['run_id']}: {causes or 'none'}.\n")
    if comparisons:
        lines += ['', '## Paired comparisons', '', 'Each run against the first complete run of its task on identical dataset bytes.', '',
                  '| Reference | Run | Paired n | Δ headline | Δ headline 95% CI | Better / worse / tie | Δ task metric |',
                  '| --- | --- | --- | --- | --- | --- | --- |']
        for item in comparisons:
            deltas = item['stored_score_mean_deltas']
            name, value = _task_metric(deltas)
            pair = item['paired_quality'] or {}
            ci = f"[{_fmt_delta(pair['ci_low'])}, {_fmt_delta(pair['ci_high'])}]" if pair.get('ci_low') is not None else '—'
            split = f"{pair['better']} / {pair['worse']} / {pair['tie']}" if pair else '—'
            lines.append(f"| {item['reference']} | {item['run']} | {item['paired_n']} | "
                         f"{_fmt_delta(deltas.get('overall_extraction_score'))} | {ci} | {split} | "
                         f"{name + ' ' + _fmt_delta(value) if name else '—'} |")
    lines += ['', 'Per-run scorer metrics and configuration links are in report.json; native quality/serving reports remain under reports/.',
              'A completed mock run validates orchestration only. Failed/missing documents are never counted as successful observations.', '']
    _atomic_write(path.parent / 'report.md', '\n'.join(lines))
    print(f'Report: {path.parent / "report.md"}')
    return report


def _cmd_report(args) -> int:
    path, plan, runs = _load(args.config)
    report = _write_report(path, plan, runs)
    return 0 if report['complete'] else 1


def _cmd_watch(args) -> int:
    from mailroom_sandbox import cli
    path, plan, runs = _load(args.config)
    marker = path.parent / 'current-run'
    if not marker.is_file():
        _atomic_write(marker, runs[0][1].run_id + '\n')
    return cli.main(['watch', '--web', '--follow', str(marker), *(['--no-browser'] if args.no_browser else [])])


def register(sub, leaf) -> None:
    group = sub.add_parser('experiment', parents=[leaf], help='design → paired sample → preflight → initials → smoke → launch → reports')
    commands = group.add_subparsers(dest='experiment_cmd')
    catalog = commands.add_parser('designs', help='list experiment designs and parameter selectors')
    catalog.set_defaults(handler=lambda args: print(json.dumps({'designs': DESIGNS, 'document_classes': CLASSES,
        'models': 'sandbox modal-matrix list', 'parameters': 'experiment create --help; --set engine.vllm.<name>=value'}, indent=2)) or 0)
    create = commands.add_parser('create', parents=[leaf], help='write a reviewable experiment; no Hub/provider calls')
    create.add_argument('study')
    create.add_argument('--task', choices=['specialists', 'pipeline', 'sorter'], default='specialists')
    create.add_argument('--agent-route', action='append', dest='agent_routes', default=[], metavar='NAME=PROVIDER:MODEL', help='per-agent provider/model; NAME=@route.yaml includes endpoint/GPU/vLLM settings')
    create.add_argument('--decision-reviewer', default=None, metavar='BACKEND:MODEL', help='freeze a decision-model reviewer (decisions:openai/gpt-6-luna-decisions with the lineage frontrunner question set, jev:jev-1.13.0, local:MODEL or mock:mock); needs --decision-class')
    create.add_argument('--decision-class', action='append', default=[], metavar='CLASS=CUTOFF', help='class the decision reviewer handles, with its cutoff in [0, 1] (repeatable)')
    create.add_argument('--specialist-tier', choices=['base', 'mid', 'full'], default='base',
                        help="specialists' model: base = the run's model, mid = Qwen3.5-35B-A3B, full = the judge's Qwen3.5-27B (config/models.yaml critical_tier)")
    create.add_argument('--design', choices=DESIGNS, default='single')
    create.add_argument('--doc-class', action='append', choices=CLASSES)
    create.add_argument('--samples', type=int, default=50, help='documents per selected class, shared across every cell')
    create.add_argument('--seed', type=int, default=42)
    create.add_argument('--subclass', action='append', help='restrict the draw to corpus subclass tokens (repeatable)')
    create.add_argument('--dataset', default='Lucius-Morningstar/mailroom-dataset')
    create.add_argument('--dataset-config', default='ground_truth')
    create.add_argument('--split', default='all')
    create.add_argument('--revision', default=FAMILY_HF_REVISION)
    create.add_argument('--local-dataset', default=None, help='local JSONL instead of Hub (also useful for offline mock checks)')
    create.add_argument('--provider', choices=['modal-vllm', 'openrouter'], default='modal-vllm')
    create.add_argument('--gpu', default='L4', help='Modal GPU class, optionally :N for tensor parallel')
    create.add_argument('--no-named-image', dest='named_image', action='store_false',
                        help='build the serving image instead of reusing the published sandbox-vllm:<tag>')
    create.add_argument('--replicas', type=int, default=None, help='override cell replica count')
    create.add_argument('--concurrency', type=int, default=None)
    create.add_argument('--max-tokens', type=int, default=8192)
    create.add_argument('--temperature', type=float, default=0.1)
    create.add_argument('--trace-sink', choices=['langfuse', 'otlp', 'phoenix', 'none'], default='langfuse')
    create.add_argument('--trace-endpoint', default=None)
    create.add_argument('--cost-cap-usd', type=float, default=None,
                        help='per-run estimated Modal GPU cap; default: recommended from samples, concurrency, GPUs and task')
    create.add_argument('--max-wall-seconds', type=int, default=None,
                        help='per-run wall-clock ceiling (the run aborts and its fleet is torn down); default: recommended')
    create.add_argument('--api-cost-cap-usd', type=float, default=None,
                        help='per-run API token spend cap for OpenRouter agents; default: recommended from token prices')
    create.add_argument('--smoke-rows', type=int, default=1)
    create.add_argument('--smoke-cost-cap-usd', type=float, default=0.10)
    create.add_argument('--mock', action='store_true', help='create an offline mock experiment; never deploys/calls providers')
    create.add_argument('--set', action='append', dest='settings', default=[], metavar='PATH=YAML_VALUE')
    create.add_argument('--output', default=None)
    create.set_defaults(handler=_create)
    for name, handler, summary in [
        ('review', _cmd_review, 'print the full configuration and spend review'),
        ('preflight', _cmd_preflight, 'prepare locked datasets/prompts for every run; no provider or deploy call'),
        ('launch', _cmd_launch, 'launch experiment; paid runs require authorization via --initials or a terminal prompt; mock runs do not'),
        ('watch', _cmd_watch, 'follow campaign membership and its current run'),
        ('report', _cmd_report, 'build coverage and paired reports from finished runs'),
    ]:
        parser = commands.add_parser(name, parents=[leaf], help=summary)
        parser.add_argument('--config', required=True, help='experiment.yaml created by experiment create')
        if name == 'launch':
            parser.add_argument('--initials', default=None, help='sign the displayed full configuration and spend review')
        if name == 'watch':
            parser.add_argument('--no-browser', action='store_true')
        parser.set_defaults(handler=handler)
    group.set_defaults(handler=lambda args: print('Use: sandbox experiment designs | create | review | preflight | launch | watch | report') or 0)
