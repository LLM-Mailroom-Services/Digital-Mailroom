"""Exercise teardown with a fake Modal CLI: errors must never certify a stopped GPU."""
import json
import os
import subprocess

import pytest

from mailroom_sandbox.paths import repo_root


@pytest.fixture
def teardown(fake_bin, monkeypatch):
    monkeypatch.setenv('PATH', str(fake_bin.root) + os.pathsep + '/usr/bin:/bin')
    monkeypatch.setenv('MODAL_VLLM_APP_NAME', 'sandbox-vllm-test')
    def run():
        return subprocess.run(['/bin/bash', 'deploy/teardown_vllm.sh'], cwd=repo_root(),
            capture_output=True, text=True, timeout=10)
    return run


@pytest.mark.parametrize('listing', [
    {'stdout': 'bad json'}, {'stdout': '{}'}, {'stdout': '[{}]'},
    {'stdout': '[]', 'rc': 1, 'stderr': 'authentication failed'},
])
def test_listing_errors_never_report_teardown_complete(fake_bin, teardown, listing):
    fake_bin.add('modal', rules=[{'prefix': ['app', 'list'], **listing}])
    result = teardown()
    assert result.returncode != 0
    assert 'teardown complete' not in result.stdout and 'verified:' not in result.stdout


def test_missing_app_is_an_idempotent_success(fake_bin, teardown):
    fake_bin.add('modal', rules=[{'prefix': ['app', 'list'], 'stdout': '[]'}])
    result = teardown()
    assert result.returncode == 0, result.stderr
    assert 'sandbox-vllm-test already stopped' in result.stdout
    assert not any(call[:2] == ['app', 'stop'] for call in fake_bin.calls('modal'))


def test_stop_verifies_exact_app_and_keeps_other_fleet(fake_bin, teardown):
    rows = [{'description': name, 'state': 'deployed'} for name in ['sandbox-vllm-test', 'sandbox-vllm-other']]
    fake_bin.add('modal', rules=[{'prefix': ['app', 'list'], 'seq': [
        {'stdout': json.dumps(rows)}, {'stdout': json.dumps(rows[1:])},
    ]}])
    result = teardown()
    assert result.returncode == 0, result.stderr
    assert ['app', 'stop', 'sandbox-vllm-test', '--yes'] in fake_bin.calls('modal')
    assert "verified: no 'sandbox-vllm-test' deployment running" in result.stdout


def test_verification_failure_after_stop_is_not_success(fake_bin, teardown):
    rows = [{'description': 'sandbox-vllm-test', 'state': 'deployed'}]
    fake_bin.add('modal', rules=[{'prefix': ['app', 'list'], 'seq': [
        {'stdout': json.dumps(rows)}, {'stdout': 'not json'},
    ]}])
    result = teardown()
    assert result.returncode != 0
    assert 'teardown complete' not in result.stdout
