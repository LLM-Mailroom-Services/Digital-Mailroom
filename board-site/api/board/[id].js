// PATCH /api/board/[cardId] — write a live kanban card back to its GitHub issue.
//
// Contract (only changed keys need to be sent):
//   { lane?, priority?, title?, desc?, evidence?, agents?, archived? }
//
// Semantics:
//   lane       -> swap stage/* label; post a dated comment mirroring the move
//   priority   -> swap priority/* label
//   title/desc/evidence -> PATCH issue title + body sections (Card ID/Lane/Priority
//                 kept; Task/Evidence plan rewritten)
//   agents     -> set issue assignees
//   archived:true  -> close the issue (done lane, auto appears in archive)
//   archived:false -> reopen it
//
// Lane flow: unassigned → assigned → in-progress → needs-attention → done
"use strict";

const ghx = require("../../lib/gh.js");

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
    if (req.method !== "PATCH") return sendJson(res, 405, { error: "method not allowed (use PATCH)" });
    const cardId = String((req.url || "").split("?")[0].split("/").pop()).toUpperCase();
    if (!/^DMR-\d{3,}$/.test(cardId)) return sendJson(res, 400, { error: `bad card id ${cardId}` });

    const issue = await ghx.findIssueByCardId(cardId);
    const body = await readBody(req);

    const want = {};
    if (body.lane !== undefined) want.lane = String(body.lane).trim();
    if (body.priority !== undefined) want.priority = String(body.priority).trim();
    if (body.archived !== undefined) want.archived = !!body.archived;
    if (body.title !== undefined) want.title = String(body.title).trim();
    if (body.desc !== undefined) want.desc = String(body.desc).trim();
    if (body.evidence !== undefined) want.evidence = String(body.evidence).trim();
    if (body.agents !== undefined) {
      want.agents = Array.isArray(body.agents) ? body.agents.map((a) => String(a).trim()).filter(Boolean) : [];
    }
    if (Object.keys(want).length === 0) return sendJson(res, 400, { error: "empty patch" });

    const actor = ghx.actor(req);
    const me = new Date().toISOString().slice(0, 10);
    const issuePath = `/repos/${ghx.repo()}/issues/${issue.number}`;

    // 1+2. Lane move / priority swap -> recompute ONE authoritative label set.
    //      GitHub's labels field REPLACES the whole set, so derive it from the
    //      current issue once and patch a single time.
    const currentLabelNames = (issue.labels || []).map((l) => l.name);
    const targetLane = want.lane ? ghx.LANES.find((l) => l.id === want.lane) : null;
    const sourceLaneId =
      currentLabelNames.map((n) => (ghx.STAGE_LABELS.includes(n) ? n.replace("stage/", "") : null)).find(Boolean) ||
      (issue.state === "closed" ? "done" : "assigned");
    const sourceLane = ghx.LANES.find((l) => l.id === sourceLaneId);

    // Keep every non-stage/non-priority label; then merge in whichever of
    // stage / priority the patch touches (or already present, untouched).
    const nextLabels = currentLabelNames.filter(
      (n) => !ghx.STAGE_LABELS.includes(n) && !n.startsWith("priority/"),
    );
    nextLabels.push(targetLane ? targetLane.label : `stage/${sourceLaneId}`);
    if (want.priority) nextLabels.push(`priority/${want.priority}`);
    else for (const p of ghx.PRI_LABELS) if (currentLabelNames.includes(p)) nextLabels.push(p);

    const comments = [];
    if (targetLane && (!sourceLane || sourceLane.id !== targetLane.id)) {
      const comment = `### Board lane move — ${me}\n\n**${cardId}:** ${sourceLane ? sourceLane.title : "?"} → **${targetLane.title}** (by ${actor})`;
      comments.push(comment);
    }

    // 3. Title / body sections
    const patch = { labels: nextLabels };
    if ("title" in want && want.title) patch.title = `${cardId}: ${want.title}`;
    if ("desc" in want || "evidence" in want || "lane" in want || "priority" in want || "agents" in want) {
      let nb = issue.body || "";
      if ("desc" in want) nb = ghx.setBodySection(nb, "Task", want.desc || "—");
      if ("evidence" in want) nb = ghx.setBodySection(nb, "Evidence plan", want.evidence || "—");
      if ("lane" in want) nb = ghx.setBodySection(nb, "Lane", want.lane);
      if ("priority" in want) nb = ghx.setBodySection(nb, "Priority", want.priority);
      if ("agents" in want) nb = ghx.setBodySection(nb, "Owner", want.agents.join(", ") || "—");
      patch.body = nb;
    }
    // 4. Agents -> the body "### Owner" section (agent/persona/harness). Never
    //    set GitHub assignees to arbitrary agent names (non-collaborators 422).
    // 5. archive = close issue
    if ("archived" in want) patch.state = want.archived ? "closed" : "open";

    await ghx.gh(issuePath, { method: "PATCH", body: patch });
    for (const comment of comments) {
      await ghx.gh(`/repos/${ghx.repo()}/issues/${issue.number}/comments`, {
        method: "POST",
        body: { body: comment },
      });
    }

    const fresh = await ghx.gh(issuePath);
    const card = ghx.toCard(fresh);
    if (comments.length) card._comments = comments;
    return sendJson(res, 200, card);
  } catch (err) {
    const status = err.status || 500;
    return sendJson(res, status, { error: err.message || String(err) });
  }
};

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", (chunk) => {
      data += chunk;
      if (data.length > 250_000) {
        reject(new ghx.HttpError(413, "payload too large"));
        req.destroy();
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