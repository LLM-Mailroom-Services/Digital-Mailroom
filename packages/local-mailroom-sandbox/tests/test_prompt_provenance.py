"""Prompt provenance for experiment logs (issue #39)."""

from __future__ import annotations

from mailroom_sandbox.eval.prompt_provenance import resolve_logged_prompt_version


def test_resolve_prefers_explicit_prompt_version():
    label, sha = resolve_logged_prompt_version(
        "sorter_local_v0",
        task="sorter",
        prompt_lock={
            "agents": {
                "sorter": {
                    "source": "local",
                    "file": "ignored_when_explicit",
                    "sha256": "deadbeef",
                }
            }
        },
    )
    assert label == "sorter_local_v0"
    assert sha == "deadbeef"


def test_resolve_local_lock_stem():
    label, sha = resolve_logged_prompt_version(
        None,
        task="contracts_specialist",
        prompt_lock={
            "agents": {
                "contracts_specialist": {
                    "source": "local",
                    "file": "contracts_specialist_v33",
                    "sha256": "abc123",
                }
            }
        },
    )
    assert label == "contracts_specialist_v33"
    assert sha == "abc123"


def test_resolve_catalog_stem_logs_eval_environment_key():
    label, sha = resolve_logged_prompt_version(
        None,
        task="correspondence_specialist",
        prompt_lock={
            "agents": {
                "correspondence_specialist": {
                    "source": "local",
                    "file": "correspondence_specialist_simplified",
                    "sha256": "eab63b5afd29906b1ad3aca2d7698bf5c15d4b7f4ce9ade3b744be535d18d4f3",
                }
            }
        },
    )
    assert label == "correspondence_specialist_v1"
    assert sha == "eab63b5afd29906b1ad3aca2d7698bf5c15d4b7f4ce9ade3b744be535d18d4f3"


def test_resolve_explicit_simplified_stem_is_eval_environment_v1():
    label, sha = resolve_logged_prompt_version(
        "contracts_specialist_v33_simplified",
        task="contracts_specialist",
    )
    assert label == "contracts_specialist_v1"
    assert sha == "d91de3967cc3b12cbd222cc5a4ae167b39578125abc83be7422498dc5024fd24"


def test_resolve_bound_prompt_when_unpinned():
    label, sha = resolve_logged_prompt_version(None, task="sorter")
    assert label != "mailroom-default"
    assert sha is None
