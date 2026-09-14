// board-site API regression tests (hub#48) — stub-tested, no network.
//
// Run: node tests/api.test.js   (from board-site/)
// Uses Node 18+ global fetch; stubs GITHUB_TOKEN + fetch with canned
// responses so the Vercel-style handlers run hermetically.
"use strict";

const assert = require("node:assert");
const path = require("node:path");

process.env.GITHUB_TOKEN = "test-token";
process.env.MAILROOM_GITHUB_REPO = "LLM-Mailroom-Services/Digital-Mailroom";

const ghx = require("../lib/gh.js");
const boardHandler = require("../api/board.js");
const cardHandler = require("../api/board/[id].js");

// ---- fetch stub --------------------------------------------------------
// Canned GitHub issues keyed by number; captures every outbound call so the
// test can assert on the PATCH bodies the API composes.
const ISSUES = new Map();
const calls = [];

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

global.fetch = async (url, opts = {}) => {
  const method = opts.method || "GET";
  const body = opts.body ? JSON.parse(opts.body) : null;
  calls.push({ url: String(url), method, body });
  const u = new URL(String(url));
  const pathname = u.pathname;

  // search/issues: return all canned issues as items
  if (pathname.endsWith("/search/issues")) {
    return jsonResponse(200, { items: [...ISSUES.values()] });
  }
  // issues list (nextCardId / listKanbanIssues)
  if (/\/issues$/.test(pathname)) {
    if (method === "POST") {
      const match = (body.title || "").match(/DMR-(\d{3,})/i);
      const n = match ? parseInt(match[1], 10) : ISSUES.size + 1;
      const rec = issueRecord(n, { title: body.title, body: body.body || "", labels: body.labels || [], state: "open" });
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
      if (body.labels !== undefined) rec.labels = body.labels;
      if (body.title !== undefined) rec.title = body.title;
      if (body.body !== undefined) rec.body = body.body;
      if (body.state !== undefined) rec.state = body.state;
      return jsonResponse(200, rec);
    }
    return jsonResponse(200, ISSUES.get(n));
  }
  // issues/{n}/comments (lane-move mirror comment)
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

// ---- minimal req/res shims ---------------------------------------------
function makeReq(method, url, body) {
  const payload = body === undefined ? "" : JSON.stringify(body);
  const req = {
    method,
    url,
    headers: { origin: "null", "content-type": "application/json", "x-mailroom-actor": "test" },
    on(ev, cb) {
      if (ev === "data" && payload) cb(payload);
      if (ev === "end") cb();
      if (ev === "error") {}
    },
  };
  return req;
}

function makeRes() {
  const res = {
    statusCode: 200,
    _headers: {},
    _body: "",
    setHeader(k, v) { res._headers[k] = v; },
    end(d) { if (d) res._body += d; res._ended = true; },
  };
  return res;
}

function runHandler(handler, req) {
  return new Promise((resolve) => {
    const res = makeRes();
    handler(req, res).then(() => resolve(res)).catch((e) => {
      res._body = JSON.stringify({ error: String(e) });
      res.statusCode = 500;
      resolve(res);
    });
  });
}

// ---- tests -------------------------------------------------------------
let passed = 0;
async function check(name, fn) {
  try {
    await fn();
    passed++;
    console.log(`ok - ${name}`);
  } catch (e) {
    console.error(`FAIL - ${name}\n  ${e.message}`);
    process.exitCode = 1;
  }
}

function reset() {
  ISSUES.clear();
  calls.length = 0;
  ISSUES.set(1, issueRecord(1)); // unassigned card (open, no stage label, no assignees)
}

// ---- run ---------------------------------------------------------------
(async () => {
  await check("PATCH priority-only keeps unassigned card lane-free", async () => {
    reset();
    const res = await runHandler(cardHandler, makeReq("PATCH", "/api/board/DMR-001", { priority: "high" }));
    assert.strictEqual(res.statusCode, 200, `expected 200 got ${res.statusCode}`);
    const patchCall = calls.find((c) => c.method === "PATCH" && /\/issues\/1$/.test(c.url));
    assert.ok(patchCall, "expected a PATCH to issue 1");
    assert.ok(!patchCall.body.labels.some((l) => l.startsWith("stage/")), "labels must not gain a stage/* on non-lane edit");
    assert.ok(patchCall.body.labels.includes("priority/high"), "priority label applied");
  });

  await check("PATCH bad priority returns 400 invalid priority", async () => {
    reset();
    const res = await runHandler(cardHandler, makeReq("PATCH", "/api/board/DMR-001", { priority: "urgent" }));
    assert.strictEqual(res.statusCode, 400, `expected 400 got ${res.statusCode}`);
    assert.ok(res._body.includes("invalid priority"), `body=${res._body}`);
  });

  await check("POST bad priority returns 400 invalid priority", async () => {
    reset();
    const res = await runHandler(boardHandler, makeReq("POST", "/api/board", { title: "x", priority: "urgent" }));
    assert.strictEqual(res.statusCode, 400, `expected 400 got ${res.statusCode}`);
    assert.ok(res._body.includes("invalid priority"), `body=${res._body}`);
  });

  await check("toCard strips both DMR- and HUB- prefixes", () => {
    const d = ghx.toCard({ number: 9, title: "DMR-009: DMR-009: task", body: "", labels: [], assignees: [], state: "open", created_at: "", updated_at: "", html_url: "" });
    assert.strictEqual(d.title, "DMR-009: task", `got ${d.title}`);
    const h = ghx.toCard({ number: 8, title: "HUB-008: task", body: "", labels: [], assignees: [], state: "open", created_at: "", updated_at: "", html_url: "" });
    assert.strictEqual(h.title, "task", `got ${h.title}`);
  });

  await check("index.html rolls back the temp card on POST failure", () => {
    const src = require("node:fs").readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
    const catchBlock = src.slice(src.indexOf(".catch((err) => {"), src.indexOf(".catch((err) => {") + 900);
    assert.ok(catchBlock.includes("state.cards.splice(idx, 1)"), "catch must remove the temp card");
    assert.ok(catchBlock.includes("renderBoard()"), "catch must re-render");
  });

  await check("explicit lane PATCH swaps the stage label", async () => {
    reset();
    const res = await runHandler(cardHandler, makeReq("PATCH", "/api/board/DMR-001", { lane: "in-progress" }));
    assert.strictEqual(res.statusCode, 200, `expected 200 got ${res.statusCode}`);
    const patchCall = calls.find((c) => c.method === "PATCH" && /\/issues\/1$/.test(c.url));
    assert.ok(patchCall.body.labels.includes("stage/in-progress"), "lane label set on explicit lane patch");
  });

  console.log(`\n${passed} checks passed`);
})();