<div align="center">

# 💻 The-Mailroom TUI

**A typed-command REPL console for the llm-mailroom pipeline.**

</div>

---

## Purpose

`mailroom-tui` is a terminal console over the same display API the web UI
serves — every trace value is Langfuse-derived, and corpus views read
`Lucius-Morningstar/mailroom-dataset` from the Hub. AgentLab-style banners,
per-doc tables, corpus browsing, and the constellation repo browser, all
from a `mailroom@floor:~$` prompt.

## Running

```bash
cd packages/The-Mailroom
pip install -e ".[dev]"
mailroom-tui                       # REPL (needs a running server or MAILROOM_API_URL)
mailroom-tui --once --view corpus  # single frame for scripting/CI
```

## REPL commands

| command | what it does |
|---|---|
| `help` / `man <cmd>` | command list / manual entry |
| `floor` | live floor desk — auto-refreshing table + banner log (`q` to leave) |
| `review` / `sessions` / `metrics` | Langfuse-derived desks |
| `inspect <trace>` | drill into one run (spans, generations, scores) |
| `debug` | fetch/WS error ring |
| `filter stage=… class=… env=…` | constrain the floor desk (`filter clear`) |
| `corpus ls [--class X] [--split X] [--page N] [--limit N]` | browse the Hub dataset (windowed — instant) |
| `corpus show <filename>` | live doc_text + ground-truth for one file |
| `corpus search <term> [--split X]` | match filename / class / subclass |
| `corpus stats` | rows per split and per doc class |
| `repos ls` / `repos <name>` | the LLM-Mailroom constellation (13 repos) |
| `open <name-or-url>` | open a repo/URL in the browser |
| `neofetch` / `date` / `echo` / `uname` / `whoami` | the small stuff |
| `clear` / `history` / `quit` | REPL life |

Keys: Tab completes · ↑/↓ recall history · Ctrl+L clears · Ctrl+C cancels
the line. `--once --view floor|review|metrics|sessions|inspect|debug|corpus|repos`
renders a single frame for scripting. `--resolve` / `--source` keep the
review workflow CLI (posted through the visualizer to the producer).

## Layout

- `mailroom_console.py` — entry, REPL loop (rich live frame), line editor,
  fetch helpers (re-exported so legacy imports/tests keep working)
- `commands.py` — command registry, completion candidates, man pages
- `views.py` — pure renderers (floor/review/metrics/sessions/inspect/
  corpus/repos/debug)
- `corpus.py` — Hub corpus client over `mailroom_ui/hf_corpus.py`
  (windowed paging, slim catalog, per-row live fetches, LRU)
- `repos.py` — constellation manifest + fail-soft GitHub metadata

## Related Files

- `web/` — Pixel console (CRT canvas)
- `hosted/` — Observatory (hosted edition)
- `terminal/` — the owlcot-style terminal site on GH Pages (`/terminal/`)
- `server/` — Backend server