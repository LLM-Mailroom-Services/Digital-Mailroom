"""Edge inputs found by fuzzing every CLI leaf: each must end in one short line, never a traceback."""
from __future__ import annotations

import pytest

from mailroom_sandbox import cli


@pytest.mark.parametrize('command', ['up', 'down'])
@pytest.mark.parametrize('value', ['', 'nope', '/etc'])
def test_unknown_compose_profile_is_a_usage_error_listing_the_choices(command, value, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args([command, '--compose-profile', value])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert 'invalid choice' in err and 'langfuse' in err


@pytest.mark.parametrize(('command', 'missing', 'hint'), [
    ('watcher', 'langfuse', "pip install -e '.[observability]'"),
    ('api', 'fastapi', 'pip install fastapi'),
])
def test_pipeline_services_name_a_missing_dependency_before_launching(command, missing, hint, monkeypatch, capsys):
    import importlib.util

    real = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, 'find_spec', lambda name, *a: None if name == missing else real(name, *a))
    monkeypatch.setattr(cli.subprocess, 'call', lambda *a, **k: pytest.fail('launched without its dependency'))
    monkeypatch.setattr(cli, 'activate', lambda *a, **k: pytest.fail('activated before the dependency check'))
    assert cli.main(['pipeline', command]) == 1
    err = capsys.readouterr().err
    assert 'Traceback' not in err
    assert f'pipeline {command} needs {missing}' in err and hint in err


@pytest.mark.parametrize('argv', [
    ['--profile', '', 'agents', 'list'], ['agents', 'list', '--profile', '  '],
    ['--model', '', 'agents', 'list'], ['eval', 'sorter', '--prompt', ''],
])
def test_an_empty_global_flag_is_rejected_not_silently_defaulted(argv, capsys):
    # `--profile "$UNSET"` used to run on the default profile without a word.
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(argv)
    assert exc.value.code == 2
    assert 'empty' in capsys.readouterr().err


def test_an_unknown_profile_is_an_error_not_a_missing_command(capsys):
    assert cli.main(['--profile', 'nope', 'agents', 'list']) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: Unknown profile 'nope'") and 'modal-vllm' in err
    assert 'command unavailable' not in err


def test_tui_answers_an_unknown_command_in_one_line(monkeypatch, capsys):
    import sys

    from mailroom_sandbox.tui import shell

    monkeypatch.setattr(sys.stdin, 'isatty', lambda: True)
    entries = iter(['nope', 'run strat', 'x' * 400, 'exit'])
    monkeypatch.setattr('builtins.input', lambda prompt: next(entries))
    monkeypatch.setattr(cli, 'main', lambda argv: pytest.fail(f'dispatched an unknown command: {argv[:2]}'))
    assert shell.run_shell() == 0
    out = capsys.readouterr().out
    assert "error: unknown command 'nope'" in out
    assert "error: unknown command 'run strat' · did you mean start" in out
    assert 'usage: sandbox' not in out
    assert 'x' * 80 not in out


def test_a_missing_input_file_is_named_not_reported_as_a_missing_command(tmp_path, capsys):
    missing = tmp_path / 'nope.yaml'
    assert cli.main(['run', 'preflight', '--config', str(missing)]) == 1
    err = capsys.readouterr().err
    assert err.strip() == f'error: file not found: {missing}'


@pytest.mark.parametrize('argv', [
    ['eval', 'specialist', ''], ['eval', 'pipeline', '--class', ' '],
    ['subagents', 'sync', '--root', ''], ['subagents', 'doctor', '--root', ''],
    ['subagents', 'list', '--package', '__bogus__'], ['subagents', 'sync', '--package', ''],
    ['subagents', 'propagate', '--package', 'nope'],
])
def test_empty_or_unknown_values_are_usage_errors(argv, capsys):
    # Each used to exit 0: an empty target ran every specialist, an empty --root
    # synced into the working directory, an unknown package listed nothing.
    with pytest.raises(SystemExit) as exc:
        cli.build_parser().parse_args(argv)
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert 'empty' in err or 'unknown package' in err


def test_known_package_still_parses():
    from mailroom_sandbox.subagents import list_packages

    package = list_packages()[0]
    assert cli.build_parser().parse_args(['subagents', 'list', '--package', package]).package == package


def test_agents_show_rejects_an_unknown_agent(capsys):
    assert cli.main(['agents', 'show', '__bogus__']) == 2
    err = capsys.readouterr().err
    assert err.startswith("error: unknown agent '__bogus__'") and 'sorter' in err


def test_an_unknown_prompt_variant_is_an_error_not_a_missing_command(capsys):
    assert cli.main(['--prompt', '__bogus__', 'agents', 'list']) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: Unknown prompt variant '__bogus__'")


def test_a_missing_family_roster_names_the_file(tmp_path, monkeypatch, capsys):
    from mailroom_sandbox.subagents import family

    missing = tmp_path / 'config' / 'subagents' / 'family-roster.yaml'
    monkeypatch.setattr(family, 'family_roster_path', lambda root=None: missing)
    assert cli.main(['subagents', 'packages']) == 1
    assert capsys.readouterr().err.strip() == f'error: file not found: {missing}'


@pytest.mark.parametrize('module', ['mailroom_sandbox', 'mailroom_sandbox.cli'])
def test_python_dash_m_runs_the_cli(module):
    # `python -m mailroom_sandbox.cli` used to import the module and exit 0 silently.
    import subprocess
    import sys

    ok = subprocess.run([sys.executable, '-m', module, 'profiles'], capture_output=True, text=True, timeout=120)
    assert ok.returncode == 0 and 'modal-vllm' in ok.stdout
    bad = subprocess.run([sys.executable, '-m', module, 'nope'], capture_output=True, text=True, timeout=120)
    assert bad.returncode == 2 and 'invalid choice' in bad.stderr


def test_hidden_eval_tasks_still_dispatch_from_the_tui():
    # Hidden tasks (eval judge, eval sorter) still parse; the shell must not reject them.
    from mailroom_sandbox.tui import shell

    catalog = shell.command_catalog(cli.build_parser())
    assert 'judge' not in catalog[[n['path'] for n in catalog].index(['eval'])]['children']
    assert shell.unknown_path(['eval', 'judge'], catalog) is None
    assert shell.unknown_path(['eval', 'sorter', '--mock'], catalog) is None
    assert shell.unknown_path(['eval', 'judgee'], catalog).startswith("error: unknown command 'eval judgee'")


@pytest.mark.parametrize(('argv', 'code', 'starts'), [
    (['run', 'status', '--run-id', '-1'], 2, "error: run_id '-1' must match"),
    (['metrics', 'compare', '--runs', '/etc'], 2, "error: run_id '/etc' must match"),
    (['modal-matrix', 'show', '__bogus__'], 2, "error: model '__bogus__' not in config/models.yaml"),
    (['modal-matrix', 'env', '--gpu', '__bogus__'], 2, "error: gpu '__bogus__' not in known classes"),
])
def test_bad_ids_and_catalog_names_are_one_line_errors(argv, code, starts, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('MAILROOM_BASE_DIR', str(tmp_path))
    assert cli.main(argv) == code
    err = capsys.readouterr().err
    assert err.startswith(starts) and len(err.strip().splitlines()) == 1


def test_a_directory_or_non_yaml_config_is_named_in_one_line(tmp_path, capsys):
    assert cli.main(['run', 'preflight', '--config', str(tmp_path)]) == 1
    assert capsys.readouterr().err.strip() == f'error: expected a file, got a directory: {tmp_path}'
    bad = tmp_path / 'bad.yaml'
    bad.write_text('a: [unclosed\n')
    assert cli.main(['run', 'preflight', '--config', str(bad)]) == 1
    err = capsys.readouterr().err
    assert err.startswith('error: not valid YAML') and len(err.strip().splitlines()) == 1


def test_an_unresolvable_host_is_one_line(tmp_path, capsys):
    assert cli.main(['board', '--host', 'no-such-host.invalid', '--root', str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert err.strip() == "error: cannot resolve host 'no-such-host.invalid'"
