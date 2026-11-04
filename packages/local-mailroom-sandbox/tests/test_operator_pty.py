"""`sandbox tui` driven through a real pseudo-terminal (readline, Tab, Ctrl keys).

Stdlib ``pty`` only; no network, no paid commands. Each step waits for the
prompt instead of sleeping, so the suite stays fast. POSIX only.
"""
from __future__ import annotations

import codecs
import os
import re
import select
import signal
import sys
import time

import pytest

pty = pytest.importorskip("pty")
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX pseudo-terminal")

PROMPT = "mailroom> "
try:  # the child runs this same interpreter, so it has the same readline backend
    import readline as _readline
    from mailroom_sandbox.tui.shell import uses_libedit

    _LIBEDIT = uses_libedit(_readline)
except ImportError:
    _LIBEDIT = False
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[=>]|[\r\x07]")
_PARTIAL_ESCAPE = re.compile(r"\x1b\[?[0-9;?]*\Z")  # an escape split across two reads


class Terminal:
    def __init__(self) -> None:
        self.pid, self.fd = pty.fork()
        if self.pid == 0:  # child: the real CLI entry point inside the pty
            os.environ.update(TERM="xterm", SANDBOX_PROFILE="ollama", NO_COLOR="1")
            os.execvp(sys.executable, [sys.executable, "-c",
                      "import sys; from mailroom_sandbox.cli import main; sys.exit(main(['tui']))"])
        self.buf = ""
        self._pending = ""  # undecoded tail: a control sequence cut off mid-read
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")  # keeps split multibyte chars

    def read_until(self, needle: str, timeout: float = 20.0) -> str:
        end = time.monotonic() + timeout
        while needle not in self.buf:
            remaining = end - time.monotonic()
            if remaining <= 0:
                raise AssertionError(f"timed out waiting for {needle!r}; got:\n{self.buf[-2000:]}")
            ready, _, _ = select.select([self.fd], [], [], min(remaining, 0.2))
            if ready:
                try:
                    data = os.read(self.fd, 65536)
                except OSError:  # child exited and closed the pty
                    data = b""
                if not data:
                    raise AssertionError(f"terminal closed waiting for {needle!r}; got:\n{self.buf[-2000:]}")
                text = self._pending + self._decoder.decode(data)
                cut = _PARTIAL_ESCAPE.search(text)
                self._pending = text[cut.start():] if cut else ""
                self.buf += _ANSI.sub("", text[:cut.start()] if cut else text)
        head, _, self.buf = self.buf.partition(needle)
        return head

    def send(self, keys: str) -> None:
        os.write(self.fd, keys.encode())

    def run(self, line: str) -> str:
        """Type a line, return everything printed before the next prompt."""
        self.send(line + "\n")
        self.read_until("\n")  # the terminal's echo of what was typed
        return self.read_until(PROMPT)

    def exit_status(self, timeout: float = 10.0) -> int:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            pid, status = os.waitpid(self.pid, os.WNOHANG)
            if pid:
                return os.waitstatus_to_exitcode(status)
            try:  # drain so the child never blocks on a full pty buffer
                if select.select([self.fd], [], [], 0.1)[0]:
                    os.read(self.fd, 65536)
            except OSError:
                pass
        raise AssertionError("tui did not exit")

    def close(self) -> None:
        try:
            os.kill(self.pid, signal.SIGKILL)
            os.waitpid(self.pid, 0)
        except (ProcessLookupError, ChildProcessError):
            pass
        os.close(self.fd)


@pytest.fixture
def term():
    t = Terminal()
    t.read_until(PROMPT, timeout=60)  # cold import of the CLI
    yield t
    t.close()


def test_nested_numeric_menus_back_and_leaf(term):
    root = term.run("menu")
    assert "sandbox\n" in root and "Select a number · help" in root
    assert re.search(r"\d+\. run\s+Spec-driven job lifecycle", root)
    index = int(re.search(r"(\d+)\. run\b", root).group(1))
    run_menu = term.run(str(index))
    assert run_menu.lstrip("\n").startswith("sandbox run") and "start" in run_menu and "· back" in run_menu
    start = int(re.search(r"(\d+)\. start\b", run_menu).group(1))
    leaf = term.run(str(start))
    assert "sandbox run start  (leaf command)" in leaf and "usage: sandbox run start" in leaf
    assert "has no subcommands" in term.run("1")
    assert term.run("back").lstrip("\n").startswith("sandbox run")
    assert term.run("back").lstrip("\n").startswith("sandbox\n")
    assert "Already at the top menu" in term.run("back")


@pytest.mark.parametrize("entry", ["0", "99", "-1"])
def test_out_of_range_menu_numbers_stay_in_the_menu(term, entry):
    term.run("menu run")
    out = term.run(entry)
    assert "select 1-" in out and "invalid choice" not in out
    assert "· back" in term.run("menu run")  # still navigable afterwards


def test_numbers_and_back_without_a_menu(term):
    assert "no open menu" in term.run("3")
    assert "no open menu" in term.run("back")


def test_unknown_commands_suggest_matches(term):
    assert "did you mean experiment" in term.run("menu experment")
    out = term.run("help run statsu")
    assert "unknown command 'run statsu'" in out and "status" in out
    assert "invalid choice" not in out


def test_tab_completion_history_and_line_editing(term):
    term.send("menu experim\t")
    term.read_until("menu experiment")
    term.send("\n")  # the completed word dispatches as typed
    assert "sandbox experiment" in term.read_until(PROMPT)
    term.send("menu run st\t")  # two matches: readline completes the common prefix
    term.read_until("menu run sta")
    term.send("\x15")  # Ctrl+U clears the line
    assert "usage: sandbox profiles" in term.run("profiles --help")
    term.run("history")  # `history` itself is not recorded
    term.send("\x1b[A")  # Up arrow recalls the last real command
    term.read_until("profiles --help")
    term.send("\x15")
    out = term.run("history")
    assert "profiles --help" in out
    term.run("menu run")
    term.run("2")
    assert "\n2\n" not in term.run("history")  # menu navigation is not recalled


def test_credentials_never_enter_history(term):
    term.run("profiles --api-key sk-or-dummy")
    assert "sk-or-dummy" not in term.run("history")


def test_ctrl_c_returns_to_prompt_and_ctrl_d_exits(term):
    term.send("half typed")
    # Wait until readline has consumed (echoed) every byte: a Ctrl+C that lands
    # while bytes are still queued makes the tty flush them, and readline's
    # rl_getc then blocks on the discarded input until the next key.
    term.read_until("half typed")
    term.send("\x03")
    assert "Interrupted" in term.read_until(PROMPT)
    assert "modal-vllm" in term.run("profiles")  # still dispatching after the interrupt
    term.send("\x04")
    assert term.exit_status() == 0


def test_tui_inside_tui_and_exit(term):
    assert "Already in the Mailroom terminal" in term.run("tui")
    term.send("exit\n")
    assert term.exit_status() == 0


def test_two_level_eval_menu_prefills_the_target_command(term):
    level1 = term.run("menu eval")
    assert "1. specialist" in level1 and "2. pipeline" in level1 and "judge" not in level1
    level2 = term.run("1")
    assert "2. contract" in level2 and "eval specialist contract" in level2
    term.send("2\n")
    term.read_until("\n")  # echo of the selection
    if _LIBEDIT:  # libedit never runs readline's startup hook: recall via history
        assert "press ↑ to recall: eval specialist contract" in term.read_until(PROMPT)
        term.send("\x1b[A")
        term.read_until("eval specialist contract")
        term.send(" --mock --dry-run\n")  # the recalled line has no trailing space
    else:
        term.read_until(PROMPT + "eval specialist contract ")  # prefilled, not executed
        term.send("--mock --dry-run\n")
    out = term.read_until(PROMPT)
    assert '"task": "contracts_specialist"' in out
    assert "error: select 1-6" in term.run("menu eval pipeline") + term.run("9")
