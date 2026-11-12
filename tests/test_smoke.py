"""
Tests for the automated smoke test (tale.smoketest) and the dummy LLM backend.

The full story run is executed in a subprocess so the game driver's global
state (mud_context, object registry, sys.modules, cwd) doesn't leak into
the other tests.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

from tale.llm.llm_io import DummyIoUtil
from tale.llm.schemas import ActionListSchema, DialogueSchema
from tale.smoketest import SmokeTestError, _check_crash_log, load_script


class TestDummyBackend(unittest.TestCase):
    def test_canned_responses_are_used_in_order(self):
        io_util = DummyIoUtil(responses=["first", "second"])
        self.assertEqual("first", io_util.synchronous_request({}, prompt="p1"))
        self.assertEqual("second", io_util.asynchronous_request({}, prompt="p2"))
        self.assertEqual(DummyIoUtil.DEFAULT_RESPONSE, io_util.stream_request({}, prompt="p3"))
        self.assertEqual(["p1", "p2", "p3"], io_util.requests)

    def test_default_response(self):
        io_util = DummyIoUtil(default_response="canned")
        self.assertEqual("canned", io_util.synchronous_request({}, prompt="x"))

    def test_structured_request_uses_valid_canned_json(self):
        io_util = DummyIoUtil(responses=['{"response": "hello there", "sentiment": "happy"}'])
        model = io_util.structured_request({}, prompt="p", model=DialogueSchema)
        self.assertEqual("hello there", model.response)
        self.assertEqual("happy", model.sentiment)

    def test_structured_request_falls_back_to_schema_defaults(self):
        # a canned answer that is not valid JSON for the model still yields a valid model
        io_util = DummyIoUtil(responses=["not json at all"])
        model = io_util.structured_request({}, prompt="p", model=DialogueSchema)
        self.assertTrue(model.response)   # required field got a non-empty canned default
        actions = io_util.structured_request({}, prompt="p", model=ActionListSchema)
        self.assertEqual([], actions.actions)


class TestSmokeTestHelpers(unittest.TestCase):
    def test_load_script_skips_comments_and_blank_lines(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
            f.write("# comment\n\nlook\n  north  \n# another\nquit\ny\n")
            path = f.name
        try:
            self.assertEqual(["look", "north", "quit", "y"], load_script(path))
        finally:
            os.unlink(path)

    def test_crash_log_check_raises_when_log_grew(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "tale_crash.log")
            with open(path, "w") as f:
                f.write("old crash\n")
            with open(path, "rb") as f:
                before = f.read()
            _check_crash_log(path, before)   # unchanged: no error
            with open(path, "a") as f:
                f.write("new crash\n")
            with self.assertRaises(SmokeTestError) as cm:
                _check_crash_log(path, before)
            message = str(cm.exception)
            self.assertIn("new crash", message)
            self.assertNotIn("old crash", message.split("changed during the smoke test:")[-1])

    def test_crash_log_check_raises_when_log_appeared(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "tale_crash.log")
            _check_crash_log(path, None)   # file did not exist before and still doesn't: no error
            with open(path, "w") as f:
                f.write("crash\n")
            with self.assertRaises(SmokeTestError):
                _check_crash_log(path, None)


class TestPrancingLlamaSmokeTest(unittest.TestCase):
    """Run the prancingllama story end-to-end with the dummy backend and the smoke script.
    Fails if any step times out or if the crash log changes during the run."""

    def test_prancingllama_smoke_test(self):
        repo_root = pathlib.Path(__file__).parent.parent.resolve()
        game = repo_root / "stories" / "prancingllama"
        script = game / "smoke_test.txt"
        self.assertTrue(script.exists(), "smoke script missing: %s" % script)
        with tempfile.TemporaryDirectory() as tmp:
            # run in a temp cwd so the crash log and other artifacts don't pollute the repo
            env = dict(os.environ, PYTHONPATH=str(repo_root) + os.pathsep + os.environ.get("PYTHONPATH", ""))
            result = subprocess.run(
                [sys.executable, "-m", "tale.smoketest",
                 "--game", str(game), "--script", str(script), "--timeout", "60"],
                cwd=tmp, env=env, capture_output=True, text=True, timeout=600)
        self.assertEqual(0, result.returncode,
                         msg="smoke test failed.\nstdout:\n%s\nstderr:\n%s" % (result.stdout, result.stderr))
        self.assertIn("SMOKE TEST OK", result.stdout)


class TestBeatsStorySmokeTest(unittest.TestCase):
    """Run the beats_test story (TIMER tick, authored beats) end-to-end with the dummy
    backend: the timer-driven beat progression must not crash the driver."""

    def test_beats_story_smoke_test(self):
        repo_root = pathlib.Path(__file__).parent.parent.resolve()
        game = repo_root / "stories" / "beats_test"
        script = game / "smoke_test.txt"
        self.assertTrue(script.exists(), "smoke script missing: %s" % script)
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PYTHONPATH=str(repo_root) + os.pathsep + os.environ.get("PYTHONPATH", ""))
            result = subprocess.run(
                [sys.executable, "-m", "tale.smoketest",
                 "--game", str(game), "--script", str(script), "--timeout", "90"],
                cwd=tmp, env=env, capture_output=True, text=True, timeout=600)
        self.assertEqual(0, result.returncode,
                         msg="smoke test failed.\nstdout:\n%s\nstderr:\n%s" % (result.stdout, result.stderr))
        self.assertIn("SMOKE TEST OK", result.stdout)


if __name__ == '__main__':
    unittest.main()
