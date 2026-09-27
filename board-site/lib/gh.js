// Zero-dependency GitHub REST proxy helpers for the Kanban dispatch board.
// Auth: GITHUB_TOKEN (or MAILROOM_GH_TOKEN) Vercel secret. Repo:
// MAILROOM_GITHUB_REPO (default LLM-Mailroom-Services/Digital-Mailroom).
//
// Lane flow: unassigned → assigned → in-progress → needs-attention → done
// Issues with no stage/* label AND no assignees land in "unassigned" (triage queue).
"use strict";

const GITHUB_API = "https://api.github.com";
const LANES = [
  { id: "unassigned",  title: "Unassigned",  label: "stage/unassigned" },
  { id: "assigned",    title: "Assigned",    label: "stage/assigned" },
  { id: "in-progress", title: "In Progress", label: "stage/in-progress" },
  { id: "needs-attention", title: "Needs Attention", label: "stage/needs-attention" },
  { id: "done",        title: "Done",        label: "stage/done" },
];
const PRI_LABELS = ["priority/critical", "priority/high", "priority/medium", "priority/low"];
const STAGE_LABELS = LANES.map((l) => l.label);

// ── CORS helpers ──────────────────────────────────────────────────────
// The board is served from its own origin, so cross-origin calls are not
// needed for normal use. Allow only the known served origins (and no
// cross-origin at all for unknown ones) so a third-party website cannot use
// a visitor's browser to PATCH the board.
const ALLOWED_ORIGINS = new Set([
  "https://digital-mailroom-theta.vercel.app",
  "https://digital-mailroom-theta-lucius-projects-54efe0bb.vercel.app",
  "http://localhost:3000",
  "http://localhost:8787",
  "null",
]);
const CORS_HEADERS = {
  "Access-Control-Allow-Methods": "GET, POST, PATCH, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Mailroom-Actor",
  "Access-Control-Max-Age": "86400",
};

function cors(req, res) {
  const origin = (req.headers["origin"] || "").toString().trim();
  if (origin && !ALLOWED_ORIGINS.has(origin)) return; // no ACAO -> browser blocks
  res.setHeader("Access-Control-Allow-Origin", origin || ALLOWED_ORIGINS.values().next().value);
  for (const [k, v] of Object.entries(CORS_HEADERS)) res.setHeader(k, v);
}

class HttpError extends Error {
  constructor(status, message, extra = {}) {
    super(message);
    this.status = status;
    Object.assign(this, extra);
  }
}

class RateLimitError extends HttpError {
  constructor(retryAfterSec, message) {
    super(503, message || `GitHub rate limited — retry in ${retryAfterSec}s`, {
      rateLimited: true,
      retryAfter: retryAfterSec,
    });
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseRetryAfterSec(res) {
  const raw = res.headers.get("retry-after");
  const n = raw ? parseInt(raw, 10) : NaN;
  if (Number.isFinite(n) && n >= 0) return n;
  const reset = res.headers.get("x-ratelimit-reset");
  if (reset) {
    const sec = parseInt(reset, 10) - Math.floor(Date.now() / 1000);
    if (sec > 0) return Math.min(sec, 3600);
  }
  return 60;
}

function token() {
  const t = process.env.GITHUB_TOKEN || process.env.MAILROOM_GH_TOKEN;
  if (!t) throw new HttpError(500, "GITHUB_TOKEN not configured on the server");
  return t;
}

function repo() {
  return process.env.MAILROOM_GITHUB_REPO || "LLM-Mailroom-Services/Digital-Mailroom";
}

function actor(req) {
  const raw = (req.headers["x-mailroom-actor"] || "").toString().trim();
  return raw ? raw.slice(0, 60) : "anonymous";
}

async function gh(path, { method = "GET", body, query, _attempt = 0 } = {}) {
  let url = `${GITHUB_API}${path}`;
  if (query) {
    const qs = new URLSearchParams(query);
    if (qs.toString()) url += (url.includes("?") ? "&" : "?") + qs.toString();
  }
  const headers = {
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "mailroom-dispatch-board",
    Authorization: `Bearer ${token()}`,
  };
  const opts = { method, headers };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  let res;
  try {
    res = await fetch(url, { ...opts, signal: AbortSignal.timeout(8000) });
  } catch (err) {
    throw new HttpError(502, `GitHub unreachable: ${err.message}`);
  }
  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (_) {
      if (res.ok) {
        // Live-or-loud (DMR-061): a 2xx with a non-JSON body is not "empty" —
        // mark it so callers never treat the phantom object as real data.
        console.warn(`[gh] ${url} answered 2xx with a non-JSON body:`, text.slice(0, 200));
        return { _nonJsonBody: text.slice(0, 300) };
      }
    }
  }
  if (!res.ok) {
    const msg = (data && (data.message || JSON.stringify(data))) || `GitHub ${res.status}`;
    const rateLimited =
      res.status === 429 ||
      (res.status === 403 &&
        /rate limit/i.test(msg) &&
        (res.headers.get("x-ratelimit-remaining") === "0" || res.headers.get("retry-after")));
    if (rateLimited) {
      const waitSec = parseRetryAfterSec(res);
      if (_attempt < 2) {
        await sleep(waitSec * 1000);
        return gh(path, { method, body, query, _attempt: _attempt + 1 });
      }
      throw new RateLimitError(waitSec, `GitHub rate limited — retry in ${waitSec}s`);
    }
    throw new HttpError(res.status, msg);
  }
  if (Array.isArray(data)) {
    return data;
  }
  return data;
}

// ---- issue -> board card normalization ---------------------------------

function cardIdFromIssue(issue) {
  const t = (issue.title || "").match(/DMR-\d{3,}/i);
  if (t) return t[0].toUpperCase();
  const b = (issue.body || "").match(/DMR-\d{3,}/i);
  return b ? b[0].toUpperCase() : null;
}

// Lane detection logic:
//   1. Explicit stage/* label wins (stage/unassigned, stage/assigned, etc.)
//   2. Closed issues → done
//   3. Open issue with no stage label AND no assignees → unassigned (triage queue)
//   4. Open issue with no stage label but HAS assignees → assigned (someone claimed it)
function laneFromIssue(issue) {
  // Check for explicit stage label first
  for (const l of issue.labels || []) {
    const lane = LANES.find((x) => x.label === l.name);
    if (lane) return lane.id;
  }
  // Closed with no label = done
  if (issue.state === "closed") return "done";
  // Open, no stage label: unassigned if no one is on it, otherwise assigned
  const hasAssignees = (issue.assignees || []).length > 0;
  return hasAssignees ? "assigned" : "unassigned";
}

function priorityFromIssue(issue) {
  for (const l of issue.labels || []) if (PRI_LABELS.includes(l.name)) return l.name.split("/")[1];
  return "medium";
}

// Robust section handling: tokenize the body by `### ` headings so sections
// are never glued together or dropped (previous regex-based rewrite corrupted
// bodies on PATCH — e.g. "### Lane\ndone### Task"). Every section is rebuilt
// with a blank-line separator.
function parseSections(body) {
  // Repair bodies previously corrupted by the old glue bug: a heading glued
  // onto a section's content ("### Lane\ndone### Task") is split back out.
  const text = (body || "").replace(/([^\n])###\s/g, "$1\n### ");
  const lines = text.split("\n");
  const sections = [];
  const preamble = [];
  let cur = null;
  for (const line of lines) {
    const m = /^###\s+([^\n]+)$/.exec(line);
    if (m) {
      if (cur) sections.push(cur);
      cur = { heading: m[1].trim(), lines: [] };
    } else if (cur) {
      cur.lines.push(line);
    } else {
      preamble.push(line);
    }
  }
  if (cur) sections.push(cur);
  return {
    preamble: preamble.join("\n"),
    sections: sections.map((s) => ({ heading: s.heading, content: s.lines.join("\n").replace(/\s+$/, "") })),
  };
}

function bodySection(body, heading) {
  const { sections } = parseSections(body || "");
  const hit = sections.find((s) => s.heading.toLowerCase() === heading.toLowerCase());
  return hit ? hit.content.trim() : "";
}

function sanitizeSectionContent(content) {
  return (content || "")
    .split("\n")
    .filter((line) => !/^###\s+/.test(line))
    .join("\n")
    .trim();
}

function setBodySection(body, heading, content) {
  const clean = sanitizeSectionContent(content);
  const { preamble, sections } = parseSections(body || "");
  const idx = sections.findIndex((s) => s.heading.toLowerCase() === heading.toLowerCase());
  if (idx >= 0) sections[idx] = { heading, content: clean || "—" };
  else sections.push({ heading, content: clean || "—" });
  const rebuilt = [
    preamble.trim(),
    ...sections.map((s) => `### ${s.heading}\n${s.content}`),
  ].join("\n\n");
  return rebuilt.endsWith("\n") ? rebuilt : rebuilt + "\n";
}

// Agents reflect the actual agent/persona/harness conducting the work, which
// is carried in the issue body's "### Owner" section (synced from the board's
// Owner column). Fall back to GitHub assignees only when no Owner is present.
function agentsFromIssue(issue) {
  const owner = bodySection(issue.body, "Owner");
  if (owner && owner !== "—") {
    return owner.split(/[,;]/).map((s) => s.trim()).filter(Boolean);
  }
  return (issue.assignees || []).map((a) => a.login);
}

function toCard(issue) {
  return {
    id: cardIdFromIssue(issue),
    issueNumber: issue.number,
    title: (issue.title || "").replace(/^(?:DMR|HUB)-\d{3,}\s*:\s*/i, ""),
    desc: bodySection(issue.body, "Task"),
    lane: laneFromIssue(issue),
    priority: priorityFromIssue(issue),
    agents: agentsFromIssue(issue),
    evidence: bodySection(issue.body, "Evidence plan") || bodySection(issue.body, "Evidence"),
    date: (issue.created_at || "").slice(0, 10),
    archived: issue.state === "closed",
    createdAt: issue.created_at,
    updatedAt: issue.updated_at,
    htmlUrl: issue.html_url,
  };
}

// ── Paginated issue fetch (handles >100 issues) ────────────────────────
async function fetchAllKanbanIssues() {
  const all = [];
  let page = 1;
  while (true) {
    const batch = await gh(`/repos/${repo()}/issues`, {
      query: { labels: "kanban", state: "all", per_page: "100", page: String(page), sort: "created", direction: "asc" },
    });
    const items = Array.isArray(batch) ? batch : [];
    if (items.length === 0) break;
    all.push(...items);
    if (items.length < 100) break; // last page
    page++;
  }
  return all;
}

async function listKanbanIssues() {
  const data = await fetchAllKanbanIssues();
  return data.map(toCard).filter((c) => c.id);
}

// ── FIX: use GitHub search API for efficient single-issue lookup ──────
// Instead of listing ALL kanban issues to find one, search by title.
async function findIssueByCardId(cardId) {
  try {
    const searchResult = await gh(`/search/issues`, {
      query: {
        q: `repo:${repo()} is:issue "${cardId}" label:kanban`,
        per_page: "5",
      },
    });
    const items = searchResult.items || [];
    const hit = items.find((issue) => cardIdFromIssue(issue) === cardId);
    if (hit) {
      const issue = await gh(`/repos/${repo()}/issues/${hit.number}`);
      return issue;
    }
  } catch (err) {
    // Search API may fail on some configs; fall back to list scan — but say
    // it out loud so a dead search endpoint cannot mask itself forever.
    console.warn(`[gh] /search/issues failed for ${cardId}, falling back to the list scan:`, err.message || err);
  }
  // Fallback: scan all kanban issues (slower, but reliable)
  const cards = await listKanbanIssues();
  const fallback = cards.find((c) => c.id === cardId);
  if (!fallback) throw new HttpError(404, `no kanban issue mirrors ${cardId}`);
  const issue = await gh(`/repos/${repo()}/issues/${fallback.issueNumber}`);
  return issue;
}

async function nextCardId() {
  const data = await fetchAllKanbanIssues();
  let max = 0;
  for (const issue of data || []) {
    const m = (issue.title || "").match(/DMR-(\d{3,})/i);
    if (m) max = Math.max(max, parseInt(m[1], 10));
  }
  return `DMR-${String(max + 1).padStart(3, "0")}`;
}

/** Kanban issues whose normalized card id equals ``cardId`` (search + title match). */
async function listIssuesByCardId(cardId) {
  const want = String(cardId || "").toUpperCase();
  try {
    const searchResult = await gh(`/search/issues`, {
      query: {
        q: `repo:${repo()} is:issue "${want}" label:kanban`,
        per_page: "100",
      },
    });
    return (searchResult.items || []).filter((issue) => cardIdFromIssue(issue) === want);
  } catch (err) {
    console.warn(`[gh] listIssuesByCardId search failed for ${want}:`, err.message || err);
    const data = await fetchAllKanbanIssues();
    return (data || []).filter((issue) => cardIdFromIssue(issue) === want);
  }
}

module.exports = {
  HttpError,
  RateLimitError,
  LANES,
  PRI_LABELS,
  STAGE_LABELS,
  CORS_HEADERS,
  cors,
  repo,
  actor,
  gh,
  toCard,
  bodySection,
  setBodySection,
  agentsFromIssue,
  listKanbanIssues,
  findIssueByCardId,
  nextCardId,
  listIssuesByCardId,
};