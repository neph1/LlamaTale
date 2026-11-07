"""
Scripted input/output, used by the automated smoke test (tale.smoketest).

Instead of a terminal, all output is recorded and input is fed externally
through player.store_input_line(). The smoke test runner uses the writes /
prompt_writes counters (guarded by cond) to wait until the driver has
processed the previous input line and written its feedback.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
import threading
import time
from typing import Any, List, Sequence, Tuple

from . import iobase


class ScriptedIo(iobase.IoAdapterBase):
    """
    I/O adapter that records all output instead of printing it to a screen.
    """
    def __init__(self, player_connection) -> None:
        super().__init__(player_connection)
        self.supports_blocking_input = True
        self.lines = []         # type: List[str]   # every line written to the "screen"
        self.writes = 0         # total number of output calls
        self.prompt_writes = 0  # number of input prompts written (driver is ready for input)
        self.cond = threading.Condition()

    def __repr__(self):
        return "<ScriptedIo @ 0x%x>" % id(self)

    def _record(self, text: str, prompt: bool) -> None:
        with self.cond:
            self.lines.append(text)
            self.writes += 1
            if prompt:
                self.prompt_writes += 1
            self.cond.notify_all()

    def singleplayer_mainloop(self, player_connection) -> None:
        """Block until the driver shuts down; input is fed externally, not read here."""
        while not self.stop_main_loop:
            time.sleep(0.05)

    def render_output(self, paragraphs: Sequence[Tuple[str, bool]], **params: Any) -> str:
        return "\n".join(text for text, formatted in paragraphs)

    def output(self, *lines: str) -> None:
        super().output(*lines)
        for line in lines:
            self._record(line, prompt=False)

    def output_no_newline(self, text: str, new_paragraph: bool = True) -> None:
        super().output_no_newline(text, new_paragraph)
        self._record(text, prompt=True)   # the driver writes input prompts through here

    def write_input_prompt(self) -> None:
        super().write_input_prompt()
        self._record(">>", prompt=True)

    def clear_screen(self) -> None:
        pass

    def pause(self, unpause: bool = False) -> None:
        pass

    def break_pressed(self) -> None:
        pass

    def abort_all_input(self, player) -> None:
        pass

    def tab_complete(self, prefix: str, driver, get_all: bool = False) -> List[str]:
        return []

    def get_transcript(self) -> str:
        """All output written so far, as a single string."""
        with self.cond:
            return "\n".join(self.lines)
