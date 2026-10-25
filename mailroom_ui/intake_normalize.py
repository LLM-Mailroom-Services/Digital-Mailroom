"""Deterministic intake normalize — mirror of llm-mailroom ``agents.intake``.

The live clerk lives in the pipeline (span ``normalize-intake``). This module
is the documented mirror so The-Mailroom tests and the eval harness can
exercise the same whitespace/hyphen/NBSP rules without importing the sibling
repo. Keep byte-compatible with ``deterministic_normalize`` / ``looks_messy``.
"""

from __future__ import annotations

import re
import unicodedata

_ZW = dict.fromkeys(map(ord, "\u200b\u200c\u200d\ufeff\u2060"), None)
_MULTI_BLANK = re.compile(r"\n[ \t]*\n(?:[ \t]*\n)+")
_MULTI_SPACE = re.compile(r"[^\S\n]{2,}")
_HYPHEN_WRAP = re.compile(r"(?<=[A-Za-z])-\n(?=[A-Za-z])")
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def deterministic_normalize(text: str) -> tuple[str, dict]:
    raw_chars = len(text or "")
    if not text:
        return "", {"raw_chars": 0, "cleaned_chars": 0, "collapsed_blank_runs": 0,
                    "hyphen_unwraps": 0, "changed": False}
    original = text
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\u2028", "\n").replace("\u2029", "\n")
    text = text.translate(_ZW)
    text = _CTRL.sub(" ", text)
    hyphen_unwraps = len(_HYPHEN_WRAP.findall(text))
    text = _HYPHEN_WRAP.sub("", text)
    collapsed_blank = len(_MULTI_BLANK.findall(text))
    text = _MULTI_BLANK.sub("\n\n", text)
    lines = []
    for line in text.split("\n"):
        stripped = line.rstrip()
        if stripped.lstrip().startswith("|") and stripped.rstrip().endswith("|"):
            lines.append(stripped)
        else:
            lines.append(_MULTI_SPACE.sub(" ", stripped).strip() if stripped else "")
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    cleaned = "\n".join(lines)
    return cleaned, {
        "raw_chars": raw_chars,
        "cleaned_chars": len(cleaned),
        "collapsed_blank_runs": collapsed_blank,
        "hyphen_unwraps": hyphen_unwraps,
        "changed": cleaned != original,
    }


def looks_messy(text: str, stats: dict | None = None) -> bool:
    if not text or not text.strip():
        return False
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if not lines:
        return False
    short = sum(1 for ln in lines if len(ln.split()) <= 2)
    avg_len = sum(len(ln) for ln in lines) / len(lines)
    ctrl_ratio = sum(
        1 for ch in text
        if ch == "\ufffd" or (unicodedata.category(ch) == "Cc" and ch not in "\n\t")
    ) / max(len(text), 1)
    hyphen_left = text.count("-\n")
    if stats and stats.get("collapsed_blank_runs", 0) >= 8:
        return True
    if ctrl_ratio > 0.01:
        return True
    if len(lines) >= 20 and short / len(lines) > 0.55 and avg_len < 28:
        return True
    if hyphen_left >= 6:
        return True
    return False
