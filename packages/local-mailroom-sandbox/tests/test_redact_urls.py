"""Credentials in endpoint URLs never reach doctor/board output."""
from __future__ import annotations

import pytest

from mailroom_sandbox.services._redact import redact_urls


def test_userinfo_is_removed_and_host_kept():
    assert redact_urls("https://user:pw@vllm.example.test/v1/models") == "https://vllm.example.test/v1/models"


def test_query_values_are_redacted():
    assert redact_urls("https://vllm.example.test/v1?api_key=secret") == "https://vllm.example.test/v1?REDACTED"


@pytest.mark.parametrize("value", [
    "https://user:p#ss@host/v1",
    "https://user:p?x@host/v1",
    "https://user:123?x@host/v1",
])
def test_ambiguous_url_tokens_are_rejected_whole(value):
    """``#``/``?`` can end ``netloc`` before the ``@host`` suffix, so formatting
    would keep a credential fragment (``https://user:p`` / ``?REDACTED``)."""
    out = redact_urls(value)
    assert out == "[invalid endpoint]"
    assert "user" not in out


def test_redaction_applies_inside_sentences():
    out = redact_urls("probe https://user:p#ss@host/v1 failed")
    assert out.startswith("probe [invalid endpoint] failed")
