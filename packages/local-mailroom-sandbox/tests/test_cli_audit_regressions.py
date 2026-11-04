"""Operator-visible defects found by the SAND-066 Terra command audit."""
from __future__ import annotations


import pytest

from mailroom_sandbox import cli
from mailroom_sandbox.eval import matrix, runners


@pytest.mark.parametrize('argv', [
    ['--agent-model', 'sorter=a', 'eval', 'sorter', '--agent-model', 'judge=b'],
    ['--agent-model', 'sorter=a', 'run', '--agent-model', 'judge=b', 'start', '--agent-model', 'sorter=c'],
])
def test_repeatable_models_accumulate_across_command_levels(argv):
    args = cli.build_parser().parse_args(argv)
    expected = {'sorter': 'c', 'judge': 'b'} if 'run' in argv else {'sorter': 'a', 'judge': 'b'}
    assert cli._agent_models(args) == expected


@pytest.mark.parametrize('command', [['eval', 'sorter'], ['matrix']])
def test_mock_and_live_are_exclusive(command):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args([*command, '--mock', '--local'])
    assert exc.value.code == 2


@pytest.mark.parametrize('argv', [
    ['eval', 'sorter', '--sample', '0'], ['eval', 'sorter', '--sample', '-3'],
    ['pilot', '--sample', '0'],
    ['matrix', '--sample', '0'], ['modernbert', 'eval', '--sample', '-1'],
    ['datasets', 'sample', '--per-class', '-1'], ['datasets', 'pull', '--max-rows', '-1'],
    ['metrics', 'estimate-suite', '--gpu-usd-per-hour', '-1'],
    ['metrics', 'estimate-suite', '--gpu-usd-per-hour', 'nan'],
    ['metrics', 'estimate-suite', '--sec-per-doc', '0'],
    ['metrics', 'estimate-suite', '--gen-tok-per-s', '-1'],
    ['metrics', 'estimate-suite', '--corpus-size', '0'],
    ['metrics', 'extrapolate', '--run', 'x', '--concurrency', '0'],
    ['metrics', 'extrapolate', '--run', 'x', '--cold-start-seconds', 'inf'],
    ['run', 'start', '--max-items', '0'], ['matrix', '--task', 'nonexistent'],
])
def test_invalid_numeric_and_task_choices_rejected(argv):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(argv)
    assert exc.value.code == 2


@pytest.mark.parametrize('argv', [
    ['run', 'resume', '--run-id', 'x'], ['run', 'cancel', '--run-id', 'x'],
    ['run', 'dispose', '--run-id', 'x', '--report', 'x.md'],
    ['run', 'scrape-metrics', '--run-id', 'x', '--label', 'mid'],
    ['run', 'card', '--run-id', 'x'], ['run', 'export-bt', '--run-id', 'x'],
    ['run', 'status', '--run-id', 'x'],
])
def test_unsupported_dry_run_never_dispatches(argv, monkeypatch):
    def unexpected(*a, **k):
        pytest.fail('action dispatched under unsupported --dry-run')
    for name in ('_cmd_run_resume', '_cmd_run_cancel', '_cmd_run_dispose', '_cmd_run_scrape_metrics', '_cmd_run_card', '_cmd_run_export_bt', '_cmd_run_status'):
        monkeypatch.setattr(cli, name, unexpected)
    with pytest.raises(SystemExit) as exc:
        cli.main([*argv, '--dry-run'])
    assert exc.value.code == 2


@pytest.mark.parametrize('argv', [
    ['eval', 'sorter', '--from-log'], ['eval', 'sorter', '--connected'],
    ['eval', 'local_vs_api', '--group', '1'],
    ['matrix', '--providers', ','], ['matrix', '--models', ','], ['matrix', '--prompts', ','],
    ['pilot', '--agent-model', 'invalid'], ['hf-pilot', '--agent-model', 'invalid'],
])
def test_misleading_ignored_options_return_usage_error(argv, capsys):
    assert cli.main([*argv, '--mock', '--dry-run']) == 2
    assert 'error:' in capsys.readouterr().err


def test_pilot_forwards_agent_overrides(monkeypatch):
    seen = {}
    monkeypatch.setattr(runners, 'run_pipeline_eval', lambda **kw: seen.update(kw) or {})
    assert cli.main(['pilot', '--mock', '--dry-run', '--agent-model', 'sorter=custom']) == 0
    assert seen['agent_models'] == {'sorter': 'custom'}


@pytest.mark.parametrize('live', [False, True])
def test_hf_pilot_scores_hf_text_and_labels(live, monkeypatch, tmp_path):
    from mailroom_sandbox import datasets
    from mailroom_sandbox.eval import experiment_log
    rows = [{'id': 'hf-unique', 'doc_type': 'correspondence', 'text': 'Unique HF document text'}]
    monkeypatch.setattr(datasets, 'load_hf_fixtures', lambda: rows)
    monkeypatch.setattr(experiment_log, 'append', lambda r: None)
    monkeypatch.setattr(runners, 'emit', lambda r: None)
    monkeypatch.setenv('MAILROOM_BASE_DIR', str(tmp_path))
    seen = []
    def predict(row, **kw):
        seen.append(row)
        return {'doc_type': 'correspondence'}
    monkeypatch.setattr(runners, '_run_pipeline_doc', predict)
    monkeypatch.setattr(cli, '_print', lambda result: seen.append(result))
    assert cli.main(['hf-pilot', '--local' if live else '--mock', '--profile', 'ollama']) == 0
    result = seen[-1]
    normalized = [{**rows[0], 'expected_doc_class': 'correspondence'}]
    assert result['fingerprint'] == datasets.dataset_fingerprint(normalized)
    assert result['n'] == 1 and result['scores']['accuracy'] == 1
    if live:
        assert seen[0] == normalized[0]
        queued = runners._materialize_row(seen[0], tmp_path)
        assert queued.read_text() == rows[0]['text']


def test_matrix_forwards_seed_and_models(monkeypatch):
    seen = []
    monkeypatch.setattr(runners, 'run_pipeline_eval', lambda **kw: seen.append(kw) or {})
    matrix.run_matrix(task='pipeline', providers=['modal-vllm'], models=['Qwen/Qwen3.5-9B'], prompts=['mailroom-default'], sample=2, seed=99, agent_models={'judge': 'custom'})
    assert seen[0]['sample_seed'] == 99
    assert seen[0]['model'] == 'Qwen/Qwen3.5-9B'  # the requested model, not the family default
    assert seen[0]['agent_models'] == {'judge': 'custom'}


def test_seeded_pipeline_draw_is_shared_across_cells_and_changes_with_seed():
    rows = [{'id': str(i), 'expected_doc_class': 'contract'} for i in range(50)]
    def fingerprint(seed):
        return runners.run_pipeline_eval(rows=rows, sample=5, sample_seed=seed, dry_run=True)['fingerprint']
    assert fingerprint(12) == fingerprint(12)
    assert fingerprint(12) != fingerprint(13)


@pytest.mark.parametrize('argv', [['legalbench', '--mock'], ['eval', 'legalbench', '--mock'], ['matrix', '--task', 'legalbench', '--mock']])
def test_legalbench_is_not_a_sandbox_task(argv, capsys):
    """LegalBench is not a primary operation; the vendored package stays, the CLI surface does not."""
    with pytest.raises(SystemExit) as exc:
        cli.main(argv)
    assert exc.value.code == 2 and 'invalid choice' in capsys.readouterr().err


def test_legalbench_run_spec_is_rejected():
    from mailroom_sandbox.job.spec import RunSpec, known_tasks

    assert 'legalbench' not in known_tasks()
    with pytest.raises(ValueError, match='unknown task'):
        RunSpec(run_id='x', task='legalbench')


# --- SAND-068: spend and safety gates -----------------------------------------------------


SECRET_URL = 'https://operator:s3cret@endpoint.example/v1?token=tok3n'


def _assert_no_secret(capsys):
    captured = capsys.readouterr()
    text = captured.out + captured.err
    assert 's3cret' not in text and 'tok3n' not in text
    return text


def _locked_run(tmp_path, run_id, *, mock, mode='endpoint'):
    """A really prepared run store; the runner and the Modal worker stay stubbed."""
    from mailroom_sandbox.job.preflight import preflight
    from mailroom_sandbox.job.spec import RunSpec

    source = tmp_path / 'input.jsonl'
    source.write_text('{"id":"d0","doc_text":"hello"}\n', encoding='utf-8')
    spec = RunSpec(
        run_id=run_id,
        dataset={'provider': 'file', 'local_path': str(source)},
        engine={'kind': 'vllm-local', 'modal': None},
        job={'mock': mock, 'mode': mode, 'cost_cap_usd': 1.0, 'max_wall_seconds': 60},
        trace={'sink': 'none'},
    )
    assert preflight(spec, offline=True)['status'] == 'prepared'


def _no_execution(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('reached execution')

    monkeypatch.setattr(cli, '_run_endpoint', forbidden)
    monkeypatch.setattr('mailroom_sandbox.job.spend.authorize', forbidden)
    monkeypatch.setattr('mailroom_sandbox.job.remote.ensure_running', forbidden)


@pytest.mark.parametrize('argv', [
    ['modal', 'stop', '--app', ''], ['modal', 'stop', '--app', '  ', '--dry-run'],
    ['modal', 'logs', '--app', ''], ['hf', 'download', ''], ['hf', 'download', '--revision', ''],
    ['hf', 'download', '--local-dir', ' '],
])
def test_empty_targets_never_fall_back_to_the_default(argv):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(argv)
    assert exc.value.code == 2


@pytest.mark.parametrize('rest', [
    ['--dry-run'], ['--', '--max-num-seqs', '2', '--dry-run'], ['--dry-run', '--', '--max-num-seqs', '2'],
])
def test_vllm_serve_dry_run_never_starts_a_server(rest, monkeypatch, capsys):
    from mailroom_sandbox.services import vllm_cli

    def forbidden(*args, **kwargs):
        raise AssertionError('started vllm serve')

    monkeypatch.setattr(vllm_cli, 'stream_tool', forbidden)
    monkeypatch.setattr(vllm_cli, '_serve_argv', lambda args: (['vllm', 'serve'], {}, None))
    assert cli.main(['vllm', 'serve', *rest]) == 0
    out = capsys.readouterr().out
    assert 'nothing started' in out and '--dry-run' not in out.splitlines()[0]


def test_run_start_refuses_a_cap_the_modal_worker_would_ignore(tmp_path, monkeypatch, job_data_dir):
    import yaml

    config = tmp_path / 'run.yaml'
    config.write_text(yaml.safe_dump({
        'run_id': 'modal-cap', 'dataset': {'provider': 'file', 'local_path': str(tmp_path / 'x.jsonl')},
        'engine': {'kind': 'vllm-local', 'modal': None}, 'job': {'mode': 'modal'}, 'trace': {'sink': 'none'},
    }), encoding='utf-8')
    monkeypatch.setattr('mailroom_sandbox.job.preflight.preflight', lambda *a, **k: pytest.fail('preflight ran'))
    assert cli.main(['run', 'start', '--config', str(config), '--max-items', '5']) == 2
    with pytest.raises(pytest.fail.Exception):
        cli.main(['run', 'start', '--config', str(config)])  # the cap was the only refusal


@pytest.mark.parametrize(('flags', 'mock', 'mode', 'code'), [
    (['--mock'], False, 'endpoint', 3),
    (['--local'], True, 'endpoint', 3),
    (['--job-mode', 'modal'], False, 'endpoint', 3),
    (['--job-mode', 'endpoint'], False, 'modal', 3),
    (['--live'], False, 'endpoint', 2),
    (['--max-items', '5'], False, 'modal', 2),
])
def test_run_resume_refuses_flags_it_cannot_honour(flags, mock, mode, code, tmp_path, monkeypatch, job_data_dir, capsys):
    _locked_run(tmp_path, 'resume-refused', mock=mock, mode=mode)
    _no_execution(monkeypatch)
    assert cli.main(['run', 'resume', '--run-id', 'resume-refused', *flags]) == code
    if code == 3:
        assert 'drift_refused' in capsys.readouterr().out


def test_run_resume_accepts_flags_matching_the_lock(tmp_path, monkeypatch, job_data_dir):
    _locked_run(tmp_path, 'resume-same', mock=True)
    monkeypatch.setattr(cli, '_run_endpoint', lambda store, args: {'state': 'done'})
    monkeypatch.setattr('mailroom_sandbox.job.spend.authorize', lambda *a, **k: None)
    assert cli.main(['run', 'resume', '--run-id', 'resume-same', '--mock', '--job-mode', 'endpoint', '--max-items', '1']) == 0


@pytest.mark.parametrize(('pinned', 'flag', 'expected', 'ok'), [
    (None, 'custom', 'custom', True),  # used to check nothing at all
    ('custom', 'custom', 'custom', True),
    ('pinned', 'other', None, False),  # a conflict must block, not silently check the pin
])
def test_benchmark_check_enforces_the_requested_modal_profile(pinned, flag, expected, ok, monkeypatch):
    from types import SimpleNamespace

    seen = {}

    def posture(*, expected_modal_profile, **kwargs):
        seen['expected'] = expected_modal_profile
        return {'ok': True, 'errors': [], 'warnings': []}

    suite = SimpleNamespace(suite_id='s', track='a', configs=['c.yaml'], modal_profile_env='',
                            resolve_modal_profile=lambda: pinned)
    monkeypatch.setattr('mailroom_sandbox.job.suite.load_suite', lambda name: suite)
    monkeypatch.setattr('mailroom_sandbox.job.spec.load_run_spec', lambda cfg: SimpleNamespace(run_id='r'))
    monkeypatch.setattr('mailroom_sandbox.job.benchmark_check.check_benchmark_posture', posture)
    rc = cli.main(['run', 'benchmark-check', '--suite', 's', '--modal-profile', flag])
    assert rc == (0 if ok else 1)
    assert seen.get('expected') == expected


def test_health_never_prints_endpoint_credentials(monkeypatch, capsys):
    from types import SimpleNamespace

    monkeypatch.setattr('mailroom_sandbox.health.health_check', lambda profile: {'ok': True, 'base_url': SECRET_URL})
    monkeypatch.setattr('mailroom_sandbox.health.missing_modal_endpoint', lambda profile: False)
    monkeypatch.setattr('mailroom_sandbox.health.probe_models', lambda *a, **k: SimpleNamespace(as_dict=lambda: {'detail': SECRET_URL}))
    assert cli.main(['health', '--profile', 'ollama']) == 0
    assert 'endpoint.example' in _assert_no_secret(capsys)


@pytest.mark.parametrize('flags', [[], ['--json']])
def test_modal_url_never_prints_endpoint_credentials(flags, monkeypatch, capsys):
    monkeypatch.setenv('VLLM_BASE_URL', SECRET_URL)
    assert cli.main(['modal', 'url', *flags]) == 0
    assert 'endpoint.example' in _assert_no_secret(capsys)


@pytest.mark.parametrize('flags', [[], ['--json']])
def test_vllm_probe_never_prints_endpoint_credentials(flags, monkeypatch, capsys):
    from mailroom_sandbox import health
    from mailroom_sandbox.services import vllm_cli

    failed = health.ProbeResult(False, 'models', SECRET_URL, f'ConnectError: {SECRET_URL}')
    monkeypatch.setattr(vllm_cli, '_endpoint', lambda name: ({'name': 'modal-vllm'}, SECRET_URL))
    monkeypatch.setattr(vllm_cli, '_get', lambda url, headers: {'ok': False, 'url': url, 'detail': url})
    monkeypatch.setattr(health, '_headers', lambda profile: {})
    monkeypatch.setattr(health, 'probe_models', lambda profile: failed)
    monkeypatch.setattr('mailroom_sandbox.providers.endpoints_for', lambda *a, **k: type('E', (), {'chat_url': SECRET_URL}))
    assert cli.main(['vllm', 'probe', *flags]) == 1
    _assert_no_secret(capsys)


def test_uncaught_service_errors_never_print_endpoint_credentials(monkeypatch, capsys):
    from mailroom_sandbox.services import vllm_cli

    def fail(name):
        raise vllm_cli.ServiceError(f'cannot reach {SECRET_URL}')

    monkeypatch.setattr(vllm_cli, '_endpoint', fail)
    assert cli.main(['vllm', 'probe']) == 1
    _assert_no_secret(capsys)


@pytest.mark.parametrize('command', ['preflight', 'start'])
def test_dry_run_creates_no_run_directory(command, tmp_path, job_data_dir):
    import yaml

    from mailroom_sandbox.job.spec import run_dir

    config = tmp_path / 'run.yaml'
    config.write_text(yaml.safe_dump({
        'run_id': 'dry-only', 'dataset': {'provider': 'file', 'local_path': str(tmp_path / 'x.jsonl')},
        'engine': {'kind': 'vllm-local', 'modal': None}, 'trace': {'sink': 'none'},
    }), encoding='utf-8')
    assert cli.main(['run', command, '--config', str(config), '--dry-run']) == 0
    assert not run_dir('dry-only').exists()


def test_run_resume_live_is_refused_before_any_preflight(tmp_path, monkeypatch, job_data_dir):
    """`--config --force --live` must not let a preflight archive the generation before refusing."""
    _locked_run(tmp_path, 'resume-live', mock=True)
    monkeypatch.setattr('mailroom_sandbox.job.preflight.preflight', lambda *a, **k: pytest.fail('preflight ran'))
    config = tmp_path / 'unused.yaml'
    assert cli.main(['run', 'resume', '--run-id', 'resume-live', '--config', str(config), '--force', '--live']) == 2


def test_hf_local_dir_is_kept_exactly():
    """A blank --local-dir is refused, but a real path is not stripped."""
    args = cli.build_parser().parse_args(['hf', 'download', '--local-dir', ' data dir '])
    assert args.local_dir == ' data dir '


@pytest.mark.parametrize(('app', 'ok'), [('sandbox-other', True), ('prod-api', False), ('my-sandbox', False)])
def test_modal_stop_is_scoped_to_sandbox_apps(app, ok, monkeypatch, capsys):
    """`sandbox modal stop` never stops an app outside the sandbox's namespace."""
    from mailroom_sandbox.services import modal_cli

    monkeypatch.setattr(modal_cli, '_prepare', lambda: None)
    code = cli.main(['modal', 'stop', '--app', app, '--dry-run'])
    out = capsys.readouterr()
    if ok:
        assert code == 0 and 'nothing stopped' in out.out
    else:
        assert code != 0 and 'not a sandbox Modal app' in out.out + out.err


@pytest.mark.parametrize('extra', [['--host', '0.0.0.0'], ['--host=0.0.0.0']])
def test_vllm_serve_never_overrides_the_loopback_host(extra, monkeypatch, capsys):
    """Extras cannot re-bind a local serve beyond loopback."""
    from mailroom_sandbox.services import vllm_cli

    monkeypatch.setattr(vllm_cli, 'stream_tool', lambda *a, **k: pytest.fail('started vllm serve'))
    monkeypatch.setattr(vllm_cli, '_serve_argv', lambda args: (['vllm', 'serve', '--host', '0.0.0.0'], {}, None))
    assert cli.main(['vllm', 'serve', '--dry-run', '--', *extra]) != 0
    out = capsys.readouterr()
    assert '127.0.0.1' in out.out + out.err
