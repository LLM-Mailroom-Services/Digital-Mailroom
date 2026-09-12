"""Corpus browser for the mailroom-tui REPL.

Reads ``Lucius-Morningstar/mailroom-dataset`` through the canonical
``mailroom_ui.hf_corpus`` paging ladder (stdlib-only, retries, no ``datasets``
dependency).  A slim in-memory catalog (filename / split / class / subclass /
sha / index offset) backs listing, stats, and search — instant once built;
full ``doc_text`` and ground-truth rows are fetched per-row on demand and kept
in a small LRU.  The Hub being unreachable is an explicit closed state
(``CorpusClosed``), never canned data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from mailroom_ui import hf_corpus

SPLITS: tuple[str, ...] = ("train", "test")


class CorpusClosed(Exception):
    """The Hub datasets-server is unreachable — corpus surface is closed."""


@dataclass
class SlimRow:
    filename: str
    split: str
    index: int
    doc_class: Optional[str] = None
    doc_subclass: Optional[str] = None
    sha256: Optional[str] = None
    chars: Optional[int] = None


def _meta(row: dict[str, Any], key: str) -> Any:
    meta = row.get("metadata")
    if isinstance(meta, dict):
        return meta.get(key)
    return None


def _extract_meta(row: dict[str, Any], split: str, index: int,
                  gt_row: Optional[dict[str, Any]] = None) -> SlimRow:
    gt = gt_row or {}
    return SlimRow(
        filename=str(row.get("filename") or f"row-{index}"),
        split=split,
        index=index,
        # Class/subclass/sha live on the GROUND-TRUTH config; the default
        # config metadata only carries provenance.
        doc_class=gt.get("expected") or _meta(row, "doc_class"),
        doc_subclass=gt.get("expected_subclass") or _meta(row, "subclass"),
        sha256=gt.get("content_sha256") or _meta(row, "content_sha256"),
        chars=len(row.get("doc_text") or ""),
    )


class CorpusClient:
    """Paged access to the mailroom-dataset Hub dataset (both configs)."""

    def __init__(self, page_size: int = 100, max_rows: Optional[int] = None,
                 page_sleep: float = 1.0) -> None:
        # datasets-server rejects length > 100 (HTTP 422) — clamp hard.
        self.page_size = min(page_size or 100, 100)
        # 1s inter-page pacing: the Hub budget (even authenticated) throttles
        # back-to-back /rows calls; the full-catalog build is one-time per
        # session and windowed listing never pays for it.
        self.page_sleep = page_sleep
        self.max_rows = max_rows
        self._catalog: Optional[list[SlimRow]] = None
        self._row_lru: dict[str, dict[str, Any]] = {}
        self._gt_lru: dict[str, dict[str, Any]] = {}
        self._lru_cap = 200

    # -- windowed browsing (instant: 1 request per config per page) ----------

    def window(self, split: str, start: int = 0, length: int = 25,
               include_gt: bool = True) -> list[SlimRow]:
        """One slim page at row index ``start`` of ``split``. Two requests
        (default + GT configs); used by ``corpus ls`` so listing never pays
        for the full-corpus catalog build."""
        try:
            page = hf_corpus.fetch_rows(
                config=hf_corpus.DEFAULT_CONFIG, split=split,
                page_size=length, max_rows=length, offset=start)
            if include_gt:
                gt_page = hf_corpus.fetch_rows(
                    config=hf_corpus.GT_CONFIG, split=split,
                    page_size=length, max_rows=length, offset=start)
                gt_by_file = {str(r.get("filename")): r for r in gt_page}
            else:
                gt_by_file = {}
            return [
                _extract_meta(r, split, start + i,
                              gt_by_file.get(str(r.get("filename"))))
                for i, r in enumerate(page)
            ]
        except Exception as exc:  # noqa: BLE001 — any Hub failure = closed
            raise CorpusClosed(str(exc)) from exc

    # -- catalog ----------------------------------------------------------

    def catalog(self, force: bool = False) -> list[SlimRow]:
        """Slim rows across both splits. Built by paging the default config."""
        if self._catalog is not None and not force:
            return self._catalog
        rows: list[SlimRow] = []
        try:
            for split in SPLITS:
                page = hf_corpus.fetch_rows(
                    config=hf_corpus.DEFAULT_CONFIG,
                    split=split,
                    page_size=self.page_size,
                    max_rows=self.max_rows,
                    page_sleep=self.page_sleep,
                )
                gt_page = hf_corpus.fetch_rows(
                    config=hf_corpus.GT_CONFIG,
                    split=split,
                    page_size=self.page_size,
                    max_rows=self.max_rows,
                    page_sleep=self.page_sleep,
                )
                gt_by_file = {str(r.get("filename")): r for r in gt_page}
                rows.extend(
                    _extract_meta(r, split, i, gt_by_file.get(str(r.get("filename"))))
                    for i, r in enumerate(page)
                )
        except Exception as exc:  # noqa: BLE001 — any Hub failure = closed
            raise CorpusClosed(str(exc)) from exc
        self._catalog = rows
        return rows

    def _refresh(self, force: bool) -> list[SlimRow]:
        if force:
            self._catalog = None
        return self.catalog(force=force)

    def split_counts(self) -> dict[str, int]:
        rows = self.catalog()
        out = {split: 0 for split in SPLITS}
        for r in rows:
            out[r.split] = out.get(r.split, 0) + 1
        return out

    def class_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.catalog():
            key = r.doc_class or "unknown"
            out[key] = out.get(key, 0) + 1
        return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))

    # -- lookup -----------------------------------------------------------

    def find(self, filename: str, split: Optional[str] = None) -> Optional[SlimRow]:
        for r in self.catalog():
            if r.filename == filename and (split is None or r.split == split):
                return r
        return None

    def search(self, term: str, split: Optional[str] = None,
               limit: int = 20) -> list[SlimRow]:
        """Match against filename, class, subclass — slim catalog only."""
        needle = re.escape(term.lower())
        pat = re.compile(needle)
        hits: list[SlimRow] = []
        for r in self.catalog():
            if split is not None and r.split != split:
                continue
            hay = " ".join(
                str(x) for x in (r.filename, r.doc_class, r.doc_subclass) if x
            ).lower()
            if pat.search(hay):
                hits.append(r)
                if len(hits) >= limit:
                    break
        return hits

    # -- full rows --------------------------------------------------------

    def _lru_get(self, lru: dict[str, dict[str, Any]], key: str) -> Optional[dict[str, Any]]:
        val = lru.pop(key, None)
        if val is not None:
            lru[key] = val  # refresh recency
        return val

    def _lru_put(self, lru: dict[str, dict[str, Any]], key: str,
                 val: dict[str, Any]) -> None:
        lru.pop(key, None)
        lru[key] = val
        while len(lru) > self._lru_cap:
            lru.pop(next(iter(lru)), None)

    def row(self, filename: str, split: Optional[str] = None) -> Optional[dict[str, Any]]:
        """Full default-config row (incl. doc_text) for one filename.

        The datasets-server rows API cannot filter server-side (the /filter
        endpoint is broken upstream), so a miss walks the splits page by page
        and exits at the match.
        """
        if split is None:
            found = self.find(filename)
            if found is None:
                return None
            split = found.split
        cached = self._lru_get(self._row_lru, f"{split}:{filename}")
        if cached is not None:
            return cached
        try:
            for start in range(0, self.max_rows or 1 << 30, self.page_size):
                page = hf_corpus.fetch_rows(
                    config=hf_corpus.DEFAULT_CONFIG,
                    split=split,
                    page_size=self.page_size,
                    max_rows=self.page_size,
                    offset=start,
                )
                for i, r in enumerate(page):
                    if r.get("filename") == filename:
                        self._lru_put(self._row_lru, f"{split}:{filename}", r)
                        return r
                if len(page) < self.page_size:
                    break
        except Exception as exc:  # noqa: BLE001
            raise CorpusClosed(str(exc)) from exc
        return None

    def gt_row(self, filename: str, split: Optional[str] = None) -> Optional[dict[str, Any]]:
        """Ground-truth config row for one filename (60-key GT columns)."""
        if split is None:
            found = self.find(filename)
            if found is None:
                return None
            split = found.split
        cached = self._lru_get(self._gt_lru, f"{split}:{filename}")
        if cached is not None:
            return cached
        try:
            for start in range(0, self.max_rows or 1 << 30, self.page_size):
                page = hf_corpus.fetch_rows(
                    config=hf_corpus.GT_CONFIG,
                    split=split,
                    page_size=self.page_size,
                    max_rows=self.page_size,
                    offset=start,
                )
                for i, r in enumerate(page):
                    if r.get("filename") == filename:
                        self._lru_put(self._gt_lru, f"{split}:{filename}", r)
                        return r
                if len(page) < self.page_size:
                    break
        except Exception as exc:  # noqa: BLE001
            raise CorpusClosed(str(exc)) from exc
        return None