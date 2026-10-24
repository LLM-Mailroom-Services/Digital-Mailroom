/* Mailroom Observatory — BERT lane panels (#111). Vanilla, DOM-free.
 *
 * Reads the terminal-manifest BERT block the server lifts onto every run
 * record as `intake_bert` (the manifest's `intake.bert` dict: handoff fields
 * + gate_outcome; see llm-mailroom bert_intake.py / _attach_gate_outcome).
 * Pure functions only — no DOM access, no fetch — so the module runs in the
 * browser, in `node` (tests), anywhere. Every value is a REDUCTION of the
 * given manifests, never fabricated: rates render from counted docs only,
 * and a missing field yields an empty state, not a zero.
 *
 * Promotion note: the lane currently runs in shadow mode, so these panels
 * render shadow-mode telemetry. They never read post-promotion authority
 * (skip-mode routing decisions exist only after the run-3 sign-off).
 */
"use strict";

var BERTPanels = (() => {
  var PANELS = [
    {
      key: "bert-pass",
      title: "BERT pass rate",
      description: "Share of BERT-triaged docs whose doc-type head passed the calibrated gate. Shadow-mode telemetry, not promotion authority.",
      fields: [
        "intake.bert.available",
        "intake.bert.method",
        "intake.bert.doc_type_pass",
        "intake.bert.gate_outcome.verdict",
      ],
    },
    {
      key: "sorter-skip",
      title: "Sorter-skip rate",
      description: "Share of BERT-triaged docs the intake gate declared eligible for sorter skip. Skipping only activates under BERT_INTAKE_MODE=skip — this window renders what the gate recorded (shadow today).",
      fields: [
        "intake.bert.gate_outcome.eligible_for_sorter_skip",
        "intake.bert.gate_outcome.mode",
      ],
    },
    {
      key: "disagreement",
      title: "Disagreement rate",
      description: "Share of BERT-triaged docs where the BERT doc-type label disagreed with the sorter verdict (agreement=false, a label flip, or a sorter-related failed check).",
      fields: [
        "intake.bert.doc_type",
        "intake.bert.agreement",
        "intake.bert.gate_outcome.failed_checks",
        "doc_type",
      ],
    },
    {
      key: "fail-soft",
      title: "Fail-soft rate",
      description: "Share of manifests where the BERT lane degraded to the deterministic clerk (available=false or method != bert). Fail-open: intake never blocks a run.",
      fields: [
        "intake.bert.available",
        "intake.bert.method",
        "intake.bert.reason",
      ],
    },
    {
      key: "extract-accuracy",
      title: "Downstream extract accuracy",
      description: "Among BERT-triaged docs, the share of extractions the judge verified CORRECT. No verdicts in the window → an awaiting state, never a guess.",
      fields: [
        "intake.bert.available",
        "intake.bert.method",
        "verdict",
      ],
    },
  ];

  var VERDICTS = { CORRECT: "CORRECT", PARTIAL: "PARTIAL", MISS: "MISS" };
  var emptyState = "No data in the live window — no manifest carries the fields this panel reads.";

  function esc(text) {
    return String(text == null ? "" : text)
      .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;").replaceAll("'", "&#39;");
  }

  function bertOf(run) {
    var b = run && run.intake_bert;
    return b && typeof b === "object" ? b : null;
  }

  function gateOf(bert) {
    var g = bert && bert.gate_outcome;
    return g && typeof g === "object" ? g : null;
  }

  function fold(a) {
    return String(a || "").trim().toLowerCase();
  }

  function pct(n, d) {
    return d ? Math.round((100 * n) / d) + "%" : null;
  }

  // True when the manifest records a real BERT classification (not a clerk
  // handoff): the runner stamps doc_type_pass on every bert handoff; the
  // flag-off/no-model clerk handoffs carry only available/reason/method.
  function isBertClassified(bert) {
    return bert && ("doc_type_pass" in bert || (bert.method === "bert" && bert.available !== false));
  }

  function isFailSoft(bert) {
    return bert && (bert.available === false || (bert.method && bert.method !== "bert"));
  }

  function disaggrees(bert, run) {
    if (!bert) return false;
    var g = gateOf(bert);
    if (bert.agreement === false) return true;
    var bertLabel = fold(bert.doc_type);
    var runLabel = fold(run && run.doc_type);
    if (bertLabel && runLabel && bertLabel !== runLabel) return true;
    if (g && Array.isArray(g.failed_checks)) {
      return g.failed_checks.some(function (t) { return /sorter|^P6$/i.test(String(t || "")); });
    }
    return false;
  }

  // ---- reduction --------------------------------------------------------
  // Returns: {runs, bertDocs, modes, panels: {key: {n, d, cohort, reasons, byRevision}}}
  // `cohort` = docs eligible for the panel's comparison; `d` = docs that
  // actually carried the compared field. cohort > d => awaiting-data state
  // (the field is missing on newer-eligible docs), never a fabricated zero.
  function compute(manifests) {
    var list = Array.isArray(manifests) ? manifests : [];
    var panels = {};
    PANELS.forEach(function (p) {
      panels[p.key] = { n: 0, d: 0, cohort: 0, reasons: {}, byRevision: {} };
    });
    var modes = [];
    var bertDocs = 0;

    function observe(key, doc) {
      panels[key].cohort += 1;
    }

    function bump(key, doc, ok) {
      var pan = panels[key];
      pan.d += 1;
      if (ok) pan.n += 1;
      var sha = doc.bert.artifact_sha;
      if (sha) {
        var rev = pan.byRevision[String(sha)] || (pan.byRevision[String(sha)] = { n: 0, d: 0 });
        rev.d += 1;
        if (ok) rev.n += 1;
      }
    }

    list.forEach(function (run) {
      var bert = bertOf(run);
      if (!bert) return;
      bertDocs += 1;
      var g = gateOf(bert);
      if (g && g.mode && !modes.includes(g.mode)) modes.push(g.mode);

      if (isBertClassified(bert)) {
        observe("bert-pass", { bert: bert });
        var passed = bert.doc_type_pass === true
          || (bert.doc_type_pass === undefined && g && g.verdict === "PASS");
        bump("bert-pass", { bert: bert }, passed);

        observe("extract-accuracy", { bert: bert });
        var verdict = fold(run && run.verdict);
        if (verdict) bump("extract-accuracy", { bert: bert }, verdict === fold(VERDICTS.CORRECT));
      }
      if (g && g.eligible_for_sorter_skip !== undefined) {
        observe("sorter-skip", { bert: bert });
        bump("sorter-skip", { bert: bert }, g.eligible_for_sorter_skip === true);
      }
      var comparable = bert.agreement !== undefined
        || (fold(bert.doc_type) && fold(run && run.doc_type))
        || (g && Array.isArray(g.failed_checks) && g.failed_checks.length > 0);
      if (comparable) {
        observe("disagreement", { bert: bert });
        bump("disagreement", { bert: bert }, disaggrees(bert, run));
      }
      // fail-soft: every intake.bert block counts (clerk handoffs included)
      observe("fail-soft", { bert: bert });
      bump("fail-soft", { bert: bert }, isFailSoft(bert));
      if (isFailSoft(bert) && bert.reason) {
        panels["fail-soft"].reasons[String(bert.reason)] =
          (panels["fail-soft"].reasons[String(bert.reason)] || 0) + 1;
      }
    });
    return { runs: list.length, bertDocs: bertDocs, modes: modes, panels: panels };
  }

  // ---- html rendering ----------------------------------------------------
  function revisionTiles(byRevision) {
    var shas = Object.keys(byRevision).sort();
    if (shas.length < 2) return "";
    return shas.map(function (sha) {
      var r = byRevision[sha];
      var label = String(sha).slice(0, 8);
      return "<dl class=\"bert-rev\"><dt>revision " + esc(label) + "</dt><dd>"
        + (pct(r.n, r.d) || "—") + " (" + r.n + "/" + r.d + ")</dd></dl>";
    }).join("");
  }

  function card(p, stats, modes) {
    var n = stats ? stats.n : 0;
    var d = stats ? stats.d : 0;
    var fields = p.fields.map(function (f) { return "<code>" + esc(f) + "</code>"; }).join(" ");
    var modeChips = modes.length
      ? modes.map(function (m) { return "<span class=\"badge badge-info\">gate mode " + esc(m) + "</span>"; }).join("")
      : "";
    var body = d ? pct(n, d) + " (" + n + "/" + d + ")" : "—";
    var extra = "";
    if (p.key === "fail-soft" && d && stats.reasons) {
      extra = Object.keys(stats.reasons).sort().map(function (r) {
        return "<span class=\"badge badge-warn\">" + esc(r) + " " + stats.reasons[r] + "</span>";
      }).join("");
    }
    // Distinguish "the field simply isn't there yet" from "nothing to count".
    var state = "";
    if (!d) {
      if (stats.cohort > 0) {
        state = "<p class=\"empty\">Awaiting data — " + esc(p.key === "extract-accuracy"
          ? "no judge verdicts on BERT-triaged docs in this window"
          : "the compared field is absent on eligible manifests (older runs)") + ".</p>";
      } else {
        state = "<p class=\"empty\">" + emptyState + "</p>";
      }
    }
    var revs = d ? revisionTiles(stats.byRevision) : "";
    return "<article class=\"tray bert-card\" aria-labelledby=\"bp-" + p.key + "\">"
      + "<h3 id=\"bp-" + p.key + "\">" + esc(p.title) + " <span class=\"tray-count\">(" + n + "/" + d + ")</span></h3>"
      + "<p class=\"bert-desc\">" + esc(p.description) + "</p>"
      + "<dl class=\"headline\"><dt>rate</dt><dd>" + body + "</dd></dl>"
      + "<p class=\"bert-fields\">reads " + fields + modeChips + " " + extra + "</p>"
      + revs
      + state
      + "</article>";
  }

  function render(manifests) {
    var out = compute(manifests);
    var head = "<h2 id=\"bert-panels-heading\">BERT lane panels</h2>"
      + "<p class=\"bert-note\">Shadow-mode telemetry reduced from terminal manifests ("
      + out.bertDocs + " of " + out.runs + " runs carry an <code>intake.bert</code> block). "
      + "Rates are counts over the live window — nothing is fabricated and nothing is promoted.</p>";
    if (!out.bertDocs) {
      head += "<p class=\"empty\">No BERT manifests in the live window — no run carries an "
        + "<code>intake.bert</code> block yet. The panels below stay empty until terminal "
        + "manifests record the lane.</p>";
    }
    return head + PANELS.map(function (p) { return card(p, out.panels[p.key], out.modes); }).join("");
  }

  return { PANELS: PANELS, bertOf: bertOf, gateOf: gateOf, compute: compute, render: render };
})();

if (typeof module !== "undefined") module.exports = BERTPanels;
if (typeof window !== "undefined") window.BERTPanels = BERTPanels;