
from typing import Any, Sequence, Tuple
from tale.player import PlayerConnection
from tale.tio import iobase, styleaware_wrapper
from . import colorama_patched as colorama


colorama.init()
assert type(colorama.Style.DIM) is str, "Incompatible colorama library installed. Please upgrade to a more recent version (0.3.6+)"

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

class ProxyIo(iobase.IoAdapterBase):
    
    def __init__(self, player_connection: PlayerConnection) -> None:
        super().__init__(player_connection)
        
        self.stop_main_loop = False
        self.waiting_input = ''


    def singleplayer_mainloop(self, player_connection: PlayerConnection) -> None:
        """Main event loop for the console I/O adapter for single player mode"""
        while not self.stop_main_loop:
            try:
                # note that we don't print any prompt ">>", that needs to be done
                # by the main thread that handles screen *output*
                # (otherwise the prompt will often appear before any regular screen output)
                old_player = player_connection.player
                # do blocking console input call
                cmd = self.waiting_input
                if cmd:
                    self.waiting_input = ''
                    player_connection.player.store_input_line(cmd)
                    if old_player is not player_connection.player:
                        # this situation occurs when a save game has been restored,
                        # we also have to unblock the old_player
                        old_player.store_input_line(cmd)
            except KeyboardInterrupt:
                self.break_pressed()
            except EOFError:
                pass

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
        super().output(*lines)
        for line in lines:
            print(self._apply_style(line, self.do_styles))

    def output_no_newline(self, text: str, new_paragraph = True) -> None:
        super().output_no_newline(text, new_paragraph)
        print(self._apply_style(text, self.do_styles), end="")

    def write_input_prompt(self) -> None:
        """write the input prompt '>>'"""
        pass

    def break_pressed(self) -> None:
        pass

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
        
    " Discord Client Events "

    class DiscordBot(discord.Client):

        def __init__(self, intents, proxyIo: 'ProxyIo'):
            super().__init__(intents=intents)
            self.proxyIo = proxyIo
                    
        async def on_ready(self):
            print(f'{self.user} has connected to Discord!')


        async def on_message(self, message: discord.Message):
            if message.channel.type == discord.ChannelType.private:
                self.proxyIo.waiting_input = message.content
            else:
                message.author.send('Please send messages in a private channel.')

