"""
Console-based input/output.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import signal
import sys
import threading
from typing import Sequence, Tuple, Any, Optional, List

from tale import lang
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

class Server(BaseHTTPRequestHandler):

    def setMessage(self, message: str):
        self.message = message

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
    def do_HEAD(self):
        self._set_headers()
        
    # GET sends back a Hello world message
    def do_GET(self):
        print('GET')
        self._set_headers()
        
        global response_message

        with open(response_message) as data_file:
            self.wfile.write(data_file.read().encode())
        
    # POST echoes the message adding a JSON field
    def do_POST(self):
        print('POST')
        # read the message and convert it into a python dictionary
        length = int(self.headers.get('content-length', "0"))
        message = json.loads(self.rfile.read(length))
        print(self.headers)
        print(message)
        # add a property to the object, just to mess with data
        message['received'] = 'ok'
        
        global response_message
        # send the message back
        self._set_headers()
        with open(response_message) as data_file:
            self.wfile.write(data_file.read().encode())

class ConsoleHttpIo(iobase.IoAdapterBase):
    """
    I/O adapter for the text-console (standard input/standard output).
    """
    def __init__(self, player_connection: PlayerConnection, port: int) -> None:
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
        server_address = ('', port)
        httpd = HTTPServer(server_address, Server)
        print('Starting httpd on port %d...' % port)
        httpd.serve_forever()

    def __repr__(self):
        return "<ConsoleIo @ 0x%x, local console, pid %d>" % (id(self), os.getpid())

    def singleplayer_mainloop(self, player_connection: PlayerConnection) -> None:
        while not self.stop_main_loop:
            try:
                pass
            except KeyboardInterrupt:
                print("* break - stopping server loop")
                if lang.yesno(input("Are you sure you want to exit the Tale driver, and kill the game? ")):
                    break
        print("Game shutting down.")

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


if __name__ == "__main__":
    def _main():
        co = ConsoleIo(PlayerConnection())
        lines = ["test Tale Console output", "'singlequotes'", '"double quotes"', "ellipsis...", "<bright>BRIGHT <rev>REVERSE </>NORMAL"]
        paragraphs = [(text, False) for text in lines]
        output = co.render_output(paragraphs, indent=2, width=50)
        co.output(output)
    _main()
