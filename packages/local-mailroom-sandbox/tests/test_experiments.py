"""Experiment design, paired data, spend gates and smoke-before-launch contracts."""
import json

import pytest
import yaml

from mailroom_sandbox import cli, experiments as ex
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.job.spec import run_dir
from mailroom_sandbox.services._exec import ServiceError


@pytest.fixture(autouse=True)
def environment(monkeypatch, job_data_dir):
    monkeypatch.setattr('mailroom_sandbox.runtime.dotenv_files', lambda: [])
    monkeypatch.setattr('mailroom_sandbox.paths.dotenv_files', lambda: [])
    monkeypatch.setenv('MODAL_WORKSPACE', 'test-workspace')
    monkeypatch.setenv('OPENROUTER_API_KEY', 'fake-for-offline-tests')


@pytest.fixture
def design(tmp_path):
    source = tmp_path / 'docs.jsonl'
    source.write_text(''.join(json.dumps({'id': f'c{i}', 'doc_text': 'Email from Jane to John: meeting tomorrow.',
        'expected_doc_class': 'correspondence', 'expected_subclass': 'email', 'expected_stage': 'archived',
        'expected_fields': {'sender': 'Jane'}}) + '\n' for i in range(3)))
    def create(*options):
        root = tmp_path / ('design-' + str(len(list(tmp_path.glob('design-*')))))
        args = ['experiment', 'create', root.name, '--doc-class', 'correspondence', '--samples', '3', '--subclass', 'email',
                '--local-dataset', str(source), '--trace-sink', 'none', '--output', str(root), *options]
        assert cli.main(args) == 0
        return root / 'experiment.yaml'
    return create


def test_sand42_creates_paired_2x2_grid_without_network(design, monkeypatch):
    import httpx
    monkeypatch.setattr(httpx, 'get', lambda *a, **k: pytest.fail('create cannot fetch'))
    config = design('--design', 'sand42', '--mock')
    _, plan, runs = ex._load(config)
    assert len(runs) == 4
    assert {(spec.engine.modal.max_containers, spec.job.concurrency) for _, spec in runs} == {(1,8),(1,16),(2,8),(2,16)}
    assert len({json.dumps(spec.dataset.model_dump(), sort_keys=True) for _, spec in runs}) == 1
    assert len({spec.engine.modal.app for _, spec in runs}) == 4
    assert cli.main(['experiment', 'preflight', '--config', str(config)]) == 0
    assert len({RunStore(run_dir(spec.run_id)).read_lock()['dataset']['sha256'] for _, spec in runs}) == 1


def test_smoke_and_full_run_are_separate_locked_subsets(design):
    config = design('--mock')
    assert cli.main(['experiment', 'launch', '--config', str(config)]) == 0
    report = json.loads((config.parent / 'report.json').read_text())
    assert report['complete'] and report['runs'][0]['ok'] == 3
    main_store = RunStore(run_dir(report['runs'][0]['run_id']))
    smoke_id = next(event['detail']['smoke_run_id'] for event in (json.loads(line) for line in main_store.events_path.read_text().splitlines()) if event.get('event') == 'experiment_smoke_passed')
    assert len(RunStore(run_dir(smoke_id)).dataset_rows()) == 1
    assert len(main_store.dataset_rows()) == 3


def test_campaign_watch_resolves_run_id_marker_and_live_context(design, monkeypatch):
    from mailroom_sandbox.tui import web
    config = design('--design', 'sand42', '--mock')
    assert cli.main(['experiment', 'preflight', '--config', str(config)]) == 0
    _, plan, runs = ex._load(config)
    marker = config.parent / 'current-run'
    marker.write_text(runs[0][1].run_id)
    states = []
    def serve(**kw):
        session = web.WatchWebSession(resolve=kw['resolve'], ledger=None,
            cap_usd=5, interval=1, times_dir=None, serving_dir=config.parent,
            follow_logs=False, campaign_path=kw['campaign_path'])
        try:
            states.append(session.refresh())
            second = runs[1][1]
            store = RunStore(run_dir(runs[0][1].run_id))
            store.write_checkpoint(state='done', cursor=3, total=3)
            marker.write_text(second.run_id)
            states.append(session.refresh())
        finally:
            session.stop()
        return 0
    monkeypatch.setattr(web, 'serve_watch_web', serve)
    assert cli.main(['experiment', 'watch', '--config', str(config), '--no-browser']) == 0
    assert states[0]['campaign']['study'] == plan.study
    assert states[0]['campaign']['total'] == 4
    assert states[1]['campaign']['completed'] == 1
    assert states[1]['snapshot']['run_id'] == runs[1][1].run_id
    assert states[1]['campaign']['current'] == runs[1][1].run_id


def _fake_execute(store):
    for row in store.dataset_rows():
        store.append_item({'item_id': row['id'], 'ok': True, 'score': {'match': 1.0}})
    store.write_checkpoint(state='done', cursor=len(store.dataset_rows()), total=len(store.dataset_rows()))
    return store.summary()


def test_unsigned_launch_never_deploys_or_probes(design, monkeypatch):
    config = design()
    monkeypatch.setattr(ex.sys.stdin, 'isatty', lambda: False)
    monkeypatch.setattr(ex, '_deploy', lambda spec: pytest.fail('unsigned deploy'))
    monkeypatch.setattr(ex, '_probe', lambda spec: pytest.fail('unsigned probe'))
    assert cli.main(['experiment', 'launch', '--config', str(config)]) == 1


def test_signed_launch_smokes_before_full_run_and_tears_down(design, monkeypatch):
    config = design()
    events = []
    monkeypatch.setattr('mailroom_sandbox.services.modal_cli._is_deployed', lambda app: False)
    def deploy(spec):
        for _, run_spec in ex._load(config)[2]:
            receipt = json.loads((run_dir(run_spec.run_id) / 'spend-authorization.json').read_text())
            assert receipt['initials'] == 'JB'
            assert receipt['workflow']['smoke_rows'] == 1
        events.append('deploy')
    def execute(store):
        events.append(len(store.dataset_rows()))
        return _fake_execute(store)
    monkeypatch.setattr(ex, '_deploy', deploy)
    monkeypatch.setattr(ex, '_execute', execute)
    monkeypatch.setattr(ex, '_probe', lambda spec: events.append('probe'))
    monkeypatch.setattr(ex, '_teardown', lambda spec: events.append('stop'))
    assert cli.main(['experiment', 'launch', '--config', str(config), '--initials', 'JB']) == 0
    assert events == ['deploy', 'probe', 1, 3, 'stop']


def test_failed_smoke_blocks_full_run_and_stops_app(design, monkeypatch):
    config = design()
    calls = []
    monkeypatch.setattr('mailroom_sandbox.services.modal_cli._is_deployed', lambda app: False)
    monkeypatch.setattr(ex, '_deploy', lambda spec: None)
    monkeypatch.setattr(ex, '_probe', lambda spec: None)
    monkeypatch.setattr(ex, '_teardown', lambda spec: calls.append('stop'))
    def fail(store):
        calls.append(len(store.dataset_rows()))
        store.write_checkpoint(state='failed', cursor=0, total=len(store.dataset_rows()))
    monkeypatch.setattr(ex, '_execute', fail)
    assert cli.main(['experiment', 'launch', '--config', str(config), '--initials', 'JB']) == 1
    assert calls == [1, 'stop']
    assert json.loads((config.parent / 'report.json').read_text())['complete'] is False


def test_partial_deploy_failure_still_tears_down(design, monkeypatch):
    config = design()
    calls = []
    monkeypatch.setattr('mailroom_sandbox.services.modal_cli._is_deployed', lambda app: False)
    monkeypatch.setattr(ex, '_deploy', lambda spec: (_ for _ in ()).throw(ServiceError('image failed')))
    monkeypatch.setattr(ex, '_teardown', lambda spec: calls.append('stop'))
    assert cli.main(['experiment', 'launch', '--config', str(config), '--initials', 'JB']) == 1
    assert calls == ['stop']


def test_pipeline_supports_hybrid_routes_and_agent_models(design):
    config = design('--task', 'pipeline', '--agent-route', 'sorter=openrouter:api-sorter',
                    '--agent-route', 'contracts_specialist=modal-vllm:Qwen/Qwen3-8B',
                    '--agent-model', 'boss=api-boss', '--mock')
    spec = ex._load(config)[2][0][1]
    assert spec.task == 'pipeline'
    assert spec.agent_routes['sorter'].model == 'api-sorter'
    assert spec.agent_routes['contracts_specialist'].modal.app.startswith('sandbox-vllm-')
    assert spec.agent_models['boss'] == 'api-boss'
    assert len(ex._deployments(spec)) == 3  # base + contracts route + SAND-078 judge tier
    assert 'sorter' in spec.agent_knobs and 'sorter_reviewer' in spec.agent_knobs


def test_unknown_setting_is_refused_without_writing(design):
    with pytest.raises(AssertionError):
        design('--set', 'engine.vllm.typo=1')


def test_unavailable_sample_refuses_before_spend(design, monkeypatch):
    config = design('--mock')
    run_path = ex._load(config)[2][0][0]
    data = yaml.safe_load(run_path.read_text())
    data['dataset']['limit'] = 4
    run_path.write_text(yaml.safe_dump(data))
    monkeypatch.setattr(ex, '_deploy', lambda spec: pytest.fail('insufficient rows must not deploy'))
    assert cli.main(['experiment', 'launch', '--config', str(config)]) == 1


def test_full_pipeline_mock_writes_observer_evidence(design):
    config = design('--task', 'pipeline', '--mock')
    assert cli.main(['experiment', 'launch', '--config', str(config)]) == 0
    spec = ex._load(config)[2][0][1]
    store = RunStore(run_dir(spec.run_id))
    assert len(store.load_items()) == 3
    assert store.summary()['state'] == 'done'
    assert 'sorter_reviewer' in store.read_lock()['agent_assignments']
    assert 'reporter' not in store.read_lock()['agent_assignments']
    report = json.loads((config.parent / 'report.json').read_text())
    assert report['complete'] and report['runs'][0]['scorer_aggregates']['connected']


def test_all_completed_jobs_are_not_redeployed(design, monkeypatch):
    config = design()
    path, plan, runs = ex._load(config)
    stores = ex._prepare(path, plan, runs)
    for store in stores:
        _fake_execute(store)
    monkeypatch.setattr(ex, '_deploy', lambda spec: pytest.fail('completed campaign must not deploy'))
    assert cli.main(['experiment', 'launch', '--config', str(config), '--initials', 'JB']) == 0


def test_hybrid_deployment_failure_cleans_every_attempted_app(design, monkeypatch):
    config = design('--task', 'pipeline', '--agent-route', 'sorter=modal-vllm:Qwen/Qwen3-8B')
    attempted, stopped = [], []
    monkeypatch.setattr('mailroom_sandbox.services.modal_cli._is_deployed', lambda app: False)
    def deploy(spec):
        attempted.append(spec.engine.modal.app)
        if len(attempted) == 2:
            raise ServiceError('second deployment failed')
    monkeypatch.setattr(ex, '_deploy', deploy)
    monkeypatch.setattr(ex, '_teardown', lambda spec: stopped.append(spec.engine.modal.app))
    assert cli.main(['experiment', 'launch', '--config', str(config), '--initials', 'JB']) == 1
    assert len(attempted) == 2 and stopped == list(reversed(attempted))


def test_route_can_replace_an_unused_default_deployment(design):
    config = design('--agent-route', 'correspondence_specialist=openrouter:api-model', '--mock')
    spec = ex._load(config)[2][0][1]
    assert ex._deployments(spec) == []


def _route_spec():
    from mailroom_sandbox.job.spec import AgentRoute, DatasetSpec, RunSpec
    return RunSpec(
        run_id='route-probe',
        task='sorter',
        profile='modal-vllm',
        dataset=DatasetSpec(provider='file', local_path='unused.jsonl'),
        engine={'kind': 'vllm-local', 'model': 'default-model', 'modal': None},
        agent_routes={'sorter': AgentRoute(provider='vllm', model='served-model', base_url='http://route.test/v1')},
        trace={'sink': 'none'},
    )


def test_route_models_probe_retries_while_the_route_boots(monkeypatch):
    """A scale-to-zero route holds /models open while booting; one 60 s GET
    used to fail verification and tear down a healthy app."""
    import httpx

    calls = {'get': 0}

    class _Resp:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def fake_get(url, headers=None, timeout=None):
        calls['get'] += 1
        if calls['get'] == 1:
            raise httpx.ReadTimeout('container booting')
        return _Resp({'data': [{'id': 'served-model'}]})

    def fake_post(url, headers=None, timeout=None, json=None):
        assert json['model'] == 'served-model'
        return _Resp({'choices': [{'message': {'content': 'OK'}}]})

    monkeypatch.setattr('httpx.get', fake_get)
    monkeypatch.setattr('httpx.post', fake_post)
    monkeypatch.setenv('SANDBOX_ENGINE_PROBE_TIMEOUT_SECONDS', '5')

    ex._probe(_route_spec())

    assert calls['get'] == 2


def test_teardown_failure_preserves_the_original_failure(design, monkeypatch, capsys):
    config = design('--task', 'pipeline', '--agent-route', 'sorter=modal-vllm:Qwen/Qwen3-8B')
    monkeypatch.setattr('mailroom_sandbox.services.modal_cli._is_deployed', lambda app: False)

    def fail_deploy(spec):
        raise ServiceError('deployment failed first')

    def fail_teardown(spec):
        raise ServiceError('stop refused')

    monkeypatch.setattr(ex, '_deploy', fail_deploy)
    monkeypatch.setattr(ex, '_teardown', fail_teardown)

    assert cli.main(['experiment', 'launch', '--config', str(config), '--initials', 'JB']) == 1
    err = capsys.readouterr().err
    assert 'deployment failed first' in err
    assert 'teardown failed' in err and 'stop refused' in err


def test_modal_pipeline_judge_gets_the_critical_tier_route(design):
    # SAND-078: the judge runs a larger sibling of the base model on its own app.
    spec = ex._load(design('--task', 'pipeline', '--mock'))[2][0][1]
    judge = spec.agent_routes['judge']
    assert (judge.provider, judge.model, judge.modal.gpu) == ('modal-vllm', 'Qwen/Qwen3.5-27B', 'L40S')
    assert judge.vllm.quantization == 'fp8' and judge.vllm.limit_mm_per_prompt == {'image': 0, 'video': 0, 'audio': 0}
    assert spec.engine.model == 'Qwen/Qwen3.5-9B'
    assert {d.engine.model for d in ex._deployments(spec)} == {'Qwen/Qwen3.5-9B', 'Qwen/Qwen3.5-27B'}
    assert set(spec.agent_routes) == {'judge'}  # the specialists stay on the base model


@pytest.mark.parametrize('options', [
    ('--provider', 'openrouter'),
    ('--agent-model', 'judge=Qwen/Qwen3.5-9B'),
    ('--agent-route', 'judge=openrouter:deepseek/deepseek-v4-flash'),
])
def test_critical_judge_is_skipped_off_modal_or_when_the_judge_is_pinned(design, options):
    spec = ex._load(design('--task', 'pipeline', '--mock', *options))[2][0][1]
    judge = spec.agent_routes.get('judge')
    assert judge is None or judge.model == 'deepseek/deepseek-v4-flash'


SPECIALISTS = {'contracts_specialist', 'corporate_records_specialist', 'correspondence_specialist',
               'insurance_claims_specialist', 'merger_agreement_specialist'}


def test_full_specialist_tier_shares_the_judge_app(design):
    # SAND-079: `full` is the judge's own model, so one app serves both roles.
    spec = ex._load(design('--task', 'pipeline', '--specialist-tier', 'full', '--mock'))[2][0][1]
    assert set(spec.agent_routes) == SPECIALISTS | {'judge'}
    assert {r.model for r in spec.agent_routes.values()} == {'Qwen/Qwen3.5-27B'}
    assert len({r.modal.app for r in spec.agent_routes.values()}) == 1
    assert {d.engine.model for d in ex._deployments(spec)} == {'Qwen/Qwen3.5-9B', 'Qwen/Qwen3.5-27B'}


def test_mid_specialist_tier_sits_between_base_and_judge(design):
    spec = ex._load(design('--task', 'pipeline', '--specialist-tier', 'mid', '--mock'))[2][0][1]
    mid = spec.agent_routes['contracts_specialist']
    assert (mid.model, mid.modal.gpu, mid.vllm.quantization) == ('Qwen/Qwen3.5-35B-A3B', 'L4:2', 'fp8')
    assert spec.agent_routes['judge'].model == 'Qwen/Qwen3.5-27B'
    assert {d.engine.model for d in ex._deployments(spec)} == {
        'Qwen/Qwen3.5-9B', 'Qwen/Qwen3.5-35B-A3B', 'Qwen/Qwen3.5-27B'}


@pytest.mark.parametrize(('tier', 'model'), [('mid', 'qwen/qwen3.5-35b-a3b'), ('full', 'qwen/qwen3.5-27b')])
def test_openrouter_specialist_tiers_use_the_preference_models(design, tier, model):
    spec = ex._load(design('--task', 'pipeline', '--provider', 'openrouter', '--specialist-tier', tier, '--mock'))[2][0][1]
    assert not spec.agent_routes
    assert {spec.agent_models[name] for name in SPECIALISTS} == {model}
    assert 'judge' not in spec.agent_models  # the openrouter judge stays deepseek


def test_specialists_task_on_a_tier_skips_the_unused_base_engine(design):
    spec = ex._load(design('--specialist-tier', 'full', '--mock'))[2][0][1]
    assert spec.task == 'correspondence_specialist'
    assert [d.engine.model for d in ex._deployments(spec)] == ['Qwen/Qwen3.5-27B']


def test_explicit_specialist_pin_beats_the_tier(design):
    spec = ex._load(design('--task', 'pipeline', '--specialist-tier', 'mid', '--mock',
                           '--agent-route', 'contracts_specialist=openrouter:api-model'))[2][0][1]
    assert spec.agent_routes['contracts_specialist'].model == 'api-model'
    assert spec.agent_routes['correspondence_specialist'].model == 'Qwen/Qwen3.5-35B-A3B'


def test_specialist_tier_is_refused_for_the_frozen_sand42_study(tmp_path, capsys):
    assert cli.main(['experiment', 'create', 'frozen', '--design', 'sand42', '--specialist-tier', 'full',
                     '--output', str(tmp_path / 'frozen'), '--mock']) != 0
    assert '--specialist-tier' in capsys.readouterr().err
    assert not (tmp_path / 'frozen').exists()


def test_create_fills_unset_ceilings_from_the_design_and_keeps_explicit_ones(design, capsys):
    from mailroom_sandbox.job.budget_advice import recommend
    _, _, runs = ex._load(design())
    spec = runs[0][1]
    advice = recommend(spec)
    assert spec.job.max_wall_seconds == advice['max_wall_seconds']
    assert spec.job.cost_cap_usd == advice['gpu_cost_cap_usd']
    assert 'recommended' in capsys.readouterr().out
    _, _, runs = ex._load(design('--max-wall-seconds', '900', '--cost-cap-usd', '3'))
    assert (runs[0][1].job.max_wall_seconds, runs[0][1].job.cost_cap_usd) == (900, 3.0)
