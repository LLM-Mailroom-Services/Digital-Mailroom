/* Cache-only pipeline advisory. No local Dojo inspection or network requests. */
const DojoUpdateNotice = (() => {
  const RELEASE_URL = "https://github.com/Exios66/llm-dojo-scoring/releases/latest";
  const release = "[0-9]{1,9}(?:\\.[0-9]{1,9}){1,3}";
  const installedPattern = new RegExp(`^${release}(?:(?:a|b|rc)[0-9]{1,9})?(?:\\.post[0-9]{1,9})?(?:\\.dev[0-9]{1,9})?(?:\\+[a-z0-9]+(?:[.-][a-z0-9]+)*)?$`);
  const stablePattern = new RegExp(`^${release}(?:\\.post[0-9]{1,9})?$`);
  const version = (s, pattern) => typeof s === "string" && s.length <= 64
    && !/[\r\n\u2028\u2029]/.test(s) && pattern.test(s);

  function text(ops) {
    const u = ops && ops.configured === true && ops.dojo_update;
    if (!u || u.status !== "update_available"
        || !version(u.installed_version, installedPattern) || !version(u.latest_version, stablePattern)
        || typeof u.checked_at !== "number" || !Number.isFinite(u.checked_at)
        || u.checked_at < 0 || u.checked_at > 253402300799
        || typeof u.stale !== "boolean" || typeof u.cache_persisted !== "boolean"
        || !["cache", "network", "none"].includes(u.source)
        || !(u.error === null || (typeof u.error === "string" && u.error.length <= 64 && /^[a-z][a-z0-9_]*$/.test(u.error)))
        || u.release_url !== RELEASE_URL) return "";
    const checked = new Date(u.checked_at * 1000).toISOString().replace(/\.\d{3}Z$/, "Z");
    const freshness = u.stale ? "stale; recheck needed" : "release page may have changed";
    return `Dojo update available for pipeline: installed ${u.installed_version}; available ${u.latest_version}. Cached release result checked ${checked} (${freshness}).`;
  }

  function render(el, ops) {
    if (!el) return;
    const message = text(ops);
    if (!message) {
      el.hidden = true;
      el.replaceChildren();
      return;
    }
    // Keep an unchanged link node (and keyboard focus) across ops snapshots.
    if (el.firstChild && el.firstChild.textContent === message + " ") return;
    const label = document.createElement("span");
    label.textContent = message + " ";
    const link = document.createElement("a");
    link.textContent = "View Dojo releases";
    link.href = RELEASE_URL;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    el.replaceChildren(label, link);
    el.hidden = false;
  }

  return { render };
})();
