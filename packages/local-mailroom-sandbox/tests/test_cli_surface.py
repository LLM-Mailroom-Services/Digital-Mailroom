"""Argparse surface checks only: no real command handlers or external services."""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pytest

from mailroom_sandbox import cli
_spec = importlib.util.spec_from_file_location(
    "check_cli_surface", Path(__file__).resolve().parents[1] / "scripts" / "check_cli_surface.py"
)
assert _spec and _spec.loader
surface = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(surface)


def _parser_at(parser, path):
    for name in path:
        parser = dict(surface.children(parser))[name]
    return parser


def _example(action):
    if action.choices:
        return str(next(iter(action.choices)))
    if action.type is not None:
        # Required typed arguments currently accept 1 or a known roster package;
        # verify rather than silently producing a misleading dispatch test if a
        # new constraint is added.
        from mailroom_sandbox.subagents import list_packages

        for candidate in ('1', '10', 'test', *list_packages()[:1]):
            try:
                action.type(candidate)
                return candidate
            except (ValueError, TypeError, argparse.ArgumentTypeError):
                continue
        raise AssertionError(f'no example for required {action.dest}')
    return 'example'


def _arguments(root, path):
    """Construct parser-valid input and retain spans for each required argument."""
    argv = []
    spans = []
    parser = root
    for index in range(len(path) + 1):
        for action in parser._actions:
            if not surface.required(action):
                continue
            start = len(argv)
            if action.option_strings:
                argv.append(action.option_strings[0])
            count = action.nargs if isinstance(action.nargs, int) else 1
            argv.extend([_example(action)] * count)
            spans.append((start, len(argv), action.dest))
        if index < len(path):
            name = path[index]
            argv.append(name)
            parser = dict(surface.children(parser))[name]
    return argv, spans


_NODE_PATHS = [path for path, _ in surface.nodes(cli.build_parser())]
_LEAF_PATHS = [path for path, parser in surface.nodes(cli.build_parser()) if not list(surface.children(parser))]


def _label(path):
    return 'sandbox ' + ' '.join(path)


def _each(paths, check):
    """Run ``check(path)`` for every command; fail once naming every offender."""
    failures = []
    for path in paths:
        try:
            check(path)
        except (AssertionError, pytest.fail.Exception) as exc:
            failures.append(f'{_label(path)}: {exc}')
    assert not failures, '\n'.join(failures)


def test_every_node_help_exits_successfully(capsys):
    def check(path):
        parser = cli.build_parser()
        with pytest.raises(SystemExit) as exc:
            parser.parse_args([*path, '--help'])
        assert exc.value.code == 0
        assert 'usage:' in capsys.readouterr().out.lower()

    _each(_NODE_PATHS, check)


def test_every_leaf_dispatches_to_registered_handler(monkeypatch):
    from mailroom_sandbox import runtime
    monkeypatch.setattr(runtime, 'load_env_file', lambda: None)

    def check(path):
        parser = cli.build_parser()
        leaf = _parser_at(parser, path)
        assert callable(leaf.get_default('handler')), 'no callable handler'
        argv, _ = _arguments(parser, path)
        seen = []

        def stub(args):
            seen.append(args)
            return 17

        leaf.set_defaults(handler=stub)
        with monkeypatch.context() as mp:
            mp.setattr(cli, 'build_parser', lambda: parser)
            assert cli.main(argv) == 17
        assert len(seen) == 1

    _each(_LEAF_PATHS, check)


def test_parser_rejects_each_missing_required_argument(capsys):
    def check(path):
        parser = cli.build_parser()
        argv, spans = _arguments(parser, path)
        for start, end, dest in spans:
            with pytest.raises(SystemExit) as exc:
                parser.parse_args(argv[:start] + argv[end:])
            assert exc.value.code == 2, dest
            assert 'required' in capsys.readouterr().err.lower(), dest

    _each(_LEAF_PATHS, check)


def test_generated_reference_is_current():
    assert surface.REFERENCE.read_text(encoding='utf-8') == surface.render(cli.build_parser())
