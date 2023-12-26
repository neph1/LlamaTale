"""
Basic Input/Output stuff not tied to a specific I/O implementation.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
import sys
from typing import Union, Sequence, Any, Tuple, Optional, List
import smartypants
from .. import verbdefs
from ..util import format_traceback


smartypants.process_escapes = lambda txt: txt  # disable the html escape processing
smartypants.tags_to_skip = ["abcdefghijklmnopqrstuvwxyz@"]   # setting it to empty list doesn't have the required effect

ALL_STYLE_TAGS = {"dim", "normal", "bright", "ul", "it", "rev", "clear", "location", "monospaced", "/monospaced", "/"}


def strip_text_styles(text: Union[str, Sequence[str]]) -> Union[str, Sequence[str]]:
    """remove any special text styling tags from the text (you can pass a single string, and also a list of strings)"""
    def strip(text: str) -> str:
        if "<" not in text:
            return text
        for tag in ALL_STYLE_TAGS:
            text = text.replace("<%s>" % tag, "")
        return text
    if isinstance(text, str):
        return strip(text)
    return [strip(line) for line in text]


class IoAdapterBase:
    """
    I/O adapter base class
    """
    def __init__(self, player_connection) -> None:
        self.do_styles = True
        self.do_smartquotes = True
        self.do_prompt_toolkit = True
        self.supports_smartquotes = True
        self.supports_blocking_input = True
        self.player_connection = player_connection
        self.stop_main_loop = False
        self.last_output_line = ""
        self.dont_echo_next_cmd = False   # used to not echo the password input, for instance
        self.echo_input = False

    def destroy(self) -> None:
        """Called when the I/O adapter is shut down"""
        pass

    def singleplayer_mainloop(self, player_connection) -> None:
        """Main event loop for this I/O adapter for single player mode"""
        raise NotImplementedError("implement this in subclass")

    def clear_screen(self) -> None:
        """Clear the screen"""
        pass

    def critical_error(self, message: str="A critical error occurred! See below and/or in the error log.") -> None:
        """called when the driver encountered a critical error and the session needs to shut down"""
        tb = "".join(format_traceback())
        self.output("\n<bright><rev>" + message + "</>")
        print(tb, file=sys.stderr)
        self.output("<rev><it>Please report this problem.</>\n")

    def abort_all_input(self, player) -> None:
        """abort any blocking input, if at all possible"""
        pass

    def render_output(self, paragraphs: Sequence[Tuple[str, bool]], **params: Any) -> str:
        """
        Render (format) the given paragraphs to a text representation.
        It doesn't output anything to the screen yet; it just returns the text string.
        Any style-tags are still embedded in the text.
        This console-implementation expects 2 extra parameters: "indent" and "width".
        """
        raise NotImplementedError("implement this in subclass")

    def smartquotes(self, text: str) -> str:
        """If enabled, apply 'smart quotes' to the text; replaces quotes and dashes by nicer looking symbols"""
        if self.supports_smartquotes and self.do_smartquotes:
            if hasattr(smartypants.Attr, "u"):
                return smartypants.smartypants(text, smartypants.Attr.q | smartypants.Attr.B |
                                               smartypants.Attr.D | smartypants.Attr.e | smartypants.Attr.u)
            else:
                # older smartypants lack attribute 'u' for avoiding html entity creation
                txt = smartypants.smartypants(text, smartypants.Attr.q | smartypants.Attr.B |
                                              smartypants.Attr.D | smartypants.Attr.e)
                import html.parser
                return html.parser.unescape(txt)    # type: ignore
        return text

    def output(self, *lines: str) -> None:
        """
        Write some text to the screen. Needs to take care of style tags that are embedded.
        Implement specific behavior in subclass (but don't forget to call base method)
        """
        self.last_output_line = lines[-1]

    def output_no_newline(self, text: str) -> None:
        """
        Like output, but just writes a single line, without end-of-line.
        Implement specific behavior in subclass (but don't forget to call base method)
        """
        self.last_output_line = text

    def write_input_prompt(self) -> None:
        """write the input prompt '>>'"""
        pass

    def break_pressed(self) -> None:
        """do something when the player types ctrl-C (break)"""
        pass

    def pause(self, unpause: bool=False) -> None:
        """pause/ unpause the input loop"""
        raise NotImplementedError("implement this in subclass")

    def tab_complete_get_all_candidates(self, driver) -> List[str]:
        return self.tab_complete("", driver, True)

    def tab_complete(self, prefix: str, driver, get_all: bool=False) -> List[str]:
        if not prefix and not get_all:
            return []
        prefix = prefix.lower()
        player = self.player_connection.player
        verbs = {verb for verb in driver.current_verbs(player) if verb.startswith(prefix)}
        livings = {living.name for living in player.location.livings if living.name.startswith(prefix)}
        livings_aliases = {alias for living in player.location.livings for alias in living.aliases if alias.startswith(prefix)}
        items = {item.name for item in player.location.items if item.name.startswith(prefix)}
        items_aliases = {alias for item in player.location.items for alias in item.aliases if alias.startswith(prefix)}
        exits = {xt for xt in player.location.exits if xt.startswith(prefix)}
        inventory = {item.name for item in player.inventory if item.name.startswith(prefix)}
        inventory_aliases = {alias for item in player.inventory for alias in item.aliases if alias.startswith(prefix)}
        emotes = {verb for verb in verbdefs.VERBS if verb.startswith(prefix)}
        return list(sorted(verbs | livings | items | exits | inventory | emotes | livings_aliases | items_aliases | inventory_aliases))
