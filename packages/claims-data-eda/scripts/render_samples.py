#!/usr/bin/env python3
"""Render real corpus documents (insurance_claim) as PDF samples.

Reads rows from a mailroom-dataset ground-truth JSONL (the publish surface of
this package's pipeline dump; see AGENTS.md "First-Time Setup"), deterministically
samples insurance_claim documents across the health strata this corpus produces
(carrier / inpatient / outpatient / pde), and renders each document's verbatim
doc_text into a faithful A4 PDF under docs/examples/ with a machine-readable
manifest (provenance + sha256), plus a human-referenced README.

The PDF writer is an intentional zero-dependency implementation (Courier
built-in font, strict WinAnsi encoding) so the samples stay byte-deterministic
on every rebuild -- same input rows, same bytes.

Usage:
    python scripts/render_samples.py --input /tmp/ground_truth_hardened.jsonl
    python scripts/render_samples.py --input ... --n-per-stratum 2 --seed 42
    python scripts/render_samples.py --input ... --record-ids carrier:887013387879564

Output (written under the repo's docs/):
    docs/examples/sample_<id>.pdf   one PDF per sampled document
    docs/examples/manifest.json     provenance + sha256 per sample
    docs/examples/README.md         what these are and how to regenerate
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

HEALTH_STRATA = ("carrier", "inpatient", "outpatient", "pde")

PAGE_W = 595.28   # A4 portrait (pt)
PAGE_H = 841.89
MARGIN = 53.0     # 0.75in
FONT = "Courier"
FONT_SIZE = 11.0
LEADING = 13.2
CH_WIDTH = FONT_SIZE * 0.6          # Courier advance = 0.6 em
CHARS_PER_LINE = int((PAGE_W - 2 * MARGIN) // CH_WIDTH)
LINES_PER_PAGE = int((PAGE_H - 2 * MARGIN) // LEADING)


def safe_latin1(text: str) -> str:
    """Strict WinAnsi-safe text; non-encodable chars become '?' (corpus text is ASCII)."""
    try:
        text.encode("cp1252")
        return text
    except UnicodeEncodeError:
        return "".join(c if ord(c) < 256 else "?" for c in text)


def layout_pages(text: str, header: str) -> list[list[str]]:
    """Chunk text into pages of wrapped lines; returns one list of lines per page."""
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        while len(raw) > CHARS_PER_LINE:
            lines.append(raw[:CHARS_PER_LINE])
            raw = raw[CHARS_PER_LINE:]
        lines.append(raw)
    pages: list[list[str]] = []
    body_per_page = LINES_PER_PAGE - 1
    for i in range(0, len(lines), body_per_page):
        pages.append(lines[i : i + body_per_page])
    if not pages:
        pages = [[]]
    pages[0] = [header, *pages[0]]
    return pages


def _esc_pdf_text(s: str) -> str:
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def text_to_pdf(text: str, header: str) -> bytes:
    """Byte-deterministic A4 PDF of `text` in Courier (no external deps)."""
    pages = layout_pages(text, header)
    objects: list[bytes] = []      # index i -> object (i+1)
    objects.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    page_ids = [3 + 3 * i for i in range(len(pages))]
    kid_str = " ".join(f"{i} 0 R" for i in page_ids)
    objects.append(f"2 0 obj\n<< /Type /Pages /Kids [{kid_str}] /Count {len(pages)} >>\nendobj\n".encode())
    for idx, p in enumerate(pages):
        page_id = page_ids[idx]
        content_id = page_id + 1
        font_id = page_id + 2
        stream = _content_stream(p)
        objects.append(
            (
                f"{page_id} 0 obj\n"
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                f"/Resources << /Font << /F1 {font_id} 0 R >> >> "
                f"/Contents {content_id} 0 R >>\nendobj\n"
            ).encode()
        )
        objects.append(f"{content_id} 0 obj\n<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"endstream\nendobj\n")
        objects.append(
            f"{font_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n".encode()
        )
    head = b"%PDF-1.4\n"
    offsets = []
    cursor = len(head)
    for obj in objects:
        offsets.append(cursor)
        cursor += len(obj)
    xref_at = cursor
    body = b"".join(objects)
    xref = bytearray()
    xref += f"xref\n0 {len(objects) + 1}\n".encode()
    xref += b"0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n".encode()
    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return head + body + bytes(xref) + trailer


def _content_stream(lines: list[str]) -> bytes:
    parts = ["BT", f"/F1 {FONT_SIZE} Tf", "1 0 0 1 0 0 Tm", "0 G"]
    y = PAGE_H - MARGIN - FONT_SIZE
    for line in lines:
        safe = _esc_pdf_text(safe_latin1(line)[:CHARS_PER_LINE])
        parts.append(f"1 0 0 1 {MARGIN} {y} Tm")
        parts.append(f"({safe}) Tj")
        y -= LEADING
    parts.append("ET")
    return "\n".join(parts).encode("latin-1")


def pick_samples(rows: list[dict], n_per_stratum: int, seed: int, strata: tuple[str, ...]) -> list[dict]:
    rng = random.Random(seed)
    picked: list[dict] = []
    for sub in strata:
        pool = [r for r in rows if r.get("expected_subclass") == sub]
        if not pool:
            continue
        picked.extend(rng.sample(pool, min(n_per_stratum, len(pool))))
    return picked


def write_sample(row: dict, examples_dir: Path, source_file: str) -> dict:
    rid = (row.get("filename") or row.get("document_id") or "row").replace(".txt", "")
    sub = row.get("expected_subclass") or "unknown"
    safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", rid)
    pdf_name = f"sample_{safe_id}.pdf"
    header = (
        f"mailroom-dataset | insurance_claim | {sub} | {rid} | "
        f"rev {row.get('source_revision', '?')}"
    )
    pdf = text_to_pdf(row.get("doc_text") or "(empty document)", header)
    out = examples_dir / pdf_name
    out.write_bytes(pdf)
    return {
        "pdf": pdf_name,
        "record_id": rid,
        "subclass": sub,
        "claim_number": row.get("claim_number"),
        "document_id": row.get("document_id"),
        "source_revision": row.get("source_revision"),
        "split": row.get("split"),
        "doc_text_chars": len(row.get("doc_text") or ""),
        "pdf_sha256": hashlib.sha256(pdf).hexdigest(),
        "pdf_bytes": len(pdf),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--input", required=True,
                   help="mailroom-dataset ground-truth JSONL (download: https://huggingface.co/datasets/"
                        "Lucius-Morningstar/mailroom-dataset/resolve/main/ground_truth_hardened.jsonl)")
    p.add_argument("--n-per-stratum", type=int, default=2)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--strata", default=",".join(HEALTH_STRATA))
    p.add_argument("--record-ids", default=None,
                   help="exact filenames to render instead of stratified sampling")
    args = p.parse_args(argv)

    strata = tuple(s.strip() for s in args.strata.split(",") if s.strip())
    examples_dir = REPO_ROOT / "docs" / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("expected") == "insurance_claim" and r.get("doc_text"):
                rows.append(r)
    if not rows:
        sys.exit(f"no insurance_claim rows with doc_text in {args.input}")
    print(f"insurance_claim rows available: {len(rows)}")

    if args.record_ids:
        wanted = set(args.record_ids.split(","))
        picked = [r for r in rows if (r.get("filename") or "").replace(".txt", "") in wanted]
        if len(picked) != len(wanted):
            sys.exit(f"record-ids not found: {sorted(wanted - {r.get('filename','').replace('.txt','') for r in picked})}")
    else:
        picked = pick_samples(rows, args.n_per_stratum, args.seed, strata)
        print("sampled: " + ", ".join(r.get("expected_subclass", "?") for r in picked))

    samples = [write_sample(r, examples_dir, args.input) for r in picked]
    manifest = {
        "title": "Real insurance-claim corpus documents rendered as PDF samples",
        "dataset": "Lucius-Morningstar/mailroom-dataset",
        "source_file": "ground_truth_hardened.jsonl",
        "sample_count": len(samples),
        "strata": sorted({s["subclass"] for s in samples}),
        "renderer": "scripts/render_samples.py",
        "seed": args.seed,
        "note": "doc_text is the verbatim corpus document rendered by this package's "
                "render_eob.py; samples regenerate byte-identically from the same rows.",
        "samples": samples,
    }
    (examples_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"wrote {len(samples)} PDFs + manifest.json to {examples_dir.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())