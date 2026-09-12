"""Typed-command registry for the mailroom-tui REPL.

Each command receives a :class:`CommandContext` (fetch helpers injected from
``mailroom_console`` so tests keep monkeypatching the same names) and returns
a list of rich renderables to push into the scrollback, or one of the
``SENTINEL_*`` constants for REPL-level actions (clear, quit, live desk).
Completion candidates and man pages live here too.
"""

from __future__ import annotations

import datetime
import shlex
from collections import deque
from typing import Any, Callable, Optional

from rich.text import Text

from tui import repos as repos_mod
from tui import views
from tui.corpus import CorpusClient, CorpusClosed, SlimRow
from tui.repos import all_repos, live_meta, lookup, open_repo

# REPL-level sentinels.
CLEAR = object()
QUIT = object()
DESK_FLOOR = object()

NEOFETCH = r"""
                 ___ ___
                /   /   \
               /   /     \
              /___/       \
              \   \       /
               \   \     /
                \___\___/
      the llm-mailroom    __
     _____________       |  |
    /             \      |  |    every file lands here,
   /  IN    OUT   /____  |  |    every decision is sealed,
   \_____________/    |  |  |    every run is traced.
                    |__|__|
"""

NEED_NETWORK = {
    "corpus": "reads Lucius-Morningstar/mailroom-dataset from the Hub "
              "(datasets-server; slim catalog for listing, live per-row "
              "doc_text + ground truth).",
    "repos": "lists the LLM-Mailroom constellation repos (bundled blurbs "
             "offline; live GitHub metadata when reachable).",
    "open": "opens a repo or URL in the default browser.",
}

MAN_PAGES: dict[str, str] = {
    "help": """HELP(1)

NAME
    help - this registry

SYNOPSIS
    help [command]

DESCRIPTION
    With no argument prints the command list. With a command name,
    prints that command's manual entry.

EXAMPLES
    help
    help corpus""",
    "man": """MAN(1)

NAME
    man - read a command's manual

SYNOPSIS
    man <command>

DESCRIPTION
    Prints the manual entry for a command. Alias of 'help <cmd>'.

EXAMPLES
    man corpus
    man floor""",
    "floor": """FLOOR(1)

NAME
    floor - enter the live pipeline floor desk

SYNOPSIS
    floor

DESCRIPTION
    Enters the live floor desk: an auto-refreshing table of every
    run in the recent window with AgentLab-style banners logged as
    runs arrive or advance stages. Type 'q' (or 'quit') to return
    to the prompt.

    Honor 'filter' constraints (filter stage=archived etc.).

EXAMPLES
    floor
    filter stage=review
    floor""",
    "review": """REVIEW(1)

NAME
    review - runs waiting on a human

SYNOPSIS
    review

DESCRIPTION
    Prints the review siding: needs_human runs with their
    escalation reasons / failure classes. Resolve a run with:

      mailroom-tui --resolve TRACE --decision approved [--doc-type X]

    or in the web UI / Observatory.""",
    "sessions": """SESSIONS(1)

NAME
    sessions - Langfuse matters

SYNOPSIS
    sessions

DESCRIPTION
    Prints Langfuse sessions (matters) with trace counts and the
    latest run per session.""",
    "metrics": """METRICS(1)

NAME
    metrics - aggregate dashboard

SYNOPSIS
    metrics

DESCRIPTION
    Prints window aggregates: counts by stage and verdict, cost,
    tokens, latencies, average quality, and the suite extra scores
    (verified precision, topic/sentiment accuracy, MAUD).""",
    "inspect": """INSPECT(1)

NAME
    inspect - drill into one trace

SYNOPSIS
    inspect <trace-id>

DESCRIPTION
    Fetches the full trace detail (spans, LLM generations, scores)
    and prints the RUN / OBSERVATIONS / LLM GENERATIONS / SCORES
    panels.

EXAMPLES
    inspect demo-x
    floor   (find a trace id)
    inspect <that id>""",
    "debug": """DEBUG(1)

NAME
    debug - fetch / WS error ring

SYNOPSIS
    debug

DESCRIPTION
    Prints the last recorded fetch / WebSocket errors, plus a pull
    of /api/debug/bundle when the server is reachable.""",
    "filter": """FILTER(1)

NAME
    filter - constrain the floor desk

SYNOPSIS
    filter [stage=X] [class=X] [env=X]
    filter clear

DESCRIPTION
    Sets filters applied to the live floor desk and the floor
    table. Each argument names a field and value:

      stage=archived   only runs at that stage
      class=contract   only runs of that doc type
      env=prod         only runs in that environment

    'filter' with no arguments prints the active filters;
    'filter clear' removes them all.""",
    "corpus": """CORPUS(1)

NAME
    corpus - browse the mailroom-dataset Hub dataset

SYNOPSIS
    corpus ls [--class X] [--split train|test] [--page N] [--limit N]
    corpus show <filename>
    corpus search <term> [--split X] [--limit N]
    corpus stats

DESCRIPTION
    Views Lucius-Morningstar/mailroom-dataset (3,302 rows).

      ls       slim listing from the catalog (filename, split,
               class, subclass, sha256, chars) — instant once the
               catalog is built
      show     full document text + ground-truth fields for one
               file (fetched live from the Hub)
      search   match term against filename / class / subclass
      stats    row counts per split and per doc class

    The Hub being unreachable is an explicit closed state — never
    canned data.

EXAMPLES
    corpus ls --class insurance_claim --limit 25
    corpus show enron_sample_003.htm
    corpus search correspondence
    corpus stats""",
    "repos": """REPOS(1)

NAME
    repos - browse the LLM-Mailroom constellation

SYNOPSIS
    repos ls
    repos <name>
    open <name>

DESCRIPTION
    Lists the standalone Exios66 repos that make up the
    constellation (pipeline, visualizer, scoring, eval, sandbox,
    corpus feeds, derived graph sites, hub). Each entry carries a
    bundled blurb and, when GitHub is reachable, live metadata
    (description, stars, language, updated). 'open' jumps to the
    repo page in your browser.

EXAMPLES
    repos ls
    repos llm-mailroom
    open llm-dojo-scoring""",
    "open": """OPEN(1)

NAME
    open - open a repo or URL in the browser

SYNOPSIS
    open <name-or-url>

DESCRIPTION
    With a constellation repo name, opens its GitHub page. With a
    URL, opens that URL.""",
    "neofetch": """NEOFETCH(1)

NAME
    neofetch - the mailroom ASCII banner

SYNOPSIS
    neofetch""",
    "clear": """CLEAR(1)

NAME
    clear - clear the scrollback

SYNOPSIS
    clear

DESCRIPTION
    Also Ctrl+L.""",
    "history": """HISTORY(1)

NAME
    history - command history

SYNOPSIS
    history

DESCRIPTION
    Prints the commands typed this session (up to 200). Arrows
    recall them.""",
    "date": """DATE(1)

NAME
    date - current date and time

SYNOPSIS
    date""",
    "echo": """ECHO(1)

NAME
    echo - print text back

SYNOPSIS
    echo <text>""",
    "uname": """UNAME(1)

NAME
    uname - system name

SYNOPSIS
    uname""",
    "whoami": """WHOAMI(1)

NAME
    whoami - who you are

SYNOPSIS
    whoami""",
    "quit": """QUIT(1)

NAME
    quit, exit - leave the TUI

SYNOPSIS
    quit""",
    "exit": """EXIT(1)

NAME
    exit, quit - leave the TUI

SYNOPSIS
    exit""",
}


class CommandContext:
    """Everything a command may touch, injected by the REPL."""

    def __init__(self) -> None:
        self.fetch: Callable[..., Optional[dict]] = lambda *a, **k: None
        self.fetch_list: Callable[..., Optional[list]] = lambda *a, **k: None
        self.fetch_floor_runs: Callable[..., Optional[list]] = lambda *a, **k: None
        self.fetch_snapshot: Callable[..., Optional[list]] = lambda *a, **k: None
        self.api_base = "http://127.0.0.1:8001"
        self.window_s = 604800
        self.corpus = CorpusClient()
        self.runs: list[dict] = []
        self.log: "deque[str]" = deque(maxlen=200)
        self.pipeline: dict = {}
        self.filters: dict[str, Optional[str]] = {
            "stage": None, "class": None, "env": None,
        }


def _print_filtered_runs(ctx: CommandContext) -> list[dict]:
    runs = ctx.runs
    f = ctx.filters
    if f["stage"]:
        runs = [r for r in runs if r.get("stage") == f["stage"]]
    if f["class"]:
        runs = [r for r in runs if (r.get("doc_type") or "") == f["class"]]
    if f["env"]:
        runs = [r for r in runs if (r.get("environment") or "") == f["env"]]
    return runs


def _flag(args: list[str], name: str, default: Optional[str] = None,
          consumed: Optional[set[str]] = None) -> Optional[str]:
    """Extract ``--name value`` (or ``--name=value``) from an arg list."""
    for i, a in enumerate(args):
        if a == name or a.startswith(name + "="):
            value = a.split("=", 1)[1] if "=" in a else (args[i + 1] if i + 1 < len(args) else None)
            if consumed is not None:
                consumed.add(i)
                if value is not None:
                    consumed.add(i + 1)
            return value
    return default


def _clean_args(args: list[str], consumed: set[str]) -> list[str]:
    return [a for i, a in enumerate(args) if i not in consumed]


def cmd_help(ctx: CommandContext, args: list[str]) -> list[Any]:
    if args:
        name = args[0]
        if name in MAN_PAGES:
            return [Text(MAN_PAGES[name], style="grey85")]
        return [Text(f"no manual for '{name}' — try: help", style="yellow")]
    lines = ["Available commands:"]
    for name in sorted(_COMMANDS):
        if name in ("quit", "exit", "open"):
            continue
        first = MAN_PAGES.get(name, "").split("\n")
        syn = ""
        for line in first:
            if line.strip().startswith(("NAME", "SYNOPSIS", "DESCRIPTION", "EXAMPLES")):
                continue
            if line.strip():
                syn = line.strip()
                break
        lines.append(f"  {name:<12} {syn or ''}")
    lines.append("")
    lines.append("Keys: Tab complete · ↑/↓ history · Ctrl+L clear · Ctrl+C cancel")
    lines.append("      q quit (from the floor desk)")
    return [Text("\n".join(lines), style="grey85")]


def cmd_floor(ctx: CommandContext, args: list[str]) -> list[Any]:
    return [DESK_FLOOR]


def cmd_review(ctx: CommandContext, args: list[str]) -> list[Any]:
    rev = ctx.fetch_list(f"/api/review-queue?since={ctx.window_s}")
    if rev is None:
        return [views.empty_hint("review queue unavailable — see [d]ebug")]
    return [views.review_table(rev)]


def cmd_sessions(ctx: CommandContext, args: list[str]) -> list[Any]:
    payload = ctx.fetch("/api/sessions?limit=50")
    if payload is None:
        return [views.empty_hint("sessions unavailable")]
    return [views.sessions_table(payload)]


def cmd_metrics(ctx: CommandContext, args: list[str]) -> list[Any]:
    m = ctx.fetch(f"/api/metrics?since={ctx.window_s}")
    if m is None:
        return [views.empty_hint("metrics unavailable")]
    return [views.metrics_table(m)]


def cmd_inspect(ctx: CommandContext, args: list[str]) -> list[Any]:
    if not args:
        return [Text("usage: inspect <trace-id>", style="yellow")]
    detail = ctx.fetch(f"/api/traces/{args[0]}")
    if detail is None or detail.get("error"):
        return [views.empty_hint(f"trace {args[0]} unavailable")]
    return views.inspect_panels(detail)


def cmd_debug(ctx: CommandContext, args: list[str]) -> list[Any]:
    return [views.debug_panel()]


def cmd_filter(ctx: CommandContext, args: list[str]) -> list[Any]:
    if args and args[0] == "clear":
        ctx.filters = {"stage": None, "class": None, "env": None}
        return [Text("filters cleared", style="green")]
    if not args:
        active = {k: v for k, v in ctx.filters.items() if v}
        if not active:
            return [Text("no active filters", style="dim")]
        return [Text("active: " + "  ".join(f"{k}={v}" for k, v in active.items()),
                     style="cyan")]
    for arg in args:
        if "=" not in arg:
            return [Text(f"bad filter '{arg}' — use key=value (stage/class/env)",
                         style="yellow")]
        key, value = arg.split("=", 1)
        if key not in ctx.filters:
            return [Text(f"unknown filter '{key}' — stage/class/env", style="yellow")]
        ctx.filters[key] = value or None
    return [Text("filter set: " + "  ".join(
        f"{k}={v}" for k, v in ctx.filters.items() if v), style="green")]


def cmd_corpus(ctx: CommandContext, args: list[str]) -> list[Any]:
    if not args:
        return [Text(MAN_PAGES["corpus"], style="grey85")]
    sub = args[0]
    rest = args[1:]
    try:
        if sub == "ls":
            consumed: set[str] = set()
            cls = _flag(rest, "--class", consumed=consumed)
            split = _flag(rest, "--split", consumed=consumed)
            page = int(_flag(rest, "--page", "0", consumed=consumed) or "0")
            limit = int(_flag(rest, "--limit", "25", consumed=consumed) or "25")
            rest = _clean_args(rest, consumed)
            if rest:
                return [Text(f"unexpected args: {' '.join(rest)}", style="yellow")]
            if cls or split:
                # Class filtering needs the full slim catalog (classes live on
                # the GT config) — one-time build, cached for the session.
                rows = ctx.corpus.catalog()
                if cls:
                    rows = [r for r in rows if r.doc_class == cls]
                if split:
                    rows = [r for r in rows if r.split == split]
                start = page * limit
                page_rows = rows[start:start + limit]
                if not page_rows:
                    return [Text(f"no corpus rows (page {page}, filtered to {len(rows)})",
                                 style="yellow")]
                return [views.corpus_table(page_rows)]
            # Plain paging is windowed: two requests per page, instant —
            # never pays for the full-corpus build.
            page_rows: list[SlimRow] = []
            for s in (split or ("train", "test")) if split else ("train", "test"):
                start = page * limit
                page_rows.extend(ctx.corpus.window(s, start, limit))
            if not page_rows:
                return [Text(f"no corpus rows on page {page}", style="yellow")]
            return [views.corpus_table(page_rows)]
        if sub == "show":
            if not rest:
                return [Text("usage: corpus show <filename>", style="yellow")]
            filename = rest[0]
            slim = ctx.corpus.find(filename)
            if slim is None:
                return [Text(f"'{filename}' not in the corpus catalog",
                             style="yellow")]
            row = ctx.corpus.row(filename)
            gt = ctx.corpus.gt_row(filename)
            return views.corpus_detail_panels(slim, row, gt)
        if sub == "search":
            consumed = set()
            split = _flag(rest, "--split", consumed=consumed)
            limit = int(_flag(rest, "--limit", "20", consumed=consumed) or "20")
            rest = _clean_args(rest, consumed)
            if not rest:
                return [Text("usage: corpus search <term> [--split X] [--limit N]",
                             style="yellow")]
            hits = ctx.corpus.search(" ".join(rest), split=split, limit=limit)
            if not hits:
                return [Text("no matches in the slim catalog (filename/class/subclass)",
                             style="yellow")]
            return [views.corpus_table(hits, title=f"CORPUS SEARCH — {rest[0]}")]
        if sub == "stats":
            return [views.corpus_stats_table(ctx.corpus.split_counts(),
                                             ctx.corpus.class_counts())]
        return [Text(f"unknown corpus subcommand '{sub}' — ls|show|search|stats",
                     style="yellow")]
    except CorpusClosed as exc:
        views.LAST_ERRORS.append(f"corpus: {exc}")
        return [views.empty_hint("corpus closed — Hub datasets-server unreachable "
                                 "(see debug)")]


def cmd_repos(ctx: CommandContext, args: list[str]) -> list[Any]:
    if args and args[0] in ("ls", "list"):
        args = args[1:]
    if args:
        repo = lookup(args[0])
        if repo is None:
            return [Text(f"no constellation repo '{args[0]}' — try: repos ls",
                         style="yellow")]
        return [views.repo_panel(repo, live_meta(repo["name"]))]
    rows = []
    for repo in all_repos():
        meta = live_meta(repo["name"])
        rows.append({**repo, "live_description": (meta or {}).get("description")})
    return [views.repos_table(rows)]


def cmd_open(ctx: CommandContext, args: list[str]) -> list[Any]:
    if not args:
        return [Text("usage: open <repo-name|url>", style="yellow")]
    target = args[0]
    if target.startswith(("http://", "https://")):
        import webbrowser
        webbrowser.open(target)
        return [Text(f"opened {target}", style="green")]
    repo = lookup(target)
    if repo is None:
        return [Text(f"no constellation repo '{target}' — try: repos ls",
                     style="yellow")]
    if open_repo(repo["name"]):
        return [Text(f"opened {repo['name']} -> {repo['url']}", style="green")]
    return [Text(f"could not open {repo['name']}", style="yellow")]


def cmd_neofetch(ctx: CommandContext, args: list[str]) -> list[Any]:
    line = Text()
    line.append(NEOFETCH, style="cyan")
    line.append("\n  mailroom@floor — llm-mailroom visual engine\n", style="bold white")
    line.append(f"  api: {ctx.api_base}   window: {ctx.window_s}s\n", style="grey50")
    return [line]


def cmd_history(ctx: CommandContext, args: list[str]) -> list[Any]:
    lines = [f"  {i + 1:>3}  {c}" for i, c in enumerate(ctx.history)]
    if not lines:
        return [Text("(no history yet)", style="dim")]
    return [Text("\n".join(lines[-40:]), style="grey85")]


def cmd_date(ctx: CommandContext, args: list[str]) -> list[Any]:
    return [Text(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z"),
                 style="cyan")]


def cmd_echo(ctx: CommandContext, args: list[str]) -> list[Any]:
    return [Text(" ".join(args))]


def cmd_uname(ctx: CommandContext, args: list[str]) -> list[Any]:
    return [Text("mailroom-tui — the llm-mailroom visual engine", style="green")]


def cmd_whoami(ctx: CommandContext, args: list[str]) -> list[Any]:
    return [Text("you are the human at the mailroom console — every run you "
                 "see was traced through Langfuse.", style="grey85")]


def cmd_clear(ctx: CommandContext, args: list[str]) -> list[Any]:
    return [CLEAR]


def cmd_quit(ctx: CommandContext, args: list[str]) -> list[Any]:
    return [QUIT]


_COMMANDS: dict[str, Callable[[CommandContext, list[str]], list[Any]]] = {
    "help": cmd_help,
    "man": cmd_help,
    "floor": cmd_floor,
    "review": cmd_review,
    "sessions": cmd_sessions,
    "metrics": cmd_metrics,
    "inspect": cmd_inspect,
    "debug": cmd_debug,
    "filter": cmd_filter,
    "corpus": cmd_corpus,
    "repos": cmd_repos,
    "open": cmd_open,
    "neofetch": cmd_neofetch,
    "history": cmd_history,
    "date": cmd_date,
    "echo": cmd_echo,
    "uname": cmd_uname,
    "whoami": cmd_whoami,
    "clear": cmd_clear,
    "quit": cmd_quit,
    "exit": cmd_quit,
}


def run_command(ctx: CommandContext, line: str) -> list[Any]:
    """Parse one typed line and return renderables / sentinels."""
    try:
        parts = shlex.split(line)
    except ValueError as exc:
        return [Text(f"parse error: {exc}", style="yellow")]
    if not parts:
        return []
    name = parts[0]
    handler = _COMMANDS.get(name)
    if handler is None:
        return [Text(f"{name}: command not found — try 'help'", style="bright_red")]
    return handler(ctx, parts[1:])


def completion_candidates(ctx: CommandContext, line: str) -> list[str]:
    """Candidates for the last word of ``line`` (for Tab completion)."""
    parts = line.split()
    trailing = line.endswith(" ")
    if not parts:
        return sorted(_COMMANDS)
    name = parts[0]
    if len(parts) == 1 and not trailing:
        prefix = parts[0]
        return [c for c in sorted(_COMMANDS) if c.startswith(prefix)]
    word = "" if trailing else parts[-1]
    if name == "corpus":
        subs = ["ls", "show", "search", "stats"]
        if len(parts) == 1 or (len(parts) == 2 and trailing):
            return [s for s in subs if s.startswith(word)]
        if len(parts) == 2:
            return [s for s in subs if s.startswith(parts[1])]
        if parts[1] == "ls":
            flags = ["--class", "--split", "--page", "--limit"]
            return [f for f in flags if f.startswith(word)]
        if parts[1] == "show" or parts[1] == "search":
            try:
                rows = ctx.corpus.window("train", 0, 50)
            except CorpusClosed:
                return []
            return [r.filename for r in rows
                    if r.filename.startswith(word)]
        return []
    if name == "repos" or name == "open":
        return [r["name"] for r in all_repos()
                if r["name"].startswith(word)]
    if name == "inspect":
        return [r.get("trace_id") or "" for r in ctx.runs
                if (r.get("trace_id") or "").startswith(word)]
    if name == "help" or name == "man":
        return [c for c in sorted(_COMMANDS) if c.startswith(word)]
    if name == "filter":
        keys = ["stage=", "class=", "env="]
        if word.startswith(("stage=", "class=", "env=")):
            return []
        return [k for k in keys if k.startswith(word)]
    return []


def command_names() -> list[str]:
    return sorted(_COMMANDS)