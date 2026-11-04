"""Local interactive CLI; dispatches the existing parser, never a system shell."""
from __future__ import annotations

import argparse
import contextlib
import difflib
import shlex
import signal
import sys
import threading


def children(parser: argparse.ArgumentParser) -> dict[str, argparse.ArgumentParser]:
    """Visible subcommands; ones marked ``_sandbox_hidden`` still parse but stay out of menus."""
    return {name: child for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
            for name, child in action.choices.items()
            if not getattr(child, "_sandbox_hidden", False)}


def hidden(parser: argparse.ArgumentParser) -> list[str]:
    """Subcommands that parse but stay out of menus (legacy eval tasks)."""
    return [name for action in parser._actions if isinstance(action, argparse._SubParsersAction)
            for name, child in action.choices.items() if getattr(child, "_sandbox_hidden", False)]


def summaries(parser: argparse.ArgumentParser) -> dict[str, str]:
    """One-line help per subcommand, as argparse lists it under the parent."""
    return {choice.dest: " ".join((choice.help or "").split())
            for action in parser._actions if isinstance(action, argparse._SubParsersAction)
            for choice in action._choices_actions}


def command_catalog(parser: argparse.ArgumentParser, path: tuple[str, ...] = ()) -> list[dict]:
    """One parser-derived catalog for completion, menus and browser manuals."""
    return [{"path": list(path), "help": parser.format_help(), "children": list(children(parser)),
             "usage": " ".join(parser.format_usage().split()), "summaries": summaries(parser),
             "targets": list(getattr(parser, "_sandbox_targets", [])), "hidden": hidden(parser)},
            *[row for name, child in children(parser).items()
              for row in command_catalog(child, (*path, name))]]


def render_menu(node: dict) -> str:
    """Compact numbered menu: the choices, not the whole manual (help shows that)."""
    path = " ".join(["sandbox", *node["path"]])
    if node.get("targets"):
        # Level 2 of a primary task: each target is a ready command line.
        width = len(str(len(node["targets"])))
        label_w = max(len(label) for label, _ in node["targets"])
        rows = [f"{i:>{width}}. {label:<{label_w}}  {command}" for i, (label, command) in enumerate(node["targets"], 1)]
        return "\n".join([path, *rows, "Select a number to put that command on the prompt (add --mock to run offline) · back"])
    if not node["children"]:
        return (f"{path}  (leaf command)\n{node['usage']}\n"
                f"Type '{' '.join(node['path'])} <options>' to execute · help {' '.join(node['path'])} for the manual · back")
    width = len(str(len(node["children"])))
    name_w = max(len(name) for name in node["children"])
    rows = [f"{i:>{width}}. {name:<{name_w}}  {node['summaries'].get(name, '')}".rstrip()
            for i, name in enumerate(node["children"], 1)]
    back = " · back" if node["path"] else ""
    return "\n".join([path, *rows, f"Select a number{back} · help [command] for a manual · or type a full command"])


def unknown_path(words: list[str], catalog: list[dict]) -> str | None:
    """Name the first unknown command word and suggest the closest siblings."""
    node, known = catalog[0], []
    for word in words:
        if word.startswith("-") or word in node.get("hidden", ()):
            return None
        if word not in node["children"]:
            close = difflib.get_close_matches(word, node["children"], n=3)
            hint = f" · did you mean {', '.join(close)}?" if close else f" · try menu {' '.join(known)}".rstrip()
            shown = " ".join([*known, word])
            shown = shown if len(shown) <= 60 else shown[:59] + "…"
            return f"error: unknown command '{shown}'{hint}"
        known.append(word)
        node = next(row for row in catalog if row["path"] == known)
        if not node["children"]:
            return None
    return None


def completions(line: str, catalog: list[dict]) -> list[str]:
    """Complete command paths only; quoted arguments are left to argparse."""
    try:
        tokens = shlex.split(line)
    except ValueError:
        return []
    if tokens[:1] == ["sandbox"]:
        tokens = tokens[1:]
    if tokens[:1] in (["help"], ["man"], ["menu"]):
        tokens = tokens[1:]
    if line.endswith(" "):
        parent, prefix = tokens, ""
    else:
        parent, prefix = tokens[:-1], tokens[-1] if tokens else ""
    node = next((row for row in catalog if row["path"] == parent), None)
    return [name for name in (node["children"] if node else []) if name.startswith(prefix)]


def uses_libedit(readline) -> bool:
    """libedit's readline emulation never calls the startup/pre-input hooks."""
    return getattr(readline, "backend", None) == "editline" or "libedit" in (readline.__doc__ or "")


@contextlib.contextmanager
def interruptible_prompt(interval: float = 0.05):
    """Keep Ctrl+C responsive while readline waits for a line.

    CPython's readline loop only raises a pending KeyboardInterrupt when its
    ``select()`` fails with EINTR. A SIGINT that lands after readline consumed a
    keystroke but before that ``select()`` starts only sets a flag, and the
    prompt froze until the next key. A short no-op SIGALRM heartbeat interrupts
    the ``select()`` (never restarted, even with SA_RESTART), so the interrupt
    surfaces within ``interval``. SA_RESTART keeps every other read/write
    uninterrupted, and the previous handler is restored before any command
    runs. An ``ITIMER_REAL`` alarm that is already armed is left alone (no
    heartbeat) so its deadline still fires on time.

    Not fixable from Python: Ctrl+C while typed bytes are still queued. The tty
    flushes them on INTR and readline's own ``rl_getc`` keeps waiting for the
    discarded byte (it retries on EINTR) until another key arrives.
    """
    if (not hasattr(signal, "setitimer") or threading.current_thread() is not threading.main_thread()
            or signal.getitimer(signal.ITIMER_REAL)[0] > 0):
        yield  # an alarm already armed (e.g. inherited across exec) keeps its deadline
        return
    previous = signal.signal(signal.SIGALRM, lambda signum, frame: None)
    signal.siginterrupt(signal.SIGALRM, False)
    old_timer = signal.setitimer(signal.ITIMER_REAL, interval, interval)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *old_timer)
        signal.signal(signal.SIGALRM, signal.SIG_DFL if previous is None else previous)


def run_shell(default_args: list[str] | None = None) -> int:
    from mailroom_sandbox import cli

    if not sys.stdin.isatty():
        raise cli.CLIUsageError("tui requires an interactive terminal; use sandbox --help in scripts")
    parser = cli.build_parser()
    catalog = command_catalog(parser)
    try:
        import readline
    except ImportError:
        readline = None
    old_completer = readline.get_completer() if readline else None
    if readline:
        def complete(text, state):
            matches = completions(readline.get_line_buffer(), catalog)
            return matches[state] if state < len(matches) else None
        readline.set_completer(complete)
        readline.parse_and_bind("bind ^I rl_complete" if uses_libedit(readline) else "tab: complete")
        readline.set_auto_history(False)
    history: list[str] = []
    menu: list[str] | None = None
    print("THE MAILROOM · local command terminal\nTab completes · ↑/↓ history · Ctrl+C interrupt · Ctrl+D exit\nmenu [command] · help [command] · history · clear · exit\nExisting CLI spend/initials gates still apply. No persistent command history.")
    try:
        while True:
            try:
                with interruptible_prompt():
                    line = input("mailroom> ").strip()
                if not line:
                    continue
                argv = shlex.split(line)
                if argv[:1] == ["sandbox"]:
                    argv = argv[1:]
                if not argv:
                    continue
                if argv[0] in {"exit", "quit"}:
                    return 0
                if argv == ["clear"]:
                    print("\033[2J\033[H", end="")
                    continue
                if argv == ["history"]:
                    print("\n".join(history))
                    continue
                # Never retain pasted credentials, even in this process's history;
                # bare menu navigation (numbers, back) is not worth recalling either.
                sensitive = any(word in line.lower() for word in ("token", "secret", "api-key", "sk-or-", "hf_"))
                navigation = argv == ["back"] or (len(argv) == 1 and argv[0].lstrip("-").isdigit())
                if not sensitive and not navigation:
                    history.append(line)
                    if readline:
                        readline.add_history(line)
                if argv == ["back"]:
                    if menu is None:
                        print("error: no open menu · type menu to browse commands")
                        continue
                    if not menu:
                        print("Already at the top menu · select a number or type a command")
                        continue
                    argv = ["menu", *menu[:-1]]
                elif len(argv) == 1 and argv[0].lstrip("-").isdigit():
                    node = next((row for row in catalog if row["path"] == menu), None) if menu is not None else None
                    if node is None:
                        print("error: no open menu · type menu to browse commands")
                        continue
                    index = int(argv[0]) - 1
                    if node.get("targets"):
                        if not 0 <= index < len(node["targets"]):
                            print(f"error: select 1-{len(node['targets'])} from the menu")  # nosec B608 - menu text, not SQL
                            continue
                        command = node["targets"][index][1] + " "
                        if readline and uses_libedit(readline):
                            # libedit ignores the startup hook, so a prefill would be
                            # silently dropped; queue it as the newest history entry
                            # (libedit drops the trailing space on recall).
                            readline.add_history(command.strip())
                            print(f"press ↑ to recall: {command.strip()} · then a space, options, Enter")
                        elif readline:
                            # Prefill the next prompt; nothing runs until Enter.
                            readline.set_startup_hook(lambda text=command: (readline.insert_text(text), readline.set_startup_hook(None)))
                        else:
                            print(f"type: {command.strip()} [--mock]")
                        continue
                    if not node["children"]:
                        print(f"error: {' '.join(['sandbox', *menu])} has no subcommands · back, or type the command with options")
                        continue
                    if not 0 <= index < len(node["children"]):
                        print(f"error: select 1-{len(node['children'])} from the menu")  # nosec B608 - menu text, not SQL
                        continue
                    argv = ["menu", *menu, node["children"][index]]
                if argv[0] == "menu":
                    path = argv[1:]
                    node = next((row for row in catalog if row["path"] == path), None)
                    if node is None:
                        print(unknown_path(path, catalog) or "error: unknown command path")
                        continue
                    menu = path
                    print(render_menu(node))
                    continue
                menu = None
                if argv[0] in {"help", "man"}:
                    problem = unknown_path(argv[1:], catalog)
                    if problem:
                        print(problem)
                        continue
                    argv = [*argv[1:], "--help"]
                else:
                    # Same one-line answer as help/menu, not argparse's full usage dump.
                    problem = unknown_path(argv, catalog)
                    if problem:
                        print(problem)
                        continue
                if argv[0] == "tui":
                    print("Already in the Mailroom terminal.")
                    continue
                try:
                    rc = cli.main([*(default_args or []), *argv])
                except SystemExit as exc:
                    rc = exc.code
                if rc:
                    print(f"command exited {rc}")
            except EOFError:
                print()
                return 0
            except KeyboardInterrupt:
                print("\nInterrupted · back at the prompt")
            except (ValueError, OSError) as exc:
                print(f"error: {exc}")
    finally:
        if readline:
            readline.set_completer(old_completer)
            readline.set_auto_history(True)


OPERATOR_CSS = """
.operator { margin: 16px 0; border: 1px solid var(--cyan); border-radius: 6px; background: #050f1a; }
.operator h2 { padding: 10px; margin: 0; color: var(--gold); font-size: 14px; border-bottom: 1px solid #294051; }
.operator .tools, .operator form { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 8px 10px; }
.operator input, .operator select, .operator button { font: inherit; color: var(--snow); background: #071a2e; border: 1px solid var(--cyan); padding: 8px; border-radius: 3px; max-width: 100%; }
.operator input { flex: 1; min-width: 140px; }
.operator pre { white-space: pre-wrap; overflow-wrap: anywhere; height: min(52vh, 560px); overflow: auto; padding: 16px; margin: 0; line-height: 1.6; }
.operator .hint { padding: 0 10px 10px; color: #b6c8d8; font-size: 11px; }
"""

OPERATOR_HTML = """
<section class="operator" data-view="terminal" id="view-terminal" role="tabpanel" aria-labelledby="tab-terminal" hidden>
  <h2 id="terminal-heading">Command terminal</h2>
  <div class="tools"><button type="button" id="command-back">← Parent</button>
    <label>Command <select id="command-menu" aria-label="Nested CLI commands"></select></label>
    <span id="command-path">sandbox</span></div>
  <pre id="command-output" tabindex="0" aria-label="Command output">Loading command catalog…</pre>
  <form id="command-form"><label for="command-input">mailroom&gt;</label>
    <input id="command-input" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="help · status · config · campaign" aria-describedby="command-hint">
    <button type="submit">Enter</button></form>
  <div class="hint" id="command-hint">Tab completes · ↑/↓ history · Ctrl+L clears · Escape resets. Browser commands inspect live state and CLI manuals. Execute full commands locally with <code>sandbox tui</code>; no paid actions run from this page.</div>
</section>
"""

OPERATOR_JS = r"""
let operatorState = {};
let commandCatalog = [];
let commandPath = [];
const commandHistory = [];
let historyIndex = 0;
const commandOutput = document.getElementById("command-output");
const commandInput = document.getElementById("command-input");
function commandPrint(text) {
  commandOutput.textContent = (commandOutput.textContent + "\n" + text).slice(-24000);
  commandOutput.scrollTop = commandOutput.scrollHeight;
}
function commandNode(path) { return commandCatalog.find(row => JSON.stringify(row.path) === JSON.stringify(path)); }
function menuText(node) {
  const path = ["sandbox", ...node.path].join(" ");
  if ((node.targets || []).length) {
    const width = Math.max(...node.targets.map(t => t[0].length));
    return [path, ...node.targets.map(([label, command], i) => `${String(i + 1).padStart(String(node.targets.length).length)}. ${label.padEnd(width)}  ${command}`),
      "Choose a target from the selector to put its command on the input"].join("\n");
  }
  if (!node.children.length) return `${path}  (leaf command)\n${node.usage || ""}\nRun locally: ${path} <options> · help ${node.path.join(" ")} for the manual`;
  const width = Math.max(...node.children.map(name => name.length));
  return [path, ...node.children.map((name, i) => `${String(i + 1).padStart(String(node.children.length).length)}. ${name.padEnd(width)}  ${(node.summaries || {})[name] || ""}`.trimEnd()),
    "Choose from the selector · help <command> for a manual"].join("\n");
}
function clip(text, max = 60) { return text.length > max ? text.slice(0, max - 1) + "…" : text; }
function editDistance(a, b) {
  // Optimal string alignment: a swapped pair of letters ("strat") costs one edit.
  const d = Array.from({length: a.length + 1}, (_, i) => [i, ...Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) d[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++) {
    d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
    if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
  }
  return d[a.length][b.length];
}
function closeNames(word, names) {
  const limit = Math.max(1, Math.floor(word.length / 3));
  return names.filter(name => (word.length >= 3 && name.startsWith(word)) || editDistance(word, name) <= limit).slice(0, 3);
}
function unknownPath(words) {
  let node = commandCatalog[0], known = [];
  for (const word of words) {
    if (word.startsWith("-") || (node.hidden || []).includes(word)) return null;
    if (!node.children.includes(word)) {
      const close = closeNames(word, node.children);
      return `Unknown command '${clip([...known, word].join(" "))}'` + (close.length ? ` · did you mean ${close.join(", ")}?` : " · type menu to browse");
    }
    known.push(word); node = commandNode(known);
    if (!node.children.length) return null;
  }
  return null;
}
function commandMenu(path, { manual = false } = {}) {
  const node = commandNode(path);
  if (!node) { commandPrint(unknownPath(path) || "Unknown command path. Type menu."); return; }
  commandPath = path;
  document.getElementById("command-path").textContent = "sandbox " + path.join(" ");
  const menu = document.getElementById("command-menu");
  const targets = node.targets || [];
  menu.replaceChildren(new Option(targets.length ? "Choose target…" : node.children.length ? "Choose subcommand…" : "Leaf command", ""));
  for (const child of node.children) menu.add(new Option(child, child));
  targets.forEach(([label], i) => menu.add(new Option(label, "#" + i)));
  menu.disabled = !node.children.length && !targets.length;
  commandPrint(manual ? node.help : menuText(node));
}
document.getElementById("command-menu").addEventListener("change", ev => {
  const value = ev.target.value;
  if (value.startsWith("#")) {
    const [label, command] = commandNode(commandPath).targets[Number(value.slice(1))];
    commandInput.value = command + " --mock";
    commandPrint(`${label}: run locally with  sandbox ${command} [--mock | --local]`);
    commandInput.focus(); ev.target.value = "";
  } else if (value) commandMenu([...commandPath, value]);
});
document.getElementById("command-back").addEventListener("click", () => commandMenu(commandPath.slice(0, -1)));
function commandRun(line) {
  const words = line.trim().split(/\s+/).filter(Boolean);
  if (words[0] === "sandbox") words.shift();
  const name = words[0] || "help";
  if (/(?:token|secret|api.key|sk-or-|hf_)/i.test(line)) {
    commandPrint("Credentials are not accepted in the browser terminal. Configure them in your local environment.");
    return;
  }
  if (!words.length && !line.trim()) { commandPrint("mailroom> "); return; }
  if (name === "clear") { commandOutput.textContent = ""; return; }
  commandPrint("mailroom> " + clip(line, 120));
  if (name === "history") { commandPrint(commandHistory.join("\n")); return; }
  commandHistory.push(line); if (commandHistory.length > 100) commandHistory.shift();
  historyIndex = commandHistory.length;
  const live = {status: operatorState.snapshot, config: operatorState.layout?.configuration,
    campaign: operatorState.campaign, services: operatorState.services, logs: operatorState.logs};
  if (Object.hasOwn(live, name)) {
    commandPrint(live[name] == null ? "Not available for the current run." : JSON.stringify(live[name], null, 2)); return;
  }
  if (["help", "man", "menu"].includes(name)) {
    if (words.length === 1 && name !== "menu") commandPrint("Live inspection: status · config · campaign · services · logs\nShell: menu [command] · help/man [command] · history · clear");
    commandMenu(words.slice(1), { manual: name !== "menu" }); return;
  }
  const path = words.filter(word => word !== "--help" && word !== "-h");
  if (commandNode(path)) { commandMenu(path, { manual: words.includes("--help") || words.includes("-h") }); commandPrint("Run locally: sandbox " + path.join(" ")); return; }
  const problem = unknownPath(path);
  if (problem) { commandPrint(problem); return; }
  const leaf = [];
  let hidden = false;
  for (const word of path) {
    // Hidden legacy tasks parse in the CLI but have no browser manual.
    if ((commandNode(leaf)?.hidden || []).includes(word)) { leaf.push(word); hidden = true; break; }
    if (!commandNode([...leaf, word])) break; leaf.push(word);
  }
  if (leaf.length && (hidden || !commandNode(leaf).children.length)) {
    const options = hidden ? `sandbox ${leaf.join(" ")} --help` : `help ${leaf.join(" ")}`;
    commandPrint(`This page does not run commands. Run it in a local terminal:\n  sandbox ${clip(words.join(" "), 200)}\nOptions: ${options}`);
    return;
  }
  commandPrint("Not a browser inspection command. Use help [command path], or execute with sandbox tui locally.");
}
document.getElementById("command-form").addEventListener("submit", ev => {
  ev.preventDefault(); const line = commandInput.value; commandInput.value = ""; commandRun(line);
});
commandInput.addEventListener("keydown", ev => {
  if (ev.key === "Tab") {
    ev.preventDefault();
    const words = commandInput.value.trimStart().split(/\s+/);
    const prefix = words.pop() || "";
    if (["sandbox", "help", "man", "menu"].includes(words[0])) words.shift();
    const local = words.length ? [] : ["help", "man", "menu", "status", "config", "campaign", "services", "logs", "history", "clear"];
    const matches = [...new Set([...local, ...(commandNode(words)?.children || [])])].filter(name => name.startsWith(prefix));
    if (matches.length === 1) commandInput.value = commandInput.value.slice(0, commandInput.value.length - prefix.length) + matches[0] + " ";
    else commandPrint(matches.join("  ") || "No matching commands");
  } else if (ev.key === "ArrowUp" || ev.key === "ArrowDown") {
    ev.preventDefault(); historyIndex = Math.max(0, Math.min(commandHistory.length, historyIndex + (ev.key === "ArrowUp" ? -1 : 1)));
    commandInput.value = commandHistory[historyIndex] || "";
  } else if (ev.key === "Escape") { commandInput.value = ""; }
  else if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "l") { ev.preventDefault(); commandOutput.textContent = ""; }
});
fetch("/api/commands", {cache: "no-store"}).then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
  .then(rows => { commandCatalog = rows; commandMenu([]); commandOutput.textContent = "THE MAILROOM · operator terminal\n\nLive commands    status · config · campaign · services · logs\nCLI navigation   help · man <command> · menu <command>\n\nChoose a command above or type help to begin.\nFull CLI execution: sandbox tui in your local terminal."; })
  .catch(err => { commandOutput.textContent = "Command catalog unavailable: " + err.message; });
"""
