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
Assertion directives check the immediately preceding command line (the run fails
if an expectation does not hold): '# expect: <text>' and '# expect-not: <text>'
check the command's output text; '# expect-beat: <id>=<status>' and
'# expect-goal: <beat>/<type>/<target>=<satisfied|unsatisfied>' check the live
story engine state (beat statuses and goal satisfaction flags).

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
import argparse
import logging
import os
import random
import sys
import threading
import time
from typing import Callable, List, Optional, Sequence, Tuple, Union

from tale import util
from tale.driver_if import IFDriver
from tale.llm import llm_config
from tale.llm.llm_io import DummyIoUtil
from tale.player import PlayerConnection
from tale.story_context import StoryContext


class SmokeTestError(Exception):
    """A smoke test step timed out, the driver failed, or the crash log changed during the run."""


DEFAULT_TIMEOUT = 30.0

# A script step is either a command line (str) or an assertion directive that applies
# to the preceding command: ("expect", text) / ("expect_not", text) check the command's
# output text; ("expect_beat", "id=status") / ("expect_goal", "beat/type/target=state")
# check the live story engine state (beat statuses / goal satisfaction flags).
ScriptStep = Union[str, Tuple[str, str]]

EXPECT_PREFIX = "# expect:"
EXPECT_NOT_PREFIX = "# expect-not:"
EXPECT_BEAT_PREFIX = "# expect-beat:"
EXPECT_GOAL_PREFIX = "# expect-goal:"


def load_script(path) -> List[str]:
    """Load a smoke test script: one command per line, '#' comments and blank lines skipped."""
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                lines.append(line)
    return lines


def load_steps(path) -> List[ScriptStep]:
    """Load a smoke test script into steps: command lines plus assertion directives.
    '# expect: <text>' / '# expect-not: <text>' are checked against the output of the
    command line they follow; '# expect-beat: <id>=<status>' and
    '# expect-goal: <beat>/<type>/<target>=<satisfied|unsatisfied>' are checked against
    the live story engine state after that command. Plain '#' lines are comments."""
    steps = []  # type: List[ScriptStep]
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith(EXPECT_NOT_PREFIX):
                steps.append(("expect_not", line[len(EXPECT_NOT_PREFIX):].strip()))
            elif line.startswith(EXPECT_BEAT_PREFIX):
                steps.append(("expect_beat", line[len(EXPECT_BEAT_PREFIX):].strip()))
            elif line.startswith(EXPECT_GOAL_PREFIX):
                steps.append(("expect_goal", line[len(EXPECT_GOAL_PREFIX):].strip()))
            elif line.startswith(EXPECT_PREFIX):
                steps.append(("expect", line[len(EXPECT_PREFIX):].strip()))
            elif line.startswith("#"):
                continue
            else:
                steps.append(line)
    return steps


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

    def __init__(self, game_path, script: Sequence[ScriptStep], *, timeout: float = DEFAULT_TIMEOUT,
                 canned_responses: Sequence[str] = (), echo: Optional[Callable[[str], None]] = None,
                 wizard: bool = False, seed: Optional[int] = None) -> None:
        self.game_path = str(game_path)
        self.steps = list(script)
        self.timeout = timeout
        self.canned_responses = list(canned_responses)
        self.echo = echo
        self.wizard = wizard
        self.seed = seed
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
        if self.seed is not None:
            random.seed(self.seed)   # reproducible dice rolls (stealth contests etc.)
        self.driver = IFDriver(screen_delay=0, io_type="scripted", wizard_override=self.wizard)
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
        steps = self.steps
        i = 0
        while i < len(steps):
            step = steps[i]
            if not isinstance(step, str):
                raise SmokeTestError("assertion directive %r must follow a command line" % (step,))
            output_lines = self._send(step)
            i += 1
            expectations = []  # type: List[Tuple[str, str]]
            while i < len(steps) and not isinstance(steps[i], str):
                expectations.append(steps[i])
                i += 1
            self._check_expectations(expectations, output_lines, step)

    def _check_expectations(self, expectations: List[Tuple[str, str]], output_lines: List[str], command: str) -> None:
        """Check assertion directives against one command's output ('# expect:' /
        '# expect-not:') or against the live story engine state ('# expect-beat:' /
        '# expect-goal:')."""
        if not expectations:
            return
        text = "\n".join(output_lines)
        for kind, needle in expectations:
            if kind == "expect" and needle not in text:
                raise SmokeTestError("after command %r, expected output to contain %r\nactual output:\n%s"
                                     % (command, needle, text))
            if kind == "expect_not" and needle in text:
                raise SmokeTestError("after command %r, expected output not to contain %r\nactual output:\n%s"
                                     % (command, needle, text))
            if kind == "expect_beat":
                self._check_beat_expectation(needle, command)
            if kind == "expect_goal":
                self._check_goal_expectation(needle, command)

    def _story_context(self):
        """The live story's beat context (StoryContext), or None if unavailable."""
        driver = self.driver
        if driver is None or getattr(driver, "story", None) is None:
            return None
        context = driver.story.config.context
        return context if isinstance(context, StoryContext) else None

    def _check_beat_expectation(self, spec: str, command: str) -> None:
        """'# expect-beat: <id>=<status>' — check a beat's status in the live context."""
        beat_id, sep, status = spec.partition("=")
        if not sep or not beat_id.strip() or not status.strip():
            raise SmokeTestError("malformed expect-beat directive %r (want '<id>=<status>')" % spec)
        context = self._story_context()
        if context is None:
            raise SmokeTestError("after command %r: no beat-based story context to check %r against" % (command, spec))
        beat = next((b for b in context.beats if b.id == beat_id.strip()), None)
        if beat is None:
            raise SmokeTestError("after command %r: no beat with id %r (beats: %s)"
                                 % (command, beat_id.strip(), [b.id for b in context.beats]))
        expected = status.strip().lower()
        actual = str(beat.status)
        if actual != expected:
            raise SmokeTestError("after command %r: expected beat %r to be %r, but it is %r"
                                 % (command, beat.id, expected, actual))

    def _check_goal_expectation(self, spec: str, command: str) -> None:
        """'# expect-goal: <beat>/<type>/<target>=<satisfied|unsatisfied>' — check a
        goal's satisfied flag in the live context."""
        goal_spec, sep, state = spec.partition("=")
        parts = goal_spec.split("/", 2)
        if not sep or len(parts) != 3 or not state.strip():
            raise SmokeTestError("malformed expect-goal directive %r "
                                 "(want '<beat>/<type>/<target>=<satisfied|unsatisfied>')" % spec)
        beat_id, goal_type, target = (p.strip() for p in parts)
        context = self._story_context()
        if context is None:
            raise SmokeTestError("after command %r: no beat-based story context to check %r against" % (command, spec))
        beat = next((b for b in context.beats if b.id == beat_id), None)
        if beat is None:
            raise SmokeTestError("after command %r: no beat with id %r (beats: %s)"
                                 % (command, beat_id, [b.id for b in context.beats]))
        goal = next((g for g in beat.goals if g.type == goal_type and g.target.lower() == target.lower()), None)
        if goal is None:
            raise SmokeTestError("after command %r: beat %r has no goal %s/%r (goals: %s)"
                                 % (command, beat_id, goal_type, target, beat.goals))
        expected = state.strip().lower() == "satisfied"
        if goal.satisfied != expected:
            raise SmokeTestError("after command %r: expected goal %s/%s of beat %r to be %s, but it is %s"
                                 % (command, goal.type, goal.target, beat_id,
                                    "satisfied" if expected else "unsatisfied",
                                    "satisfied" if goal.satisfied else "unsatisfied"))

    def _send(self, line: str) -> List[str]:
        """Feed one input line and wait until the driver has processed it and is ready
        for the next input (a new prompt is written) or the game has stopped.
        Returns the output lines produced while processing it."""
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
            output_lines = list(io.lines[before_lines:])
        for output_line in output_lines:
            self._log(output_line)
        return output_lines

    def _stop_driver_thread(self) -> None:
        if self.driver is not None:
            self.driver._stop_mainloop = True
            for conn in self.driver.all_players.values():
                if conn.player:
                    conn.player.input_is_available.set()   # wake the main loop so it can exit


def run_smoke_test(game_path, script_path, *, timeout: float = DEFAULT_TIMEOUT,
                   echo: Optional[Callable[[str], None]] = print, wizard: bool = False,
                   seed: Optional[int] = None) -> str:
    """Run a smoke test on the given story with the given command script.
    Returns the game transcript. Raises SmokeTestError on failure."""
    runner = SmokeTestRunner(game_path, load_steps(script_path), timeout=timeout, echo=echo,
                             wizard=wizard, seed=seed)
    return runner.run()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="""
        Automated smoke test: start a story with a dummy LLM backend (canned answers),
        execute the commands from the script file (waiting for each one to be processed),
        check any '# expect:' / '# expect-not:' assertions against each command's output,
        '# expect-beat:' / '# expect-goal:' against the live story engine state,
        and fail if anything was appended to the crash log (%s) during the run.
        """ % util.CRASH_LOG_FILENAME)
    parser.add_argument('-g', '--game', type=str, required=True, help='path to the story directory')
    parser.add_argument('-s', '--script', type=str, required=True,
                        help='path to the script file with commands to execute (one per line)')
    parser.add_argument('-t', '--timeout', type=float, default=DEFAULT_TIMEOUT,
                        help='per-step timeout in seconds (default %(default)s)')
    parser.add_argument('-w', '--wizard', action='store_true',
                        help='start the game in wizard mode (enables wizard commands such as set_concealment and perceive)')
    parser.add_argument('--seed', type=int, default=None,
                        help='seed the random number generator for reproducible dice rolls')
    args = parser.parse_args(argv)
    try:
        transcript = run_smoke_test(args.game, args.script, timeout=args.timeout,
                                    wizard=args.wizard, seed=args.seed)
    except SmokeTestError as x:
        print("SMOKE TEST FAILED: %s" % x, file=sys.stderr)
        return 1
    print("SMOKE TEST OK")
    print(transcript)
    return 0


if __name__ == "__main__":
    sys.exit(main())
