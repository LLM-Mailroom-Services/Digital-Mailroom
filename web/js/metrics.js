/* The-Mailroom metrics view: aggregation tiles.
 * Works with /api/metrics in live mode, or computes from local data in demo mode. */

const MetricsView = (() => {
  const gridEl = document.getElementById("metrics-grid");

  function tile(label, value, cls = "") {
    return `<div class="tile">
      <div class="tile-value ${cls}">${value}</div>
      <div class="tile-label">${label}</div>
    </div>`;
  }

  function bars(title, entries, color) {
    const max = Math.max(1, ...entries.map((e) => e.value));
    const rows = entries
      .map((e) => `<div class="bar-row">
        <span class="bar-label">${Mailroom.esc(e.label)}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${Math.round((e.value / max) * 100)}%;background:${e.color || color}"></span></span>
        <span class="bar-num">${e.value}</span>
      </div>`)
      .join("");
    return `<div class="tile wide">
      <div class="tile-label" style="margin:0 0 8px">${title}</div>
      ${rows}
    </div>`;
  }

  function scoreValue(run, name) {
    const scores = run.scores;
    const aliases = {
      extraction_overall_verified_precision: "extraction_verified_precision",
      extraction_verified_precision: "extraction_overall_verified_precision",
    };
    const names = [name];
    if (aliases[name]) names.push(aliases[name]);
    for (const key of names) {
      if (!scores) continue;
      if (Array.isArray(scores)) {
        const hit = scores.find((s) => s && s.name === key && s.value != null);
        if (hit) {
          const n = Number(hit.value);
          if (Number.isFinite(n)) return n;
        }
        continue;
      }
      if (typeof scores === "object" && scores[key] != null) {
        const v = scores[key];
        if (typeof v === "object" && v !== null && "value" in v) {
          const n = Number(v.value);
          if (Number.isFinite(n)) return n;
        } else {
          const n = Number(v);
          if (Number.isFinite(n)) return n;
        }
      }
    }
    return null;
  }

  function computeLocalMetrics(runs) {
    const m = {
      total_docs: 0,
      archived: 0,
      review: 0,
      reconsideration: 0,
      failed: 0,
      in_flight: 0,
      total_cost_usd: 0,
      total_tokens: 0,
      llm_calls: 0,
      avg_cost_usd: 0,
      avg_latency_s: 0,
      p95_generation_latency_s: null,
      verdict_counts: {},
      per_doc_type: {},
      avg_quality: null,
      n_grounded_runs: 0,
      avg_extraction_field_score: null,
      avg_extraction_overall_score: null,
      avg_entity_list_precision: null,
      avg_entity_list_recall: null,
      avg_hallucination_rate: null,
      avg_expected_field_presence: null,
      avg_run_duration_s: null,
      avg_classification_attempts: null,
      avg_extraction_attempts: null,
      avg_extraction_verified_precision: null,
      avg_content_topic_accuracy: null,
      avg_content_topic_f1_macro: null,
      avg_sentiment_accuracy: null,
      avg_sentiment_f1_macro: null,
      avg_maud_question_accuracy: null,
      avg_maud_question_macro_accuracy: null,
      avg_maud_clause_presence: null,
      avg_maud_valid_class_rate: null,
      avg_maud_category_accuracy: null,
      per_doc_subclass: {},
    };
    const latencies = [];
    const qualities = [];
    const buckets = {
      extraction_field_score: [],
      extraction_overall_score: [],
      entity_list_precision: [],
      entity_list_recall: [],
      extraction_hallucination_rate: [],
      expected_field_presence: [],
      run_duration_seconds: [],
      classification_attempts: [],
      extraction_attempts: [],
      extraction_overall_verified_precision: [],
      content_topic_accuracy: [],
      content_topic_f1_macro: [],
      sentiment_accuracy: [],
      sentiment_f1_macro: [],
      maud_question_accuracy: [],
      maud_question_macro_accuracy: [],
      maud_clause_presence: [],
      maud_valid_class_rate: [],
      maud_category_accuracy: [],
    };
    for (const r of runs) {
      m.total_docs++;
      if (r.needs_reconsideration) m.reconsideration++;
      if (r.stage === "failed") m.failed++;
      else if (r.stage === "review" || r.needs_human) m.review++;
      else if (r.stage === "archived") m.archived++;
      else m.in_flight++;
      m.total_cost_usd += r.cost_usd || 0;
      m.total_tokens += r.total_tokens || 0;
      m.llm_calls += r.llm_call_count || 0;
      if (r.latency != null) latencies.push(r.latency);
      if (r.verdict) {
        m.verdict_counts[r.verdict] = (m.verdict_counts[r.verdict] || 0) + 1;
      }
      if (r.quality != null) qualities.push(r.quality);
      if (r.doc_type) {
        m.per_doc_type[r.doc_type] = (m.per_doc_type[r.doc_type] || 0) + 1;
      }
      if (r.doc_subclass) {
        const subKey = `${r.doc_type || "unknown"}/${r.doc_subclass}`;
        m.per_doc_subclass[subKey] = (m.per_doc_subclass[subKey] || 0) + 1;
      }
      const fs = scoreValue(r, "extraction_field_score");
      if (fs != null) m.n_grounded_runs++;
      for (const key of Object.keys(buckets)) {
        const v = scoreValue(r, key);
        if (v != null) buckets[key].push(v);
      }
    }
    if (m.total_docs > 0) m.avg_cost_usd = m.total_cost_usd / m.total_docs;
    if (latencies.length > 0) {
      m.avg_latency_s = latencies.reduce((a, b) => a + b, 0) / latencies.length;
    }
    if (qualities.length > 0) {
      m.avg_quality = qualities.reduce((a, b) => a + b, 0) / qualities.length;
    }
    const attrMap = {
      extraction_field_score: "avg_extraction_field_score",
      extraction_overall_score: "avg_extraction_overall_score",
      entity_list_precision: "avg_entity_list_precision",
      entity_list_recall: "avg_entity_list_recall",
      extraction_hallucination_rate: "avg_hallucination_rate",
      expected_field_presence: "avg_expected_field_presence",
      run_duration_seconds: "avg_run_duration_s",
      classification_attempts: "avg_classification_attempts",
      extraction_attempts: "avg_extraction_attempts",
      extraction_overall_verified_precision: "avg_extraction_verified_precision",
      content_topic_accuracy: "avg_content_topic_accuracy",
      content_topic_f1_macro: "avg_content_topic_f1_macro",
      sentiment_accuracy: "avg_sentiment_accuracy",
      sentiment_f1_macro: "avg_sentiment_f1_macro",
      maud_question_accuracy: "avg_maud_question_accuracy",
      maud_question_macro_accuracy: "avg_maud_question_macro_accuracy",
      maud_clause_presence: "avg_maud_clause_presence",
      maud_valid_class_rate: "avg_maud_valid_class_rate",
      maud_category_accuracy: "avg_maud_category_accuracy",
    };
    for (const [key, attr] of Object.entries(attrMap)) {
      if (buckets[key] && buckets[key].length) {
        m[attr] = buckets[key].reduce((a, b) => a + b, 0) / buckets[key].length;
      }
    }
    return m;
  }

  function trendBars(runs) {
    if (!runs || !runs.length) return "";
    // Bucket by hour over the last 6 hours
    const now = Date.now();
    const buckets = new Array(6).fill(0);
    const costBuckets = new Array(6).fill(0);
    const labels = [];
    for (let i = 5; i >= 0; i--) {
      const h = new Date(now - i * 3600000);
      labels.push(`${String(h.getHours()).padStart(2,"0")}:00`);
    }
    for (const r of runs) {
      const ts = r.updated_at || r.created_at;
      if (!ts) continue;
      const age = (now - new Date(ts).getTime()) / 3600000;
      // Bucket 5 is the current hour: age 0–1h → 5, 1–2h → 4, …
      // (floor(5 - age) put the last hour one bar early and left "now" empty).
      const bucket = 5 - Math.floor(Math.max(0, age));
      if (bucket >= 0 && bucket < 6) {
        buckets[bucket]++;
        costBuckets[bucket] += r.cost_usd || 0;
      }
    }
    const maxCount = Math.max(1, ...buckets);
    return `<div class="tile wide">
      <div class="tile-label" style="margin:0 0 8px">RUNS PER HOUR (last 6h)</div>
      ${buckets.map((v, i) => `<div class="bar-row">
        <span class="bar-label">${labels[i]}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${Math.round((v / maxCount) * 100)}%;background:var(--blue-light)"></span></span>
        <span class="bar-num">${v}${costBuckets[i] > 0 ? ` · $${costBuckets[i].toFixed(3)}` : ""}</span>
      </div>`).join("")}
    </div>`;
  }

  function render(m, rawRuns) {
    const verdictMix = (m.verdict_counts || {});
    const vColors = { CORRECT: "#5f9e6e", PARTIAL: "#f7d156", MISS: "#e26863" };
    const vBars = Object.entries(verdictMix)
      .filter(([, v]) => v > 0)
      .map(([k, v]) => ({ label: k, value: v, color: vColors[k] || "#7d97b5" }));

    const docBars = Object.entries(m.per_doc_type || {})
      .map(([k, v]) => ({
        label: ((Mailroom.meta && Mailroom.meta.doc_classes) || {})[k] || k,
        value: v,
        color: "#d9a866",
      }));
    const subclassBars = Object.entries(m.per_doc_subclass || {})
      .map(([k, v]) => ({ label: k, value: v, color: "#8aa3c0" }));

    const quality = m.avg_quality == null ? "—" : Number(m.avg_quality).toFixed(2);
    const qcls = m.avg_quality != null ? (m.avg_quality >= 0.8 ? "good" : "warn") : "";

    const pct = (v) => (v == null ? "—" : `${(Number(v) * 100).toFixed(1)}%`);

    let html = "";
    html += tile("TOTAL DOCS", m.total_docs ?? "—");
    html += tile("ARCHIVED", m.archived ?? "—", "good");
    html += tile("REVIEW", m.review ?? "—", "warn");
    if (m.reconsideration) {
      html += tile("RECONSIDER", m.reconsideration, "warn");
    }
    html += tile("FAILED", m.failed ?? "—", m.failed ? "bad" : "");
    html += tile("IN FLIGHT", m.in_flight ?? "—");
    html += tile("LLM CALLS", Mailroom.fmt.tokens(m.llm_calls));
    html += tile("TOTAL COST", Mailroom.fmt.cost(m.total_cost_usd));
    html += tile("TOTAL TOKENS", Mailroom.fmt.tokens(m.total_tokens));
    html += tile("AVG COST / DOC", Mailroom.fmt.cost(m.avg_cost_usd));
    html += tile("AVG LATENCY", Mailroom.fmt.latency(m.avg_latency_s));
    html += tile("P95 GEN LATENCY", m.p95_generation_latency_s != null ? Mailroom.fmt.latency(m.p95_generation_latency_s) : "—");
    html += tile("AVG QUALITY", quality, qcls);
    if (m.n_grounded_runs) {
      // Grounded-run extraction quality — mirrors llm-mailroom SCORE_CONFIGS
      // deterministic scoring + the entity-extraction diagnostics.
      html += tile("GROUNDED RUNS", m.n_grounded_runs, "good");
      html += tile("FIELD SCORE", pct(m.avg_extraction_field_score),
        m.avg_extraction_field_score >= 0.8 ? "good" : "warn");
      html += tile("OVERALL SCORE", pct(m.avg_extraction_overall_score),
        m.avg_extraction_overall_score >= 0.8 ? "good" : "warn");
      html += tile("LIST PRECISION", pct(m.avg_entity_list_precision));
      html += tile("LIST RECALL", pct(m.avg_entity_list_recall));
      html += tile("HALLUCINATION", pct(m.avg_hallucination_rate),
        m.avg_hallucination_rate <= 0.05 ? "good" : "bad");
      html += tile("FIELD PRESENCE", pct(m.avg_expected_field_presence));
    }
    if (m.avg_extraction_verified_precision != null) {
      html += tile("VERIFIED PRECISION", pct(m.avg_extraction_verified_precision),
        m.avg_extraction_verified_precision >= 0.8 ? "good" : "warn");
    }
    if (m.avg_content_topic_accuracy != null) {
      html += tile("TOPIC ACC", pct(m.avg_content_topic_accuracy));
    }
    if (m.avg_content_topic_f1_macro != null) {
      html += tile("TOPIC F1", pct(m.avg_content_topic_f1_macro));
    }
    if (m.avg_sentiment_accuracy != null) {
      html += tile("SENTIMENT ACC", pct(m.avg_sentiment_accuracy));
    }
    if (m.avg_sentiment_f1_macro != null) {
      html += tile("SENTIMENT F1", pct(m.avg_sentiment_f1_macro));
    }
    if (m.avg_maud_question_accuracy != null) {
      html += tile("MAUD Q ACC", pct(m.avg_maud_question_accuracy));
    }
    if (m.avg_maud_question_macro_accuracy != null) {
      html += tile("MAUD Q MACRO", pct(m.avg_maud_question_macro_accuracy));
    }
    if (m.avg_maud_clause_presence != null) {
      html += tile("MAUD CLAUSE", pct(m.avg_maud_clause_presence));
    }
    if (m.avg_maud_valid_class_rate != null) {
      html += tile("MAUD VALID", pct(m.avg_maud_valid_class_rate));
    }
    if (m.avg_maud_category_accuracy != null) {
      html += tile("MAUD CATEGORY", pct(m.avg_maud_category_accuracy));
    }
    if (m.avg_run_duration_s != null) {
      html += tile("AVG RUN DURATION", Mailroom.fmt.latency(m.avg_run_duration_s));
    }
    if (m.avg_classification_attempts != null && m.avg_classification_attempts > 1) {
      html += tile("AVG CLASSIFY RETRIES", Number(m.avg_classification_attempts - 1).toFixed(2), "warn");
    }
    if (m.avg_extraction_attempts != null && m.avg_extraction_attempts > 1) {
      html += tile("AVG EXTRACT RETRIES", Number(m.avg_extraction_attempts - 1).toFixed(2), "warn");
    }
    if (vBars.length) html += bars("JUDGE VERDICTS", vBars, "#5f9e6e");
    if (docBars.length) html += bars("DOC TYPES", docBars, "#d9a866");
    if (subclassBars.length) html += bars("DOC SUBCLASSES", subclassBars, "#8aa3c0");
    if (rawRuns && rawRuns.length) html += trendBars(rawRuns);
    gridEl.innerHTML = html || `<div class="hint mono">NO METRICS YET</div>`;
  }

  // V-27: default window matches the floor's MAILROOM_RECENT_WINDOW (7d) —
  // the old 1h default showed zeros whenever no runs happened in the hour.
  async function refresh(since = 604800) {
    gridEl.innerHTML = `<div class="hint mono">LOADING METRICS FROM LANGFUSE…</div>`;
    try {
      let data;
      let rawRuns = [];
      if (window.Mailroom.demoMode) {
        rawRuns = window.Mailroom.demoRuns || [];
        data = computeLocalMetrics(rawRuns);
      } else {
        data = await Mailroom.api.metrics(since);
        // Also fetch raw runs for the trend chart (optional — but V-18: a
        // failure must be visible, not silently swallowed)
        try {
          const tdata = await Mailroom.api.traces(since, 200);
          rawRuns = tdata.runs || [];
        } catch (e) {
          console.warn("[mailroom] trend data unavailable:", e.message || e);
        }
      }
      render(data, rawRuns);
      return data;
    } catch (err) {
      gridEl.innerHTML = `<div class="insp-error">metrics unavailable — ${Mailroom.esc(err.message || String(err))}</div>`;
      throw err;
    }
  }

  return { refresh, computeLocalMetrics };
})();