#!/usr/bin/env python3
"""Semver release workflow for The-Mailroom.

Performs the mechanical release steps and prints the exact commit/tag
commands — the release itself is always a human `git commit` + `git tag`.

    python scripts/release.py --bump minor --note "M2: pixel engine + web floor"
    python scripts/release.py --check
    python scripts/release.py --help

Rules (see AGENTS.md -> "Release process"):
  * version lives in pyproject.toml; the tag must match the CHANGELOG header.
  * refuses to run --bump on a dirty working tree.
  * --check validates repo state without changing anything.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG = ROOT / "CHANGELOG.md"

VERSION_RE = re.compile(r'^version\s*=\s*"([0-9]+)\.([0-9]+)\.([0-9]+)"', re.M)


def fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def run_git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def current_version(root: Path = ROOT) -> tuple[int, int, int]:
    m = VERSION_RE.search((root / "pyproject.toml").read_text())
    if not m:
        fail("could not find version in pyproject.toml")
    return tuple(int(g) for g in m.groups())  # type: ignore[return-value]


def bump_version(version: tuple[int, int, int], bump: str) -> tuple[int, int, int]:
    major, minor, patch = version
    if bump == "major":
        return major + 1, 0, 0
    if bump == "minor":
        return major, minor + 1, 0
    return major, minor, patch + 1


def parse_changelog(root: Path = ROOT) -> tuple[str, list[str]]:
    """Return (unreleased_bullets, released_headers)."""
    text = (root / "CHANGELOG.md").read_text()
    m = re.search(r"^## \[Unreleased\]\s*\n(.*?)(?=^## )", text, re.M | re.S)
    if not m:
        fail("CHANGELOG.md has no '## [Unreleased]' section")
    bullets = [ln for ln in m.group(1).splitlines() if ln.strip()]
    headers = re.findall(r"^## \[([0-9]+\.[0-9]+\.[0-9]+)\]", text, re.M)
    return bullets, headers


def write_version(version: tuple[int, int, int], root: Path = ROOT) -> None:
    path = root / "pyproject.toml"
    text = path.read_text()
    text = VERSION_RE.sub(f'version = "{version[0]}.{version[1]}.{version[2]}"', text, count=1)
    path.write_text(text)


# Every other place the app version is spelled out. They drifted by up to
# three releases (FastAPI 0.3.0, Observatory ?v=0.3.13 cache-bust, README
# badge, ui/package.json) because only pyproject.toml was bumped.
_VERSION_SITES: tuple[tuple[str, str, str], ...] = (
    ("web/index.html", r"\?v=[0-9][0-9.]*", "?v={v}"),
    ("hosted/index.html", r"\?v=[0-9][0-9.]*", "?v={v}"),
    ("terminal/index.html", r"\?v=[0-9][0-9.]*", "?v={v}"),
    ("README.md", r"badge/version-[0-9.]+-blue", "badge/version-{v}-blue"),
    ("README.md", r"badge/release-v[0-9.]+-blue\)\]\(https://github.com/Exios66/The-Mailroom/releases/tag/v[0-9.]+",
     "badge/release-v{v}-blue)](https://github.com/Exios66/The-Mailroom/releases/tag/v{v}"),
    ("ui/package.json", r'"version": "[0-9.]+"', '"version": "{v}"'),
)


def sync_version_sites(version: tuple[int, int, int], root: Path = ROOT) -> list[str]:
    """Rewrite every secondary version string; return the files touched."""
    ver = f"{version[0]}.{version[1]}.{version[2]}"
    touched: list[str] = []
    for rel, pattern, repl in _VERSION_SITES:
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text()
        new = re.sub(pattern, repl.format(v=ver), text)
        if new != text:
            path.write_text(new)
            if rel not in touched:
                touched.append(rel)
    return touched


def version_site_drift(root: Path = ROOT) -> list[str]:
    """Secondary version strings that disagree with pyproject.toml."""
    ver = current_version(root)
    ver_s = f"{ver[0]}.{ver[1]}.{ver[2]}"
    drift: list[str] = []
    for rel, pattern, _repl in _VERSION_SITES:
        path = root / rel
        if not path.exists():
            continue
        for hit in re.findall(pattern, path.read_text()):
            if ver_s not in hit:
                drift.append(f"{rel}: {hit}")
    return drift


def release_changelog(version: tuple[int, int, int], note: str, root: Path = ROOT) -> None:
    """Move the Unreleased body under ``## [X.Y.Z] - date``; leave Unreleased empty.

    The previous implementation inserted the new header *above* the Unreleased
    bullets without removing them, so every cut duplicated the section.
    """
    path = root / "CHANGELOG.md"
    text = path.read_text()
    m = re.search(r"^## \[Unreleased\]\s*\n(.*?)(?=^## )", text, re.M | re.S)
    if not m:
        fail("CHANGELOG.md has no '## [Unreleased]' section")
    unreleased_body = m.group(1).strip()
    ver = f"{version[0]}.{version[1]}.{version[2]}"
    today = _dt.date.today().isoformat()
    body = unreleased_body
    if body and not body.startswith("###") and not body.startswith(">"):
        body = f"### Added\n\n{body}"
    note_line = f"> {note}\n\n" if note else ""
    if body:
        section = f"## [{ver}] - {today}\n\n{note_line}{body}\n"
    else:
        section = f"## [{ver}] - {today}\n\n{note_line}".rstrip() + "\n"
    replacement = f"## [Unreleased]\n\n{section}\n"
    new_text = text[: m.start()] + replacement + text[m.end() :]
    if new_text == text:
        fail("failed to rewrite CHANGELOG.md")
    path.write_text(new_text)


def check_state() -> None:
    print("checking repo state...")
    if not CHANGELOG.exists():
        fail("CHANGELOG.md missing")
    bullets, headers = parse_changelog()
    ver = current_version()
    ver_s = f"{ver[0]}.{ver[1]}.{ver[2]}"
    if bullets and headers and ver_s not in headers:
        print(f"warn: pyproject version {ver_s} has no CHANGELOG header")
    if headers and ver_s in headers and bullets:
        print(f"warn: Unreleased entries remain after {ver_s} was released")
    dupes = sorted({h for h in headers if headers.count(h) > 1})
    if dupes:
        fail(f"CHANGELOG.md repeats version headers: {', '.join(dupes)}")
    drift = version_site_drift()
    if drift:
        fail("version strings disagree with pyproject.toml:\n  " + "\n  ".join(drift))
    print("running tests...")
    subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"], cwd=ROOT, check=True)
    print(f"ok: version {ver_s} · changelog entries: {len(bullets)} unreleased")
    print("tip: after a pushed major/minor release, run wiki/sync-wiki.sh")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bump", choices=["patch", "minor", "major"], help="bump the version")
    ap.add_argument("--note", default="", help="one-line summary for the tag/changelog")
    ap.add_argument("--check", action="store_true", help="validate state, change nothing")
    args = ap.parse_args()

    if args.check:
        check_state()
        return
    if not args.bump:
        ap.error("nothing to do: pass --bump or --check")

    if run_git("status", "--porcelain"):
        fail("working tree is dirty — commit or stash first")

    bullets, _ = parse_changelog()
    if not bullets:
        fail("CHANGELOG.md has no Unreleased entries to release")

    version = bump_version(current_version(), args.bump)
    ver_s = f"{version[0]}.{version[1]}.{version[2]}"

    print("running tests...")
    subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"], cwd=ROOT, check=True)

    write_version(version)
    touched = sync_version_sites(version)
    release_changelog(version, args.note)
    print(f"bumped to {ver_s}; CHANGELOG [Unreleased] moved to [{ver_s}]")
    if touched:
        print(f"synced version strings in: {', '.join(touched)}")

    print("\nnext steps:")
    print(f"  git add pyproject.toml CHANGELOG.md README.md ui/package.json "
          f"web/index.html hosted/index.html terminal/index.html wiki/ docs/")
    print(f"  git commit -m \"{args.note or f'Release {ver_s}'}\"")
    print(f"  git tag -a v{ver_s} -m \"{ver_s} — {args.note or 'release'}\"")
    print("  git push && git push --tags")
    print("  wiki/sync-wiki.sh   # after pushed major/minor releases")


if __name__ == "__main__":
    main()
