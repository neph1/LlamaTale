"""
Player code

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import json
import os
import queue
import requests
import time
import traceback
from threading import Event
from typing import Any, Sequence, Tuple, IO, Optional, Set, List, Union

from . import base
from . import lang
from . import mud_context
from . import pubsub
from . import util
from .errors import ActionRefused
from .story import GameMode
from .tio import DEFAULT_SCREEN_WIDTH, DEFAULT_SCREEN_INDENT
from .tio.iobase import strip_text_styles, IoAdapterBase
from .vfs import VirtualFileSystem, Resource


class Player(base.Living, pubsub.Listener):
    """
    Player controlled entity.
    Has a Soul for social interaction.
    """
    def __init__(self, name: str, gender: str, *, race: str="human", descr: str="", short_descr: str="") -> None:
        title = lang.capital(name)
        super().__init__(name, gender, race=race, title=title, descr=descr, short_descr=short_descr)
        self.turns = 0
        self.screen_width = DEFAULT_SCREEN_WIDTH
        self.screen_indent = DEFAULT_SCREEN_INDENT
        self.screen_styles_enabled = True
        self.smartquotes_enabled = True
        self.prompt_toolkit_enabled = True
        self.output_line_delay = 50   # milliseconds.
        self.brief = 0  # 0=off, 1=short descr. for known locations, 2=short descr. for all locations
        self.known_locations = set()   # type: Set[base.Location]
        self.last_input_time = time.time()
        self.init_nonserializables()
        
        self.genparams = {'stop_sequence': '\n\n', 'max_length':300, 'max_context_length':512, 'temperature':0.8, 'top_k':120, 'top_a':0.0, 'top_p':0.85, 'typical_p':1.0, 'tfs':1.0, 'rep_pen':1.1, 'rep_pen_range':128, 'mirostat':0, 'mirostat_tau':5.0, 'mirostat_eta':0.1, 'sampler_order':[6,0,1,3,4,2,5], 'seed':-1}

    def init_nonserializables(self) -> None:
        # these things cannot be serialized or have to be reinitialized
        # call this function after deserialization.
        self._input = queue.Queue()   # type: queue.Queue[str]
        self.input_is_available = Event()
        self.transcript = None   # type: Optional[IO[str]]
        self._output = TextBuffer()

    def init_names(self, name: str, title: str, descr: str, short_descr: str) -> None:
        title = lang.capital(title or name)  # make sure the title of a player remains capitalized
        super().init_names(name, title, descr, short_descr)

    def __repr__(self):
        return "<%s '%s' #%d @ 0x%x, privs:%s>" % (self.__class__.__name__, self.name, self.vnum,
                                                   id(self), ",".join(self.privileges) or "-")

    def set_screen_sizes(self, indent: int, width: int) -> None:
        self.screen_indent = indent
        self.screen_width = width

    def tell(self, message: str, *, end: bool=False, format: bool=True, evoke: bool=False, max_length : bool=False) -> base.Living:
        """
        Sends a message to a player, meant to be printed on the screen.
        Message will be converted to str if required.
        If you want to output a paragraph separator, either set end=True or tell a single newline.
        If you provide format=False, this paragraph of text won't be formatted when it is outputted,
        and whitespace is untouched. Empty strings aren't outputted at all.
        The player object is returned so you can chain calls.
        """
        if evoke:
            msg = self.evoke(message, max_length = max_length)
        else:
            msg = str(message)     
        
        super().tell(msg)
        if msg == "\n":
            self._output.p()
        else:
            self._output.print(msg, end=end, format=format)
        return self
    
    def evoke(self, message: str, max_length : bool=False):
        if len(message) > 0 and str(message) != "\n":
            amount = len(message) * 2
            print(f'evoke {message}')
            prompt = ' ### Instruction: Below is a piece of text containing story or description. Rewrite it in your own words using evokative and vivid language. Use max %s words. Text:\n\n' % amount
            prompt += str(message)
            prompt += "\n\n End of text. \n\n"
            prompt += " ### Response: \n\n"
            
            request_body = self.genparams
            request_body['prompt'] = prompt
            if max_length:
                request_body['max_length'] = amount
            response = requests.post('http://localhost:5006/api/v1/generate', data=json.dumps(request_body))
            text = json.loads(response.text)['results'][0]['text']
            return self.trim_response(text)
        return str(message)
    
    def trim_response(self, message: str):
        enders = ['.', '!', '?', '`', '*', '"', ')', '}', '`', ']']
        lastChar = 0
        for c in enders:
            last = message.rfind(c)
            if last > lastChar:
                lastChar = last
        return message[:lastChar+1]

    def tell_text_file(self, file_resource: Resource, reformat=True) -> None:
        """
        Show the contents of the given text file resource to the player.
        """
        if reformat:
            for paragraph in file_resource.text.split("\n\n"):
                paragraph = "\n".join(line.strip() for line in paragraph.splitlines())
                self.tell(paragraph, end=True)
        else:
            self.tell(file_resource.text, format=False)

    def look(self, short: Optional[bool]=None) -> None:
        """look around in your surroundings (it excludes the player himself from livings)"""
        if short is None:
            if self.brief == 2:
                short = True
            elif self.brief == 1:
                short = self.location in self.known_locations
            else:
                short = False
        if self.location:
            self.known_locations.add(self.location)
            look_paragraphs = self.location.look(exclude_living=self, short=short)
            
            #for paragraph in look_paragraphs:
            self.tell(look_paragraphs, end=True, evoke=True)
        else:
            self.tell("You see nothing.")

    def move(self, target: base.ContainingType, actor: base.Living=None,
             *, silent: bool=False, is_player: bool=True, verb: str="move", direction_names: Sequence[str]=None) -> None:
        """
        Delegate to Living but with is_player set to True.
        Moving the player is only supported to a target Location.
        """
        super().move(target, actor, silent=silent, is_player=True, verb=verb, direction_names=direction_names)

    def create_wiretap(self, target: Union[base.Location, base.Living]) -> None:
        if "wizard" not in self.privileges:
            raise ActionRefused("wiretap requires wizard privilege")
        tap = target.get_wiretap()
        tap.subscribe(self)

    def pubsub_event(self, topicname: pubsub.TopicNameType, event: Tuple[base.MudObject, str]) -> None:
        sender, message = event
        self.tell("[wiretapped from `%s': %s]" % (sender, message), end=True)

    def clear_wiretaps(self) -> None:
        # clear all wiretaps that this player has
        pubsub.unsubscribe_all(self)

    def destroy(self, ctx: Optional[util.Context]) -> None:
        self.clear_wiretaps()
        self.deactivate_transcript()
        super().destroy(ctx)

    def allow_give_money(self, amount: float, actor: Optional[base.Living]) -> None:
        """Do we accept money? Raise ActionRefused if not. For Player, the default is that we accept."""
        pass

    def allow_give_item(self, item: base.Item, actor: Optional[base.Living]) -> None:
        """Do we accept given items? Raise ActionRefused if not. For Player, the default is that we accept."""
        pass

    def get_pending_input(self) -> Sequence[str]:
        """return the full set of lines in the input buffer (if any)"""
        result = []
        self.input_is_available.clear()
        try:
            while True:
                result.append(self._input.get_nowait())
        except queue.Empty:
            return result

    def store_input_line(self, cmd: str) -> None:
        """store a line of entered text in the input command buffer"""
        cmd = cmd.strip()
        self._input.put(cmd)
        if self.transcript:
            self.transcript.write("\n\n>> %s\n" % cmd)
        self.input_is_available.set()
        self.last_input_time = time.time()

    @property
    def idle_time(self) -> float:
        return time.time() - self.last_input_time

    def tell_object_location(self, obj: base.MudObject, known_container: Union[base.Living, base.Item, base.Location, None],
                             print_parentheses: bool=True) -> None:
        """Tells the player some details about the location of the given object."""
        if known_container is None:
            if print_parentheses:
                self.tell("(It's not clear where %s is)." % obj.name)
            else:
                self.tell("It's not clear where %s is." % obj.name)
            return
        elif known_container in self:
            if print_parentheses:
                self.tell("(%s was found in %s, in your inventory)." % (obj.name, known_container.title))
            else:
                self.tell("%s was found in %s, in your inventory." % (lang.capital(obj.name), known_container.title))
        elif known_container is self.location:
            if print_parentheses:
                self.tell("(%s was found in your current location)." % obj.name)
            else:
                self.tell("%s was found in your current location." % lang.capital(obj.name))
        elif known_container is self:
            if print_parentheses:
                self.tell("(%s was found in your inventory)." % obj.name)
            else:
                self.tell("%s was found in your inventory." % lang.capital(obj.name))
        else:
            if print_parentheses:
                self.tell("(%s was found in %s)." % (obj.name, known_container.name))
            else:
                self.tell("%s was found in %s." % (lang.capital(obj.name), known_container.name))

    def activate_transcript(self, file: str, vfs: VirtualFileSystem) -> None:
        if self.transcript:
            raise ActionRefused("There's already a transcript being made to " + self.transcript.name)
        self.transcript = vfs.open_write("transcripts/" + file, mimetype="text/plain", append=True)
        self.tell("Transcript is being written to " + self.transcript.name)
        self.transcript.write("\n*Transcript starting at %s*\n\n" % time.ctime())

    def deactivate_transcript(self) -> None:
        if self.transcript:
            self.transcript.write("\n*Transcript ending at %s*\n\n" % time.ctime())
            self.transcript.close()
            self.transcript = None
            self.tell("Transcript ended.")

    def search_extradesc(self, keyword: str, include_inventory: bool=True, include_containers_in_inventory: bool=False) -> str:
        """
        Searches the extradesc keywords for an location/living/item within the 'visible' world around the player,
        including their inventory.  If there's more than one hit, just return the first extradesc description text.
        """
        assert keyword
        keyword = keyword.lower()
        desc = self.location.extra_desc.get(keyword)
        if desc:
            return desc
        for item in self.location.items:
            desc = item.extra_desc.get(keyword)
            if desc:
                return desc
        for living in self.location.livings:
            desc = living.extra_desc.get(keyword)
            if desc:
                return desc
        if include_inventory:
            for item in self.inventory:
                desc = item.extra_desc.get(keyword)
                if desc:
                    return desc
        if include_containers_in_inventory:
            for container in self.inventory:
                try:
                    inventory = container.inventory
                except ActionRefused:
                    continue    # no access to inventory, just skip this item silently
                else:
                    for item in inventory:
                        desc = item.extra_desc.get(keyword)
                        if desc:
                            return desc
        return ""

    def test_peek_output_paragraphs(self) -> Sequence[Sequence[str]]:
        """
        Returns a copy of the output paragraphs that sit in the buffer so far
        This is for test purposes. No text styles are included.
        """
        paragraphs = self._output.get_paragraphs(clear=False)
        return [strip_text_styles(paragraph_text) for paragraph_text, formatted in paragraphs]

    def test_get_output_paragraphs(self) -> Sequence[Sequence[str]]:
        """
        Gets the accumulated output paragraphs in raw form.
        This is for test purposes. No text styles are included.
        """
        paragraphs = self._output.get_paragraphs(clear=True)
        return [strip_text_styles(paragraph_text) for paragraph_text, formatted in paragraphs]


class TextBuffer:
    """
    Buffered output for the text that the player will see on the screen.
    The buffer queues up output text into paragraphs.
    Notice that no actual output formatting is done here, that is performed elsewhere.
    """
    class Paragraph:
        def __init__(self, format: bool=True) -> None:
            self.format = format
            self.lines = []  # type: List[str]

        def add(self, line: str) -> None:
            self.lines.append(line)

        def text(self) -> str:
            return "\n".join(self.lines) + "\n"

    def __init__(self) -> None:
        self.init()

    def init(self) -> None:
        self.paragraphs = []  # type: List[TextBuffer.Paragraph]
        self.in_paragraph = False

    def p(self) -> None:
        """Paragraph terminator. Start new paragraph on next line."""
        if not self.in_paragraph:
            self.__new_paragraph(False)
        self.in_paragraph = False

    def __new_paragraph(self, format: bool) -> Paragraph:
        p = TextBuffer.Paragraph(format)
        self.paragraphs.append(p)
        self.in_paragraph = True
        return p

    def print(self, line: str, end: bool=False, format: bool=True) -> None:
        """
        Write a line of text. A single space is inserted between lines, if format=True.
        If end=True, the current paragraph is ended and a new one begins.
        If format=True, the text will be formatted when output, otherwise it is outputted as-is.
        """
        if not line and format and not end:
            return
        if self.in_paragraph:
            p = self.paragraphs[-1]
        else:
            p = self.__new_paragraph(format)
        if p.format != format:
            p = self.__new_paragraph(format)
        if format:
            line = line.strip()
        p.add(line)
        if end:
            self.in_paragraph = False

    def get_paragraphs(self, clear: bool=True) -> Sequence[Tuple[str, bool]]:
        paragraphs = [(p.text(), p.format) for p in self.paragraphs]
        if clear:
            self.init()
        return paragraphs


class PlayerConnection:
    """
    Represents a player and the i/o connection that is used for him/her.
    Provides high level i/o operations to input commands and write output for the player.
    Other code should not have to call the i/o adapter directly.
    """
    dummy_player_name = "dummy-player-for-initial-connection"
    __dummy_player = Player(dummy_player_name, "n")     # will be registered in MudObjRegistry so beware
    __dummy_io = IoAdapterBase(None)

    def __init__(self, player: Player=__dummy_player, io: IoAdapterBase=__dummy_io) -> None:
        self.player = player
        self.io = io
        self.need_new_input_prompt = True

    def get_output(self) -> str:
        """
        Gets the accumulated output lines, formats them nicely, and clears the buffer.
        If there is nothing to be outputted, empty string is returned.
        """
        paragraphs = self.player._output.get_paragraphs()
        if paragraphs:
            formatted = self.io.render_output(paragraphs, width=self.player.screen_width, indent=self.player.screen_indent)
            if formatted and self.player.transcript:
                self.player.transcript.write(formatted)
            return formatted or ""
        return ""

    @property
    def last_output_line(self) -> str:
        return self.io.last_output_line

    @property
    def idle_time(self) -> float:
        return self.player.idle_time

    def write_output(self) -> None:
        """print any buffered output to the player's screen"""
        if not self.io:
            return
        output = self.get_output()
        if output:
            # (re)set a few io parameters because they can be changed dynamically
            self.io.do_styles = self.player.screen_styles_enabled
            self.io.do_smartquotes = self.player.smartquotes_enabled
            self.io.do_prompt_toolkit = self.player.prompt_toolkit_enabled
            if mud_context.config.server_mode == GameMode.IF and self.player.output_line_delay > 0:
                if os.name == "nt" and self.io.do_prompt_toolkit:
                    line_delay = 0.0    # on windows, when using prompt_toolkit, printing individual lines is already very slow
                else:
                    line_delay = self.player.output_line_delay / 1000.0
                for line in output.rstrip().splitlines():
                    self.io.output(line)
                    if line_delay > 0:
                        time.sleep(line_delay)  # delay the output for a short period
            else:
                self.io.output(output.rstrip())

    def output(self, *lines: str) -> None:
        """directly writes the given text to the player's screen, without buffering and formatting/wrapping"""
        self.io.output(*lines)

    def output_no_newline(self, line: str) -> None:
        """similar to output() but writes a single line, without newline at the end"""
        self.io.output_no_newline(self.io.smartquotes(line))

    def input_direct(self, prompt: str) -> str:
        """
        Writes any pending output and prompts for input directly. Returns stripped result.
        The driver does NOT use this for the regular game loop!
        This call is *blocking* and will not work in a multi user situation.
        """
        assert self.io.supports_blocking_input
        self.write_output()
        if not prompt.endswith(" "):
            prompt += " "
        self.output_no_newline(prompt)
        self.player.input_is_available.wait()   # blocking wait
        self.need_new_input_prompt = True
        return self.player.get_pending_input()[0].strip()   # use just the first line, strip whitespace

    def write_input_prompt(self) -> None:
        # only actually write a prompt when the flag is set.
        # this avoids writing a prompt on every server tick even when nothing is entered.
        if self.need_new_input_prompt:
            self.io.write_input_prompt()
            self.need_new_input_prompt = False

    def clear_screen(self) -> None:
        self.io.clear_screen()

    def break_pressed(self) -> None:
        self.io.break_pressed()

    def critical_error(self) -> None:
        self.io.critical_error()

    def singleplayer_mainloop(self) -> None:
        self.io.singleplayer_mainloop(self)   # this does not return, unless game is closed

    def pause(self, unpause: bool=False) -> None:
        self.io.pause(unpause)

    def destroy(self) -> None:
        ctx = None
        if self.io and self.player:
            ctx = util.Context.from_global(player_connection=self)
        if self.io:
            self.io.stop_main_loop = True
            self.io.destroy()
            if self.player and mud_context.config.server_mode == GameMode.IF:
                self.player.destroy(ctx)
                self.io.abort_all_input(self.player)
                self.player = None      # type: ignore
            self.io = None              # type: ignore
        if self.player:
            self.player.destroy(ctx)
            self.player = None          # type: ignore
