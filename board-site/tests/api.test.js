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
    assert.ok(patchCall.body.body.includes("### Lane\nin-progress"), "body Lane section mirrors the move");
  });

  // #69 lane-axis validation — mirror the hub#48 priority pins.
  await check("POST rejects a work lane (in-progress) on create with 400 invalid lane", async () => {
    reset();
    const res = await runHandler(boardHandler, makeReq("POST", "/api/board", { title: "x", lane: "in-progress" }));
    assert.strictEqual(res.statusCode, 400, `expected 400 got ${res.statusCode}`);
    assert.ok(res._body.includes("invalid lane"), `body=${res._body}`);
    assert.ok(res._body.includes("unassigned"), `create-lane allowlist must be machine-readable, body=${res._body}`);
    assert.ok(!calls.some((c) => c.method === "POST" && /\/issues$/.test(c.url)), "no GitHub create issued for a rejected lane");
  });

  await check("POST rejects an unknown lane string with 400 invalid lane", async () => {
    reset();
    const res = await runHandler(boardHandler, makeReq("POST", "/api/board", { title: "x", lane: "bogus-lane" }));
    assert.strictEqual(res.statusCode, 400, `expected 400 got ${res.statusCode}`);
    assert.ok(res._body.includes("invalid lane"), `body=${res._body}`);
  });

  await check("POST lane unassigned keeps byte-identical create (201, stage/unassigned)", async () => {
    reset();
    const res = await runHandler(boardHandler, makeReq("POST", "/api/board", { title: "x", lane: "unassigned", priority: "medium" }));
    assert.strictEqual(res.statusCode, 201, `expected 201 got ${res.statusCode}`);
    const call = calls.find((c) => c.method === "POST" && /\/issues$/.test(c.url));
    assert.deepStrictEqual(call.body.labels, ["kanban", "type/task", "stage/unassigned", "priority/medium"], `labels=${JSON.stringify(call.body.labels)}`);
    assert.ok(call.body.body.includes("### Lane\n\nunassigned"), "body Lane section written");
  });

  await check("POST lane assigned + agents keeps byte-identical create (201, stage/assigned)", async () => {
    reset();
    const res = await runHandler(boardHandler, makeReq("POST", "/api/board", { title: "x", lane: "assigned", agents: ["bob"] }));
    assert.strictEqual(res.statusCode, 201, `expected 201 got ${res.statusCode}`);
    const call = calls.find((c) => c.method === "POST" && /\/issues$/.test(c.url));
    assert.ok(call.body.labels.includes("stage/assigned"), `labels=${JSON.stringify(call.body.labels)}`);
    assert.ok(call.body.body.includes("### Lane\n\nassigned"), "body Lane section written");
  });

  await check("POST lane defaults to unassigned when omitted (201)", async () => {
    reset();
    const res = await runHandler(boardHandler, makeReq("POST", "/api/board", { title: "x" }));
    assert.strictEqual(res.statusCode, 201, `expected 201 got ${res.statusCode}`);
    const call = calls.find((c) => c.method === "POST" && /\/issues$/.test(c.url));
    assert.ok(call.body.labels.includes("stage/unassigned"), "default create route is unchanged");
  });

  await check("PATCH rejects an unknown lane with 400 invalid lane and performs no write", async () => {
    reset();
    const res = await runHandler(cardHandler, makeReq("PATCH", "/api/board/DMR-001", { lane: "bogus-lane" }));
    assert.strictEqual(res.statusCode, 400, `expected 400 got ${res.statusCode}`);
    assert.ok(res._body.includes("invalid lane"), `body=${res._body}`);
    assert.ok(res._body.includes("needs-attention"), `full lane allowlist must be machine-readable, body=${res._body}`);
    assert.ok(!calls.some((c) => c.method === "PATCH" && /\/issues\/1$/.test(c.url)), "no GitHub PATCH issued for a rejected lane");
  });

  await check("PATCH rejects an empty-string lane with 400 invalid lane", async () => {
    reset();
    const res = await runHandler(cardHandler, makeReq("PATCH", "/api/board/DMR-001", { lane: "  " }));
    assert.strictEqual(res.statusCode, 400, `expected 400 got ${res.statusCode}`);
    assert.ok(res._body.includes("invalid lane"), `body=${res._body}`);
  });

  // #70 B6: oversized payloads must answer 413 — not throw on req.destroy().
  await check("POST oversized payload returns 413 without a req.destroy TypeError", async () => {
    reset();
    const blob = "x".repeat(1_100_000);
    const res = await runHandler(boardHandler, makeReq("POST", "/api/board", { title: "x", desc: blob }));
    assert.strictEqual(res.statusCode, 413, `expected 413 got ${res.statusCode}`);
    assert.ok(res._body.includes("payload too large"), `body=${res._body.slice(0, 120)}`);
  });

  await check("PATCH oversized payload returns 413 without a req.destroy TypeError", async () => {
    reset();
    const blob = "x".repeat(300_000);
    const res = await runHandler(cardHandler, makeReq("PATCH", "/api/board/DMR-001", { desc: blob }));
    assert.strictEqual(res.statusCode, 413, `expected 413 got ${res.statusCode}`);
    assert.ok(res._body.includes("payload too large"), `body=${res._body.slice(0, 120)}`);
  });

  // #70 B3: exactly one Vercel Insights include survives.
  await check("index.html has exactly one Insights include and one window.va definition", () => {
    const src = require("node:fs").readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
    assert.strictEqual((src.match(/\/_vercel\/insights\/script\.js/g) || []).length, 1, "insights script must be included once");
    assert.strictEqual((src.match(/window\.va\s*=/g) || []).length, 1, "window.va must be defined once");
  });

  // #69 UI law: the create modal may only offer the two create lanes; the
  // full five-lane set is restored for edit by setFormLaneOptions(false).
  await check("index.html create modal offers only unassigned/assigned; edit restores all five", () => {
    const src = require("node:fs").readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
    const staticSelect = src.slice(src.indexOf('<select class="form-select" id="formLane"'), src.indexOf("</select>"));
    assert.ok(staticSelect.includes('value="unassigned"') && staticSelect.includes('value="assigned"'), "create lanes present");
    assert.ok(!staticSelect.includes('value="in-progress"') && !staticSelect.includes('value="done"'), "work lanes must not be offered on create");
    assert.ok(src.includes("setFormLaneOptions(false);"), "edit path must restore the full lane set");
  });

  await check("GET board without GITHUB_TOKEN returns 500", async () => {
    reset();
    const saved = process.env.GITHUB_TOKEN;
    delete process.env.GITHUB_TOKEN;
    try {
      const res = await runHandler(boardHandler, makeReq("GET", "/api/board"));
      assert.strictEqual(res.statusCode, 500, `expected 500 got ${res.statusCode}`);
      assert.ok(res._body.includes("GITHUB_TOKEN"), res._body);
    } finally {
      process.env.GITHUB_TOKEN = saved;
    }
  });

  await check("GET board passes through GitHub 401", async () => {
    reset();
    const origFetch = global.fetch;
    global.fetch = async () => ({
      ok: false,
      status: 401,
      headers: new Map(),
      text: async () => JSON.stringify({ message: "Bad credentials" }),
    });
    try {
      const res = await runHandler(boardHandler, makeReq("GET", "/api/board"));
      assert.strictEqual(res.statusCode, 401, res._body);
    } finally {
      global.fetch = origFetch;
    }
  });

  await check("GET board returns rateLimited JSON after GitHub 429 (hub#166)", async () => {
    reset();
    const origFetch = global.fetch;
    let hits = 0;
    global.fetch = async () => {
      hits++;
      return {
        ok: false,
        status: 429,
        headers: { get: (name) => (name === "retry-after" ? "0" : null) },
        text: async () => JSON.stringify({ message: "API rate limit exceeded" }),
      };
    };
    try {
      const res = await runHandler(boardHandler, makeReq("GET", "/api/board"));
      assert.strictEqual(res.statusCode, 503, res._body);
      const body = JSON.parse(res._body);
      assert.strictEqual(body.rateLimited, true);
      assert.ok(hits >= 3, "expected retries before surfacing rate limit");
    } finally {
      global.fetch = origFetch;
    }
  });

  await check("index.html keeps cards when refresh hits rateLimited (hub#166)", () => {
    const src = require("node:fs").readFileSync(path.join(__dirname, "..", "index.html"), "utf8");
    assert.ok(src.includes("if (err.rateLimited)"), "refreshBoard must branch on rateLimited");
    assert.ok(src.includes("● RATE LIMITED"), "rate limit badge copy present");
    const rateBranch = src.slice(src.indexOf("if (err.rateLimited)"), src.indexOf("} else {", src.indexOf("if (err.rateLimited)")));
    assert.ok(!rateBranch.includes("state.cards = []"), "rate limit branch must not wipe cards");
  });

  await check("GET board maps fetch network failure to 502", async () => {
    reset();
    const origFetch = global.fetch;
    global.fetch = async () => {
      throw new Error("ECONNRESET");
    };
    try {
      const res = await runHandler(boardHandler, makeReq("GET", "/api/board"));
      assert.strictEqual(res.statusCode, 502, res._body);
      assert.ok(res._body.includes("unreachable"), res._body);
    } finally {
      global.fetch = origFetch;
    }
  });

  console.log(`\n${passed} checks passed`);
})();