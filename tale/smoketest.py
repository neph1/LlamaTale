"""
Automated smoke test for stories.

Starts a story headless with a dummy LLM backend (canned answers, see
backend_dummy.yaml / DummyIoUtil) and a scripted I/O connection, then feeds
it a list of commands (one per line), waiting for the driver to process each
one before sending the next. Exceptions that occur while the game runs are
recorded through the regular crash log (tale_crash.log, see tale.util.log_crash);
the smoke test compares that log before and after the run and raises
SmokeTestError if anything was appended to it.

Usage:
    python -m tale.smoketest --game stories/prancingllama --script stories/prancingllama/smoke_test.txt

Script format: one command per line; blank lines and lines starting with '#'
are ignored. The first lines usually answer the character creation dialog.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
import argparse
import logging
import os
import sys
import threading
import time
from typing import Callable, List, Optional, Sequence

from tale import util
from tale.driver_if import IFDriver
from tale.llm import llm_config
from tale.llm.llm_io import DummyIoUtil
from tale.player import PlayerConnection


class SmokeTestError(Exception):
    """A smoke test step timed out, the driver failed, or the crash log changed during the run."""


DEFAULT_TIMEOUT = 30.0


def load_script(path) -> List[str]:
    """Load a smoke test script: one command per line, '#' comments and blank lines skipped."""
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                lines.append(line)
    return lines


def _crash_log_path() -> str:
    """Path of the crash log file. Pre-arms the crash logger so the path is fixed to the
    current directory before the driver chdirs into the story directory."""
    logger = util._get_crash_logger()
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            return handler.baseFilename
    return os.path.join(os.getcwd(), util.CRASH_LOG_FILENAME)


def _read_file(path: str) -> Optional[bytes]:
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        return None


def _check_crash_log(path: str, before: Optional[bytes]) -> None:
    """Raise SmokeTestError if the crash log has changed (grown) since the `before` snapshot."""
    after = _read_file(path)
    if before != after:
        new_content = (after or b"")[len(before):] if before else (after or b"")
        raise SmokeTestError("crash log %s changed during the smoke test:\n%s" % (
            path, new_content.decode("utf-8", "replace")))


class SmokeTestRunner:
    """Runs a story headless and executes a script of commands, failing on crashes or timeouts."""

    def __init__(self, game_path, script: Sequence[str], *, timeout: float = DEFAULT_TIMEOUT,
                 canned_responses: Sequence[str] = (), echo: Optional[Callable[[str], None]] = None) -> None:
        self.game_path = str(game_path)
        self.script = list(script)
        self.timeout = timeout
        self.canned_responses = list(canned_responses)
        self.echo = echo
        self.driver = None          # type: Optional[IFDriver]
        self.connection = None      # type: Optional[PlayerConnection]
        self._thread = None         # type: Optional[threading.Thread]
        self._thread_error = None   # type: Optional[BaseException]

    def _log(self, message: str) -> None:
        if self.echo:
            self.echo(message)

    def _driver_thread_main(self) -> None:
        try:
            assert self.driver is not None
            self.driver.start(self.game_path)   # blocks until the game is stopped
        except BaseException as x:
            self._thread_error = x

    def _check_thread_error(self) -> None:
        if self._thread_error is not None:
            raise SmokeTestError("driver thread crashed: %r" % (self._thread_error,)) from self._thread_error

    def run(self) -> str:
        """Run the smoke test. Returns the transcript of everything the game output.
        Raises SmokeTestError on timeout, driver failure, or crash log changes."""
        crash_log = _crash_log_path()
        before = _read_file(crash_log)
        old_cwd = os.getcwd()
        old_path = list(sys.path)
        old_excepthook = sys.excepthook
        # use the dummy backend with canned answers; no real LLM server is needed
        llm_config.params['BACKEND'] = 'dummy'
        self.driver = IFDriver(screen_delay=0, io_type="scripted")
        if self.canned_responses:
            io_util = self.driver.llm_util.io_util
            if isinstance(io_util, DummyIoUtil):
                io_util.responses.extend(self.canned_responses)
        self._thread = threading.Thread(name="smoke-test-driver", target=self._driver_thread_main, daemon=True)
        self._thread.start()
        try:
            self._wait_for_connection()
            self._run_script()
        finally:
            self._stop_driver_thread()
            if self._thread is not None:
                self._thread.join(timeout=5)
            os.chdir(old_cwd)
            sys.path[:] = old_path
            sys.excepthook = old_excepthook
        self._check_thread_error()
        _check_crash_log(crash_log, before)
        io = self.connection.io if self.connection else None
        return io.get_transcript() if io else ""

    def _wait_for_connection(self) -> None:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            self._check_thread_error()
            assert self.driver is not None
            if self.driver.all_players:
                self.connection = next(iter(self.driver.all_players.values()))
                self._wait_for_prompt()   # wait until the login dialog asks for input
                return
            time.sleep(0.02)
        raise SmokeTestError("timed out waiting for the driver to connect a player")

    def _wait_for_prompt(self, before: int = 0) -> None:
        io = self.connection.io
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            self._check_thread_error()
            with io.cond:
                if io.prompt_writes > before or not self.driver.is_running():
                    return
            time.sleep(0.02)
        raise SmokeTestError("timed out waiting for an input prompt from the driver")

    def _run_script(self) -> None:
        for line in self.script:
            self._send(line)

    def _send(self, line: str) -> None:
        """Feed one input line and wait until the driver has processed it and is ready
        for the next input (a new prompt is written) or the game has stopped."""
        conn = self.connection
        player = conn.player
        io = conn.io
        with io.cond:
            before_prompts = io.prompt_writes
            before_lines = len(io.lines)
        self._log(">> " + line)
        player.store_input_line(line)
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            self._check_thread_error()
            with io.cond:
                consumed = not player.input_is_available.is_set()
                if consumed and (io.prompt_writes > before_prompts or not self.driver.is_running()):
                    break
            time.sleep(0.02)
        else:
            raise SmokeTestError("timed out waiting for feedback after command %r" % line)
        with io.cond:
            for output_line in io.lines[before_lines:]:
                self._log(output_line)

    def _stop_driver_thread(self) -> None:
        if self.driver is not None:
            self.driver._stop_mainloop = True
            for conn in self.driver.all_players.values():
                if conn.player:
                    conn.player.input_is_available.set()   # wake the main loop so it can exit


def run_smoke_test(game_path, script_path, *, timeout: float = DEFAULT_TIMEOUT,
                   echo: Optional[Callable[[str], None]] = print) -> str:
    """Run a smoke test on the given story with the given command script.
    Returns the game transcript. Raises SmokeTestError on failure."""
    runner = SmokeTestRunner(game_path, load_script(script_path), timeout=timeout, echo=echo)
    return runner.run()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="""
        Automated smoke test: start a story with a dummy LLM backend (canned answers),
        execute the commands from the script file (waiting for each one to be processed),
        and fail if anything was appended to the crash log (%s) during the run.
        """ % util.CRASH_LOG_FILENAME)
    parser.add_argument('-g', '--game', type=str, required=True, help='path to the story directory')
    parser.add_argument('-s', '--script', type=str, required=True,
                        help='path to the script file with commands to execute (one per line)')
    parser.add_argument('-t', '--timeout', type=float, default=DEFAULT_TIMEOUT,
                        help='per-step timeout in seconds (default %(default)s)')
    args = parser.parse_args(argv)
    try:
        transcript = run_smoke_test(args.game, args.script, timeout=args.timeout)
    except SmokeTestError as x:
        print("SMOKE TEST FAILED: %s" % x, file=sys.stderr)
        return 1
    print("SMOKE TEST OK")
    print(transcript)
    return 0


if __name__ == "__main__":
    sys.exit(main())
