#!/usr/bin/env python3
"""Release-notes generator for the mailroom-hub GitHub releases.

Renders the ``.github/RELEASE_TEMPLATE.md`` template into the ``--notes-file``
body for ``gh release create`` for one hub release. The body is compiled from
the freshly-stamped ``CHANGELOG.md`` section (the source of truth for what
landed), the merged pull requests in the release window, and the key commits —
so a release always carries: a summary of the changes, the PRs related, and
the critical commits, all referencing the changelog.

Usage:
    python scripts/release_notes.py X.Y.Z [--previous vA.B.C] [--out FILE]
                                      [--no-net] [--json]

  X.Y.Z        the version being released (must have a ## [X.Y.Z] section)
  --previous   previous version tag to diff against (default: newest older
               version tag found in the chain, i.e. the compare base Changelog
               used when the section was stamped)
  --out FILE   write the rendered notes file (default: print to stdout)
  --no-net     skip the GitHub PR lookup — render the PRs section from the
               merge commits present in the git history only (offline mode)
  --json       machine-readable render (template variables + final body)

The PR lookup uses the ``gh`` CLI (network); the commit range + changelog
section are local git only. Stdlib only; mirrors the chain definitions in
``release_chain.py``.

Rendered-template contract (what a valid release body must contain):
  - a title line (``# Mailroom Hub vX.Y.Z``) naming the version
  - a Highlights section summarising the changes in one line per card
  - the full changelog section body (the detailed change description)
  - a PRs section naming every pull request merged into the release
  - a Key commits section naming the DMR-card commits that landed
  - changelog + compare references
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
TEMPLATE = REPO_ROOT / ".github" / "RELEASE_TEMPLATE.md"
REPO = "LLM-Mailroom-Services/Digital-Mailroom"
TAG_PREFIX = "v"

SECTION_RE = re.compile(r"^## \[(?P<name>[^\]]+)\](?P<stamp> - \d{4}-\d{2}-\d{2})?\s*$")
VERSION_RE = re.compile(r"^(?P<maj>\d+)\.(?P<min>\d+)\.(?P<pat>\d+)(?:-[0-9A-Za-z.-]+)?$")
CARD_RE = re.compile(r"\b(?:DMR|HUB)-\d{3,}\b")
PR_MERGE_RE = re.compile(r"\bMerge pull request #(?P<num>\d+) from")


class ReleaseNotesError(Exception):
    """Blocking failure (exit 1)."""


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise ReleaseNotesError(f"{' '.join(cmd)} failed: {proc.stderr.strip()}")
    return proc


def git(*args: str) -> str:
    return run(["git", *args]).stdout


def gh(*args: str) -> list[dict]:
    proc = run(["gh", *args], check=False)
    if proc.returncode != 0:
        return []
    return json.loads(proc.stdout) if proc.stdout.strip() else []


def parse_semver(version: str) -> tuple[int, int, int] | None:
    m = VERSION_RE.match(version.removeprefix(TAG_PREFIX))
    if not m:
        return None
    return (int(m["maj"]), int(m["min"]), int(m["pat"]))


def version_tags() -> list[dict]:
    out = git("tag", "--list", f"{TAG_PREFIX}*", "--format=%(refname:short)%09%(creatordate:iso8601)")
    tags = []
    for line in out.splitlines():
        if not line.strip() or "\t" not in line:
            continue
        name, date = line.split("\t", 1)
        if parse_semver(name) is None:
            continue
        tags.append({"tag": name, "version": name[len(TAG_PREFIX):], "date": date.strip()})
    return sorted(tags, key=lambda t: parse_semver(t["version"]) or (0, 0, 0), reverse=True)


def changelog_sections() -> list[dict]:
    sections = []
    lines = CHANGELOG.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        m = SECTION_RE.match(line)
        if m:
            sections.append({
                "name": m["name"],
                "start": i + 1,
                "is_unreleased": m["name"].lower() == "unreleased",
            })
    if not sections:
        raise ReleaseNotesError("no ## [section] headers parse in CHANGELOG.md")
    for idx, sec in enumerate(sections):
        end = sections[idx + 1]["start"] - 1 if idx + 1 < len(sections) else len(lines)
        body = lines[sec["start"]:end]
        while body and not body[0].strip():
            body.pop(0)
        while body and not body[-1].strip():
            body.pop()
        sec["body"] = "\n".join(body)
    return sections


def section_for(version: str) -> dict:
    for sec in changelog_sections():
        if sec["name"] == version and not sec["is_unreleased"]:
            return sec
    raise ReleaseNotesError(f"no ## [{version}] section in CHANGELOG.md — cut the release first")


def previous_tag(version: str, tags: list[dict]) -> str | None:
    """Newest version tag strictly older-or-equal (excludes the same version)."""
    target = parse_semver(version)
    for t in tags:
        if parse_semver(t["version"]) == target:
            continue
        if parse_semver(t["version"]) < target:
            return t["tag"]
    return None


def bold_headlines(body: str) -> list[str]:
    """The bolded headlines of top-level bullets in a changelog section.

    A changelog card headline can span lines:
        '- **Headline text
          (DMR-0NN, 2026-09-04):** the body...'
    -> 'Headline text'. Returns each headline (trailing card refs trimmed).
    """
    lines = body.split("\n")
    headlines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("- **"):
            buf = line.lstrip("- ").lstrip("*").lstrip()
            while ":**" not in buf and i + 1 < len(lines):
                i += 1
                buf += " " + lines[i].strip()
            head, _, _ = buf.partition(":**")
            head = head.strip().strip("*").strip()
            for sep in (" (DMR-", " (HUB-", " — ", " - ", " ("):
                if sep in head:
                    head = head.split(sep, 1)[0]
            headlines.append(head.strip(" .:"))
        i += 1
    return headlines


def highlights_from_section(body: str) -> list[str]:
    """One line per landed card (the bolded headline), for the Highlights list."""
    headlines = bold_headlines(body)
    return headlines[:12] or ["See the changelog section below."]


def _tagged(version: str) -> str:
    """Normalize a version string to a v-prefixed tag (v0.4.0, HEAD, vX.Y.Z)."""
    v = version.strip()
    if v in ("HEAD", "main", "origin/main"):
        return v
    return v if v.startswith(TAG_PREFIX) else TAG_PREFIX + v


def commits_in_range(prev_tag: str, version: str) -> list[dict]:
    if prev_tag:
        out = git("log", "--oneline", "--no-merges", f"{_tagged(prev_tag)}..{_tagged(version)}")
    else:
        out = git("log", "--oneline", "--no-merges", _tagged(version))
    commits = []
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, _, subject = line.partition(" ")
        commits.append({"sha": sha[:12], "subject": subject.strip()})
    return commits


def prs_in_range(prev_tag: str, version: str, *, net: bool) -> list[dict]:
    """PRs merged into the release window. Online: gh search by merged window.
    Offline/fallback: parse 'Merge pull request #N' commits from git only."""
    if prev_tag:
        merge_log = git("log", "--oneline", "--merges", f"{_tagged(prev_tag)}..{_tagged(version)}")
    else:
        merge_log = git("log", "--oneline", "--merges", _tagged(version))
    merge_shas = [line.split()[0] for line in merge_log.splitlines() if line.strip()]

    window_prs: list[dict] = []
    if net and merge_shas:
        # Query gh for merged PRs whose merge commit is in the window (robust
        # across timezones + branch histories).
        merged = gh("pr", "list", "--state", "merged", "--repo", REPO,
                    "--limit", "200", "--json", "number,title,mergedAt,mergeCommit,url")
        by_sha = {pr.get("mergeCommit", {}).get("oid", ""): pr for pr in merged}
        for sha in merge_shas:
            full = git("rev-parse", sha).strip()
            pr = by_sha.get(full)
            if pr:
                window_prs.append({
                    "number": pr["number"], "title": pr["title"],
                    "merged_at": (pr.get("mergedAt") or "")[:10], "url": pr.get("url", ""),
                })
        # de-dup + keep merge order (newest first)
        seen = set()
        window_prs = [p for p in window_prs if not (p["number"] in seen or seen.add(p["number"]))]
    elif not net and merge_shas:
        # git-only PR numbers from merge subjects (branch ref suffix as the hint)
        for line in merge_log.splitlines():
            m = PR_MERGE_RE.search(line)
            if m:
                branch = line.split(" from ", 1)[1].split("/", 1)[-1].strip() if " from " in line else ""
                window_prs.append({"number": int(m["num"]),
                                   "title": f"(offline — branch {branch})" if branch else "(offline)",
                                   "merged_at": "", "url": ""})

    if not window_prs:
        return []
    return window_prs


def key_commits(commits: list[dict], limit: int = 15) -> list[dict]:
    """Prefer DMR-card-referenced commits (the critical ones); pad with the
    rest so the release always names its commit evidence."""
    hub = [c for c in commits if CARD_RE.search(c["subject"])]
    others = [c for c in commits if not CARD_RE.search(c["subject"])]
    chosen = hub + others
    return chosen[:limit]


def render(vars_: dict) -> str:
    template = TEMPLATE.read_text(encoding="utf-8")
    for key, value in vars_.items():
        template = template.replace("{{" + key + "}}", value or "")
    return template


def build(version: str, previous: str | None, net: bool, title: str | None = None) -> dict:
    version = version.removeprefix(TAG_PREFIX)
    if parse_semver(version) is None:
        raise ReleaseNotesError(f"{version!r} is not semver (X.Y.Z)")

    tags = version_tags()
    prev = previous or previous_tag(version, tags)
    prev = prev.removeprefix(TAG_PREFIX) if prev else None

    section = section_for(version)
    body = section["body"]
    commits = commits_in_range(_tagged(prev) if prev else None, version)
    prs = prs_in_range(_tagged(prev) if prev else None, version, net=net)
    highlights = highlights_from_section(body)

    base = f"https://github.com/{REPO}"
    compare_url = f"{base}/compare/{TAG_PREFIX}{prev}...{TAG_PREFIX}{version}" if prev else f"{base}/releases/tag/{TAG_PREFIX}{version}"
    compare_label = f"{TAG_PREFIX}{prev}...{TAG_PREFIX}{version}" if prev else f"first release {TAG_PREFIX}{version}"

    # Epoch title from the first bolded headline (e.g. "Terminal-stylized TUI"
    # -> "terminal-stylized tui epoch"); an explicit --title wins.
    if title:
        epoch_title = title.strip()
    else:
        headlines = bold_headlines(body)
        epoch = ""
        if headlines:
            head = headlines[0].strip(" .:")
            if head.lower().rstrip(" .:") not in ("hub release", "changelog", "added", "fixed", "changed"):
                if len(head) > 44:
                    head = head[:44].rstrip(" ,;:") + "…"
                epoch = head + " epoch"
        epoch_title = epoch or "hub release"

    prs_text = "\n".join(
        f"- **{p['title']}** — #{p['number']} {('(' + p['merged_at'] + ')') if p.get('merged_at') else ''}".rstrip()
        for p in prs
    ) or "None."

    commits_text = "\n".join(
        f"- `{c['sha']}` {c['subject'][:100]}" for c in key_commits(commits)
    ) or "None."

    highlights_text = "\n".join(f"- {h}" for h in highlights)

    vars_ = {
        "version": version,
        "epoch_title": epoch_title,
        "summary": (
            f"Official hub release **v{version}** ({epoch_title}) — cut from the "
            f"accumulated work in `[Unreleased]` and documented in the changelog "
            f"section below."
        ),
        "highlights": highlights_text,
        "changelog_section": body,
        "prs": prs_text,
        "commits": commits_text,
        "changelog_url": f"{base}/blob/main/CHANGELOG.md",
        "compare_label": compare_label,
        "compare_url": compare_url,
        "previous": prev or "n/a",
        "previous_release_url": f"{base}/releases/tag/{TAG_PREFIX}{prev}" if prev else "(none)",
    }
    rendered = render(vars_)
    return {"version": version, "previous": prev, "body": rendered, "vars": vars_}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", help="version being released, e.g. 0.5.0 (v prefix tolerated)")
    parser.add_argument("--previous", help="previous version tag to diff against (default: newest older tag)")
    parser.add_argument("--title", help="explicit release title suffix (e.g. '0.6.0 — relations epoch'; default derives from the first changelog headline)")
    parser.add_argument("--out", help="write the rendered notes file (default: stdout)")
    parser.add_argument("--no-net", action="store_true", help="skip the gh PR lookup (offline PR list from git)")
    parser.add_argument("--json", action="store_true", help="print as JSON (for tooling)")
    args = parser.parse_args(argv)

    try:
        result = build(args.version, args.previous, net=not args.no_net, title=args.title)
    except ReleaseNotesError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"version": result["version"], "previous": result["previous"],
                          "body": result["body"]}, indent=2))
        return 0

    if args.out:
        Path(args.out).write_text(result["body"], encoding="utf-8")
        print(f"wrote release notes for v{result['version']} -> {args.out} ({len(result['body'])} chars)")
        print(f"pass --notes-file {args.out} to `gh release create`")
    else:
        print(result["body"])
    return 0


if __name__ == "__main__":
    sys.exit(main())