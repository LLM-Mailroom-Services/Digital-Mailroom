#!/usr/bin/env python3
"""Deploy EDA reports to GitHub Pages via a gh-pages branch.

No GitHub Actions required.  Run from the monorepo root:

    python scripts/deploy_gh_pages.py --package mailroom-corpus-eda
    python scripts/deploy_gh_pages.py --package claims-data-eda
    python scripts/deploy_gh_pages.py --package Enron-Evaluation-Environment
    python scripts/deploy_gh_pages.py --all

What it does:
  1. Copies reports/<kind>/ into a temp dir.
  2. Generates an index.html landing page (auto-discovers figures, tables, markdown).
  3. Force-pushes the content to the gh-pages branch of the standalone repo.
  4. Enables GitHub Pages on the repo (if not already on).

Prerequisites: git, gh CLI (authenticated), Python 3.11+.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ROOT / "packages"

# Repo slug → (package dir name, reports subdir, display title)
REPOS: dict[str, tuple[str, str, str]] = {
    "mailroom-corpus-eda": (
        "mailroom-corpus-eda",
        "reports",
        "Mailroom Corpus EDA",
    ),
    "claims-data-eda": (
        "claims-data-eda",
        "reports",
        "CMS DE-SynPUF Claims EDA",
    ),
    "Enron-Evaluation-Environment": (
        "Enron-Evaluation-Environment",
        "reports",
        "Enron Correspondence EDA",
    ),
}

FIGURE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
TABLE_EXTS = {".csv", ".json", ".tsv"}
DOC_EXTS = {".md", ".txt", ".html"}


# ── index.html generation ──────────────────────────────────────────────

def _browse_tree(path: Path, base: Path) -> dict[str, list[str]]:
    """Return {relative_dir: [filenames]} for a reports tree."""
    tree: dict[str, list[str]] = {}
    for f in sorted(path.rglob("*")):
        if f.is_dir():
            continue
        rel = f.relative_to(base)
        d = str(rel.parent)
        tree.setdefault(d, []).append(rel.name)
    return tree


def _render_index(title: str, tree: dict[str, list[str]], base: Path) -> str:
    """Build a self-contained index.html."""
    sections: list[str] = []
    for dir_name in sorted(tree):
        files = tree[dir_name]
        heading = dir_name if dir_name != "." else title
        sections.append(f'<h2>{heading}</h2>\n<ul>')
        for fname in files:
            rel = f"{dir_name}/{fname}" if dir_name != "." else fname
            icon = "📊" if Path(fname).suffix in TABLE_EXTS else \
                   "📈" if Path(fname).suffix in FIGURE_EXTS else \
                   "📄" if Path(fname).suffix in DOC_EXTS else "📎"
            sections.append(f'  <li>{icon} <a href="{rel}">{fname}</a></li>')
        sections.append("</ul>")

    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }}
    h1 {{ border-bottom: 2px solid #e0e0e0; padding-bottom: 0.5rem; }}
    h2 {{ color: #333; margin-top: 1.5rem; }}
    ul {{ list-style: none; padding: 0; }}
    li {{ padding: 0.3rem 0; }}
    a {{ color: #0366d6; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .note {{ color: #666; font-size: 0.9rem; margin-top: 2rem; border-top: 1px solid #eee; padding-top: 0.5rem; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  {body}
  <p class="note">Auto-generated from the monorepo reports tree.
     Re-run <code>python scripts/deploy_gh_pages.py --all</code> to update.</p>
</body>
</html>"""


# ── git operations ──────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)


def _get_remote_url(repo_slug: str) -> str:
    """Construct the push URL from the gh CLI auth status."""
    # Use gh to get the repo clone URL (SSH preferred)
    result = _run(["gh", "api", f"repos/Exios66/{repo_slug}", "--jq", ".ssh_url"], ROOT, check=False)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    print(
        f"  WARN: could not resolve the ssh_url via `gh api` (rc={result.returncode}, "
        f"{result.stderr.strip()[:200]}) — falling back to the HTTPS URL; the push "
        f"may need a token",
        file=sys.stderr,
    )
    # Fallback to HTTPS
    return f"https://github.com/Exios66/{repo_slug}.git"


def _deploy_to_gh_pages(
    repo_slug: str,
    reports_dir: Path,
    display_title: str,
    dry_run: bool = False,
) -> int:
    """Build and push a gh-pages branch for one repo; returns 0 on success.

    Live-or-loud (DMR-061): a failed force-push or a failed Pages-enable
    exits 1 — a stale gh-pages site must never present as deployed.
    """
    remote_url = _get_remote_url(repo_slug)
    print(f"\n{'='*60}")
    print(f"  Deploying {display_title} → gh-pages branch")
    print(f"  Remote: {remote_url}")
    print(f"{'='*60}")

    with tempfile.TemporaryDirectory(prefix=f"ghpages-{repo_slug}-") as tmp:
        work = Path(tmp) / "site"

        # 1. Copy reports into the working dir
        shutil.copytree(reports_dir, work)
        print(f"  Copied {sum(1 for _ in work.rglob('*') if _.is_file())} files from {reports_dir}")

        # 2. .nojekyll (disables Jekyll processing, which breaks inline JS
        #    in Plotly interactive HTML files) + index.html handling.
        #    If the source reports/ already has a custom index.html, keep it;
        #    otherwise generate a browsable tree index.
        (work / ".nojekyll").write_text("")
        if (reports_dir / "index.html").exists():
            print(f"  Kept existing index.html ({(work / 'index.html').stat().st_size} bytes)")
        else:
            tree = _browse_tree(work, work)
            index_html = _render_index(display_title, tree, work)
            (work / "index.html").write_text(index_html)
            print(f"  Generated index.html ({len(index_html)} bytes) + .nojekyll")

        # 3. Init git repo and push to gh-pages
        _run(["git", "init", "--initial-branch=gh-pages"], work)
        _run(["git", "config", "user.email", "bot@exios66.github.io"], work)
        _run(["git", "config", "user.name", "gh-pages-deploy"], work)
        _run(["git", "add", "-A"], work)
        _run(["git", "commit", "-m", "Deploy EDA reports to GitHub Pages"], work, check=False)

        if dry_run:
            print("  [dry-run] Would push to gh-pages branch")
            _run(["git", "log", "--oneline", "-1"], work)
            return 0

        _run(["git", "remote", "add", "origin", remote_url], work)
        # Force push to gh-pages (safe — this branch is ephemeral by design)
        result = _run(["git", "push", "--force", "origin", "gh-pages"], work, check=False)
        if result.returncode != 0:
            print(f"  ERROR: push failed: {result.stderr.strip()}")
            # Try with HTTPS token if SSH failed
            print("  Retrying with gh auth token...")
            token_proc = subprocess.run(
                ["gh", "auth", "token"], capture_output=True, text=True
            )
            token = token_proc.stdout.strip() if token_proc.returncode == 0 else ""
            if token:
                auth_url = remote_url.replace(
                    "https://github.com/",
                    f"https://x-access-token:{token}@github.com/",
                ).replace(
                    "git@github.com:",
                    f"https://x-access-token:{token}@github.com/",
                )
                _run(["git", "remote", "set-url", "origin", auth_url], work)
                result = _run(["git", "push", "--force", "origin", "gh-pages"], work, check=False)
                if result.returncode != 0:
                    print(f"  ERROR: push still failed: {result.stderr.strip()}")
                    return 1
            else:
                print("  ERROR: no auth token available")
                return 1

        print(f"  Pushed to gh-pages ✓")

    # 4. Enable GitHub Pages (branch must exist first, so skip on dry-run)
    pages_ok = True
    if not dry_run:
        pages_ok = _enable_pages(repo_slug)
    return 0 if pages_ok else 1


def _enable_pages(repo_slug: str) -> bool:
    """Enable GitHub Pages on the gh-pages branch via the API; True on success."""
    # Check current state
    result = _run(
        ["gh", "api", f"repos/Exios66/{repo_slug}/pages", "--jq", ".html_url"],
        ROOT, check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        print(f"  Pages already enabled: {result.stdout.strip()}")
        return True

    # Enable Pages
    result = _run(
        ["gh", "api", "-X", "POST", f"repos/Exios66/{repo_slug}/pages",
         "-f", "source[branch]=gh-pages", "-f", "source[path]=/"],
        ROOT, check=False,
    )
    if result.returncode == 0:
        data = json.loads(result.stdout) if result.stdout.strip() else {}
        url = data.get("html_url", f"https://exios66.github.io/{repo_slug}/")
        print(f"  Pages enabled → {url}")
        return True
    print(f"  ERROR: could not enable Pages via API: {result.stderr.strip()}")
    print(f"  Enable manually: https://github.com/Exios66/{repo_slug}/settings/pages")
    return False


# ── CLI ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy EDA reports to GitHub Pages")
    parser.add_argument("--package", choices=list(REPOS.keys()), help="Deploy one package")
    parser.add_argument("--all", action="store_true", help="Deploy all three EDA repos")
    parser.add_argument("--dry-run", action="store_true", help="Build but don't push")
    parser.add_argument("--list-urls", action="store_true", help="Print expected URLs and exit")
    args = parser.parse_args()

    if args.list_urls:
        for slug, (_, _, title) in REPOS.items():
            print(f"  {title}: https://exios66.github.io/{slug}/")
        return

    if not args.package and not args.all:
        parser.error("Specify --package or --all")

    targets = list(REPOS.keys()) if args.all else [args.package]

    failures = 0
    for slug in targets:
        pkg_dir, reports_subdir, title = REPOS[slug]
        reports_dir = PACKAGES / pkg_dir / reports_subdir
        if not reports_dir.exists():
            print(f"SKIP {slug}: {reports_dir} does not exist")
            continue
        failures += _deploy_to_gh_pages(slug, reports_dir, title, dry_run=args.dry_run)

    if failures:
        print(f"\nDONE WITH {failures} FAILURE(S) — see the ERROR lines above; do not treat the site as deployed.")
        sys.exit(1)
    print(f"\nDone. URLs:")
    for slug in targets:
        print(f"  https://exios66.github.io/{slug}/")


if __name__ == "__main__":
    main()
