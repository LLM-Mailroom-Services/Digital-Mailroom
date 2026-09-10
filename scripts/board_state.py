#!/usr/bin/env python3
"""Board governance state tracker for the Digital-Mailroom Kanban board (DMR-001).

Reads the LIVE state of ``governance/TASKS.md`` — the single source of truth
for cross-agent task state in the monorepo — into a computationally readable
form, validates the board's own laws against reality, and mirrors lane state
onto GitHub (labels on synced issues, plus an optional GitHub Projects v2
board with Lane/Owner/Card fields).

Usage:
    python scripts/board_state.py status         [--json]
    python scripts/board_state.py card DMR-0NN   [--json]
    python scripts/board_state.py check          [--with-issues] [--stale-days N]
                                                 [--log-limit N] [--strict] [--json]
    python scripts/board_state.py sync-issues    [--apply] [--repo OWNER/NAME]
    python scripts/board_state.py pull-issues    [--apply] [--repo OWNER/NAME]
    python scripts/board_state.py project-init   [--title T] [--owner OWNER]
    python scripts/board_state.py project-sync   [--apply]

  status        human-readable live board snapshot (lanes, cards, counts)
  card          one card's full parsed state + every commit referencing it
  check         validate board invariants; exit 1 on errors, 0 otherwise
                (warnings stay warnings unless --strict)
  sync-issues   apply stage/attention/kanban/domain/priority labels to synced
                issues so they match the board (dry-run default)
  pull-issues   REVERSE sync — import issue-side lane moves (made on the
                served dispatch board) back into TASKS.md Lane cells +
                Evidence notes, so the board stays canonical after site
                edits (dry-run default; one-way, never auto-creates cards)
  project-init  one-time: create the Projects v2 mirror + Lane/Owner/Card
                fields, record them in scripts/board_config.json
  project-sync  make the project mirror match the open table (dry-run default)

Parsing rules (governance/TASKS.md structure):
  open cards  | Card | Status | Task | Owner | Issue | Evidence | rows under
              "## Open cards"; the lane is the backticked token in Status.
  archive     "- **DMR-0NN** (done YYYY-MM-DD) — ..." bullets under "## Archive".

Findings severity contract:
  error    machine-verifiable structural contradiction (duplicate IDs, invalid
           lanes, malformed issue links, missing attention tags, phantom
           commit references) — check exits 1.
  warning  board-law hygiene needing a human/agent fix (pending-archive
           lingering, lane/owner mismatch, stale in_progress, unclaimed cards
           with commits, label drift) — check exits 0 unless --strict.

Requires: git (local history cross-checks). ``sync-issues`` / ``project-*``
additionally require the ``gh`` CLI authenticated against the repo
(``project-*`` needs the ``project`` token scope). Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BOARD_PATH = REPO_ROOT / "governance" / "TASKS.md"
CONFIG_PATH = REPO_ROOT / "scripts" / "board_config.json"

DEFAULT_REPO = "LLM-Mailroom-Services/Digital-Mailroom"
DEFAULT_PROJECT_TITLE = "digital-mailroom board"

LANES = ("unassigned", "assigned", "in_progress", "needs_attention", "done")
LANE_LABELS = {
    "unassigned": "stage/unassigned",
    "assigned": "stage/assigned",
    "in_progress": "stage/in-progress",
    "needs_attention": "stage/needs-attention",
    "done": "stage/done",
}
ATTENTION_LABELS = {
    "needs:": "attention/blocked",
    "review:": "attention/review",
    "decision:": "attention/decision",
}
PRIORITIES = ("low", "medium", "high", "critical")
DOMAIN_DASH = {"—", "--", "-"}

CARD_RE = re.compile(r"DMR-\d{3,}")
ARCHIVE_ROW_RE = re.compile(r"^\s*-\s+\*\*(DMR-\d+)\*\*\s+\(done\s+(\d{4}-\d{2}-\d{2})\)")
ISSUE_LINK_RE = re.compile(r"\[#(\d+)\]\((https://github\.com/[^)\s]+/issues/\d+)\)")
ISSUE_BARE_RE = re.compile(r"^\s*#(\d+)\s*$")


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=REPO_ROOT, check=False, text=True, capture_output=True)


# ---------------------------------------------------------------- parsing


@dataclass
class Card:
    id: str
    section: str  # "open" | "archive"
    lane: str | None = None
    pending_archive: bool = False
    owner: str = ""
    task: str = ""
    issue_raw: str = ""
    issue_number: int | None = None
    issue_url: str | None = None
    issue_wellformed: bool | None = None  # None = board-only (no issue)
    evidence: str = ""
    commits: list[str] = field(default_factory=list)
    archived_date: str | None = None

    @property
    def attention_tags(self) -> list[str]:
        text = f"{self.task} {self.evidence}".lower()
        return [tag for tag in ATTENTION_LABELS if tag in text]

    def to_json(self) -> dict:
        data = asdict(self)
        data["attention_tags"] = self.attention_tags
        return data


@dataclass
class BoardState:
    board_path: str
    read_at: str
    head: str | None
    head_dirty: bool
    open_cards: list[Card]
    archived_cards: list[Card]

    def counts(self) -> dict:
        by_lane = {lane: 0 for lane in LANES}
        for card in self.open_cards:
            if card.lane in by_lane:
                by_lane[card.lane] += 1
        return {
            "open": len(self.open_cards),
            "open_by_lane": by_lane,
            "archived": len(self.archived_cards),
            "synced": sum(1 for c in self.open_cards if c.issue_number),
            "board_only": sum(1 for c in self.open_cards if not c.issue_number),
        }

    def find(self, card_id: str) -> Card | None:
        for card in [*self.open_cards, *self.archived_cards]:
            if card.id == card_id:
                return card
        return None

    def to_json(self) -> dict:
        return {
            "schema_version": 1,
            "board_path": self.board_path,
            "read_at": self.read_at,
            "head": self.head,
            "head_dirty": self.head_dirty,
            "counts": self.counts(),
            "open_cards": [c.to_json() for c in self.open_cards],
            "archived_cards": [c.to_json() for c in self.archived_cards],
        }


def parse_issue_cell(raw: str) -> tuple[int | None, str | None, bool | None]:
    """Returns (number, url, wellformed); wellformed is None for board-only cards."""
    text = raw.strip()
    if text in DOMAIN_DASH or not text:
        return None, None, None
    match = ISSUE_LINK_RE.search(text)
    if match:
        number, url = int(match.group(1)), match.group(2)
        return number, url, url.rstrip("/").endswith(f"/issues/{number}")
    bare = ISSUE_BARE_RE.match(text)
    if bare:
        return int(bare.group(1)), None, False
    return None, None, False


def parse_board(board_path: Path | None = None) -> BoardState:
    board_path = board_path or BOARD_PATH
    lines = board_path.read_text(encoding="utf-8").splitlines()
    open_cards: list[Card] = []
    archived_cards: list[Card] = []
    section = "preamble"

    for line in lines:
        if line.startswith("## "):
            heading = line[3:].strip().lower()
            section = ("open" if heading.startswith("open cards")
                       else "archive" if heading.startswith("archive") else "other")
            continue

        if section == "open" and line.lstrip().startswith("|") and CARD_RE.search(line):
            cells = [cell.strip().replace(r"\|", "|")
                     for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
            if len(cells) < 6 or not CARD_RE.fullmatch(cells[0] or ""):
                continue
            status_raw = cells[1]
            lane_match = re.match(r"`([a-z_]+)`", status_raw)
            number, url, wellformed = parse_issue_cell(cells[4])
            open_cards.append(Card(
                id=cells[0],
                section="open",
                lane=lane_match.group(1) if lane_match else None,
                pending_archive="(pending archive)" in status_raw,
                owner=cells[3] or "unclaimed",
                task=cells[2],
                issue_raw=cells[4],
                issue_number=number,
                issue_url=url,
                issue_wellformed=wellformed,
                evidence=cells[5],
            ))

        elif section == "archive":
            match = ARCHIVE_ROW_RE.match(line)
            if match:
                card_id, date = match.group(1), match.group(2)
                text = line.strip()
                number, url, wellformed = parse_issue_cell(text)
                archived_cards.append(Card(
                    id=card_id,
                    section="archive",
                    lane="done",
                    task=text,
                    issue_raw=card_id,
                    issue_number=number,
                    issue_url=url,
                    issue_wellformed=wellformed,
                    evidence=text,
                    archived_date=date,
                ))

    head, dirty = git_head()
    return BoardState(
        board_path=str(board_path.relative_to(REPO_ROOT)) if board_path.is_relative_to(REPO_ROOT) else str(board_path),
        read_at=utc_now(),
        head=head,
        head_dirty=dirty,
        open_cards=open_cards,
        archived_cards=archived_cards,
    )


# ---------------------------------------------------------------- git + gh


def git_head() -> tuple[str | None, bool]:
    head = run(["git", "rev-parse", "--short", "HEAD"])
    sha = head.stdout.strip() if head.returncode == 0 else None
    dirty = run(["git", "status", "--porcelain"]).stdout.strip() != ""
    return sha, dirty


def commit_log(limit: int) -> list[tuple[str, str]]:
    result = run(["git", "log", f"--max-count={limit}", "--pretty=%h%x09%s"])
    commits = []
    for line in result.stdout.splitlines():
        if "\t" in line:
            sha, subject = line.split("\t", 1)
            commits.append((sha.strip(), subject.strip()))
    return commits


def commits_for_cards(limit: int) -> dict[str, list[tuple[str, str]]]:
    refs: dict[str, list[tuple[str, str]]] = {}
    for sha, subject in commit_log(limit):
        for card_id in set(CARD_RE.findall(subject)):
            refs.setdefault(card_id, []).append((sha, subject))
    return refs


def default_repo() -> str:
    result = run(["git", "remote", "get-url", "origin"])
    url = result.stdout.strip() if result.returncode == 0 else ""
    if url.endswith(".git"):
        url = url[:-4]
    if "github.com" in url:
        return url.split("github.com")[-1].lstrip(":/")
    return DEFAULT_REPO


def gh_json(args: list[str]) -> dict | list | None:
    result = run(["gh", *args])
    if result.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)} failed: {result.stderr.strip()}")
    out = result.stdout.strip()
    return json.loads(out) if out else None


# ---------------------------------------------------------------- findings


@dataclass
class Finding:
    severity: str  # "error" | "warning" | "info"
    code: str
    card: str | None
    message: str

    def render(self) -> str:
        where = self.card or "board"
        return f"[{self.severity.upper():7}] {self.code} ({where}): {self.message}"


def board_findings(state: BoardState, refs: dict[str, list[tuple[str, str]]],
                   stale_days: int, origin_repo: str) -> list[Finding]:
    findings: list[Finding] = []
    open_ids = [c.id for c in state.open_cards]
    all_ids = open_ids + [c.id for c in state.archived_cards]

    for card_id in sorted({cid for cid in all_ids if all_ids.count(cid) > 1}):
        open_card = next((c for c in state.open_cards if c.id == card_id), None)
        if open_card and open_card.pending_archive:
            findings.append(Finding("warning", "pending-archive-duplicate", card_id,
                                    "card sits in both the open table (done, pending archive) and the Archive — remove the open row"))
        else:
            findings.append(Finding("error", "duplicate-card-id", card_id,
                                    "card ID appears more than once on the board"))

    for card in state.open_cards:
        if card.lane not in LANES:
            findings.append(Finding("error", "invalid-lane", card.id,
                                    f"lane {card.lane!r} is not one of {list(LANES)}"))
            continue
        if card.pending_archive:
            findings.append(Finding("warning", "pending-archive", card.id,
                                    "done card still in the open table — move it to the Archive"))
        if card.lane == "needs_attention" and not card.attention_tags:
            findings.append(Finding("error", "attention-tag-missing", card.id,
                                    "needs_attention card lacks a needs:/review:/decision: tag"))
        if card.lane == "unassigned" and card.owner not in ("", "unclaimed"):
            findings.append(Finding("error", "unassigned-with-owner", card.id,
                                    f"lane unassigned but Owner is {card.owner!r} — unassigned is the free-to-claim lane"))
        if card.lane == "assigned" and card.owner in ("", "unclaimed"):
            findings.append(Finding("warning", "assigned-unclaimed", card.id,
                                    "Owner is unclaimed in the assigned lane — move the card to unassigned (free to claim)"))
        if card.lane == "in_progress" and card.owner in ("", "unclaimed"):
            findings.append(Finding("warning", "in-progress-unclaimed", card.id,
                                    "in_progress means an owner holds it — set Owner or move back to assigned"))

        card_commits = refs.get(card.id, [])
        if card.lane == "assigned" and card.owner == "unclaimed" and card_commits:
            findings.append(Finding("warning", "unclaimed-with-commits", card.id,
                                    f"{len(card_commits)} commit(s) reference this card but it is assigned+unclaimed — claim it"))
        if card.lane == "assigned" and card.owner not in ("", "unclaimed") and card_commits:
            findings.append(Finding("warning", "assigned-with-commits", card.id,
                                    "work exists (commits reference this card) — the law says in_progress, label before the code"))

        if card.issue_number is None:
            continue
        if card.issue_wellformed is False:
            if card.issue_url is None:
                findings.append(Finding("warning", "issue-bare-number", card.id,
                                        f"issue column uses a bare number ({card.issue_raw}) — the law wants the full markdown link"))
            else:
                findings.append(Finding("error", "issue-link-malformed", card.id,
                                        f"issue column does not parse as [#NNN](.../issues/NNN): {card.issue_raw}"))
        if card.issue_url and origin_repo not in card.issue_url:
            findings.append(Finding("warning", "issue-cross-repo", card.id,
                                    f"issue link points outside {origin_repo} (allowed for package-scoped work, verify intent)"))

    for card_id in sorted(refs):
        if card_id not in all_ids:
            latest = refs[card_id][0][1]
            findings.append(Finding("error", "phantom-card-reference", card_id,
                                    f"commits reference a card missing from the board (latest: {latest[:80]})"))

    cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
    for card in state.open_cards:
        if card.lane != "in_progress" or not refs.get(card.id):
            continue
        latest_sha = refs[card.id][0][0]
        result = run(["git", "show", "-s", "--format=%cI", latest_sha])
        if result.returncode == 0:
            try:
                committed = datetime.fromisoformat(result.stdout.strip()).astimezone(timezone.utc)
                if committed < cutoff:
                    findings.append(Finding("warning", "stale-in-progress", card.id,
                                            f"latest referencing commit {latest_sha} is older than {stale_days} days"))
            except ValueError:
                pass

    return findings


def issue_findings(state: BoardState, origin_repo: str) -> list[Finding]:
    findings: list[Finding] = []
    for card in state.open_cards:
        if not card.issue_number:
            continue
        try:
            issue = gh_json(["issue", "view", str(card.issue_number), "--repo", origin_repo,
                             "--json", "state,title,labels"])
        except RuntimeError as exc:
            findings.append(Finding("info", "issue-lookup-unavailable", card.id, str(exc)))
            continue
        if issue is None:
            continue
        labels = {entry["name"] for entry in issue.get("labels", [])}
        expect_open = card.lane != "done"
        if (issue["state"] == "OPEN") != expect_open:
            findings.append(Finding("error", "issue-state-mismatch", card.id,
                                    f"issue #{card.issue_number} is {issue['state']} but card lane is {card.lane}"))
        if card.id not in issue.get("title", ""):
            findings.append(Finding("warning", "issue-title-mismatch", card.id,
                                    f"issue #{card.issue_number} title does not name the card"))
        if "kanban" not in labels:
            findings.append(Finding("warning", "issue-label-kanban", card.id,
                                    f"issue #{card.issue_number} lacks the kanban label (run sync-issues)"))
        lane_label = LANE_LABELS.get(card.lane or "")
        if lane_label and lane_label not in labels:
            findings.append(Finding("warning", "issue-label-lane", card.id,
                                    f"issue #{card.issue_number} lacks {lane_label} (run sync-issues)"))

    for card in state.archived_cards:
        if not card.issue_number:
            continue
        try:
            issue = gh_json(["issue", "view", str(card.issue_number), "--repo", origin_repo,
                             "--json", "state"])
        except RuntimeError as exc:
            findings.append(Finding("info", "issue-lookup-unavailable", card.id, str(exc)))
            continue
        if issue and issue.get("state") != "CLOSED":
            findings.append(Finding("warning", "archived-issue-open", card.id,
                                    f"archived card's issue #{card.issue_number} is still open"))
    return findings


# ---------------------------------------------------------------- commands


def cmd_status(args: argparse.Namespace) -> int:
    state = parse_board()
    if args.json:
        print(json.dumps(state.to_json(), indent=2))
        return 0

    counts = state.counts()
    print(f"board     {state.board_path}  (HEAD {state.head or '?'}{', dirty' if state.head_dirty else ''})")
    print(f"read at   {state.read_at}")
    print(f"open      {counts['open']} cards  — " +
          "  ".join(f"{lane}: {n}" for lane, n in counts["open_by_lane"].items()))
    print(f"          synced: {counts['synced']}   board-only: {counts['board_only']}")
    print(f"archived  {counts['archived']} cards")
    print()
    header = f"{'card':8} {'lane':16} {'owner':22} {'issue':7} task"
    print(header)
    print("-" * max(len(header), 100))
    for card in state.open_cards:
        task = card.task.replace("**", "").replace("`", "")
        pending = " (pending archive)" if card.pending_archive else ""
        issue = f"#{card.issue_number}" if card.issue_number else "—"
        print(f"{card.id:8} {card.lane or '?':16} {card.owner[:22]:22} {issue:7} {task[:64]}{pending}")
    return 0


def cmd_card(args: argparse.Namespace) -> int:
    state = parse_board()
    card = state.find(args.card_id.upper())
    if card is None:
        known = ", ".join(c.id for c in state.open_cards) or "none"
        print(f"no card {args.card_id.upper()} on the board (open: {known})", file=sys.stderr)
        return 1
    refs = commits_for_cards(args.log_limit)
    card.commits = [sha for sha, _ in refs.get(card.id, [])]
    if args.json:
        print(json.dumps(card.to_json(), indent=2))
        return 0
    print(f"card      {card.id}  ({card.section})")
    print(f"lane      {card.lane}{' (pending archive)' if card.pending_archive else ''}")
    print(f"owner     {card.owner or 'unclaimed'}")
    if card.section == "archive":
        print(f"archived  {card.archived_date}")
    print(f"issue     {card.issue_raw or '—'}")
    if card.commits:
        print(f"commits   {', '.join(card.commits)}")
    else:
        print(f"commits   none in last {args.log_limit} commits")
    print(f"task      {card.task}")
    print(f"evidence  {card.evidence}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    state = parse_board()
    refs = commits_for_cards(args.log_limit)
    origin_repo = args.repo or default_repo()
    findings = board_findings(state, refs, args.stale_days, origin_repo)
    network_note = None
    if args.with_issues:
        try:
            findings.extend(issue_findings(state, origin_repo))
        except RuntimeError as exc:
            network_note = f"issue checks skipped — {exc}"
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    passed = errors == 0 and not (args.strict and warnings)

    if args.json:
        print(json.dumps({
            "schema_version": 1,
            "board": state.to_json(),
            "findings": [asdict(f) for f in findings],
            "errors": errors,
            "warnings": warnings,
            "passed": passed,
        }, indent=2))
    else:
        if network_note:
            print(f"note: {network_note}")
        if not findings:
            print(f"board OK: {state.counts()['open']} open cards, all invariants hold")
        for finding in findings:
            print(finding.render())
        tail = f"{errors} error(s), {warnings} warning(s)"
        if warnings and not args.strict:
            tail += "  (--strict would fail)"
        print(f"\n{tail}")
    return 0 if passed else 1


# ------------------------------------------------- labels on synced issues


def issue_body_section(body: str, heading: str) -> str | None:
    match = re.search(rf"^### {re.escape(heading)}\s*\n(.*?)(?=^### |\Z)", body,
                      re.MULTILINE | re.DOTALL)
    if not match:
        return None
    return match.group(1).strip() or None


def issue_body_set_section(body: str, heading: str, content: str) -> str:
    """Set/replace one '### heading' section, rebuilding the body cleanly so
    headings are never glued together (mirrors board-site/lib/gh.js). Returns
    the new body. The section is inserted at the end if not already present."""
    body = (body or "").replace(r"\r\n", "\n")
    lines = body.split("\n")
    sections: list[tuple[str, list[str]]] = []
    preamble: list[str] = []
    cur: list[str] | None = None
    cur_head = ""
    for line in lines:
        m = re.match(r"^###\s+([^\n]+)$", line)
        if m:
            if cur is not None:
                sections.append((cur_head, cur))
            cur_head = m.group(1).strip()
            cur = []
        elif cur is not None:
            cur.append(line)
        else:
            preamble.append(line)
    if cur is not None:
        sections.append((cur_head, cur))
    clean = (content or "").strip()
    clean = clean if clean else "—"
    found = False
    out_sections: list[tuple[str, str]] = []
    for h, ln in sections:
        if h.lower() == heading.lower():
            out_sections.append((h, clean))
            found = True
        else:
            out_sections.append((h, "\n".join(ln).rstrip()))
    if not found:
        out_sections.append((heading, clean))
    rebuilt = "\n\n".join(
        [preamble_text.rstrip()] + [f"### {h}\n{c}" for h, c in out_sections]
    ) if (preamble_text := "\n".join(preamble)) else "\n\n".join(
        [f"### {h}\n{c}" for h, c in out_sections]
    )
    return rebuilt.rstrip() + "\n"


def owner_identity(owner: str) -> str:
    """The agent/persona/harness conducting the work, without the claim date
    that rides the board Owner cell (e.g. 'opencode (GLM-5.3-Flash) 2026-09-03'
    -> 'opencode (GLM-5.3-Flash)')."""
    return re.sub(r"\s+\d{4}-\d{2}-\d{2}\s*$", "", owner.strip()) or owner.strip()


def domain_label_from_answer(answer: str) -> str | None:
    value = answer.strip().lower().split(" (")[0].strip()
    known = {"hub": "domain/hub", "governance": "domain/governance", "tooling": "domain/tooling"}
    if value in known:
        return known[value]
    slug = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return f"domain/{slug}" if slug else None


def desired_labels(card: Card, body: str | None) -> list[str]:
    labels = ["kanban"]
    if card.lane in LANE_LABELS:
        labels.append(LANE_LABELS[card.lane])
    labels += [ATTENTION_LABELS[tag] for tag in card.attention_tags]
    if body:
        domain_answer = issue_body_section(body, "Domain")
        if domain_answer:
            label = domain_label_from_answer(domain_answer)
            if label:
                labels.append(label)
        priority_answer = issue_body_section(body, "Priority")
        if priority_answer and priority_answer.strip().lower() in PRIORITIES:
            labels.append(f"priority/{priority_answer.strip().lower()}")
    return list(dict.fromkeys(labels))


def desired_body(card: Card, body: str) -> str:
    """Sync the board's source-of-truth fields into the issue body so the
    served board can show the actual agent, description and evidence trace.
    Only touches the sections it owns; returns the body unchanged if none
    drift."""
    nb = body
    updates = {
        "Card ID": card.id,
        "Owner": owner_identity(card.owner),
        "Lane": card.lane or "assigned",
        "Priority": "",
        "Task": card.task,
        "Evidence plan": card.evidence,
    }
    changed = False
    for heading, content in updates.items():
        if content == "":
            continue
        if issue_body_section(nb, heading) != content:
            nb = issue_body_set_section(nb, heading, content)
            changed = True
    return nb if changed else body


def cmd_sync_issues(args: argparse.Namespace) -> int:
    state = parse_board()
    repo = args.repo or default_repo()
    if not args.apply:
        print("dry run — pass --apply to write labels + body sections\n")
    failures = 0
    touched = 0
    for card in state.open_cards:
        if not card.issue_number:
            continue
        try:
            issue = gh_json(["issue", "view", str(card.issue_number), "--repo", repo,
                             "--json", "labels,body,state"])
        except RuntimeError as exc:
            print(f"{card.id}: lookup failed — {exc}")
            failures += 1
            continue
        if issue["state"] != "OPEN":
            print(f"{card.id}: issue #{card.issue_number} is {issue['state']} — skipped")
            continue
        want = desired_labels(card, issue.get("body") or "")
        have = {entry["name"] for entry in issue["labels"]}
        missing = [label for label in want if label not in have]
        stale = [label for label in sorted(have)
                 if (label.startswith("stage/") or label.startswith("attention/"))
                 and label not in want]
        body_delta = desired_body(card, issue.get("body") or "")
        body_changed = body_delta != (issue.get("body") or "")
        if not missing and not stale and not body_changed:
            print(f"{card.id}: issue #{card.issue_number} labels + body current")
            continue
        touched += 1
        print(f"{card.id}: issue #{card.issue_number}"
              + (f" add labels {missing}" if missing else "")
              + (f" remove labels {stale}" if stale else "")
              + (" body-sync" if body_changed else ""))
        if args.apply:
            edit = ["gh", "issue", "edit", str(card.issue_number), "--repo", repo]
            for label in missing:
                edit += ["--add-label", label]
            for label in stale:
                edit += ["--remove-label", label]
            if body_changed:
                edit += ["--body", body_delta]
            result = run(edit)
            if result.returncode != 0:
                failures += 1
                print(f"  FAILED: {result.stderr.strip()}", file=sys.stderr)
    verb = "applied to" if args.apply else "would apply to"
    print(f"\n{verb} {touched} issue(s); {failures} failure(s)")
    return 1 if failures else 0


# ------------------------------------------------------- issues -> board

# Reverse sync: the served dispatch board writes through to GitHub ISSUES
# (lane moves = stage/* label changes + comments). TASKS.md stays the
# canonical board, so pull-issues imports those issue-side moves back into
# the "Lane" cell + appends a dated Evidence note. One-way, never auto-creates.


def _reverse_lane_from_issue(issue: dict) -> str | None:
    """stage/* label wins; closed issue => done; else assigned."""
    for entry in issue.get("labels") or []:
        name = entry.get("name", "")
        if "stage/" in name and name in LANE_LABELS.values():
            for lane, label in LANE_LABELS.items():
                if label == name:
                    return lane
    state_str = issue.get("state") or "open"
    return "done" if state_str == "closed" else "assigned"


def _list_kanban_issues(repo: str) -> list[dict]:
    data = gh_json(["issue", "list", "--repo", repo, "--label", "kanban",
                    "--state", "all", "--limit", "100", "--json",
                    "number,title,labels,state,updatedAt"])
    return data or []


def _card_id_from_issue(issue: dict) -> str | None:
    match = re.search(r"\b(DMR-\d{3,})\b", issue.get("title") or "", re.I)
    if match:
        return match.group(1).upper()
    if issue.get("body"):
        section = issue_body_section(issue["body"], "Card ID")
        if section:
            match = re.search(r"\b(DMR-\d{3,})\b", section, re.I)
            if match:
                return match.group(1).upper()
    return None


LANE_RE = re.compile(r"^\|\s*(DMR-\d{3,})\s*\|\s*`([a-z_]+)`")


def cmd_pull_issues(args: argparse.Namespace) -> int:
    state = parse_board()
    repo = args.repo or default_repo()
    lines = BOARD_PATH.read_text(encoding="utf-8").splitlines(keepends=True)

    issues = _list_kanban_issues(repo)
    if not issues:
        print("pull-issues: no kanban issues found (board feed empty?)", file=sys.stderr)
        return 1

    by_id: dict[str, list[dict]] = {}
    for issue in issues:
        cid = _card_id_from_issue(issue)
        if cid:
            by_id.setdefault(cid, []).append(issue)

    if not args.apply:
        print("dry run — pass --apply to write the board\n")

    drift: list[str] = []
    applied = 0
    failures: list[str] = []

    open_by_id = {c.id: c for c in state.open_cards}

    # 1. lane drift on synced open cards (issue -> board)
    for cid, card in open_by_id.items():
        if not card.issue_number:
            continue
        possibles = by_id.get(cid, [])
        issue = next((i for i in possibles if i.get("number") == card.issue_number), None)
        if issue is None:
            failures.append(f"{cid}: linked issue #{card.issue_number} missing/superseded on the kanban list")
            continue
        issue_lane = _reverse_lane_from_issue(issue)
        if issue_lane is None or issue_lane == card.lane:
            continue
        if issue_lane == "done" and card.lane != "done":
            drift.append(f"{cid}: issue #{issue['number']} CLOSED (lane done) but board says `{card.lane}` — card should move to done + archive pending")
        else:
            drift.append(f"{cid}: issue #{issue['number']} lane {issue_lane} but board says `{card.lane}`")

    # 2. issues that reference a card not on the board (orphan / duplicate / phantom)
    board_ids = {c.id for c in [*state.open_cards, *state.archived_cards]}
    for cid, issue_list in sorted(by_id.items()):
        if cid not in board_ids:
            drift.append(f"kanban issue(s) {[i['number'] for i in issue_list]} reference {cid} which is NOT on the board (orphan)")
        elif len(issue_list) > 1:
            drift.append(f"{cid}: multiple kanban issues mirror one card: {[i['number'] for i in issue_list]} — one-card-one-issue law violated")

    for entry in drift:
        print(entry)
    for entry in failures:
        print(f"FAILED  {entry}", file=sys.stderr)

    if args.apply:
        applied = 0
        for cid, card in open_by_id.items():
            if not card.issue_number:
                continue
            issue = next((i for i in by_id.get(cid, []) if i.get("number") == card.issue_number), None)
            if issue is None:
                continue
            issue_lane = _reverse_lane_from_issue(issue)
            if issue_lane is None or issue_lane == card.lane:
                continue
            row_idx = next((i for i, ln in enumerate(lines)
                            if ln.startswith(f"| {cid} |")), None)
            if row_idx is None:
                failures.append(f"{cid}: open-table row not found — cannot rewrite")
                continue
            row = lines[row_idx]
            if not LANE_RE.match(row):
                failures.append(f"{cid}: row not in a rewritable shape: {row[:60].strip()}…")
                continue
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            new_row = re.sub(r"^\|\s*(DMR-\d{3,})\s*\|\s*`[a-z_]+`",
                             rf"| \1 | `{issue_lane}`", row, count=1)
            note = f" **pull-issues {today}:** lane synced from issue #{issue['number']} (`{card.lane}` → `{issue_lane}`)"
            # Append the note to the LAST cell (Evidence), before the row's closing " |".
            new_row = new_row.rstrip()
            if new_row.endswith("|"):
                new_row = new_row[:-1].rstrip() + note + " |"
            else:
                new_row = new_row + note
            lines[row_idx] = new_row + ("\n" if not new_row.endswith("\n") else "")
            applied += 1

        if lines:
            BOARD_PATH.write_text("".join(lines), encoding="utf-8")

    verb = "applied" if args.apply else "would apply"
    print(f"\npull-issues {verb} {applied} lane rewrite(s); {len(drift)} drift line(s); {len(failures)} failure(s)")
    if drift and not args.apply:
        print("re-run with --apply to rewrite the board lanes")
    return 1 if failures else (1 if drift or applied else 0)


# ---------------------------------------------------------------- project v2


def load_project_config() -> dict:
    if not CONFIG_PATH.is_file():
        raise SystemExit(f"no {CONFIG_PATH.name} — run: python scripts/board_state.py project-init")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_project_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def find_project(owner: str, title: str) -> dict | None:
    data = gh_json(["project", "list", "--owner", owner, "--format", "json"]) or {}
    projects = data.get("projects", data if isinstance(data, list) else [])
    for project in projects:
        if project.get("title") == title:
            return project
    return None


def project_fields(number: int, owner: str) -> dict[str, dict]:
    data = gh_json(["project", "field-list", str(number), "--owner", owner, "--format", "json"]) or {}
    fields = {}
    for entry in data.get("fields", []):
        options = {opt["name"]: opt["id"] for opt in entry.get("options") or []}
        fields[entry["name"]] = {"id": entry["id"], "dataType": entry.get("dataType"), "options": options}
    return fields


def ensure_field(number: int, owner: str, fields: dict[str, dict], name: str,
                 data_type: str, options: list[str] | None) -> None:
    if name in fields:
        return
    cmd = ["project", "field-create", str(number), "--owner", owner,
           "--name", name, "--data-type", data_type]
    if options:
        cmd += ["--single-select-options", ",".join(options)]
    result = run(["gh", *cmd, "--format", "json"])
    if result.returncode != 0:
        raise SystemExit(f"field-create {name} failed: {result.stderr.strip()}")
    entry = json.loads(result.stdout)
    entry = entry.get("field") or entry
    fields[name] = {"id": entry["id"], "dataType": data_type,
                    "options": {opt["name"]: opt["id"] for opt in entry.get("options") or []}}


PROJECT_SCOPE_HINT = ("prerequisite: run `gh auth refresh -s read:project` once "
                      "(interactive; grants the Projects v2 scope)")


def cmd_project_init(args: argparse.Namespace) -> int:
    owner, title = args.owner, args.title
    try:
        project = find_project(owner, title)
    except RuntimeError as exc:
        raise SystemExit(f"{exc}\n{PROJECT_SCOPE_HINT}")
    if project is None:
        result = run(["gh", "project", "create", "--owner", owner, "--title", title, "--format", "json"])
        if result.returncode != 0:
            raise SystemExit(f"project create failed: {result.stderr.strip()}")
        project = json.loads(result.stdout)
        print(f"created project {title!r} (#{project['number']})")
    fields = project_fields(project["number"], owner)
    ensure_field(project["number"], owner, fields, "Lane", "SINGLE_SELECT", list(LANES))
    ensure_field(project["number"], owner, fields, "Owner", "TEXT", None)
    ensure_field(project["number"], owner, fields, "Card", "TEXT", None)

    save_project_config({
        "version": 1,
        "note": "Projects v2 mirror of governance/TASKS.md — written by board_state.py project-init",
        "owner": owner,
        "project_title": title,
        "project_number": project["number"],
        "project_id": project["id"],
        "fields": fields,
    })
    print(f"fields ready: Lane/Owner/Card; config written to {CONFIG_PATH.relative_to(REPO_ROOT)}")
    return 0


def item_field_values(item: dict) -> dict[str, dict]:
    values = {}
    for node in (item.get("fieldValues") or {}).get("nodes") or []:
        name = (node.get("field") or {}).get("name")
        if not name:
            continue
        if node.get("optionId"):
            values[name] = {"optionId": node["optionId"], "name": node.get("name")}
        elif node.get("text") is not None:
            values[name] = {"text": node["text"]}
        elif node.get("value") is not None:
            values[name] = {"text": node["value"]}
    return values


def cmd_project_sync(args: argparse.Namespace) -> int:
    state = parse_board()
    config = load_project_config()
    number, owner, project_id = config["project_number"], config["owner"], config["project_id"]
    try:
        fields = project_fields(number, owner)
    except RuntimeError as exc:
        raise SystemExit(f"{exc}\n{PROJECT_SCOPE_HINT}")
    lane_field, owner_field, card_field = fields.get("Lane"), fields.get("Owner"), fields.get("Card")
    if not (lane_field and owner_field and card_field):
        raise SystemExit("project lacks Lane/Owner/Card fields — re-run project-init")

    items = (gh_json(["project", "item-list", str(number), "--owner", owner,
                      "--format", "json", "--limit", "300"]) or {}).get("items", [])
    by_url = {((item.get("content") or {}).get("url") or ""): item for item in items}
    by_title = {item.get("title") or "": item for item in items}

    failures: list[str] = []
    matched_items: set[str] = set()
    plan: list[str] = []

    def apply_edits(item_id: str, edits: list[tuple[str, str, str]]) -> None:
        for field_id, flag, value in edits:
            result = run(["gh", "project", "item-edit", "--id", item_id, "--project-id", project_id,
                          "--field-id", field_id, flag, value])
            if result.returncode != 0:
                failures.append(f"item-edit {item_id} {field_id}: {result.stderr.strip()}")

    def field_edits(item: dict, want_lane: str, want_owner: str, want_card: str) -> list[tuple[str, str, str]]:
        current = item_field_values(item)
        edits: list[tuple[str, str, str]] = []
        lane_opt = lane_field["options"].get(want_lane)
        if lane_opt and current.get("Lane", {}).get("optionId") != lane_opt:
            edits.append((lane_field["id"], "--single-select-option-id", lane_opt))
        if current.get("Owner", {}).get("text", "") != want_owner:
            edits.append((owner_field["id"], "--text", want_owner))
        if current.get("Card", {}).get("text", "") != want_card:
            edits.append((card_field["id"], "--text", want_card))
        return edits

    for card in state.open_cards:
        want_owner = card.owner if card.owner not in ("", "unclaimed") else "unclaimed"
        want_lane = card.lane if card.lane in LANES else (
            "unassigned" if card.owner in ("", "unclaimed") else "assigned")
        if card.issue_url:
            item = by_url.get(card.issue_url)
            if item is None:
                plan.append(f"add issue {card.issue_url} ({card.id}, lane={want_lane})")
                if args.apply:
                    result = run(["gh", "project", "item-add", str(number), "--owner", owner,
                                  "--url", card.issue_url, "--format", "json"])
                    if result.returncode != 0:
                        failures.append(f"{card.id}: item-add failed: {result.stderr.strip()}")
                        continue
                    item = json.loads(result.stdout).get("item") or json.loads(result.stdout)
                    matched_items.add(item["id"])
                    edits = field_edits(item, want_lane, want_owner, card.id)
                    if edits:
                        plan.append(f"  set {card.id} fields ({len(edits)})")
                        apply_edits(item["id"], edits)
            else:
                matched_items.add(item["id"])
                edits = field_edits(item, want_lane, want_owner, card.id)
                if edits:
                    plan.append(f"edit {card.id} ({item.get('title', '')[:40]!r}) — {len(edits)} field(s)")
                    if args.apply:
                        apply_edits(item["id"], edits)
        else:
            match = next((t for t in by_title if t.startswith(card.id + ":") or t.startswith(card.id + " ")), None)
            if match is None:
                title = f"{card.id}: {card.task.replace('**', '').replace('`', '')[:80]}"
                plan.append(f"create draft item {title!r} (lane={want_lane})")
                if args.apply:
                    result = run(["gh", "project", "item-create", str(number), "--owner", owner,
                                  "--title", title,
                                  "--body", f"Board-only card {card.id} — source of truth: governance/TASKS.md",
                                  "--format", "json"])
                    if result.returncode != 0:
                        failures.append(f"{card.id}: item-create failed: {result.stderr.strip()}")
                        continue
                    item = json.loads(result.stdout).get("item") or json.loads(result.stdout)
                    matched_items.add(item["id"])
                    edits = field_edits(item, want_lane, want_owner, card.id)
                    if edits:
                        plan.append(f"  set {card.id} fields ({len(edits)})")
                        apply_edits(item["id"], edits)
            else:
                item = by_title[match]
                matched_items.add(item["id"])
                edits = field_edits(item, want_lane, want_owner, card.id)
                if edits:
                    plan.append(f"edit {card.id} ({match[:40]!r}) — {len(edits)} field(s)")
                    if args.apply:
                        apply_edits(item["id"], edits)

    for item in items:
        if item["id"] not in matched_items:
            plan.append(f"remove stale item {(item.get('title') or item['id'])!r} (no open card matches)")
            if args.apply:
                result = run(["gh", "project", "item-delete", "--id", item["id"],
                              "--project-id", project_id])
                if result.returncode != 0:
                    failures.append(f"item-delete {item['id']}: {result.stderr.strip()}")

    for entry in plan:
        print(entry)
    if not plan:
        print(f"project #{number} in sync with the open table ({len(state.open_cards)} cards)")
    if failures:
        for failure in failures:
            print(f"FAILED  {failure}", file=sys.stderr)
    verb = "applied" if args.apply else "would apply"
    print(f"\n{verb} {len(plan)} change(s); {len(failures)} failure(s)")
    return 1 if failures else 0


# ---------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="live board snapshot")
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=cmd_status)

    p_card = sub.add_parser("card", help="one card's full state")
    p_card.add_argument("card_id")
    p_card.add_argument("--json", action="store_true")
    p_card.add_argument("--log-limit", type=int, default=500)
    p_card.set_defaults(func=cmd_card)

    p_check = sub.add_parser("check", help="validate board invariants (exit 1 on errors)")
    p_check.add_argument("--with-issues", action="store_true", help="also verify synced issues via gh")
    p_check.add_argument("--stale-days", type=int, default=7)
    p_check.add_argument("--log-limit", type=int, default=500)
    p_check.add_argument("--strict", action="store_true", help="fail on warnings too")
    p_check.add_argument("--json", action="store_true")
    p_check.add_argument("--repo", help="OWNER/NAME for issue checks (default: git origin)")
    p_check.set_defaults(func=cmd_check)

    p_sync = sub.add_parser("sync-issues", help="apply board-derived labels to synced issues")
    p_sync.add_argument("--apply", action="store_true", help="write (default: dry run)")
    p_sync.add_argument("--repo", help="OWNER/NAME (default: git origin)")
    p_sync.set_defaults(func=cmd_sync_issues)

    p_pull = sub.add_parser("pull-issues", help="reverse-sync issue lane moves back into TASKS.md")
    p_pull.add_argument("--apply", action="store_true", help="write the board (default: dry run)")
    p_pull.add_argument("--repo", help="OWNER/NAME (default: git origin)")
    p_pull.set_defaults(func=cmd_pull_issues)

    p_init = sub.add_parser("project-init", help="create the Projects v2 mirror + fields")
    p_init.add_argument("--title", default=DEFAULT_PROJECT_TITLE)
    p_init.add_argument("--owner", default=DEFAULT_REPO.split("/")[0])
    p_init.set_defaults(func=cmd_project_init)

    p_psync = sub.add_parser("project-sync", help="mirror the open table into Projects v2")
    p_psync.add_argument("--apply", action="store_true", help="write (default: dry run)")
    p_psync.set_defaults(func=cmd_project_sync)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
