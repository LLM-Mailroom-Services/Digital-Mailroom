/* eslint-env browser */
/* md.js — minimal, safe Markdown → HTML for the served board.
 *
 * Design: ESCAPE-FIRST. Every byte of input is HTML-escaped at the block
 * level and again per inline segment before any token is emitted, so the
 * only tags that can appear are the ones this renderer emits itself
 * (p / strong / em / del / code / pre / a / ul / ol / li / blockquote /
 * h1-h4 / br / hr). Renderers never produce attributes except whitelisted
 * link hrefs (http/https only — javascript:, data: etc. are dropped and
 * the link text is kept as plain text).
 *
 * Subset: `**bold**`, `*italic*`, `~~strike~~`, `` `code` ``, fenced /
 * 4-space-indented code, `#`–`####` headings, `- ` / `1. ` lists, `> `
 * quotes, `[t](url)` links, `---` rules, blank-line-separated paragraphs.
 * Deliberately NOT supported: images (CSP 'self' anyway), `_italic_`
 * (snake_case collisions), inline HTML (never rendered), tables.
 */
window.mdToHtml = (function () {
  'use strict';

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function safeUrl(url) {
    var u = String(url).replace(/[\x00-\x20"'<>`\\]/g, '');
    if (!/^https?:\/\/[^\s]+$/i.test(u)) return null;
    return u;
  }

  /* Inline formatting on an already-escaped segment. Code spans are pulled
   * out first (placeholder tokens), so asterisks/links inside code are
   * never mistaken for markup. */
  function inlineEscape(raw) {
    var esc = escapeHtml(raw);
    var placeholder = '\u0001';
    var codes = [];
    var last = 0;
    var out = '';
    var re = /`([^`\n]+)`/g;
    var m;
    while ((m = re.exec(esc)) !== null) {
      out += esc.slice(last, m.index);
      codes.push(m[1]);
      out += placeholder + (codes.length - 1) + placeholder;
      last = m.index + m[0].length;
    }
    out += esc.slice(last);

    out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    out = out.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    out = out.replace(/~~([^~]+)~~/g, '<del>$1</del>');
    out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, function (_, text, url) {
      var href = safeUrl(url);
      if (!href) return text;
      return '<a href="' + escapeHtml(href) + '" target="_blank" rel="noopener noreferrer">' + text + '</a>';
    });

    out = out.replace(/\u0001(\d+)\u0001/g, function (_, i) { return '<code>' + codes[+i] + '</code>'; });
    return out;
  }

  function mdToHtml(text) {
    if (!text) return '';
    var lines = String(text).replace(/\r\n?/g, '\n').split('\n');
    var out = [];
    var para = [];
    var list = null;      /* { type: 'ul' | 'ol', items: [] } */
    var quote = [];
    var code = null;      /* { lines: [], fenced: bool } */
    var i, line, match;

    function flushPara() {
      if (para.length) {
        out.push('<p>' + para.map(inlineEscape).join(' ') + '</p>');
        para = [];
      }
    }
    function flushList() {
      if (!list) return;
      var tag = list.type;
      out.push('<' + tag + '>' + list.items.map(function (it) {
        return '<li>' + inlineEscape(it) + '</li>';
      }).join('') + '</' + tag + '>');
      list = null;
    }
    function flushQuote() {
      if (!quote.length) return;
      out.push('<blockquote>' + quote.map(function (q) {
        return '<p>' + inlineEscape(q) + '</p>';
      }).join('') + '</blockquote>');
      quote = [];
    }
    function flushCode() {
      if (!code) return;
      out.push('<pre><code>' + escapeHtml(code.lines.join('\n')) + '</code></pre>');
      code = null;
    }

    for (i = 0; i < lines.length; i++) {
      line = lines[i];

      /* fenced code: emit verbatim-escaped, never inline-parsed */
      if (/^```/.test(line)) {
        if (code && code.fenced) {
          flushCode();
        } else {
          flushPara(); flushList(); flushQuote(); flushCode();
          code = { lines: [], fenced: true };
        }
        continue;
      }
      if (code) {
        /* 4-space-indented block (fenced=false) or fence body */
        code.lines.push(line);
        continue;
      }

      if (/^\s*$/.test(line)) { flushPara(); flushList(); flushQuote(); continue; }
      if (/^\s*(---|\*\*\*)\s*$/.test(line)) { flushPara(); flushList(); flushQuote(); out.push('<hr>'); continue; }

      match = /^(#{1,4})\s+(.*)$/.exec(line);
      if (match) {
        flushPara(); flushList(); flushQuote();
        var h = match[1].length;
        out.push('<h' + h + '>' + inlineEscape(match[2]) + '</h' + h + '>');
        continue;
      }

      match = /^>\s?(.*)$/.exec(line);
      if (match) { flushPara(); flushList(); quote.push(match[1]); continue; }
      flushQuote();

      match = /^([-*])\s+(.*)$/.exec(line);
      if (match) {
        flushPara();
        if (!list || list.type !== 'ul') { flushList(); list = { type: 'ul', items: [] }; }
        list.items.push(match[2]);
        continue;
      }
      match = /^(\d+)[.)]\s+(.*)$/.exec(line);
      if (match) {
        flushPara();
        if (!list || list.type !== 'ol') { flushList(); list = { type: 'ol', items: [] }; }
        list.items.push(match[2]);
        continue;
      }
      flushList();

      match = /^( {4}|\t)(.*)$/.exec(line);
      if (match) {
        flushPara(); flushList();
        code = { lines: [match[2]], fenced: false };
        continue;
      }

      para.push(line);
    }

    flushCode();
    flushPara();
    flushList();
    flushQuote();
    return out.join('');
  }

  return mdToHtml;
})();
