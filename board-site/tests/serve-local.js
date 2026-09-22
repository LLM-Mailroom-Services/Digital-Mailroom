// board-site local serve harness — reproducible local API/UI checks (hub#110).
//
// Starts the REAL board-site API handlers (api/board.js + api/board/[id].js)
// behind a plain Node http server and serves the frontend (index.html) from
// the same origin — no Vercel, no GitHub credentials. Outbound GitHub calls
// are stubbed with the same canned-issue pattern as tests/api.test.js, so
// the GET/POST/PATCH contract (200/201/400/405/413, no-store) is exercised
// hermetically on loopback AND on the LAN (default bind 0.0.0.0, port 8787 —
// one of the origins already allowlisted in lib/gh.js).
//
// Run (from board-site/):
//   node tests/serve-local.js                # serve + static frontend
//   node tests/serve-local.js --port 8788    # different port
//   node tests/serve-local.js --smoke        # self-check, then exit 0/1
//
// --smoke proves: GET /api/board -> 200 cards; create-lane 400 -> the exact
// documented error body; valid create -> 201; frontend -> 200 html.
"use strict";

const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const os = require("node:os");

// Hermetic GitHub backend: no credentials needed. Mirrors tests/api.test.js.
process.env.GITHUB_TOKEN = process.env.GITHUB_TOKEN || "serve-local-stub";
process.env.MAILROOM_GITHUB_REPO = process.env.MAILROOM_GITHUB_REPO
  || "LLM-Mailroom-Services/Digital-Mailroom";

const ghx = require("../lib/gh.js");
const boardHandler = require("../api/board.js");
const cardHandler = require("../api/board/[id].js");

// ---- fetch stub (canned issues, same shape as api.test.js) ------------
const ISSUES = new Map();

function issueRecord(n, over = {}) {
  const id = `DMR-${String(n).padStart(3, "0")}`;
  return {
    number: n,
    state: "open",
    title: `${id}: task ${n}`,
    body: `### Card ID\n\n${id}\n\n### Lane\n\nunassigned\n\n### Priority\n\nmedium\n\n### Task\n\n—\n\n### Evidence plan\n\n—`,
    labels: [],
    assignees: [],
    created_at: "2026-09-13T00:00:00Z",
    updated_at: "2026-09-13T00:00:00Z",
    html_url: `https://github.com/LLM-Mailroom-Services/Digital-Mailroom/issues/${n}`,
    ...over,
  };
}

// Seed: one unassigned card, one assigned card (stage label + Owner section).
ISSUES.set(1, issueRecord(1));
ISSUES.set(2, issueRecord(2, {
  title: "DMR-002: claimed task",
  body: `### Card ID\n\nDMR-002\n\n### Lane\n\nassigned\n\n### Priority\n\nhigh\n\n### Task\n\n—\n\n### Evidence plan\n\n—\n\n### Owner\n\nlucius`,
  labels: [{ name: "stage/assigned" }, { name: "priority/high" }, { name: "kanban" }],
  assignees: [],
}));

function asGithubLabels(raw) {
  // The API hands the stub plain label strings; GitHub serves {name} objects
  // and laneFromIssue/priorityFromIssue read l.name — normalize like GitHub.
  return (raw || []).map((l) => (typeof l === "string" ? { name: l } : l));
}

global.fetch = async (url, opts = {}) => {
  const method = opts.method || "GET";
  const body = opts.body ? JSON.parse(opts.body) : null;
  const u = new URL(String(url));
  const pathname = u.pathname;

  // search/issues: findIssueByCardId probe
  if (pathname.endsWith("/search/issues")) {
    return jsonResponse(200, { items: [...ISSUES.values()] });
  }
  // issues list (nextCardId / listKanbanIssues / plain GET)
  if (/\/issues$/.test(pathname)) {
    if (method === "POST") {
      const match = (body.title || "").match(/DMR-(\d{3,})/i);
      const n = match ? parseInt(match[1], 10) : ISSUES.size + 1;
      const rec = issueRecord(n, {
        title: body.title, body: body.body || "", labels: asGithubLabels(body.labels), state: "open",
      });
      ISSUES.set(n, rec);
      return jsonResponse(201, rec);
    }
    return jsonResponse(200, [...ISSUES.values()]);
  }
  // issues/{n}
  const m = pathname.match(/\/issues\/(\d+)$/);
  if (m) {
    const n = parseInt(m[1], 10);
    if (!ISSUES.has(n)) return jsonResponse(404, { message: "Not Found" });
    if (method === "PATCH") {
      const rec = ISSUES.get(n);
      if (body.labels !== undefined) rec.labels = asGithubLabels(body.labels);
      if (body.title !== undefined) rec.title = body.title;
      if (body.body !== undefined) rec.body = body.body;
      if (body.state !== undefined) rec.state = body.state;
      return jsonResponse(200, rec);
    }
    return jsonResponse(200, ISSUES.get(n));
  }
  // lane-move mirror comments
  if (/\/issues\/\d+\/comments$/.test(pathname) && method === "POST") {
    return jsonResponse(201, { id: 1 });
  }
  return jsonResponse(404, { message: `no stub for ${pathname}` });
};

function jsonResponse(status, data) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: new Map([["etag", '"x"']]),
    text: async () => JSON.stringify(data),
  };
}

// ---- server ------------------------------------------------------------
const ROOT = path.join(__dirname, "..");
const INDEX = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");

function send(res, status, contentType, body) {
  res.statusCode = status;
  res.setHeader("Content-Type", contentType);
  res.setHeader("Cache-Control", "no-store"); // live-only: the proxy never caches
  res.end(body);
}

function createServer() {
  return http.createServer((req, res) => {
    const url = String(req.url || "");
    const pathname = url.split("?")[0];

    if (pathname === "/" || pathname === "/index.html") {
      return send(res, 200, "text/html; charset=utf-8", INDEX);
    }
    if (pathname === "/lib/md.js") {
      // Client-side markdown helper (board-site/lib/md.js → window.mdToHtml).
      const md = fs.readFileSync(path.join(ROOT, "lib", "md.js"), "utf8");
      return send(res, 200, "text/javascript; charset=utf-8", md);
    }
    // Vercel-only probes — absent locally; answer empty so the board renders
    // without console noise (never fabricates analytics).
    if (pathname.startsWith("/_vercel/")) {
      return send(res, 204, "text/plain", "");
    }
    if (pathname === "/api/board") {
      return boardHandler(req, res).catch((err) =>
        send(res, err.status || 500, "application/json; charset=utf-8",
          JSON.stringify({ error: err.message || String(err) })));
    }
    if (pathname.startsWith("/api/board/")) {
      return cardHandler(req, res).catch((err) =>
        send(res, err.status || 500, "application/json; charset=utf-8",
          JSON.stringify({ error: err.message || String(err) })));
    }
    return send(res, 404, "text/plain; charset=utf-8", "not found");
  });
}

function lanUrls() {
  const out = [];
  try {
    for (const infos of Object.values(os.networkInterfaces())) {
      for (const info of infos || []) {
        if (info.family === "IPv4" && !info.internal) out.push(`http://${info.address}:`);
      }
    }
  } catch (_e) { /* no LAN info available */ }
  return out;
}

// ---- --smoke self-check ------------------------------------------------
function httpGet(port, pathname, opts = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request({ host: "127.0.0.1", port, path: pathname, method: opts.method || "GET", headers: { "content-type": "application/json", "x-mailroom-actor": "serve-local-smoke" } }, (res) => {
      let data = "";
      res.on("data", (c) => { data += c; });
      res.on("end", () => resolve({ status: res.statusCode, headers: res.headers, body: data }));
    });
    req.on("error", reject);
    if (opts.body !== undefined) req.write(JSON.stringify(opts.body));
    req.end();
  });
}

async function smoke(port) {
  const checks = [];
  const ok = (name, cond, extra = "") => {
    checks.push(cond);
    console.log(`${cond ? "ok" : "FAIL"} - ${name}${extra ? ` (${extra})` : ""}`);
  };

  // 1. GET /api/board -> 200 + schema + both seeded cards
  const board = await httpGet(port, "/api/board");
  const parsed = JSON.parse(board.body);
  ok("GET /api/board returns 200 with no-store", board.status === 200
    && /no-store/.test(board.headers["cache-control"] || ""), `status=${board.status}`);
  ok("GET /api/board lists seeded cards", board.status === 200
    && parsed.schema === 1 && parsed.cards.length === 2
    && parsed.cards[0].id === "DMR-001" && parsed.cards[1].lane === "assigned");

  // 2. POST create-lane 400 -> the EXACT documented error body
  const bad = await httpGet(port, "/api/board", { method: "POST", body: { title: "smoke", lane: "in-progress" } });
  const want = JSON.stringify({ error: "invalid lane", allowed: ["unassigned", "assigned"] });
  ok("POST work lane rejected 400 with documented error body", bad.status === 400 && bad.body === want,
    `body=${bad.body}`);

  // 3. POST valid create -> 201 (unassigned default)
  const good = await httpGet(port, "/api/board", { method: "POST", body: { title: "smoke", priority: "high", desc: "smoke card" } });
  ok("POST valid create returns 201 unassigned", good.status === 201
    && JSON.parse(good.body).lane === "unassigned" && JSON.parse(good.body).priority === "high",
    `status=${good.status}`);

  // 4. PATCH leg on the seeded card -> 200 (write path live behind the stub)
  const patch = await httpGet(port, "/api/board/DMR-001", { method: "PATCH", body: { priority: "low" } });
  ok("PATCH /api/board/DMR-001 returns 200", patch.status === 200
    && JSON.parse(patch.body).priority === "low", `status=${patch.status}`);

  // 5. frontend served
  const page = await httpGet(port, "/");
  ok("GET / serves the frontend html", page.status === 200
    && page.body.includes("DMR Dispatch Board"));

  console.log(`\n${checks.filter(Boolean).length}/${checks.length} smoke checks passed`);
  return checks.every(Boolean) ? 0 : 1;
}

// ---- main --------------------------------------------------------------
if (require.main === module) {
  const argv = process.argv.slice(2);
  const port = (() => {
    const i = argv.indexOf("--port");
    return i >= 0 ? parseInt(argv[i + 1], 10) : 8787;
  })();
  const host = (() => {
    const i = argv.indexOf("--host");
    return i >= 0 ? argv[i + 1] : "0.0.0.0";
  })();
  const server = createServer();

  server.listen(port, host, async () => {
    if (argv.includes("--smoke")) {
      const code = await smoke(port);
      server.close();
      process.exit(code);
      return;
    }
    console.log(`Mailroom dispatch board serving (stub-backed, no GitHub creds)`);
    console.log(`  local  http://127.0.0.1:${port}/   api  /api/board  (GET/POST)  /api/board/DMR-0NN  (PATCH)`);
    for (const lan of lanUrls()) console.log(`  lan    ${lan}${port}/`);
    console.log(`Ctrl-C to stop`);
  });
}

module.exports = { createServer, smoke };