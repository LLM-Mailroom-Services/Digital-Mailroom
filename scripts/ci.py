#!/usr/bin/env python3
"""Local CI runner for the Digital-Mailroom monorepo (DMR-090).

GitHub Actions is unusable for this account, so CI runs here: the same gates
the workflows run (board-governance / release-governance) PLUS the gates the
workflows never ran (lock, vendor drift, hub script tests, board-site tests and
one pytest suite per package). It can then report a real ``ci`` commit status
to GitHub, which is the context branch protection requires (DMR-080).

Gates (name -> command), grouped:

    governance   board-check, audit-references, taxonomy-parity, release-chain,
                 labels-audit (needs GitHub credentials; classified ``skip``
                 with a reason when none are available -- never a pass)
    lock         uv lock --check
    vendor       python scripts/sync_vendor.py --check
    scripts      python3 -m unittest discover scripts/tests
    board-site   node tests/api.test.js (skipped with a reason without node)
    <package>    uv run --frozen pytest <path> -q -p no:cacheprovider
                 (one invocation per package; passed/failed/skipped parsed
                 from the pytest summary line)

Subcommands:

    run [--all | --changed [--base origin/main]] [--only GATE...] [--json]
        [--report-status]
                                 run gates (default: --changed), print a table,
                                 write .ci/last-run.json + .ci/last-run.md
                                 (pasteable into a PR body); exit 1 if any
                                 gate failed
    status [--json]              print the last run

``--changed`` maps changed paths (``git diff --name-only <merge-base>...HEAD``
plus uncommitted/untracked changes) to gates:

    packages/<pkg>/**            that package's suite
    packages/llm-dojo-scoring/** | packages/llm-mailroom/**
                                 also vendor + the sandbox suite (vendored copies)
    packages/local-mailroom-sandbox/vendor/**
                                 also the vendor gate
    scripts/** governance/** .github/**
                                 governance + scripts
    board-site/**                board-site
    pyproject.toml | uv.lock     lock + every package suite
    anything else (or no diff)   governance only

``--report-status`` posts the ``ci`` commit status for HEAD. It refuses when
the working tree is dirty, when HEAD is not on a remote branch, or when a
partial run (anything but ``--all``) would post ``success`` -- a partial run
may only ever post ``failure``. Token: GITHUB_TOKEN, MAILROOM_GH_TOKEN, then
``gh auth token``; repo override: MAILROOM_GITHUB_REPO.

Stdlib only. Exit codes: 0 all gates pass/skip, 1 a gate failed (or the status
POST failed), 2 usage error or ``--report-status`` refused.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPO = "LLM-Mailroom-Services/Digital-Mailroom"
STATUS_CONTEXT = "ci"
CI_DIR_NAME = ".ci"
UTC_FMT = "%Y-%m-%dT%H:%M:%SZ"

# package directory -> pytest path, per AGENTS.md "Per-package test suites".
PACKAGE_TESTS: dict[str, str] = {
    "llm-dojo-scoring": "packages/llm-dojo-scoring/tests",
    "llm-mailroom": "packages/llm-mailroom/src/tests",
    "The-Mailroom": "packages/The-Mailroom/tests",
    "local-mailroom-sandbox": "packages/local-mailroom-sandbox/tests",
    "mailroom-corpus-eda": "packages/mailroom-corpus-eda/tests",
    "claims-data-eda": "packages/claims-data-eda/tests",
    "Enron-Evaluation-Environment": "packages/Enron-Evaluation-Environment/tests",
}
VENDORED_PACKAGES = ("llm-dojo-scoring", "llm-mailroom")
SANDBOX = "local-mailroom-sandbox"
GOVERNANCE_GATES = ("board-check", "audit-references", "taxonomy-parity", "release-chain", "labels-audit")

STATUS_PASS, STATUS_FAIL, STATUS_SKIP = "pass", "fail", "skip"


# --------------------------------------------------------------------------
# Gates
# --------------------------------------------------------------------------

@dataclass
class Gate:
    name: str
    group: str
    argv: list[str]
    cwd: Optional[Path] = None
    parse: str = ""  # "pytest" -> parse the summary line into counts
    precheck: Optional[Callable[[], Optional[str]]] = field(default=None, repr=False)
    env: dict = field(default_factory=dict)


def find_token(environ: Optional[dict] = None, gh_runner: Optional[Callable[[], str]] = None) -> Optional[str]:
    """GITHUB_TOKEN, then MAILROOM_GH_TOKEN, then ``gh auth token``; None if none."""
    env = os.environ if environ is None else environ
    for key in ("GITHUB_TOKEN", "MAILROOM_GH_TOKEN"):
        val = (env.get(key) or "").strip()
        if val:
            return val
    if gh_runner is None:
        if not shutil.which("gh"):
            return None

        def gh_runner() -> str:
            proc = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=20)
            return proc.stdout if proc.returncode == 0 else ""
    try:
        out = (gh_runner() or "").strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return out or None


def target_repo(environ: Optional[dict] = None) -> str:
    env = os.environ if environ is None else environ
    return (env.get("MAILROOM_GITHUB_REPO") or "").strip() or DEFAULT_REPO


def build_gates(root: Path = REPO_ROOT) -> list[Gate]:
    py = sys.executable or "python3"

    def need_creds() -> Optional[str]:
        if find_token() is None:
            return "no GitHub credentials (GITHUB_TOKEN / MAILROOM_GH_TOKEN / gh auth token)"
        return None

    def need_node() -> Optional[str]:
        return None if shutil.which("node") else "node not installed"

    gates = [
        Gate("board-check", "governance", [py, "scripts/board_state.py", "check", "--log-limit", "500"]),
        Gate("audit-references", "governance", [py, "scripts/audit_references.py"]),
        Gate("taxonomy-parity", "governance", [py, "scripts/taxonomy_parity.py"]),
        Gate("release-chain", "governance", [py, "scripts/release_chain.py", "check"]),
        Gate("labels-audit", "governance",
             [py, "scripts/github_labels.py", "audit", "--repo", target_repo()],
             precheck=need_creds),
        Gate("lock", "lock", ["uv", "lock", "--check"]),
        Gate("vendor", "vendor", [py, "scripts/sync_vendor.py", "--check"]),
        Gate("scripts", "scripts", [py, "-m", "unittest", "discover", "scripts/tests"]),
        Gate("board-site", "board-site", ["node", "tests/api.test.js"],
             cwd=root / "board-site", precheck=need_node),
    ]
    for pkg, path in PACKAGE_TESTS.items():
        gates.append(Gate(pkg, "pytest",
                          ["uv", "run", "--frozen", "pytest", path, "-p", "no:cacheprovider"],
                          parse="pytest"))
    return gates


# --------------------------------------------------------------------------
# Path -> gate mapping
# --------------------------------------------------------------------------

def map_paths_to_gates(paths: Sequence[str]) -> list[str]:
    """Map changed repo-relative paths to gate names (canonical gate order)."""
    sel: set[str] = set()
    for raw in paths:
        p = raw.strip().replace("\\", "/")
        while p.startswith("./"):
            p = p[2:]
        if not p:
            continue
        parts = p.split("/")
        if parts[-1] in ("pyproject.toml", "uv.lock"):
            sel.add("lock")
            sel.update(PACKAGE_TESTS)
        elif parts[0] == "packages" and len(parts) > 2 and parts[1] in PACKAGE_TESTS:
            pkg = parts[1]
            sel.add(pkg)
            if pkg in VENDORED_PACKAGES:
                sel.update(("vendor", SANDBOX))
            if pkg == SANDBOX and parts[2] == "vendor":
                sel.add("vendor")
        elif parts[0] in ("scripts", "governance", ".github"):
            sel.update(GOVERNANCE_GATES)
            sel.add("scripts")
        elif parts[0] == "board-site":
            sel.add("board-site")
        else:
            sel.update(GOVERNANCE_GATES)  # unknown path -> governance only
    if not sel:
        sel.update(GOVERNANCE_GATES)  # empty diff -> governance only
    order = [g.name for g in build_gates()]
    return [n for n in order if n in sel]


# --------------------------------------------------------------------------
# pytest summary parsing
# --------------------------------------------------------------------------

_ITEM = r"\d+ [A-Za-z]+"
_SUMMARY_RE = re.compile(rf"^({_ITEM}(?:, {_ITEM})*)(?: in [\d.]+s.*)?$")
_NO_TESTS_RE = re.compile(r"^no tests ran(?: in [\d.]+s.*)?$")
_COUNT_KEYS = {
    "passed": "passed", "failed": "failed", "skipped": "skipped",
    "error": "errors", "errors": "errors", "xfailed": "xfailed", "xpassed": "xpassed",
}


def parse_pytest_summary(output: str) -> dict:
    """Parse the final pytest summary line into counts.

    Returns passed/failed/skipped/errors/xfailed/xpassed (ints, 0 when absent)
    plus ``found`` (False when no summary line was recognised, e.g. a crash
    before pytest reported).
    """
    counts = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "xfailed": 0, "xpassed": 0, "found": False}
    lines = output.splitlines()
    for line in reversed(lines):
        text = line.strip().strip("=").strip()
        if not text:
            continue
        if _NO_TESTS_RE.match(text):
            counts["found"] = True
            return counts
        if _SUMMARY_RE.match(text):
            for num, word in re.findall(r"(\d+) ([A-Za-z]+)", text.split(" in ")[0]):
                key = _COUNT_KEYS.get(word)
                if key:
                    counts[key] += int(num)
            counts["found"] = True
            return counts
    return _count_progress_chars(lines, counts)


_PROGRESS_RE = re.compile(r"^([.sFExX]+)\s*(?:\[\s*\d+%\])?$")
_PROGRESS_KEYS = {".": "passed", "s": "skipped", "F": "failed", "E": "errors", "x": "xfailed", "X": "xpassed"}


def _count_progress_chars(lines: list[str], counts: dict) -> dict:
    """Fallback when pytest printed no summary line (e.g. a suite's addopts
    carry ``-q -q``): tally the progress characters (``.`` ``s`` ``F`` ``E``
    ``x`` ``X``) from the dotted progress lines."""
    seen = False
    for line in lines:
        m = _PROGRESS_RE.match(line.strip())
        if m:
            seen = True
            for ch in m.group(1):
                counts[_PROGRESS_KEYS[ch]] += 1
    counts["found"] = seen
    return counts


# --------------------------------------------------------------------------
# Git helpers
# --------------------------------------------------------------------------

def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True)


def head_sha(root: Path) -> str:
    proc = _git(root, "rev-parse", "HEAD")
    return proc.stdout.strip() if proc.returncode == 0 else ""


def current_branch(root: Path) -> str:
    proc = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return proc.stdout.strip() if proc.returncode == 0 else ""


def changed_paths(root: Path, base: str) -> Optional[list[str]]:
    """Paths changed vs the merge-base of ``base`` plus uncommitted/untracked.

    None when the merge-base cannot be computed (caller falls back to every
    gate, the safe direction).
    """
    mb = _git(root, "merge-base", base, "HEAD")
    if mb.returncode != 0 or not mb.stdout.strip():
        return None
    out: list[str] = []
    for args in (("diff", "--name-only", f"{mb.stdout.strip()}...HEAD"),
                 ("diff", "--name-only", "HEAD"),
                 ("ls-files", "--others", "--exclude-standard")):
        proc = _git(root, *args)
        if proc.returncode == 0:
            out.extend(l for l in proc.stdout.splitlines() if l.strip())
    return sorted(set(out))


def is_dirty(root: Path) -> bool:
    proc = _git(root, "status", "--porcelain")
    return proc.returncode != 0 or bool(proc.stdout.strip())


def head_on_remote(root: Path) -> bool:
    proc = _git(root, "branch", "-r", "--contains", "HEAD")
    return proc.returncode == 0 and bool(proc.stdout.strip())


# --------------------------------------------------------------------------
# Running
# --------------------------------------------------------------------------

def run_gate(gate: Gate, root: Path, ci_dir: Path) -> dict:
    rec = {"name": gate.name, "group": gate.group, "command": " ".join(gate.argv),
           "status": STATUS_PASS, "rc": 0, "duration_s": 0.0, "reason": "", "counts": None, "log": ""}
    if gate.precheck:
        reason = gate.precheck()
        if reason:
            rec.update(status=STATUS_SKIP, rc=None, reason=reason)
            return rec
    env = dict(os.environ)
    env.update(gate.env)
    if gate.name == "labels-audit":
        tok = find_token()
        if tok:
            env["GH_TOKEN"] = tok
    start = time.monotonic()
    try:
        proc = subprocess.run(gate.argv, cwd=str(gate.cwd or root), env=env,
                              capture_output=True, text=True)
        rc, output = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except OSError as exc:
        rc, output = 127, f"could not execute {gate.argv[0]!r}: {exc}\n"
    rec["duration_s"] = round(time.monotonic() - start, 1)
    rec["rc"] = rc
    ci_dir.mkdir(parents=True, exist_ok=True)
    log = ci_dir / f"{gate.name}.log"
    log.write_text(output, encoding="utf-8")
    rec["log"] = f"{CI_DIR_NAME}/{log.name}"
    if gate.parse == "pytest":
        rec["counts"] = parse_pytest_summary(output)
    if rc != 0:
        rec["status"] = STATUS_FAIL
        rec["reason"] = f"exit {rc}"
        rec["tail"] = "\n".join(output.splitlines()[-25:])
    return rec


def describe(n: int, p: int, f: int, s: int, partial: bool = False) -> str:
    """Status description, e.g. ``12 gates: 11 pass, 1 skip`` (zero fail/skip omitted)."""
    parts = [f"{p} pass"]
    if f:
        parts.append(f"{f} fail")
    if s:
        parts.append(f"{s} skip")
    text = f"{n} gates: " + ", ".join(parts)
    if partial:
        text = "partial run, " + text
    return text[:140]


def summarize(records: list[dict], *, mode: str, sha: str, branch: str, started: str) -> dict:
    n = len(records)
    p = sum(r["status"] == STATUS_PASS for r in records)
    f = sum(r["status"] == STATUS_FAIL for r in records)
    s = sum(r["status"] == STATUS_SKIP for r in records)
    return {"schema": 1, "sha": sha, "branch": branch, "mode": mode, "started": started,
            "gates": records,
            "totals": {"gates": n, "pass": p, "fail": f, "skip": s},
            "state": "failure" if f else "success",
            "description": describe(n, p, f, s, partial=(mode != "all"))}


def _detail(r: dict) -> str:
    c = r.get("counts")
    if c and c.get("found"):
        bits = [f"{c['passed']} passed"]
        for key in ("failed", "skipped", "errors", "xfailed", "xpassed"):
            if c[key]:
                bits.append(f"{c[key]} {key}")
        return ", ".join(bits)
    if c is not None and r["status"] != STATUS_SKIP:
        return "no pytest summary line" + (f" ({r['reason']})" if r["reason"] else "")
    return r["reason"]


def render_table(summary: dict) -> str:
    rows = [("GATE", "STATUS", "TIME", "DETAIL")]
    for r in summary["gates"]:
        rows.append((r["name"], r["status"].upper(), f"{r['duration_s']:.1f}s", _detail(r)))
    widths = [max(len(row[i]) for row in rows) for i in range(3)]
    lines = ["  ".join(c.ljust(widths[i]) for i, c in enumerate(row[:3])) + "  " + row[3] for row in rows]
    lines.append("")
    lines.append(f"ci: {summary['state']} -- {summary['description']} "
                 f"(mode={summary['mode']}, sha={summary['sha'][:8] or '?'})")
    return "\n".join(lines)


def render_markdown(summary: dict) -> str:
    out = [f"### Local CI (`scripts/ci.py`): {summary['state']}", "",
           f"- commit: `{summary['sha']}` on `{summary['branch']}`",
           f"- mode: `{summary['mode']}`" + ("" if summary["mode"] == "all" else
                                           " (partial run: cannot mark the required `ci` check green)"),
           f"- started: {summary['started']}",
           f"- result: {summary['description']}", "",
           "| Gate | Status | Time | Detail |", "| --- | --- | --- | --- |"]
    for r in summary["gates"]:
        out.append(f"| `{r['name']}` | {r['status']} | {r['duration_s']:.1f}s | {_detail(r) or '-'} |")
    return "\n".join(out) + "\n"


def write_summary(root: Path, summary: dict) -> None:
    d = root / CI_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    (d / "last-run.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (d / "last-run.md").write_text(render_markdown(summary), encoding="utf-8")


# --------------------------------------------------------------------------
# Status reporting
# --------------------------------------------------------------------------

def build_status_payload(summary: dict) -> dict:
    return {"state": summary["state"], "context": STATUS_CONTEXT,
            "description": summary["description"][:140]}


def post_status(url: str, token: str, payload: dict) -> tuple[int, str]:
    """POST a commit status to GitHub. Isolated so tests can fake it."""
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json", "User-Agent": "mailroom-local-ci"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except urllib.error.URLError as exc:
        return 0, str(exc.reason)


class Refused(Exception):
    """--report-status refused (exit 2)."""


def report_status(summary: dict, root: Path, *, poster: Callable = post_status,
                  token: Optional[str] = None, repo: Optional[str] = None) -> dict:
    """Post the ``ci`` status for HEAD, or raise Refused with the reason."""
    sha = head_sha(root)
    if not sha:
        raise Refused("cannot resolve HEAD")
    if summary.get("sha") and summary["sha"] != sha:
        raise Refused(f"HEAD moved during the run ({summary['sha'][:8]} -> {sha[:8]}); re-run")
    if is_dirty(root):
        raise Refused("working tree is dirty; commit or clean it so the status describes HEAD")
    if not head_on_remote(root):
        raise Refused("HEAD is not on any remote branch (`git branch -r --contains HEAD` is empty); push first")
    if summary["state"] == "success" and summary["mode"] != "all":
        raise Refused(f"mode={summary['mode']} is a partial run; only `run --all` may post success "
                      "(a partial run may only post failure)")
    token = token or find_token()
    if not token:
        raise Refused("no GitHub token (GITHUB_TOKEN / MAILROOM_GH_TOKEN / gh auth token)")
    repo = repo or target_repo()
    url = f"https://api.github.com/repos/{repo}/statuses/{sha}"
    payload = build_status_payload(summary)
    code, body = poster(url, token, payload)
    if not 200 <= code < 300:
        raise RuntimeError(f"status POST failed: HTTP {code}: {body[:200]}")
    return {"url": url, "payload": payload, "http": code}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime(UTC_FMT)


def cmd_run(args, root: Path, gates: list[Gate], poster: Callable) -> int:
    log = sys.stderr if args.json else sys.stdout
    mode = "all" if args.all else "changed"
    if args.all:
        selected = [g.name for g in gates]
    else:
        paths = changed_paths(root, args.base)
        if paths is None:
            print(f"ci: cannot compute merge-base with {args.base}; running ALL gates", file=log)
            selected = [g.name for g in gates]
        else:
            wanted = set(map_paths_to_gates(paths))
            selected = [g.name for g in gates if g.name in wanted]
    if args.only:
        wanted = set()
        for tok in args.only:
            hit = [g.name for g in gates if g.name == tok or g.group == tok]
            if not hit:
                known = sorted({g.name for g in gates} | {g.group for g in gates})
                print(f"ci: unknown gate/group {tok!r}; known: {', '.join(known)}", file=sys.stderr)
                return 2
            wanted.update(hit)
        selected = [g.name for g in gates if g.name in wanted]
        mode = "only"
    by_name = {g.name: g for g in gates}
    started = _now()
    records = []
    for i, name in enumerate(selected, 1):
        print(f"[{i}/{len(selected)}] {name} ...", file=log, flush=True)
        rec = run_gate(by_name[name], root, root / CI_DIR_NAME)
        records.append(rec)
        print(f"[{i}/{len(selected)}] {name}: {rec['status'].upper()} {_detail(rec)}", file=log, flush=True)
        if rec["status"] == STATUS_FAIL and rec.get("tail"):
            print(rec["tail"], file=log)
    summary = summarize(records, mode=mode, sha=head_sha(root), branch=current_branch(root), started=started)
    rc = 1 if summary["totals"]["fail"] else 0
    if args.report_status:
        try:
            posted = report_status(summary, root, poster=poster)
        except Refused as exc:
            print(f"ci: --report-status REFUSED: {exc}", file=sys.stderr)
            summary["report"] = {"refused": str(exc)}
            rc = rc or 2
        except RuntimeError as exc:
            print(f"ci: --report-status FAILED: {exc}", file=sys.stderr)
            summary["report"] = {"error": str(exc)}
            rc = 1
        else:
            print(f"ci: posted {posted['payload']['state']} status to {posted['url']}", file=log)
            summary["report"] = {"posted": posted["payload"]["state"], "url": posted["url"]}
    write_summary(root, summary)
    print(json.dumps(summary, indent=2) if args.json else render_table(summary))
    return rc


def cmd_status(args, root: Path) -> int:
    path = root / CI_DIR_NAME / "last-run.json"
    if not path.exists():
        print("ci: no previous run (.ci/last-run.json missing)", file=sys.stderr)
        return 1
    summary = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(summary, indent=2) if args.json else render_table(summary))
    return 0


def main(argv: Optional[list[str]] = None, *, gates: Optional[list[Gate]] = None,
         poster: Callable = post_status, root: Optional[Path] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="run gates (default: --changed)")
    mode = p_run.add_mutually_exclusive_group()
    mode.add_argument("--all", action="store_true", help="run every gate")
    mode.add_argument("--changed", action="store_true", help="run gates for changed paths (default)")
    p_run.add_argument("--base", default="origin/main", help="base ref for --changed (default origin/main)")
    p_run.add_argument("--only", nargs="+", metavar="GATE", help="restrict to these gates/groups (partial run)")
    p_run.add_argument("--json", action="store_true", help="machine-readable output")
    p_run.add_argument("--report-status", action="store_true", help="post the `ci` commit status for HEAD")

    p_status = sub.add_parser("status", help="print the last run")
    p_status.add_argument("--json", action="store_true", help="machine-readable output")

    args = parser.parse_args(argv)
    root = root or REPO_ROOT
    if args.command == "status":
        return cmd_status(args, root)
    return cmd_run(args, root, gates if gates is not None else build_gates(root), poster)


if __name__ == "__main__":
    sys.exit(main())
