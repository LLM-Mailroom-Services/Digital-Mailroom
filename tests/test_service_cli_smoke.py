"""Opt-in real CLI contracts; endpoint smoke has its own billed-request opt-in.

SANDBOX_SERVICE_SMOKE=1 pytest -q tests/test_service_cli_smoke.py
Add SANDBOX_LIVE_PROVIDER_SMOKE=1 and VLLM_BASE_URL to probe a live endpoint.
No test deploys an app, downloads weights, stops an app, or changes credentials.
"""
import os

import pytest

from mailroom_sandbox import cli
from mailroom_sandbox.services._exec import run_tool
from mailroom_sandbox.services.modal_cli import PINNED_SDK

pytestmark = [
    pytest.mark.service_smoke,
    pytest.mark.skipif(os.environ.get('SANDBOX_SERVICE_SMOKE') != '1', reason='SANDBOX_SERVICE_SMOKE not set'),
]


def test_real_modal_version_and_wrapper_flags():
    result = run_tool(['modal', '--version'])
    assert PINNED_SDK in result.stdout
    for command, flags in [(['app', 'stop'], ['--yes']), (['app', 'logs'], ['--follow']), (['app', 'list'], ['--json'])]:
        help_text = run_tool(['modal', *command, '--help']).stdout
        assert all(flag in help_text for flag in flags)


def test_real_hf_wrapper_flags():
    for command, flags in [(['download'], ['--revision', '--include', '--exclude', '--local-dir', '--repo-type']),
                           (['cache', 'ls'], ['--revisions']), (['auth', 'whoami'], [])]:
        help_text = run_tool(['hf', *command, '--help']).stdout
        assert all(flag in help_text for flag in flags)


@pytest.mark.skipif(os.environ.get('SANDBOX_LIVE_PROVIDER_SMOKE') != '1', reason='billed endpoint smoke not opted in')
def test_live_provider_contract():
    assert os.environ.get('VLLM_BASE_URL'), 'export the deployed VLLM_BASE_URL explicitly'
    assert cli.main(['vllm', 'probe', '--profile', 'modal-vllm', '--json']) == 0
