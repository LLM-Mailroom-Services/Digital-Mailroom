"""The board's opt-in polling publishes bounded, offline-by-default doctor snapshots."""
from threading import Event

import pytest

from mailroom_sandbox import cli
from mailroom_sandbox.services import poll
from mailroom_sandbox.services.doctor import ServiceStatus
from mailroom_sandbox.tui.services_snapshot import read_services


def test_polling_is_disabled_by_default(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError('default board must never run doctor')
    monkeypatch.setattr(poll, 'run_doctor', boom)
    with poll.periodic_services('modal-vllm'):
        pass


def test_periodic_checks_publish_and_stop(tmp_path, monkeypatch):
    calls = []
    repeated = Event()
    def doctor(profile, *, live):
        calls.append((profile, live))
        if len(calls) >= 2:
            repeated.set()
        return [ServiceStatus('test', 'ok', 'ready')]
    monkeypatch.setattr(poll, 'run_doctor', doctor)
    with poll.periodic_services('modal-vllm', interval=0.01, root=tmp_path):
        assert read_services(tmp_path)['services'][0]['detail'] == 'ready'
        assert repeated.wait(2)
    assert all(call == ('modal-vllm', False) for call in calls)
    count = len(calls)
    assert not Event().wait(0.04)
    assert len(calls) == count


def test_initial_publish_failure_warns_and_still_yields(tmp_path, monkeypatch, capsys):
    """A read-only/missing --root must not stop the board: publishing is optional."""
    monkeypatch.setattr(poll, 'run_doctor', lambda profile, **kw: [ServiceStatus('test', 'ok', 'ready')])

    def unavailable(*args, **kwargs):
        raise OSError('read-only root')

    monkeypatch.setattr(poll, 'publish_services', unavailable)
    with poll.periodic_services('modal-vllm', interval=0.01, root=tmp_path):
        pass
    assert 'could not publish service snapshot' in capsys.readouterr().err


def test_board_passes_polling_options_to_tui(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(poll, 'run_doctor', lambda profile, **kw: calls.append((profile, kw)) or [])
    assert cli.main(['board', '--profile', 'modal-vllm', '--tui', '--once', '--root', str(tmp_path), '--probe-interval', '60']) == 0
    assert calls == [('modal-vllm', {'live': False})]
    assert read_services(tmp_path)['live'] is False


@pytest.mark.parametrize('value', ['0', '-1', 'nan', 'inf'])
def test_polling_interval_must_be_finite_and_positive(value):
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(['board', '--probe-interval', value])


def test_live_requires_periodic_opt_in(capsys):
    assert cli.main(['board', '--live']) == 1
    assert '--probe-interval' in capsys.readouterr().err
