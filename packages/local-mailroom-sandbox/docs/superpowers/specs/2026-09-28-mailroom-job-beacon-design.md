# Mailroom job beacon + board — design

**Goal:** any long job in the mailroom package family publishes live progress that one persistent,
mailroom-themed display (browser + terminal TUI) shows and keeps updating — surviving job restarts,
showing stalls, keeping finished jobs as history. Approved scope (2026-09-28): this repo + sibling repos
reachable locally (eval-environment). The-Mailroom is excluded: its doctrine makes Langfuse the sole
display source (no local data). mailroom-ml is not checked out here.

## Protocol — `mailroom.beacon/v1`
- Root: `$MAILROOM_BEACON_DIR`, default `~/.mailroom/jobs/`.
- `<job_id>.json` (atomic tmp+rename): `schema, job_id, package, title, phase, state (running|done|failed),
  done, total, ok, errors, metrics{}, started_at, updated_at, finished_at, pid, host`.
- `<job_id>.log`: appended lines; readers show the tail.
- Writer (`beacon.py`, stdlib-only, single file, vendorable): `Beacon(job_id, package, title=...)`,
  `.update(**fields)`, `.log(line)`, `.finish(state)`, context manager (exception → `failed`).
  **A beacon never raises into the job** (all IO guarded).

## Board — `sandbox board`
- Derived status: `running`, `stalled` (running but `updated_at` older than `--stale-s`, default 120, or
  same-host pid gone), `done`, `failed`. Sorted live → stalled → finished (newest first).
- Browser: `http://127.0.0.1:8767/` job cards (theme from `pretty_log` via `tui/web.THEME`, terminal hero),
  SSE `/api/jobs/stream`, JSON `/api/jobs`. Localhost-only by default.
- Terminal: `sandbox board --tui` (live, alt-screen) / `--once` — `pretty_log` boxes + progress bars.
- `sandbox board --demo` adds a synthetic job writer (no Modal, no spend) for dev/browser testing.
- Persistence across reboots: `deploy/launchd/com.mailroom.board.plist` template (user installs).

## Wiring
- local-mailroom-sandbox: `job.runner.run` wraps `on_event` → one beacon per `sandbox run start` job
  (`job_id` = run_id); finish on terminal state. `sandbox beacon update …` for shell jobs.
- eval-environment: vendored `src/evals/beacon.py` (sha-pinned header), `_execute_cases` updates per
  completed case; `run_task` finishes it.

## Testing
Writer atomicity/never-raises/context manager; board status derivation (stale by age and dead pid),
ordering, log tail; HTTP `/`, `/api/jobs`, SSE, 404; TUI frame render; CLI wiring (`board`, `beacon`);
runner emits and finishes a beacon; eval-environment case loop emits. Browser-verify board + demo.
