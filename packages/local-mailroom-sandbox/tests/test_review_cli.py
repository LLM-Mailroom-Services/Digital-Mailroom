"""`sandbox review`: terminal human review over the mailroom API (httpx.MockTransport, no network)."""

from __future__ import annotations

import json

import httpx
import pytest

from mailroom_sandbox import cli, review_cli

TOKEN = "s3cr3t-token-value"

DISAGREE = {
    "doc_id": "doc_disagree",
    "matter_id": "M-1",
    "original_filename": "letter.pdf",
    "stage": "review",
    "doc_type": "contract",
    "classification_confidence": 0.91,
    "review_causes": ["reviewer_disagreement"],
    "review_verdict": "disagree",
    "reviewer_doc_type": "correspondence",
    "reviewer_confidence": 0.82,
    "reviewer_model": "qwen3-8b",
    "escalation_reason": (
        "decision review: sorter='contract' (0.91) -> reviewer='correspondence' "
        "(0.82, cutoff 0.90): disagree [reviewer_disagreement] -- routing to human review"
    ),
}
LOW_CONF = {
    "doc_id": "doc_low",
    "original_filename": "claim.pdf",
    "stage": "review",
    "doc_type": "insurance_claim",
    "classification_confidence": 0.7,
    "review_causes": ["reviewer_low_confidence"],
    "reviewer_doc_type": "insurance_claim",
    "reviewer_confidence": 0.55,
    "escalation_reason": "decision review: ... cutoff 0.90 ... [reviewer_low_confidence]",
}
QUEUE = {"review_queue": 2, "documents": [DISAGREE, LOW_CONF]}


class Api:
    """Records requests and answers like the mailroom API."""

    def __init__(self, resolve_response=None, queue=QUEUE):
        self.requests: list[httpx.Request] = []
        self.resolve_response = resolve_response or httpx.Response(
            200, json={"status": "ok", "doc_id": "doc_disagree", "decision": "approved", "disposition": "resume",
                       "class_override": {"doc_type": "correspondence"},
                       "resume": {"stage": "archived", "doc_type": "correspondence", "extraction_confidence": 0.93}},
        )
        self.queue = queue

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method == "GET" and request.url.path == "/review/queue":
            return httpx.Response(200, json=self.queue)
        if request.method == "POST" and request.url.path.endswith("/resolve"):
            return self.resolve_response
        return httpx.Response(404, json={"detail": "not found"})

    @property
    def posts(self):
        return [r for r in self.requests if r.method == "POST"]


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setenv("MAILROOM_API_URL", "http://mailroom.test")
    monkeypatch.setenv("MAILROOM_API_TOKEN", TOKEN)
    holder = {"api": Api()}

    def fake_client(base_url, token, timeout):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return httpx.Client(base_url=base_url, headers=headers, timeout=timeout,
                            transport=httpx.MockTransport(holder["api"]))

    monkeypatch.setattr(review_cli, "_client", fake_client)
    return holder


def test_list_shows_causes_and_both_labels(api, capsys):
    assert cli.main(["review", "list"]) == 0
    out = capsys.readouterr().out
    assert "doc_disagree" in out and "doc_low" in out
    assert "contract" in out and "correspondence" in out  # sorter and reviewer labels
    assert "0.91" in out and "0.82" in out
    assert "reviewer_disagreement" in out and "reviewer_low_confidence" in out
    assert TOKEN not in out
    assert api["api"].requests[0].headers["authorization"] == f"Bearer {TOKEN}"


def test_list_empty_queue_says_so(api, capsys):
    api["api"] = Api(queue={"review_queue": 0, "documents": []})
    assert cli.main(["review", "list"]) == 0
    assert "empty" in capsys.readouterr().out.lower()


def test_show_prints_cutoff_reason_and_opinions(api, capsys):
    assert cli.main(["review", "show", "doc_disagree"]) == 0
    out = capsys.readouterr().out
    assert "cutoff 0.90" in out  # the API only carries the cutoff inside escalation_reason
    assert "contract" in out and "0.91" in out  # sorter opinion
    assert "correspondence" in out and "0.82" in out and "qwen3-8b" in out  # reviewer opinion
    assert "disagree" in out
    assert "reviewer_disagreement" in out
    assert "sandbox review resolve doc_disagree" in out  # next-step hint
    assert TOKEN not in out


def test_show_unknown_doc_is_an_error(api, capsys):
    assert cli.main(["review", "show", "nope"]) == 1
    assert "nope" in capsys.readouterr().err


def test_resolve_sends_disposition_resume_and_override(api, capsys):
    argv = ["review", "resolve", "doc_disagree", "--decision", "approved",
            "--doc-type", "correspondence", "--notes", "header says letter"]
    assert cli.main(argv) == 0
    (post,) = api["api"].posts
    assert post.url.path == "/review/doc_disagree/resolve"
    assert json.loads(post.content) == {
        "decision": "approved",
        "disposition": "resume",
        "notes": "header says letter",
        "override_doc_type": "correspondence",
    }
    out = capsys.readouterr().out
    assert "approved" in out and "archived" in out and "0.93" in out
    assert TOKEN not in out


def test_reject_sends_no_override(api):
    assert cli.main(["review", "resolve", "doc_disagree", "--decision", "rejected"]) == 0
    (post,) = api["api"].posts
    body = json.loads(post.content)
    assert body["decision"] == "rejected" and "override_doc_type" not in body


def test_disagreement_approval_requires_doc_type(api, capsys):
    assert cli.main(["review", "resolve", "doc_disagree", "--decision", "approved"]) == 2
    err = capsys.readouterr().err
    assert "--doc-type" in err and "reviewer_disagreement" in err
    assert api["api"].posts == []


def test_non_disagreement_approval_needs_no_doc_type(api):
    api["api"].resolve_response = httpx.Response(200, json={"status": "ok", "doc_id": "doc_low", "decision": "approved", "disposition": "resume"})
    assert cli.main(["review", "resolve", "doc_low", "--decision", "approved"]) == 0
    assert "override_doc_type" not in json.loads(api["api"].posts[0].content)


def test_approval_of_unknown_doc_without_doc_type_fails_closed(api, capsys):
    assert cli.main(["review", "resolve", "nope", "--decision", "approved"]) == 2
    assert "not in the review queue" in capsys.readouterr().err
    assert api["api"].posts == []


@pytest.mark.parametrize("causes", [None, []], ids=["none", "empty"])
def test_approval_without_recorded_causes_fails_closed(api, capsys, causes):
    api["api"] = Api(queue={"documents": [{**LOW_CONF, "review_causes": causes}]})
    assert cli.main(["review", "resolve", "doc_low", "--decision", "approved"]) == 2
    assert "no recorded review causes" in capsys.readouterr().err
    assert api["api"].posts == []


def test_explicit_doc_type_or_reject_skips_the_causes_check(api):
    api["api"] = Api(queue={"documents": []})
    assert cli.main(["review", "resolve", "nope", "--decision", "approved", "--doc-type", "contract"]) == 0
    assert cli.main(["review", "resolve", "nope", "--decision", "rejected"]) == 0
    assert len(api["api"].posts) == 2


def test_malformed_json_200_is_a_clean_error(api, capsys):
    api["api"].resolve_response = httpx.Response(200, text="<html>not json</html>")
    assert cli.main(["review", "resolve", "doc_disagree", "--decision", "rejected"]) == 1
    err = capsys.readouterr().err
    assert "non-JSON" in err and "Traceback" not in err


def test_doc_type_with_reject_is_a_usage_error(api, capsys):
    argv = ["review", "resolve", "doc_disagree", "--decision", "rejected", "--doc-type", "contract"]
    assert cli.main(argv) == 2
    assert "--doc-type" in capsys.readouterr().err
    assert api["api"].requests == []


@pytest.mark.parametrize("value", ["", "   "])
def test_empty_doc_type_is_a_usage_error(api, capsys, value):
    assert cli.main(["review", "resolve", "doc_disagree", "--decision", "approved", "--doc-type", value]) == 2
    assert api["api"].requests == []


def test_api_unreachable_gives_clear_error(monkeypatch, capsys):
    monkeypatch.setenv("MAILROOM_API_URL", "http://mailroom.test")
    monkeypatch.setenv("MAILROOM_API_TOKEN", TOKEN)

    def refuse(request):
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(
        review_cli, "_client",
        lambda base_url, token, timeout: httpx.Client(base_url=base_url, transport=httpx.MockTransport(refuse)),
    )
    assert cli.main(["review", "list"]) == 1
    err = capsys.readouterr().err
    assert "http://mailroom.test" in err and "MAILROOM_API_URL" in err
    assert "Traceback" not in err and TOKEN not in err


def test_second_resolve_reports_api_error(api, capsys):
    api["api"].resolve_response = httpx.Response(
        400, json={"detail": "Document is not in review (current stage: archived); use disposition=record"}
    )
    argv = ["review", "resolve", "doc_disagree", "--decision", "approved", "--doc-type", "contract"]
    assert cli.main(argv) == 1
    err = capsys.readouterr().err
    assert "400" in err and "not in review" in err


def test_unauthorized_never_leaks_token(api, capsys):
    def deny(request):
        return httpx.Response(401, json={"detail": "Missing or invalid API token"})

    api["api"] = deny
    assert cli.main(["review", "list"]) == 1
    captured = capsys.readouterr()
    assert "401" in captured.err and "MAILROOM_API_TOKEN" in captured.err
    assert TOKEN not in captured.err + captured.out


def test_token_is_scrubbed_from_error_text(api, capsys):
    api["api"].resolve_response = httpx.Response(500, text=f"boom {TOKEN} boom")
    argv = ["review", "resolve", "doc_disagree", "--decision", "rejected"]
    assert cli.main(argv) == 1
    err = capsys.readouterr().err
    assert TOKEN not in err and "boom" in err


def test_error_redacts_token_before_truncating_body(api, capsys):
    api["api"].resolve_response = httpx.Response(500, text="x" * 495 + TOKEN)
    assert cli.main(["review", "resolve", "doc_disagree", "--decision", "rejected"]) == 1
    assert TOKEN[:5] not in capsys.readouterr().err


def test_resolve_timeout_warns_without_retrying(api, capsys):
    attempts = []

    def timeout(request):
        attempts.append(request)
        raise httpx.ReadTimeout("sensitive provider error", request=request)

    api["api"] = timeout
    assert cli.main(["review", "resolve", "doc_disagree", "--decision", "rejected"]) == 1
    assert len(attempts) == 1
    err = capsys.readouterr().err
    assert "may still be running" in err and "before retrying" in err
    assert "sensitive" not in err


def test_url_defaults_to_the_api_local_default(monkeypatch):
    monkeypatch.delenv("MAILROOM_API_URL", raising=False)
    assert review_cli.api_url() == "http://127.0.0.1:8000"


def test_url_must_be_http(monkeypatch):
    monkeypatch.setenv("MAILROOM_API_URL", "ftp://x")
    with pytest.raises(cli.CLIUsageError):
        review_cli.api_url()


def test_review_flags_work_before_or_after_subcommand(api):
    assert cli.main(["--profile", "ollama", "review", "list"]) == 0
    assert cli.main(["review", "list", "--profile", "ollama"]) == 0


@pytest.mark.parametrize("url", [
    f"http://user:{TOKEN}@mailroom.test", f"http://mailroom.test?token={TOKEN}",
    f"http://mailroom.test#{TOKEN}", "http://", "http://mailroom.test:bad",
    "http://mailroom.test:0", "http://mailroom.test/with space", "http://[invalid",
])
def test_invalid_api_url_is_rejected_without_echoing_secrets(monkeypatch, capsys, url):
    monkeypatch.setenv("MAILROOM_API_URL", url)
    assert cli.main(["review", "list"]) == 2
    captured = capsys.readouterr()
    assert TOKEN not in captured.err + captured.out


@pytest.mark.parametrize("body", [[], None, {}, {"status": "failed"}])
def test_resolve_does_not_claim_success_for_unexpected_response(api, capsys, body):
    api["api"].resolve_response = httpx.Response(200, content=json.dumps(body))
    assert cli.main(["review", "resolve", "doc_disagree", "--decision", "rejected"]) == 1
    captured = capsys.readouterr()
    assert "Resolved" not in captured.out
    assert "check `sandbox review list`" in captured.err


@pytest.mark.parametrize("url,token,warn", [
    ("http://mailroom.test", TOKEN, True),
    ("http://192.0.2.1", TOKEN, True),
    ("http://mailroom.test", "", False),
    ("https://mailroom.test", TOKEN, False),
    ("http://localhost", TOKEN, False),
    ("http://mailroom.localhost.", TOKEN, False),
    ("http://127.0.0.2", TOKEN, False),
    ("http://[::1]", TOKEN, False),
])
def test_http_token_warning(monkeypatch, capsys, url, token, warn):
    monkeypatch.setattr(review_cli, "_INSECURE_WARNED", False)
    monkeypatch.setenv("MAILROOM_API_URL", url)
    monkeypatch.setenv("MAILROOM_API_TOKEN", token)
    assert review_cli.api_url() == url
    captured = capsys.readouterr()
    assert ("Warning" in captured.err) is warn
    assert TOKEN not in captured.err


def test_plain_http_token_warns_once(capsys):
    review_cli._INSECURE_WARNED = False
    review_cli._warn_plain_http_token("http://203.0.113.7:8000", "s3cr3t")
    first = capsys.readouterr().err
    assert "MAILROOM_API_TOKEN" in first and "plain HTTP" in first
    # second call is suppressed (once per process)
    review_cli._warn_plain_http_token("http://203.0.113.7:8000", "s3cr3t")
    assert capsys.readouterr().err == ""
    # loopback hosts do not warn
    review_cli._INSECURE_WARNED = False
    review_cli._warn_plain_http_token("http://127.0.0.1:8000", "s3cr3t")
    assert capsys.readouterr().err == ""
    review_cli._INSECURE_WARNED = False


def test_api_url_warns_once_before_constructing_client(monkeypatch, capsys):
    monkeypatch.setattr(review_cli, "_INSECURE_WARNED", False)
    monkeypatch.setenv("MAILROOM_API_URL", "http://mailroom.test")
    monkeypatch.setenv("MAILROOM_API_TOKEN", TOKEN)
    url = review_cli.api_url()
    assert "plain HTTP" in capsys.readouterr().err
    assert review_cli.api_url() == url
    with review_cli._client(url, TOKEN, 1):
        pass
    assert capsys.readouterr().err == ""
