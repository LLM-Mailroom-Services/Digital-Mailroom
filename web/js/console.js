/* The-Mailroom live console: a scrolling log of pipeline activity.
 *
 * GH Pages edition: doubles as the agent debug console — every line is
 * mirrored into window.__MAILROOM_DEBUG__, and the DEBUG toggle (or ?debug=1)
 * reveals low-level lines + verbose capture output. */

const ConsoleView = (() => {
  const el = document.getElementById("console-log");
  const toolsEl = document.getElementById("console-tools");
  const MAX_LINES = 500;

  function stamp() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  }

  function append(line) {
    el.appendChild(line);
    while (el.children.length > MAX_LINES) el.removeChild(el.firstChild);
    el.scrollTop = el.scrollHeight;
  }

  function log(msg, cls = "") {
    if (window.Mailroom && Mailroom.capture) Mailroom.capture("log", { msg: String(msg), cls });
    const line = document.createElement("div");
    line.className = `line ${cls}`;
    line.textContent = `[${stamp()}] ${msg}`;
    append(line);
  }

  function banner(msg) {
    if (window.Mailroom && Mailroom.capture) Mailroom.capture("log", { msg: `*** ${msg} ***`, cls: "banner" });
    const line = document.createElement("div");
    line.className = "line banner";
    line.textContent = `*** ${msg} ***`;
    append(line);
  }

  // DEBUG toggle: shows c-dim detail lines and flips verbose capture
  // (?debug=1 pre-enables; state persists via localStorage).
  function setDebug(on) {
    if (window.__MAILROOM_DEBUG__) window.__MAILROOM_DEBUG__.setVerbose(on);
    el.classList.toggle("hide-dim", !on);
    const btn = document.getElementById("debug-toggle");
    if (btn) btn.textContent = on ? "DEBUG ON" : "DEBUG OFF";
    if (toolsEl) toolsEl.hidden = false;
  }

  function wireToggle() {
    const btn = document.getElementById("debug-toggle");
    if (!btn) return;
    btn.addEventListener("click", () => {
      const current = window.__MAILROOM_DEBUG__ ? window.__MAILROOM_DEBUG__.verbose : false;
      const on = !current;
      try { localStorage.setItem("mailroom.debug", on ? "1" : "0"); } catch (e) { /* storage blocked */ }
      setDebug(on);
      log(`DEBUG MODE ${on ? "ON" : "OFF"}`, on ? "c-ok" : "c-warn");
    });
    setDebug(window.__MAILROOM_DEBUG__ ? window.__MAILROOM_DEBUG__.verbose : false);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wireToggle);
  } else {
    wireToggle();
  }

  return { log, banner };
})();
