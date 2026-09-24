#!/usr/bin/env python3
"""Generate requirements/*.txt from pyproject.toml extras (DMR-078).

Source of truth is pyproject.toml. Re-run after changing dependencies::

    python3 scripts/sync_requirements.py
    python3 scripts/sync_requirements.py --check   # exit 1 on drift
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
REQ_DIR = ROOT / "requirements"

HEADER = """\
# AUTO-GENERATED from pyproject.toml by scripts/sync_requirements.py — do not
# hand-edit. Source of truth: [project] / [project.optional-dependencies].
# Refresh: python3 scripts/sync_requirements.py
"""

# (filename, extras to append after base, include_base_via_r)
# extras=() → base only. ``all`` expands every real extra.
EXPORTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("base.txt", ()),
    ("dev.txt", ("dev",)),
    ("pipeline.txt", ("pipeline",)),
    ("deploy.txt", ("deploy",)),
    ("observability.txt", ("observability",)),
    ("hf.txt", ("hf",)),
    ("notebooks.txt", ("notebooks",)),
    # Modal job worker image (deploy/modal_job.py::uv_pip_install) — no Modal
    # SDK / pytest / jupyter on the worker.
    ("modal-job.txt", ("pipeline", "hf", "observability")),
    ("all.txt", ("dev", "deploy", "hf", "observability", "notebooks", "pipeline")),
)


def _parse_bracket_list(text: str, start_pat: str) -> list[str]:
    """Parse a TOML ``name = [ ... ]`` list, ignoring ``]`` inside comments."""
    m = re.search(start_pat, text, flags=re.M)
    if not m:
        raise RuntimeError(f"pyproject.toml: list not found for {start_pat!r}")
    i = m.end()
    depth = 1
    buf: list[str] = []
    while i < len(text) and depth:
        ch = text[i]
        if ch == "#":
            # Skip to end of line (comments may contain ``]`` / ``[``).
            nl = text.find("\n", i)
            if nl < 0:
                break
            i = nl + 1
            continue
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                break
        elif ch == '"':
            j = i + 1
            while j < len(text) and text[j] != '"':
                if text[j] == "\\":
                    j += 2
                    continue
                j += 1
            buf.append(text[i + 1 : j])
            i = j + 1
            continue
        i += 1
    return [s.strip() for s in buf if s.strip()]


def _parse_dep_lists(text: str) -> dict[str, list[str]]:
    """Minimal TOML list extractor for [project] dependencies / extras."""
    out: dict[str, list[str]] = {
        "base": _parse_bracket_list(text, r"^dependencies\s*=\s*\[")
    }

    opt = re.search(
        r"^\[project\.optional-dependencies\]\s*\n(.*?)(?=\n\[|\Z)",
        text,
        flags=re.M | re.S,
    )
    if not opt:
        raise RuntimeError("pyproject.toml: [project.optional-dependencies] missing")
    body = opt.group(1)
    for name in re.findall(r"^([a-zA-Z0-9_-]+)\s*=\s*\[", body, flags=re.M):
        deps = _parse_bracket_list(body, rf"^{re.escape(name)}\s*=\s*\[")
        deps = [d for d in deps if not d.startswith("mailroom-sandbox[")]
        out[name] = deps
    return out


def _dedupe(deps: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for dep in deps:
        key = dep.split(";")[0].strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(dep)
    return out


def _render(*, extras_deps: list[str], include_base: bool) -> str:
    lines = [HEADER.rstrip(), ""]
    if include_base:
        lines.append("-r base.txt")
        lines.append("")
    for dep in _dedupe(extras_deps):
        lines.append(dep)
    lines.append("")
    return "\n".join(lines)


def sync(*, check: bool = False) -> int:
    lists = _parse_dep_lists(PYPROJECT.read_text(encoding="utf-8"))
    REQ_DIR.mkdir(parents=True, exist_ok=True)
    drifted: list[str] = []

    for filename, extras in EXPORTS:
        if filename == "base.txt":
            body = _render(extras_deps=lists["base"], include_base=False)
        else:
            extras_deps: list[str] = []
            for extra in extras:
                extras_deps.extend(lists.get(extra, []))
            body = _render(extras_deps=extras_deps, include_base=True)

        path = REQ_DIR / filename
        if check:
            if not path.is_file():
                drifted.append(f"missing {path}")
            elif path.read_text(encoding="utf-8") != body:
                drifted.append(f"drift {path.relative_to(ROOT)}")
            else:
                print(f"ok {path.relative_to(ROOT)}")
        else:
            path.write_text(body, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")

    root_req = ROOT / "requirements.txt"
    shim = (
        HEADER
        + "\n# Convenience shim — offline-dev surface (base + [dev]).\n"
        + "-r requirements/dev.txt\n"
    )
    if check:
        if not root_req.is_file() or root_req.read_text(encoding="utf-8") != shim:
            drifted.append("drift requirements.txt")
        else:
            print("ok requirements.txt")
    else:
        root_req.write_text(shim, encoding="utf-8")
        print("wrote requirements.txt")

    if check and drifted:
        for line in drifted:
            print(f"ERROR: {line}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="fail if requirements/ drifts from pyproject.toml",
    )
    return sync(check=bool(ap.parse_args(argv).check))


if __name__ == "__main__":
    raise SystemExit(main())
