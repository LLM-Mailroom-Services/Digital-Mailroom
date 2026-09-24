// GET /api/board — live kanban cards from GitHub issues (labels=kanban).
// POST /api/board — create a new card (opens a GitHub issue).
//
// Lane flow: unassigned → assigned → in-progress → needs-attention → done
// New cards created WITHOUT agents default to "unassigned" (triage queue).
"use strict";

const ghx = require("../lib/gh.js");

// #69: a brand-new card may only be created into the triage queue or the
// claimed queue. The work lanes (in-progress → done) are reached by LANE
// MOVES on existing cards, never by create — otherwise a client could mint
// a card straight into done/needs-attention and skip the board's laws.
const CREATE_LANES = new Set(["unassigned", "assigned"]);

function sendJson(res, status, obj) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(obj));
}

module.exports = async function handler(req, res) {
  // Handle CORS preflight
  ghx.cors(req, res);
  if (req.method === "OPTIONS") {
    res.statusCode = 204;
    return res.end();
  }

  try {
    if (req.method === "GET") {
      const cards = await ghx.listKanbanIssues();
      return sendJson(res, 200, {
        schema: 1,
        generatedAt: new Date().toISOString(),
        repo: ghx.repo(),
        cards,
      });
    }

    if (req.method === "POST") {
      const body = await readBody(req);
      const title = (body.title || "").trim();
      const desc = (body.desc || "").trim();
      const lane = (body.lane || "unassigned").trim();
      const priority = (body.priority || "medium").trim();
      const agents = Array.isArray(body.agents) ? body.agents.map((a) => String(a).trim()).filter(Boolean) : [];
      if (!title) return sendJson(res, 400, { error: "title is required" });
      // hub#48: agent-facing contract — validate priority against the known
      // labels so a bad value returns a helpful 400 instead of a GitHub 422.
      if (!ghx.PRI_LABELS.includes(`priority/${priority}`)) {
        return sendJson(res, 400, { error: "invalid priority" });
      }
      // #69: lane-axis twin of the priority guard — the board's own lanes,
      // validated against the canonical set so a bad create cannot silently
      // fall into ghx.LANES[0] or mint a card in a work lane.
      if (body.lane !== undefined && !CREATE_LANES.has(lane)) {
        return sendJson(res, 400, { error: "invalid lane", allowed: [...CREATE_LANES] });
      }

      // Route: cards with NO agents → unassigned; cards WITH agents → assigned
      const effectiveLane = agents.length === 0 ? "unassigned" : lane;
      const laneObj = ghx.LANES.find((l) => l.id === effectiveLane) || ghx.LANES[0];
      const labels = ["kanban", "type/task", laneObj.label, `priority/${priority}`];

      const issueBody = (id) => [
        "## Board card — the issue is the mirror, the board is the truth",
        "",
        "Synced from the Mailroom Dispatch Board (served site).",
        "",
        `### Card ID\n\n${id}`,
        "",
        `### Owner\n\n${agents.length ? agents.join(", ") : "—"}`,
        "",
        `### Lane\n\n${effectiveLane}`,
        "",
        `### Priority\n\n${priority}`,
        "",
        `### Task\n\n${desc || "—"}`,
        "",
        `### Evidence plan\n\n—`,
      ].join("\n");

      const MAX_CREATE_ATTEMPTS = 5;
      let created = null;
      for (let attempt = 0; attempt < MAX_CREATE_ATTEMPTS; attempt++) {
        const id = await ghx.nextCardId();
        const existing = await ghx.listIssuesByCardId(id);
        if (existing.length > 0) continue;

        created = await ghx.gh(`/repos/${ghx.repo()}/issues`, {
          method: "POST",
          body: {
            title: `${id}: ${title}`,
            body: issueBody(id),
            labels,
          },
        });

        const after = await ghx.listIssuesByCardId(id);
        if (after.length <= 1) break;

        const winner = after.reduce((a, b) => (a.number < b.number ? a : b));
        if (created.number !== winner.number) {
          await ghx.gh(`/repos/${ghx.repo()}/issues/${created.number}`, {
            method: "PATCH",
            body: { state: "closed" },
          });
          created = null;
          continue;
        }
        break;
      }
      if (!created) {
        return sendJson(res, 503, { error: "could not allocate a unique card id — retry shortly" });
      }
      return sendJson(res, 201, ghx.toCard(created));
    }

    return sendJson(res, 405, { error: "method not allowed" });
  } catch (err) {
    const status = err.status || 500;
    const payload = { error: err.message || String(err) };
    if (err.rateLimited) {
      payload.rateLimited = true;
      payload.retryAfter = err.retryAfter;
    }
    return sendJson(res, status, payload);
  }
};

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    let aborted = false;
    req.on("data", (chunk) => {
      if (aborted) return;
      data += chunk;
      if (data.length > 1_000_000) {
        // #69/#70: the 413 response is what ends this exchange — req.destroy()
        // is not a Vercel/Node IncomingMessage method, only an optional
        // serverless-adapter abort hook, so it must be probed before calling.
        aborted = true;
        reject(new ghx.HttpError(413, "payload too large"));
        if (typeof req.destroy === "function") req.destroy();
      }
    });
    req.on("end", () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch (e) {
        reject(new ghx.HttpError(400, "invalid JSON body"));
      }
    });
    req.on("error", reject);
  });
}