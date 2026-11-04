"""Paid CLI work requires initials bound to the reviewed generation/settings."""
import json
import time

import pytest

from mailroom_sandbox import cli
from mailroom_sandbox.job import preflight, spend
from mailroom_sandbox.job.checkpoint import RunStore
from mailroom_sandbox.job.spec import DatasetSpec, EngineSpec, JobSpec, RunSpec, TraceSpec, run_dir
from mailroom_sandbox.services._exec import ServiceError


@pytest.fixture
def locked(tmp_path, monkeypatch, job_data_dir):
    monkeypatch.setattr('mailroom_sandbox.runtime.dotenv_files', lambda: [])
    monkeypatch.setattr('mailroom_sandbox.paths.dotenv_files', lambda: [])
    monkeypatch.setenv('VLLM_BASE_URL', 'https://gpu.test/v1')
    data = tmp_path / 'data.jsonl'
    data.write_text(json.dumps({'id': '1', 'doc_text': 'email', 'expected_doc_class': 'correspondence'})+'\n')
    spec = RunSpec(run_id='spend-test', task='sorter', profile='modal-vllm',
        dataset=DatasetSpec(provider='file', local_path=str(data)),
        engine=EngineSpec(kind='modal-vllm'), trace=TraceSpec(sink='none', otlp=False),
        job=JobSpec(mock=False, concurrency=1, cost_cap_usd=1, max_wall_seconds=60))
    import yaml
    config = tmp_path / 'run.yaml'
    config.write_text(yaml.safe_dump(spec.model_dump(by_alias=True)))
    assert preflight.preflight(spec, offline=True)['status'] == 'prepared'
    monkeypatch.setattr(spend.sys.stdin, 'isatty', lambda: False)
    return RunStore(run_dir(spec.run_id)), config


def test_unsigned_paid_start_and_resume_never_execute(locked, monkeypatch):
    store, config = locked
    monkeypatch.setattr(cli, '_run_endpoint', lambda *a, **k: pytest.fail('unsigned spend'))
    assert cli.main(['run', 'start', '--config', str(config)]) == 1
    assert cli.main(['run', 'resume', '--run-id', store.run_id]) == 1
    assert not (store.dir / spend.RECEIPT).exists()


def test_signature_is_recorded_and_reusable(locked):
    store, _ = locked
    receipt = spend.authorize(store, initials='jb')
    assert receipt['initials'] == 'JB'
    assert spend.authorize(store) == receipt
    assert (store.dir / spend.RECEIPT).stat().st_mode & 0o777 == 0o600


def test_endpoint_change_invalidates_signature(locked, monkeypatch):
    store, _ = locked
    spend.authorize(store, initials='JB')
    monkeypatch.setenv('VLLM_BASE_URL', 'https://other.test/v1')
    with pytest.raises(ServiceError, match='NOT authorized'):
        spend.authorize(store)


def test_workflow_smoke_change_invalidates_signature(locked):
    store, _ = locked
    spend.authorize(store, initials='JB', extra={'smoke_rows': 1})
    with pytest.raises(ServiceError):
        spend.authorize(store, extra={'smoke_rows': 3})


@pytest.mark.parametrize('initials', ['', 'J', 'yes!', 'ABCDEFG'])
def test_invalid_initials_never_authorize(locked, initials):
    store, _ = locked
    with pytest.raises(ServiceError):
        spend.authorize(store, initials=initials)
    assert not (store.dir / spend.RECEIPT).exists()


def test_expired_receipt_requires_new_signature(locked):
    store, _ = locked
    receipt = spend.authorize(store, initials='JB')
    receipt['signed_at'] = time.time() - spend.MAX_AGE_S - 1
    (store.dir / spend.RECEIPT).write_text(json.dumps(receipt))
    with pytest.raises(ServiceError):
        spend.authorize(store)


def test_signature_output_and_receipt_redact_credentials(locked, monkeypatch, capsys):
    store, _ = locked
    monkeypatch.setenv('VLLM_BASE_URL', 'https://user-secret:password-secret@gpu.test/v1?token=query-secret')
    spend.authorize(store, initials='JB')
    text = capsys.readouterr().err + (store.dir / spend.RECEIPT).read_text()
    assert 'gpu.test' in text
    assert all(secret not in text for secret in ['user-secret', 'password-secret', 'query-secret'])


@pytest.mark.parametrize("name", ["pipeline-modal", "pipeline-openrouter", "pipeline-hybrid", "pilot-sorter-modal-hf"])
def test_paid_example_configs_carry_a_budget(name):
    """SAND-087: shipped paid examples must pass the spend budget guard as written."""
    from pathlib import Path

    from mailroom_sandbox.job.spec import load_run_spec

    spec = load_run_spec(Path(__file__).resolve().parents[1] / "config" / "runs" / "examples" / f"{name}.yaml")
    assert spec.job.mock is False
    assert (spec.job.cost_cap_usd, spec.job.max_wall_seconds) == (1.0, 1800)
    spend.require_budget({"job": spec.job.model_dump()})


def test_gated_start_appends_a_ledger_row(locked):
    from mailroom_sandbox.job import ledger

    store, config = locked
    spend.authorize(store, initials='jb', ledger={'action': 'start', 'config': str(config)})
    [row] = ledger.rows()
    assert row['initials'] == 'JB' and row['action'] == 'start' and row['run_id'] == 'spend-test'
    assert row['spec'] == store.spec_hash()[:12] and row['rows'] == '1' and row['result'] == ''
    # Resume reuses the receipt and records a second row with the same signer.
    spend.authorize(store, ledger={'action': 'resume'})
    assert [r['action'] for r in ledger.rows()] == ['start', 'resume']


def test_refused_gate_appends_nothing(locked):
    from mailroom_sandbox.job import ledger

    store, _ = locked
    with pytest.raises(ServiceError):
        spend.authorize(store, ledger={'action': 'start'})
    assert ledger.rows() == []


@pytest.mark.parametrize('remaining, ok', [(5.0, True), (4.0, False), (0.5, False), (None, True)])
def test_key_headroom_gate(monkeypatch, remaining, ok):
    lock = {'engine': {'kind': 'openrouter'}, 'job': {'mock': False, 'api_cost_cap_usd': 1.2}}
    monkeypatch.delenv('OPENROUTER_KEY_RESERVE_USD', raising=False)  # the cases assume the default $3.00 reserve
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-not-a-key')
    monkeypatch.setattr(spend, 'key_headroom', lambda: {'limit': 12, 'limit_remaining': remaining, 'limit_reset': 'weekly'})
    if ok:
        spend.require_key_headroom(lock)
    else:
        with pytest.raises(ServiceError, match='remaining'):
            spend.require_key_headroom(lock)


def test_key_reserve_is_a_floor(monkeypatch):
    monkeypatch.setenv('OPENROUTER_KEY_RESERVE_USD', '1.0')
    assert spend.key_reserve_usd() == 3.0          # cannot be lowered
    assert spend.spendable_usd(5.25) == pytest.approx(2.25)
    assert spend.spendable_usd(2.0) == 0.0
    monkeypatch.setenv('OPENROUTER_KEY_RESERVE_USD', '4.5')
    assert spend.key_reserve_usd() == 4.5          # can be raised


def test_key_headroom_fails_closed(monkeypatch):
    lock = {'engine': {'kind': 'openrouter'}, 'job': {'mock': False, 'api_cost_cap_usd': 1.2}}
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-not-a-key')

    def boom():
        raise OSError('offline')
    monkeypatch.setattr(spend, 'key_headroom', boom)
    with pytest.raises(ServiceError, match='could not read'):
        spend.require_key_headroom(lock)


def test_key_headroom_skips_mock_and_non_openrouter(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-not-a-key')
    monkeypatch.setattr(spend, 'key_headroom', lambda: pytest.fail('queried'))
    spend.require_key_headroom({'engine': {'kind': 'openrouter'}, 'job': {'mock': True}})
    spend.require_key_headroom({'engine': {'kind': 'modal-vllm'}, 'job': {'mock': False}})
