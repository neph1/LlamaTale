"""
Console-based input/output.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
import os
import signal
import sys
import threading
from typing import Sequence, Tuple, Any, Optional, List
try:
    import prompt_toolkit
    from prompt_toolkit.contrib.completers import WordCompleter
except ImportError:
    prompt_toolkit = None

from . import colorama_patched as colorama
from . import styleaware_wrapper, iobase
from ..driver import Driver
from ..player import PlayerConnection, Player
from .. import mud_context


colorama.init()
assert type(colorama.Style.DIM) is str, "Incompatible colorama library installed. Please upgrade to a more recent version (0.3.6+)"

__all__ = ["ConsoleIo"]

style_words = {
    "dim": colorama.Style.DIM,
    "normal": colorama.Style.NORMAL,
    "bright": colorama.Style.BRIGHT,
    "ul": colorama.Style.UNDERLINED,
    "it": colorama.Style.ITALIC,
    "rev": colorama.Style.REVERSEVID,
    "/": colorama.Style.RESET_ALL,
    "location": colorama.Style.BRIGHT,
    "clear": "\033[1;1H\033[2J",  # ansi sequence to clear the console screen
    "monospaced": "",  # we assume the console is already monospaced font
    "/monospaced": ""
}
assert len(set(style_words.keys()) ^ iobase.ALL_STYLE_TAGS) == 0, "mismatch in list of style tags"

if os.name == "nt":
    if not hasattr(colorama, "win32") or colorama.win32.windll is None:
        style_words.clear()  # running on windows without colorama ansi support


class ConsoleIo(iobase.IoAdapterBase):
    """
    I/O adapter for the text-console (standard input/standard output).
    """
    def __init__(self, player_connection: PlayerConnection) -> None:
        super().__init__(player_connection)
        try:
            # try to output a unicode character such as smartypants uses for nicer formatting
            encoding = getattr(sys.stdout, "encoding", sys.getfilesystemencoding())
            chr(8230).encode(encoding)
        except (UnicodeEncodeError, TypeError):
            self.supports_smartquotes = False
        self.stop_main_loop = False
        self.input_not_paused = threading.Event()
        self.input_not_paused.set()

    def __repr__(self):
        return "<ConsoleIo @ 0x%x, local console, pid %d>" % (id(self), os.getpid())

    def singleplayer_mainloop(self, player_connection: PlayerConnection) -> None:
        """Main event loop for the console I/O adapter for single player mode"""
        while not self.stop_main_loop:
            # Input a single line of text by the player. It is stored in the internal
            # command buffer of the player. The driver's main loop can look into that
            # to see if any input should be processed.
            self.input_not_paused.wait()
            try:
                # note that we don't print any prompt ">>", that needs to be done
                # by the main thread that handles screen *output*
                # (otherwise the prompt will often appear before any regular screen output)
                old_player = player_connection.player
                # do blocking console input call
                if prompt_toolkit and self.do_prompt_toolkit:
                    # word completion for the names of things and people
                    all_candidates = self.tab_complete_get_all_candidates(mud_context.driver)
                    completer = WordCompleter(all_candidates)
                    # unfortunately prompt_toolkit doesn't allow ansi style codes in the prompt so we use a plain one.
                    cmd = prompt_toolkit.prompt("\n>> ", patch_stdout=True, completer=completer, complete_while_typing=False)
                else:
                    cmd = input()
                player_connection.player.store_input_line(cmd)
                if old_player is not player_connection.player:
                    # this situation occurs when a save game has been restored,
                    # we also have to unblock the old_player
                    old_player.store_input_line(cmd)
            except KeyboardInterrupt:
                self.break_pressed()
            except EOFError:
                pass

    def pause(self, unpause: bool=False) -> None:
        if unpause:
            self.input_not_paused.set()
        else:
            self.input_not_paused.clear()

    def clear_screen(self) -> None:
        """Clear the screen"""
        if os.name == "nt":
            os.system("cls")
        elif os.name == "posix":
            os.system("clear")
        elif style_words:
            print("\033[2J", end="")
        else:
            print("\n" * 10)

    def install_tab_completion(self, driver: Driver) -> None:
        """Install tab completion using readline, or prompt_toolkit, if available"""
        if prompt_toolkit:
            return   # completion is handled when the prompt_toolkit prompt is created
        if os.name == "nt":
            # pyreadline on windows behaves weird and screws up the output. So disable by default.
            return
        try:
            # noinspection PyUnresolvedReferences
            import readline
        except ImportError:
            return
        else:
            completer = ReadlineTabCompleter(driver, self)
            readline.set_completer(completer.complete)
            if readline.__doc__ and "libedit" in readline.__doc__:
                # this is for osx pythons with libedit instead of gnu readline
                readline.parse_and_bind("bind ^I rl_complete")
            else:
                readline.parse_and_bind("tab: complete")

    def abort_all_input(self, player: Player) -> None:
        """abort any blocking input, if at all possible"""
        # This requires some drastic measures unfortunately.
        # The main thread is stuck in a blocking input (reading from stdin)
        # You really can't seem to interrupt that. So we terminate the process forcefully.
        # That will kill the whole process (including server) but because this
        # console io is only used in single player 'if' mode, nobody will notice.
        player.store_input_line("")
        sys.stdout.flush()
        sys.stderr.flush()
        os.kill(os.getpid(), signal.SIGINT)

    def render_output(self, paragraphs: Sequence[Tuple[str, bool]], **params: Any) -> str:
        """
        Render (format) the given paragraphs to a text representation.
        It doesn't output anything to the screen yet; it just returns the text string.
        Any style-tags are still embedded in the text.
        This console-implementation expects 2 extra parameters: "indent" and "width".
        """
        if not paragraphs:
            return ""
        indent = " " * params["indent"]
        wrapper = styleaware_wrapper.StyleTagsAwareTextWrapper(width=params["width"], fix_sentence_endings=True,
                                                               initial_indent=indent, subsequent_indent=indent)
        output = []
        for txt, formatted in paragraphs:
            if formatted:
                txt = wrapper.fill(txt) + "\n"
            else:
                # unformatted output, prepend every line with the indent but otherwise leave them alone
                txt = indent + ("\n" + indent).join(txt.splitlines()) + "\n"
            assert txt.endswith("\n")
            output.append(txt)
        return self.smartquotes("".join(output))

    def output(self, *lines: str) -> None:
        """Write some text to the screen. Takes care of style tags that are embedded."""
        super().output(*lines)
        for line in lines:
            print(self._apply_style(line, self.do_styles))
        sys.stdout.flush()

    def output_no_newline(self, text: str, new_paragraph = True) -> None:
        """Like output, but just writes a single line, without end-of-line."""
        if prompt_toolkit and self.do_prompt_toolkit:
            self.output(text)
        else:
            super().output_no_newline(text, new_paragraph)
            print(self._apply_style(text, self.do_styles), end="")
            sys.stdout.flush()

    def write_input_prompt(self) -> None:
        """write the input prompt '>>'"""
        if not prompt_toolkit or not self.do_prompt_toolkit:
            print(self._apply_style("\n<dim>>></> ", self.do_styles), end="")
            sys.stdout.flush()

    def break_pressed(self) -> None:
        """do something when the player types ctrl-C (break)"""
        if threading.current_thread().name != "MainThread":
            # ony trigger the ^C handling if we're running in the main thread,
            # otherwise we could get two triggers (one from the async i/o thread, and
            # one from the main thread)
            return
        if self.stop_main_loop:
            # don't write the feedback if the loop is already stopping
            return
        print(self._apply_style("\n* break: Use <quit> if you want to quit.", self.do_styles))
        sys.stdout.flush()

    def _apply_style(self, line: str, do_styles: bool) -> str:
        """Convert style tags to ansi escape sequences suitable for console text output"""
        if "<" not in line:
            return line
        elif style_words and do_styles:
            for tag, replacement in style_words.items():
                line = line.replace("<%s>" % tag, replacement)
            return line
        else:
            return iobase.strip_text_styles(line)       # type: ignore


class ReadlineTabCompleter:
    """
    Class used to provide tab-completion on the command line using readline.
    """
    def __init__(self, driver: Driver, io: ConsoleIo) -> None:
        self.driver = driver
        self.io = io
        self.candidates = []   # type: List[str]

    def complete(self, prefix: str, state: int) -> str:
        if not prefix:
            return ""   # we wont auto-suggest every possible command
        if not state:
            # first time called for this prefix, recalculate candidates
            self.candidates = list(self.io.tab_complete(prefix, self.driver))
        try:
            return self.candidates[state]
        except IndexError:
            return ""


if __name__ == "__main__":
    def _main():
        co = ConsoleIo(PlayerConnection())
        lines = ["test Tale Console output", "'singlequotes'", '"double quotes"', "ellipsis...", "<bright>BRIGHT <rev>REVERSE </>NORMAL"]
        paragraphs = [(text, False) for text in lines]
        output = co.render_output(paragraphs, indent=2, width=50)
        co.output(output)
    _main()
