"""`sandbox hf …`: a guarded passthrough to the installed ``hf`` CLI (never ``huggingface-cli``).

Driven through ``cli.main`` with a fake ``hf``. The sandbox contributes three things: the
missing-binary guard, the pinned dataset revision as the default for the sandbox corpus,
and an explicit ``HF_HOME`` (the operator's own by default, ``data/cache/hf`` on request).
"""

from __future__ import annotations

import pytest

from mailroom_sandbox import cli
from mailroom_sandbox.datasets import HF_DATASET
from mailroom_sandbox.job.spec import FAMILY_HF_REVISION
from mailroom_sandbox.paths import repo_root


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setattr("mailroom_sandbox.paths.dotenv_files", lambda: [])
    for name in ("HF_HOME", "HF_TOKEN"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("sub", [["whoami"], ["download"], ["cache"]])
def test_missing_hf_names_the_install_hint_and_not_the_deprecated_cli(fake_bin, capsys, sub):
    assert cli.main(["hf", *sub]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and "`hf` not found" in err and "huggingface_hub" in err
    assert "huggingface-cli" not in err.replace("never `huggingface-cli`", "")


def test_whoami_runs_hf_auth_whoami_and_prints_the_identity(fake_bin, capsys):
    fake_bin.add("hf", stdout="alice\n")
    assert cli.main(["hf", "whoami"]) == 0
    assert fake_bin.calls("hf") == [["auth", "whoami"]]
    assert "alice" in capsys.readouterr().out


def test_whoami_when_logged_out_explains_both_ways_to_authenticate(fake_bin, capsys):
    fake_bin.add("hf", stderr="Not logged in\n", rc=1)
    assert cli.main(["hf", "whoami"]) == 1
    err = capsys.readouterr().err
    assert "hf auth login" in err and "HF_TOKEN" in err


def test_whoami_with_an_env_token_does_not_print_the_token(fake_bin, capsys, monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "hf_secret_value")
    fake_bin.add("hf", stdout="alice\n")
    assert cli.main(["hf", "whoami"]) == 0
    captured = capsys.readouterr()
    assert "hf_secret_value" not in captured.out + captured.err


def test_download_defaults_to_the_pinned_sandbox_dataset(fake_bin, capsys):
    fake_bin.add("hf")
    assert cli.main(["hf", "download"]) == 0
    assert fake_bin.calls("hf") == [
        ["download", HF_DATASET, "--repo-type", "dataset", "--revision", FAMILY_HF_REVISION]
    ]
    assert "sandbox datasets" in capsys.readouterr().out  # the next step


def test_download_an_explicit_revision_wins_over_the_pin(fake_bin):
    fake_bin.add("hf")
    assert cli.main(["hf", "download", "--revision", "main"]) == 0
    assert fake_bin.calls("hf")[0][-2:] == ["--revision", "main"]


def test_download_of_another_repo_is_not_pinned_to_the_dataset_revision(fake_bin):
    fake_bin.add("hf")
    assert cli.main(["hf", "download", "Qwen/Qwen3-8B", "--include", "*.json", "--include", "*.txt"]) == 0
    argv = fake_bin.calls("hf")[0]
    assert argv == ["download", "Qwen/Qwen3-8B", "--include", "*.json", "--include", "*.txt"]


def test_download_forwards_repo_type_exclude_and_local_dir(fake_bin, tmp_path):
    fake_bin.add("hf")
    target = str(tmp_path / "out")
    assert cli.main(
        ["hf", "download", "org/ds", "--repo-type", "dataset", "--exclude", "*.bin", "--local-dir", target]
    ) == 0
    assert fake_bin.calls("hf")[0] == [
        "download", "org/ds", "--repo-type", "dataset", "--exclude", "*.bin", "--local-dir", target,
    ]


def test_download_uses_the_operators_own_hf_home_by_default(fake_bin, monkeypatch):
    monkeypatch.setenv("HF_HOME", "/operator/hf")
    fake_bin.add("hf")
    cli.main(["hf", "download"])
    assert fake_bin.envs("hf")[0]["HF_HOME"] == "/operator/hf"


def test_download_sandbox_cache_points_hf_home_at_the_repo_cache(fake_bin, monkeypatch, capsys):
    monkeypatch.setenv("HF_HOME", "/operator/hf")
    fake_bin.add("hf")
    assert cli.main(["hf", "download", "--sandbox-cache"]) == 0
    expected = str(repo_root() / "data" / "cache" / "hf")
    assert fake_bin.envs("hf")[0]["HF_HOME"] == expected
    assert expected in capsys.readouterr().out  # the cache in use is always printed


def test_download_dry_run_prints_the_command_and_runs_nothing(fake_bin, capsys):
    fake_bin.add("hf")
    assert cli.main(["hf", "download", "--sandbox-cache", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert f"hf download {HF_DATASET} --repo-type dataset --revision {FAMILY_HF_REVISION}" in out
    assert "HF_HOME=" in out
    assert fake_bin.calls() == []


def test_download_dry_run_needs_no_hf_binary(fake_bin):
    assert cli.main(["hf", "download", "--dry-run"]) == 0


@pytest.mark.parametrize("stderr", ["401 Client Error: Unauthorized", "Cannot access gated repo"])
def test_download_auth_failures_point_at_the_token(fake_bin, capsys, stderr):
    fake_bin.add("hf", stderr=stderr + "\n", rc=1)
    assert cli.main(["hf", "download"]) == 1
    err = capsys.readouterr().err
    assert "rc=1" in err and "HF_TOKEN" in err


def test_download_other_failures_are_one_error_line(fake_bin, capsys):
    fake_bin.add("hf", stderr="connection reset\n", rc=1)
    assert cli.main(["hf", "download"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error: ") and "Traceback" not in err


def test_cache_lists_the_hf_cache(fake_bin, capsys):
    fake_bin.add("hf", stdout="ID  SIZE\n")
    assert cli.main(["hf", "cache"]) == 0
    assert fake_bin.calls("hf") == [["cache", "ls"]]
    assert "ID" in capsys.readouterr().out


def test_cache_revisions_and_sandbox_cache(fake_bin, capsys):
    fake_bin.add("hf")
    assert cli.main(["hf", "cache", "--revisions", "--sandbox-cache"]) == 0
    assert fake_bin.calls("hf") == [["cache", "ls", "--revisions"]]
    assert fake_bin.envs("hf")[0]["HF_HOME"].endswith("data/cache/hf")


def test_raw_passes_arguments_through_and_mirrors_the_exit_code(fake_bin):
    fake_bin.add("hf", rc=7)
    assert cli.main(["hf", "raw", "--", "auth", "login"]) == 7
    assert fake_bin.calls("hf") == [["auth", "login"]]


def test_raw_without_arguments_is_a_usage_error(fake_bin, capsys):
    fake_bin.add("hf")
    assert cli.main(["hf", "raw"]) == 2
    assert "usage" in capsys.readouterr().err


def test_bare_hf_group_prints_usage(capsys):
    assert cli.main(["hf"]) == 0
    out = capsys.readouterr().out
    assert "whoami" in out and "download" in out and "cache" in out


def test_whoami_failure_detail_has_no_colour_codes(fake_bin, capsys):
    """Seen against the real hf 2.3.0: its error text is wrapped in ANSI escapes."""
    fake_bin.add("hf", stderr="\x1b[1m\x1b[31mError: Not logged in.\x1b[0m\n", rc=1)
    assert cli.main(["hf", "whoami"]) == 1
    err = capsys.readouterr().err
    assert "\x1b" not in err and "Not logged in" in err


@pytest.mark.parametrize('command', [['whoami'], ['download'], ['cache'], ['raw', '--', 'auth', 'whoami']])
def test_dotenv_settings_reach_every_hf_child(fake_bin, monkeypatch, tmp_path, command):
    import hashlib

    env_file = tmp_path / '.env'
    monkeypatch.delenv("SANDBOX_SKIP_DOTENV")
    env_file.write_text('HF_TOKEN=dotenv-secret\nHF_HOME=/dotenv/cache\n')
    monkeypatch.setattr('mailroom_sandbox.runtime.dotenv_files', lambda: [env_file])
    fake_bin.add('hf')
    assert cli.main(['hf', *command]) == 0
    env = fake_bin.envs('hf')[0]
    assert env['HF_HOME'] == '/dotenv/cache'
    assert env['HF_TOKEN'] == 'sha256:' + hashlib.sha256(b'dotenv-secret').hexdigest()
    assert 'dotenv-secret' not in fake_bin.log.read_text()


def test_fake_binary_never_records_inherited_credentials(fake_bin, monkeypatch):
    monkeypatch.setenv('HF_TOKEN', 'inherited-hf-secret')
    monkeypatch.setenv('VLLM_API_KEY', 'inherited-vllm-secret')
    fake_bin.add('hf')
    assert cli.main(['hf', 'whoami']) == 0
    logged = fake_bin.log.read_text()
    assert 'inherited-hf-secret' not in logged and 'inherited-vllm-secret' not in logged
