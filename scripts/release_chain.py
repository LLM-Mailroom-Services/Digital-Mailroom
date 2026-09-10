#!/usr/bin/env python3
"""Release-chain governor for the mailroom-hub core repo (HUB-024).

Keeps the hub's changelog <-> semver tag <-> pyproject version chain honest.
The hub versions the monorepo as a whole; package-level releases remain the
standalone repos' concern (HUB-005 release train).

Chain law (severity contract mirrors board_state.py):

- structural errors (exit 1):
  * CHANGELOG.md missing/unparseable, or no ``[Unreleased]`` section
  * a ``vX.Y.Z`` tag exists WITHOUT a matching changelog section
    (released outside the discipline)
  * duplicate or non-semver version sections; sections not in strictly
    descending order
  * hub ``pyproject.toml`` version behind the newest tag (release cut
    without a version bump)
- hygiene drift (warned, not fatal):
  * changelog section stamped but not yet tagged (natural prep state)
  * annotated tag message outside the ``mailroom-hub vX.Y.Z`` convention
  * lightweight (non-annotated) version tag
  * hub version ahead of the newest tag with an empty ``[Unreleased]``

Subcommands:

    status [--json]              chain snapshot (tags, sections, pyproject)
    check                        verify the chain; exit 1 on structural error
    cut VERSION [--apply] [--tag] [--allow-dirty] [--allow-empty]
                                 stamp ``[Unreleased]`` -> ``[VERSION] - DATE``,
                                 bump the hub pyproject version (dry-run plan
                                 by default; ``--tag`` adds the annotated tag;
                                 never commits, never pushes — the caller
                                 commits with its HUB-0NN reference)

Stdlib only; network-free (tag/release inspection is local git + changelog).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"
TAG_PREFIX = "v"
TAG_MESSAGE_PREFIX = "mailroom-hub"

SECTION_RE = re.compile(r"^## \[(?P<name>[^\]]+)\](?P<stamp> - \d{4}-\d{2}-\d{2})?\s*$")
VERSION_RE = re.compile(r"^(?P<maj>\d+)\.(?P<min>\d+)\.(?P<pat>\d+)(?:-[0-9A-Za-z.-]+)?$")
PYPROJECT_VERSION_RE = re.compile(r'^version\s*=\s*"(?P<version>[^"]+)"\s*$', re.MULTILINE)


class ChainError(Exception):
    """Structural chain violation (exit 1)."""


def run_git(*args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise ChainError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def parse_semver(version: str) -> tuple[int, int, int] | None:
    match = VERSION_RE.match(version)
    if not match:
        return None
    return (int(match["maj"]), int(match["min"]), int(match["pat"]))


def hub_pyproject_version() -> str:
    match = PYPROJECT_VERSION_RE.search(PYPROJECT.read_text(encoding="utf-8"))
    if not match:
        raise ChainError(f"no version = line found in {PYPROJECT.relative_to(REPO_ROOT)}")
    return match["version"]


def list_version_tags() -> list[dict]:
    """All vX.Y.Z tags with type + subject, newest (semver-desc) first."""
    out = run_git(
        "tag",
        "--list",
        f"{TAG_PREFIX}*",
        "--format=%(refname:short)%09%(objecttype)%09%(contents:subject)",
    )
    tags = []
    for line in out.splitlines():
        if not line.strip():
            continue
        name, objtype, subject = (line.split("\t", 2) + ["", ""])[:3]
        version = name[len(TAG_PREFIX):] if name.startswith(TAG_PREFIX) else name
        if parse_semver(version) is None:
            continue  # not a version tag; ignore (other tag namespaces allowed)
        tags.append({"tag": name, "version": version, "type": objtype, "subject": subject})
    tags.sort(key=lambda t: parse_semver(t["version"]) or (0, 0, 0), reverse=True)
    return tags


def parse_changelog() -> list[dict]:
    """Ordered section list: [{name, stamp, line_no, is_unreleased}]."""
    sections = []
    for line_no, line in enumerate(
        CHANGELOG.read_text(encoding="utf-8").splitlines(), start=1
    ):
        match = SECTION_RE.match(line)
        if match:
            sections.append(
                {
                    "name": match["name"],
                    "stamp": match["stamp"].lstrip(" -") if match["stamp"] else "",
                    "line_no": line_no,
                    "is_unreleased": match["name"].lower() == "unreleased",
                }
            )
    if not sections:
        raise ChainError(f"no ## [section] headers parse in {CHANGELOG.relative_to(REPO_ROOT)}")
    if not sections[0]["is_unreleased"]:
        raise ChainError("CHANGELOG.md must open with a ## [Unreleased] section")
    return sections


def chain_state() -> dict:
    pyproject_version = hub_pyproject_version()
    tags = list_version_tags()
    sections = parse_changelog()
    version_sections = [s for s in sections if not s["is_unreleased"]]

    section_versions = [s["name"] for s in version_sections]
    tagged_versions = {t["version"] for t in tags}

    unreleased = sections[0]
    unreleased_body = _section_body(unreleased, sections)

    return {
        "pyproject_version": pyproject_version,
        "tags": tags,
        "newest_tag": tags[0]["tag"] if tags else None,
        "newest_tag_version": tags[0]["version"] if tags else None,
        "sections": [s["name"] for s in sections],
        "version_sections": section_versions,
        "unreleased_empty": not unreleased_body.strip(),
        "unreleased_line": unreleased["line_no"],
    }


def _section_body(section: dict, sections: list[dict]) -> str:
    lines = CHANGELOG.read_text(encoding="utf-8").splitlines()
    start = section["line_no"]  # 1-indexed -> slice start after the header
    end = sections[sections.index(section) + 1]["line_no"] - 1 if sections.index(section) + 1 < len(sections) else len(lines)
    return "\n".join(lines[start:end])


def check_chain(state: dict) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for the live chain."""
    errors: list[str] = []
    warnings: list[str] = []

    tagged_versions = {t["version"] for t in state["tags"]}
    tagged_by_version = {t["version"]: t for t in state["tags"]}

    # tag <-> section parity
    for version in tagged_versions:
        if version not in state["version_sections"]:
            errors.append(
                f"tag {TAG_PREFIX}{version} has no matching CHANGELOG section "
                f"## [{version}] — released outside the discipline"
            )
    for version in state["version_sections"]:
        if parse_semver(version) is None:
            errors.append(f"CHANGELOG section [{version}] is not semver (X.Y.Z)")
            continue
        if version not in tagged_versions:
            warnings.append(
                f"CHANGELOG section [{version}] is stamped but tag {TAG_PREFIX}{version} "
                "not found locally yet (prep state — tag before publishing the release)"
            )

    # duplicates + ordering
    seen: set[str] = set()
    parsed: list[tuple[int, int, int]] = []
    for version in state["version_sections"]:
        if version in seen:
            errors.append(f"duplicate CHANGELOG section [{version}]")
        seen.add(version)
        if sv := parse_semver(version):
            parsed.append(sv)
    if parsed != sorted(parsed, reverse=True):
        errors.append("CHANGELOG version sections are not in strictly descending order")

    # version skew: pyproject must never be behind the newest tag
    if state["newest_tag_version"] is not None:
        pv = parse_semver(state["pyproject_version"])
        nv = parse_semver(state["newest_tag_version"])
        if pv is None:
            errors.append(f"hub pyproject version '{state['pyproject_version']}' is not semver")
        elif pv < nv:
            errors.append(
                f"hub pyproject version {state['pyproject_version']} is behind the newest "
                f"tag {state['newest_tag']} — a release was cut without a version bump"
            )

    # tag hygiene
    for tag in state["tags"]:
        if tag["type"] != "tag":
            warnings.append(f"tag {tag['tag']} is lightweight — hub releases must be annotated")
        elif not tag["subject"].startswith(f"{TAG_MESSAGE_PREFIX} {tag['tag']}"):
            warnings.append(
                f"tag {tag['tag']} message outside the '{TAG_MESSAGE_PREFIX} {tag['tag']}' convention"
            )

    # dev-state hygiene
    if (
        state["pyproject_version"] not in tagged_versions
        and state["unreleased_empty"]
        and not any(
            w.startswith("CHANGELOG section [") and "stamped but tag" in w
            for w in warnings
        )
    ):
        warnings.append(
            f"hub pyproject version {state['pyproject_version']} is ahead of the newest tag "
            "with an empty [Unreleased] — nothing recorded for the in-development work"
        )

    return errors, warnings


def status(state: dict, as_json: bool = False) -> None:
    if as_json:
        print(json.dumps(state, indent=2))
        return
    print(f"hub pyproject version : {state['pyproject_version']}")
    print(f"newest version tag    : {state['newest_tag'] or '(none)'}")
    print(f"version tags          : {len(state['tags'])}")
    for tag in state["tags"]:
        print(f"    {tag['tag']:<14} {tag['type']:<8} {tag['subject']}")
    print(f"changelog sections    : {', '.join(state['sections'])}")
    print(
        "unreleased            : "
        + ("empty" if state["unreleased_empty"] else "content pending release")
    )


def check(state: dict) -> int:
    errors, warnings = check_chain(state)
    for warning in warnings:
        print(f"WARN  {warning}")
    for error in errors:
        print(f"ERROR {error}")
    if errors:
        print(f"\nrelease chain: {len(errors)} structural error(s), {len(warnings)} warning(s)")
        return 1
    print(f"\nrelease chain: OK ({len(warnings)} warning(s))")
    return 0


def _bump_pyproject(version: str) -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    new_text, count = PYPROJECT_VERSION_RE.subn(f'version = "{version}"', text, count=1)
    if count != 1:
        raise ChainError("failed to bump the pyproject version line")
    PYPROJECT.write_text(new_text, encoding="utf-8")


def _stamp_changelog(version: str, today: str) -> None:
    lines = CHANGELOG.read_text(encoding="utf-8").splitlines()
    # The "## [Unreleased]" header may sit below a preamble (title + scope
    # note); locate it and preserve everything above it (a file that starts
    # with the header keeps an empty preamble).
    unreleased_idx = None
    for idx, line in enumerate(lines):
        if SECTION_RE.match(line) and line.rstrip().lower() == "## [unreleased]":
            unreleased_idx = idx
            break
    if unreleased_idx is None:
        raise ChainError("expected a ## [Unreleased] section header in the CHANGELOG")
    preamble = lines[:unreleased_idx]
    # find the end of the Unreleased body (next section header or EOF)
    end = len(lines)
    for idx in range(unreleased_idx + 1, len(lines)):
        if SECTION_RE.match(lines[idx]):
            end = idx
            break
    body = lines[unreleased_idx + 1:end]
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    stamped = [*preamble, "## [Unreleased]", "", f"## [{version}] - {today}", *body, ""]
    CHANGELOG.write_text("\n".join(stamped + lines[end:]) + "\n", encoding="utf-8")


def _relink_footer(new_version: str, previous: str | None) -> None:
    text = CHANGELOG.read_text(encoding="utf-8")
    base = "https://github.com/LLM-Mailroom-Services/Digital-Mailroom"
    old_unreleased = f"[Unreleased]: {base}/compare/{TAG_PREFIX}{previous}...HEAD" if previous else f"[Unreleased]: {base}/compare/{TAG_PREFIX}{new_version}...HEAD"
    new_unreleased = f"[Unreleased]: {base}/compare/{TAG_PREFIX}{new_version}...HEAD"
    links = [new_unreleased]
    if previous:
        links.append(f"[{previous}]: {base}/compare/{TAG_PREFIX}{previous}...{TAG_PREFIX}{new_version}")
    if old_unreleased in text:
        text = text.replace(old_unreleased, "\n".join(links), 1)
    else:
        # footer missing or malformed — rebuild from the first link line
        text = re.sub(
            r"^\[Unreleased\]:.*$",
            "\n".join(links),
            text,
            count=1,
            flags=re.MULTILINE,
        )
    release_link = f"[{new_version}]: {base}/releases/tag/{TAG_PREFIX}{new_version}"
    if f"[{new_version}]:" not in text:
        text = text.rstrip("\n") + f"\n{release_link}\n"
    CHANGELOG.write_text(text, encoding="utf-8")


def cut(version: str, apply: bool, make_tag: bool, allow_dirty: bool, allow_empty: bool) -> int:
    version = version.removeprefix(TAG_PREFIX)
    if parse_semver(version) is None:
        print(f"ERROR '{version}' is not semver (X.Y.Z) — refusing to cut", file=sys.stderr)
        return 1

    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "status", "--porcelain"], capture_output=True, text=True
    )
    if proc.returncode != 0:
        print(f"ERROR git status failed: {proc.stderr.strip()}", file=sys.stderr)
        return 1
    if proc.stdout.strip() and not allow_dirty:
        print(
            "ERROR working tree is not clean — commit or stash first "
            "(or pass --allow-dirty)",
            file=sys.stderr,
        )
        return 1

    state = chain_state()
    if version in state["version_sections"]:
        print(f"ERROR CHANGELOG already has a [{version}] section", file=sys.stderr)
        return 1
    if any(t["version"] == version for t in state["tags"]):
        print(f"ERROR tag {TAG_PREFIX}{version} already exists", file=sys.stderr)
        return 1
    if state["unreleased_empty"] and not allow_empty:
        print(
            "ERROR [Unreleased] is empty — nothing to release (pass --allow-empty to force)",
            file=sys.stderr,
        )
        return 1

    previous = state["newest_tag_version"]
    today = _dt.date.today().isoformat()
    print(f"cut plan — v{version} ({today}):")
    print(f"  1. CHANGELOG: [Unreleased] body -> ## [{version}] - {today} (fresh [Unreleased] on top)")
    print(f"  2. pyproject.toml: version {state['pyproject_version']} -> {version}")
    print(f"  3. footer links: Unreleased-compare -> v{version}; release link [{version}] added")
    if make_tag:
        print(f"  4. annotated tag {TAG_PREFIX}{version} (message: '{TAG_MESSAGE_PREFIX} {TAG_PREFIX}{version}')")
    print("  (commit + push stay with the caller — reference the DMR card)")

    if not apply:
        print("\ndry run — pass --apply to write the changes")
        return 0

    _stamp_changelog(version, today)
    _bump_pyproject(version)
    _relink_footer(version, previous)
    print(f"applied: CHANGELOG stamped, pyproject bumped to {version}")
    if make_tag:
        tag = f"{TAG_PREFIX}{version}"
        run_git("tag", "-a", tag, "-m", f"{TAG_MESSAGE_PREFIX} {tag}")
        print(f"tagged: {tag} (annotated) — push with: git push origin {tag}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="chain snapshot")
    p_status.add_argument("--json", action="store_true", help="machine-readable output")

    sub.add_parser("check", help="verify the chain (exit 1 on structural errors)")

    p_cut = sub.add_parser("cut", help="stamp [Unreleased] into a release section + bump version")
    p_cut.add_argument("version", help="version to cut, e.g. 0.2.0 (v prefix tolerated)")
    p_cut.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")
    p_cut.add_argument("--tag", action="store_true", help="also create the annotated version tag")
    p_cut.add_argument("--allow-dirty", action="store_true", help="permit a dirty working tree")
    p_cut.add_argument("--allow-empty", action="store_true", help="permit an empty [Unreleased]")

    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            status(chain_state(), as_json=args.json)
            return 0
        if args.command == "check":
            return check(chain_state())
        if args.command == "cut":
            return cut(args.version, args.apply, args.tag, args.allow_dirty, args.allow_empty)
    except ChainError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
