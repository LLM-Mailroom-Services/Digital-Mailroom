"""`sandbox review`: terminal human review over the mailroom API.

A thin client for `GET /review/queue` and `POST /review/{doc_id}/resolve`. All
resolve logic (class validation, re-extraction, the audit trail) stays in the API;
this module only formats what it returns and refuses a few unambiguous misuses
before spending a request. The token is read from the environment and is never
printed, including inside error text.
"""

from __future__ import annotations

import ipaddress
import os
import sys
from typing import Any
from urllib.parse import quote, urlsplit

import httpx

from mailroom_sandbox.services._exec import ServiceError

# The vendored API binds 127.0.0.1:8000 unless MAILROOM_API_HOST / MAILROOM_API_PORT say otherwise.
DEFAULT_API_URL = "http://127.0.0.1:8000"
# Warn once per process when a bearer token rides plain HTTP off loopback.
_INSECURE_WARNED = False
DISAGREEMENT = "reviewer_disagreement"
LIST_TIMEOUT = 30.0
# An approving resume re-runs extraction (an LLM call) inside the request.
RESOLVE_TIMEOUT = 300.0
_FILE_WIDTH = 28


class ReviewError(ServiceError):
    """The API was unreachable or refused the request."""


def _usage(message: str) -> Exception:
    from mailroom_sandbox.cli import CLIUsageError  # lazy: cli imports this module's handlers lazily too

    return CLIUsageError(message)


def api_url() -> str:
    url = (os.environ.get("MAILROOM_API_URL") or "").strip() or DEFAULT_API_URL
    try:
        parts = urlsplit(url)
        valid = (
            parts.scheme in {"http", "https"} and parts.hostname and parts.port != 0
            and parts.username is None and parts.password is None
            and not parts.query and not parts.fragment
            and not any(c.isspace() or ord(c) < 32 for c in url)
        )
    except ValueError:
        valid = False
    if not valid:
        raise _usage("MAILROOM_API_URL must be an HTTP(S) URL without credentials, query, or fragment")
    _warn_plain_http_token(url, _token())
    return url.rstrip("/")


def _token() -> str | None:
    return (os.environ.get("MAILROOM_API_TOKEN") or "").strip() or None


def _warn_plain_http_token(base_url: str, token: str | None) -> None:
    """Stderr-warn once when a bearer token is sent over plain HTTP to a non-loopback host."""
    global _INSECURE_WARNED
    if _INSECURE_WARNED or not token or urlsplit(base_url).scheme != "http":
        return
    host = (urlsplit(base_url).hostname or "").rstrip(".").lower()
    try:
        loopback = ipaddress.ip_address(host).is_loopback
    except ValueError:
        loopback = host == "localhost" or host.endswith(".localhost")
    if loopback:
        return
    _INSECURE_WARNED = True
    print("Warning: MAILROOM_API_TOKEN is sent over plain HTTP to a non-loopback host; use HTTPS or a loopback URL",
          file=sys.stderr)


def _client(base_url: str, token: str | None, timeout: float) -> httpx.Client:
    _warn_plain_http_token(base_url, token)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return httpx.Client(base_url=base_url, headers=headers, timeout=timeout)


def _scrub(text: str, token: str | None) -> str:
    return text.replace(token, "***") if token else text


def _detail(resp: httpx.Response, token: str | None) -> str:
    """FastAPI puts the reason under ``detail``; fall back to the raw body."""
    try:
        detail = resp.json().get("detail")
    except (ValueError, AttributeError):
        detail = None
    if detail is None:
        detail = resp.text
    if not isinstance(detail, str):
        detail = str(detail)
    return " ".join(_scrub(detail, token).split())[:500] or resp.reason_phrase


def _request(method: str, path: str, *, timeout: float, json: dict | None = None) -> Any:
    base, token = api_url(), _token()
    try:
        with _client(base, token, timeout) as client:
            resp = client.request(method, path, json=json)
    except httpx.TimeoutException:
        raise ReviewError(
            f"the mailroom API at {base} did not answer within {timeout:g}s; "
            "a resume may still be running, so check `sandbox review list` before retrying"
        ) from None
    except httpx.HTTPError:
        raise ReviewError(
            f"cannot reach the mailroom API at {base}; start it with `sandbox pipeline api` "
            "or set MAILROOM_API_URL"
        ) from None
    if resp.status_code == 401:
        hint = "check MAILROOM_API_TOKEN" if token else "set MAILROOM_API_TOKEN"
        raise ReviewError(f"the API rejected the request (HTTP 401): {hint}")
    if resp.status_code >= 400:
        raise ReviewError(_scrub(f"HTTP {resp.status_code} from {base}: {_detail(resp, token)}", token))
    try:
        return resp.json()
    except ValueError:
        raise ReviewError(f"{base} returned a non-JSON response for {method} {path}") from None


def fetch_queue() -> list[dict[str, Any]]:
    body = _request("GET", "/review/queue", timeout=LIST_TIMEOUT)
    docs = body.get("documents") if isinstance(body, dict) else None
    if not isinstance(docs, list):
        raise ReviewError("unexpected /review/queue response: no 'documents' list")
    return [d for d in docs if isinstance(d, dict)]


def _causes(doc: dict[str, Any]) -> list[str]:
    causes = doc.get("review_causes")
    return [str(c) for c in causes] if isinstance(causes, list) else []


def _conf(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "-"
    return f"{value:.2f}"


def _label(name: Any, conf: Any) -> str:
    return f"{name or '-'} ({_conf(conf)})"


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    fmt = lambda cells: "  ".join(c.ljust(w) for c, w in zip(cells, widths)).rstrip()  # noqa: E731
    return [fmt(headers), fmt(["-" * w for w in widths]), *(fmt(r) for r in rows)]


def _cause_labels() -> dict[str, str]:
    try:
        from pipeline.reconsideration import CAUSE_LABELS
    except Exception:  # the plain token is still shown
        return {}
    return dict(CAUSE_LABELS)


def cmd_list(args) -> int:
    docs = fetch_queue()
    if not docs:
        print(f"Review queue is empty ({api_url()}).")
        return 0
    rows = []
    for d in docs:
        name = str(d.get("original_filename") or "-")
        if len(name) > _FILE_WIDTH:
            name = name[: _FILE_WIDTH - 3] + "..."
        rows.append([
            str(d.get("doc_id") or "-"),
            name,
            _label(d.get("doc_type"), d.get("classification_confidence")),
            _label(d.get("reviewer_doc_type"), d.get("reviewer_confidence")),
            ", ".join(_causes(d)) or "-",
        ])
    noun = "document" if len(docs) == 1 else "documents"
    print(f"Review queue: {len(docs)} {noun} waiting ({api_url()})\n")
    print("\n".join(_table(["DOC ID", "FILE", "SORTER (conf)", "REVIEWER (conf)", "CAUSES"], rows)))
    print("\nInspect one with: sandbox review show DOC_ID")
    return 0


def _find(doc_id: str) -> dict[str, Any] | None:
    return next((d for d in fetch_queue() if d.get("doc_id") == doc_id), None)


def cmd_show(args) -> int:
    doc = _find(args.doc_id)
    if doc is None:
        raise ReviewError(f"{args.doc_id} is not in the review queue ({api_url()}); `sandbox review list` shows what is")
    doc_id = str(doc.get("doc_id"))
    labels = _cause_labels()
    causes = _causes(doc)
    sorter, reviewer = doc.get("doc_type"), doc.get("reviewer_doc_type")

    print(f"Document  {doc_id}")
    print(f"File      {doc.get('original_filename') or '-'}  (matter {doc.get('matter_id') or '-'}, stage {doc.get('stage') or '-'})")
    print()
    print(f"Sorter    {sorter or '-'}  confidence {_conf(doc.get('classification_confidence'))}")
    reviewer_line = f"Reviewer  {reviewer or '-'}  confidence {_conf(doc.get('reviewer_confidence'))}"
    if doc.get("reviewer_model"):
        reviewer_line += f"  model {doc['reviewer_model']}"
    print(reviewer_line)
    if doc.get("reviewer_doc_subclass"):
        print(f"          subclass {doc['reviewer_doc_subclass']}")
    print(f"Verdict   {doc.get('review_verdict') or '-'}")
    print()
    print("Why it was parked")
    for cause in causes or ["(no causes recorded)"]:
        print(f"  {cause}" + (f"  {labels[cause]}" if cause in labels else ""))
    if doc.get("escalation_reason"):
        # The API returns the class cutoff only inside this sentence, not as its own field.
        print("\nPipeline reason (includes the class cutoff)")
        print(f"  {doc['escalation_reason']}")
    print("\nNext")
    base = f"sandbox review resolve {doc_id}"
    options = []
    if DISAGREEMENT in causes:
        if reviewer:
            options.append((f"--decision approved --doc-type {reviewer}", "take the reviewer's class"))
        if sorter:
            options.append((f"--decision approved --doc-type {sorter}", "keep the sorter's class"))
    else:
        options.append(("--decision approved", "accept and re-extract"))
    options.append(("--decision rejected", "send to the failed bin"))
    width = max(len(flags) for flags, _ in options)
    for flags, note in options:
        print(f"  {base} {flags.ljust(width)}   # {note}")
    return 0


def cmd_resolve(args) -> int:
    doc_type = args.doc_type
    if doc_type is not None:
        doc_type = doc_type.strip()
        if not doc_type:
            raise _usage("--doc-type must not be empty")
        if args.decision == "rejected":
            raise _usage("--doc-type only applies to --decision approved; a rejected document is not reclassified")
    elif args.decision == "approved":
        # Fail closed: without an explicit class, approve only a document the queue confirms
        # and whose recorded causes show no disagreement.
        doc = _find(args.doc_id)
        if doc is None:
            raise _usage(
                f"{args.doc_id} is not in the review queue ({api_url()}), so its causes cannot be checked; "
                "run `sandbox review list`, or pass --doc-type CLASS to approve explicitly"
            )
        causes = _causes(doc)
        if not causes:
            raise _usage(
                f"{args.doc_id} has no recorded review causes, so the approval cannot be checked for a "
                "reviewer disagreement; pass --doc-type CLASS to approve explicitly, or use --decision rejected"
            )
        if DISAGREEMENT in causes:
            raise _usage(
                f"{args.doc_id} was parked for {DISAGREEMENT} (sorter: {doc.get('doc_type') or '-'}, "
                f"reviewer: {doc.get('reviewer_doc_type') or '-'}); approving needs --doc-type CLASS "
                "for the class you decide on, or use --decision rejected"
            )

    body: dict[str, Any] = {"decision": args.decision, "disposition": "resume", "notes": args.notes or ""}
    if doc_type:
        body["override_doc_type"] = doc_type
    result = _request("POST", f"/review/{quote(args.doc_id, safe='')}/resolve", timeout=RESOLVE_TIMEOUT, json=body)

    if not isinstance(result, dict) or result.get("status") != "ok":
        raise ReviewError("unexpected resolve response; check `sandbox review list` before retrying")
    print(f"Resolved {result.get('doc_id') or args.doc_id}: {result.get('decision') or args.decision} "
          f"({result.get('disposition') or 'resume'})")
    override = result.get("class_override")
    if isinstance(override, dict) and override:
        print("  class override  " + ", ".join(f"{k}={v}" for k, v in override.items()))
    resume = result.get("resume")
    if isinstance(resume, dict):
        print(f"  resumed stage   {resume.get('stage') or '-'}")
        print(f"  doc type        {resume.get('doc_type') or '-'}")
        print(f"  extraction conf {_conf(resume.get('extraction_confidence'))}")
    if args.notes:
        print(f"  notes           {args.notes}")
    return 0
