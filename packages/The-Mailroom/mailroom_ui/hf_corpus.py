"""Hugging Face corpus pin for The-Mailroom eval / Langfuse dataset sync.

``Lucius-Morningstar/mailroom-dataset`` (v9, pinned revision) is the
authoritative full corpus. Display still comes from Langfuse traces; this
module only covers Hub GT / pilot intake so scripts hit one pinned revision
via the datasets-server REST API (no ``datasets`` / ``huggingface_hub``
runtime dep on the hot path).
"""

from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any

ORG = "Lucius-Morningstar"
# Renamed 2026-09-02 (human directive): Hub repo mailroom-corpus
# (formerly docclass-merged); old id serves a Hub redirect. The v9
# successor (2026-09-12) is published as mailroom-dataset; mailroom-corpus
# stays as the frozen v8 baseline.
FULL_CORPUS_ID = f"{ORG}/mailroom-dataset"
EXAMPLES_ID = f"{ORG}/docclass-pilot"
# v9 tip (2026-09-12): mailroom-dataset v1 — 3,302-row hardened ground_truth
# on top of the frozen v8 base eafe1ab4.
FULL_CORPUS_REVISION = "fe3a6f96130d2f9612e9bd1aa5a730de965f332f"
GT_CONFIG = "ground_truth"
DEFAULT_CONFIG = "default"
ROWS_API = "https://datasets-server.huggingface.co/rows"


def corpus_id() -> str:
    return (os.environ.get("MAILROOM_HF_DATASET") or FULL_CORPUS_ID).strip()


def corpus_revision() -> str:
    return (os.environ.get("MAILROOM_HF_REVISION") or FULL_CORPUS_REVISION).strip()


def gt_config() -> str:
    return (os.environ.get("MAILROOM_HF_CONFIG") or GT_CONFIG).strip() or GT_CONFIG


def _auth_headers() -> dict[str, str]:
    token = (
        os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        or ""
    ).strip()
    headers = {"User-Agent": "the-mailroom-hf-corpus/1.0", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_rows(
    *,
    dataset: str | None = None,
    config: str,
    split: str,
    revision: str | None = None,
    page_size: int = 100,
    max_rows: int | None = None,
    offset: int = 0,
    page_sleep: float = 0.0,
) -> list[dict[str, Any]]:
    """Page the Hub datasets-server ``/rows`` API for one config/split.

    ``offset`` starts paging at a row index within the split (used for
    single-row / windowed fetches by the TUI corpus browser and the Pages
    corpus catalog).  ``page_sleep`` paces requests between pages — the
    unauthenticated Hub budget is small, so long exports should pass
    something like 1.0.
    """
    ds = dataset or corpus_id()
    rev = revision if revision is not None else corpus_revision()
    out: list[dict[str, Any]] = []
    headers = _auth_headers()
    while True:
        length = page_size
        if max_rows is not None:
            remaining = max_rows - len(out)
            if remaining <= 0:
                break
            length = min(page_size, remaining)
        q = {
            "dataset": ds,
            "config": config,
            "split": split,
            "offset": str(offset),
            "length": str(length),
        }
        if rev:
            q["revision"] = rev
        url = ROWS_API + "?" + urllib.parse.urlencode(q)
        last: Exception | None = None
        page: dict[str, Any] | None = None
        # 429 (rate limit) needs a much slower ladder than transient 5xx
        # blips — the unauthenticated datasets-server budget is small.
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as resp:
                    page = json.loads(resp.read().decode())
                break
            except urllib.error.HTTPError as exc:
                last = exc
                if exc.code == 429:
                    time.sleep(5.0 * (2 ** attempt))  # 5s, 10s, 20s, 40s
                else:
                    time.sleep(2 * (attempt + 1))
            except Exception as exc:  # noqa: BLE001 — transient Hub blips
                last = exc
                time.sleep(2 * (attempt + 1))
        if page is None:
            raise RuntimeError(f"HF rows fetch failed: {url}: {last}")
        batch = [r["row"] for r in (page.get("rows") or [])]
        if not batch:
            break
        out.extend(batch)
        if len(batch) < length:
            break
        offset += len(batch)
        if page_sleep > 0:
            time.sleep(page_sleep)
    return out


def load_ground_truth(
    *,
    splits: tuple[str, ...] = ("train", "test"),
    dataset: str | None = None,
    revision: str | None = None,
) -> dict[str, dict[str, Any]]:
    """filename → ground_truth row from the corrected merged corpus."""
    by_file: dict[str, dict[str, Any]] = {}
    for split in splits:
        for row in fetch_rows(
            dataset=dataset,
            config=gt_config(),
            split=split,
            revision=revision,
        ):
            fn = row.get("filename")
            if fn:
                by_file[str(fn)] = row
    return by_file
