"""
Mud driver (server).

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import collections
import datetime
import heapq
import importlib
import inspect
import os
import pathlib
import pkgutil
import random
import sys
import threading
import time
import typing
from functools import total_ordering
from types import ModuleType
from typing import Sequence, Union, Tuple, Any, Dict, Callable, Iterable, Generator, Set, List, MutableSequence, Optional

import appdirs

from tale import story_builder
from tale.llm.LivingNpc import LivingNpc

from . import __version__ as tale_version_str, _check_required_libraries
from . import mud_context, errors, util, cmds, player, pubsub, charbuilder, lang, verbdefs, vfs, base
from .story import TickMethod, GameMode, MoneyType, StoryBase
from .tio import DEFAULT_SCREEN_WIDTH
from .races import playable_races
from .errors import StoryCompleted, StoryConfigError
from tale.load_character import CharacterLoader, CharacterV2
from tale.llm.llm_ext import DynamicStory
from tale.llm.llm_utils import LlmUtil


topic_pending_actions = pubsub.topic("driver-pending-actions")
topic_pending_tells = pubsub.topic("driver-pending-tells")
topic_async_dialogs = pubsub.topic("driver-async-dialogs")


class Commands:
    """
    Some utility functions to manage the registered commands.
    """
    def __init__(self) -> None:
        self.commands_per_priv = {"": {}}    # type: Dict[str, Dict[str, Callable]]
        self.no_soul_parsing = set()   # type: Set[str]

    def add(self, verb: str, func: Callable, privilege: str="") -> None:
        self.validatefunc(func)
        for commands in self.commands_per_priv.values():
            if verb in commands:
                raise ValueError("command defined more than once: " + verb)
        self.commands_per_priv.setdefault(privilege, {})[verb] = func

    def override(self, verb: str, func: Callable, privilege: str="") -> Callable:
        self.validatefunc(func)
        if verb in self.commands_per_priv[privilege]:
            existing = self.commands_per_priv[privilege][verb]
            self.commands_per_priv[privilege][verb] = func
            return existing
        raise LookupError("command not defined: " + verb)

    def validatefunc(self, func: Callable) -> None:
        if not hasattr(func, "is_tale_command_func"):
            raise ValueError("the function '%s' is not a proper command function (did you forget the decorator?)" % func.__name__)

    def get(self, privileges: Iterable[str]) -> Dict[str, Callable]:
        result = dict(self.commands_per_priv[""])  # always include the cmds for empty privilege
        for priv in privileges:
            if priv in self.commands_per_priv:
                result.update(self.commands_per_priv[priv])
        return result

    def adjust_available_commands(self, server_mode: GameMode) -> None:
        # disable commands flagged with the given game_mode
        # disable soul verbs flagged with override
        # mark non-soul commands
        for commands in self.commands_per_priv.values():
            for cmd, func in list(commands.items()):
                disabled_mode = getattr(func, "disabled_in_mode", None)
                if server_mode == disabled_mode:
                    del commands[cmd]
                elif getattr(func, "overrides_soul", False):
                    del verbdefs.VERBS[cmd]
                if getattr(func, "no_soul_parse", False):
                    self.no_soul_parsing.add(cmd)


@total_ordering
class Deferred:
    """
    Represents a callable action that will be invoked (with the given arguments) sometime in the future.
    This object captures the action that must be invoked in a way that is serializable.
    That means that you can't pass all types of callables, there are a few that are not
    serializable (lambda's and scoped functions). They will trigger an error if you use those.
    If you set a (low_seconds, high_seconds) periodical tuple, the deferred will be called periodically
    where the next trigger time is randomized within the given interval.
    The due time is given in Game Time, not in real/wall time!
    Note that the vargs/kwargs should be serializable or savegames are impossible!
    """
    def __init__(self, due_gametime: datetime.datetime, action: Callable, vargs: Sequence[Any], kwargs: Dict[str, Any],
                 *, periodical: Tuple[float, float]=None) -> None:
        assert isinstance(due_gametime, datetime.datetime)
        assert callable(action)
        assert kwargs is None or "ctx" not in kwargs, "ctx will be provided by the driver when calling this"
        if periodical:
            if not len(periodical) == 2:
                raise ValueError("periodical arg must be None or a tuple(float,float)")
            if periodical[0] < 0.1 or periodical[1] < 0.1:
                raise ValueError("periodial interval values must be > 0.1")
        self.due_gametime = due_gametime   # in game time
        self.owner = getattr(action, "__self__", None)
        if isinstance(self.owner, ModuleType):
            # encode a module simply by its name
            self.owner = "module:" + self.owner.__name__
        if self.owner is None:
            action_module = getattr(action, "__module__", None)
            if action_module:
                if hasattr(sys.modules[action_module], action.__name__):
                    self.owner = "module:" + action_module
                else:
                    # a callable was passed that we cannot serialize.
                    raise ValueError("cannot use scoped functions or lambdas as deferred: " + str(action))
            else:
                raise ValueError("cannot determine action's owner object: " + str(action))
        self.action = action.__name__    # store name instead of object, to make this serializable
        self.vargs = vargs
        self.kwargs = kwargs
        self.periodical = periodical

    def __eq__(self, other):
        if self.__class__ == other.__class__:
            return self.due_gametime == other.due_gametime and self.owner.__class__ == other.owner.__class__ \
                and self.action == other.action and self.vargs == other.vargs and self.kwargs == other.kwargs
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ == other.__class__:
            return self.due_gametime < other.due_gametime   # deferreds must be sortable
        return NotImplemented

    def when_due(self, game_clock: util.GameDateTime, realtime: bool=False) -> datetime.timedelta:
        """
        In what time is this deferred due to occur? (timedelta)
        Normally it is in terms of game-time, but if you pass realtime=True,
        you will get the real-time timedelta.
        """
        secs = (self.due_gametime - game_clock.clock).total_seconds()
        if realtime:
            secs = int(secs / game_clock.times_realtime)
        return datetime.timedelta(seconds=secs)

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        self.kwargs = self.kwargs or {}
        if callable(self.action):
            func = self.action
        else:
            # deferred action is stored as the name of the function to call,
            # so we need to obtain the actual function from the owner object.
            if isinstance(self.owner, str):
                if self.owner.startswith("module:"):
                    # the owner refers to a module
                    self.owner = sys.modules[self.owner[7:]]
                else:
                    raise RuntimeError("invalid owner specifier: " + self.owner)
            func = getattr(self.owner, self.action)
        if self.periodical and hasattr(func, "_tale_periodically") and not func._tale_periodically:     # type: ignore
            return  # no longer marked as periodical
        if "ctx" in inspect.signature(func).parameters:
            self.kwargs["ctx"] = kwargs["ctx"]  # add a 'ctx' keyword argument to the call for convenience
        func(*self.vargs, **self.kwargs)
        if self.periodical and (not hasattr(func, "_tale_periodically") or func._tale_periodically):    # type: ignore
            # reschedule the same call!
            assert self.periodical[0] > 0 and self.periodical[1] > 0
            due = random.uniform(self.periodical[0], self.periodical[1])
            self.due_gametime = mud_context.driver.game_clock.plus_realtime(datetime.timedelta(seconds=due))
            if "ctx" in self.kwargs:
                del self.kwargs["ctx"]    # will be passed in again next call by driver, and required to remove because not serializable
            mud_context.driver._enqueue_deferred(self)  # reschedule!
            # note: when owner is deleted/destroyed, it must make sure that any deferreds from it are removed from the queue!
        else:
            # our lifetime has ended, remove references asap:
            del self.owner
            del self.action
            del self.kwargs
            del self.vargs


class Driver(pubsub.Listener):
    """
    The Mud 'driver'.
    Reads story file and config, initializes game state.
    Handles main game loop, player connections, and loading/saving of game state.
    """
    def __init__(self) -> None:
        self.unbound_exits = []    # type: List[base.Exit]
        self.deferreds = []   # type: List[Deferred]  # heapq
        self.deferreds_lock = threading.Lock()
        self.server_started = datetime.datetime.now().replace(microsecond=0)
        self.server_loop_durations = collections.deque(maxlen=10)    # type: MutableSequence[float]
        self.commands = Commands()
        self.all_players = {}   # type: Dict[str, player.PlayerConnection]  # maps playername to player connection object
        self.zones = None       # type: ModuleType
        self.moneyfmt = None    # type: Optional[util.MoneyFormatter]
        self.resources = None   # type: vfs.VirtualFileSystem
        self.user_resources = None  # type: vfs.VirtualFileSystem
        self.story = None       # type: StoryBase
        self.game_clock = None    # type: util.GameDateTime
        self.game_mode = None     # type: GameMode
        self._stop_mainloop = True
        self.llm_util = LlmUtil() # type: LlmUtil
        # playerconnections that wait for input; maps connection to tuple (dialog, validator, echo_input)
        self.waiting_for_input = {}   # type: Dict[player.PlayerConnection, Tuple[Generator, Any, Any]]
        mud_context.driver = self
        for verb, func, privilege in cmds.all_registered_commands():
            self.commands.add(verb, func, privilege)
        topic_pending_actions.subscribe(self)
        topic_pending_tells.subscribe(self)
        topic_async_dialogs.subscribe(self)

    def is_running(self):
        return not self._stop_mainloop

    def start(self, game_file_or_path: str) -> None:
        """Start the driver from a parsed set of arguments"""
        _check_required_libraries()
        gamepath = pathlib.Path(game_file_or_path)
        if gamepath.is_dir():
            # cd into the game directory (we can import it then), and load its config and zones
            os.chdir(str(gamepath))
            sys.path.insert(0, os.curdir)
        elif gamepath.is_file():
            # the game argument points to a file, assume it is a zipfile, add it to the import path
            sys.path.insert(0, str(gamepath))
        else:
            raise FileNotFoundError("Cannot find specified game")
        assert "story" not in sys.modules, "cannot start new story if it was already loaded before"
        cmds.clear_registered_commands()    # needed to allow stories to define their own custom commands after this
        import story
        if not hasattr(story, "Story"):
            raise AttributeError("Story class not found in the story file. It should be called 'Story'.")
        self.story = story.Story()
        self.story._verify(self)
            
            
        if self.game_mode not in self.story.config.supported_modes:
            raise ValueError("driver mode '%s' not supported by this story. Valid modes: %s" %
                             (self.game_mode, list(self.story.config.supported_modes)))
        self.story.config.mud_host = self.story.config.mud_host or "localhost"
        self.story.config.mud_port = self.story.config.mud_port or 8180
        self.story.config.server_mode = self.game_mode
        if self.game_mode != GameMode.IF and self.story.config.server_tick_method == TickMethod.COMMAND:
            raise ValueError("'command' tick method can only be used in 'if' game mode")
        # Register the driver and add some more stuff in the global context.
        self.resources = vfs.VirtualFileSystem(root_package="story")   # read-only story resources
        mud_context.config = self.story.config
        mud_context.resources = self.resources
        # check for existence of cmds package in the story root
        loader = pkgutil.get_loader("cmds")
        if loader:
            ld = pathlib.Path(loader.get_filename("cmds")).parent.parent.resolve()      # type: ignore
            sd = pathlib.Path(inspect.getabsfile(story)).parent
            if ld == sd:   # only load them if the directory is the same as where the story was loaded from
                cmds.clear_registered_commands()   # making room for the story's commands
                # noinspection PyUnresolvedReferences
                import cmds as story_cmds      # import the cmd package from the story
                for verb, func, privilege in cmds.all_registered_commands():
                    try:
                        self.commands.add(verb, func, privilege)
                    except ValueError:
                        self.commands.override(verb, func, privilege)
                cmds.clear_registered_commands()
        self.commands.adjust_available_commands(self.story.config.server_mode)
        self.game_clock = util.GameDateTime(self.story.config.epoch or self.server_started, self.story.config.gametime_to_realtime)
        self.moneyfmt = None
        if self.story.config.money_type != MoneyType.NOTHING:
            self.moneyfmt = util.MoneyFormatter.create_for(self.story.config.money_type)
        user_data_dir = pathlib.Path(appdirs.user_data_dir("Tale-" + util.storyname_to_filename(self.story.config.name),
                                                           "Razorvine", roaming=True))
        user_data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.user_resources = vfs.VirtualFileSystem(root_path=user_data_dir, readonly=False)  # r/w to the local 'user data' directory
        self.story.init(self)
        self.llm_util.set_story(self.story)
        if self.story.config.playable_races:
            # story provides playable races. Check that every race is known.
            invalid = self.story.config.playable_races - playable_races
            if invalid:
                raise errors.StoryConfigError("invalid playable_races")
        else:
            # no particular races in story config, take the defaults
            self.story.config.playable_races = playable_races
        self.zones = self._load_zones(self.story.config.zones)
        if not self.story.config.startlocation_player:
            raise errors.StoryConfigError("player startlocation not configured in story")
        if not self.story.config.startlocation_wizard:
            self.story.config.startlocation_wizard = self.story.config.startlocation_player
        self.lookup_location(self.story.config.startlocation_player)
        self.lookup_location(self.story.config.startlocation_wizard)
        if self.story.config.server_tick_method == TickMethod.COMMAND:
            # If the server tick is synchronized with player commands, this factor needs to be 1,
            # because at every command entered the game time simply advances 1 x server_tick_time.
            self.story.config.gametime_to_realtime = 1
        assert self.story.config.server_tick_time > 0
        assert self.story.config.max_wait_hours >= 0
        self.game_clock = util.GameDateTime(self.story.config.epoch or self.server_started, self.story.config.gametime_to_realtime)
        # convert textual exit strings to actual exit object bindings
        for x in self.unbound_exits:
            x._bind_target(self.zones)
        self.unbound_exits = []
        sys.excepthook = util.excepthook  # install custom verbose crash reporter
        self.start_main_loop()   # doesn't exit! (unless game is killed)
        self._stop_driver()

    def start_main_loop(self):
        raise NotImplementedError

    def connect_player(self, player_io_type: str, line_delay: int) -> player.PlayerConnection:
        raise NotImplementedError

    def _main_loop_wrapper(self, conn: Optional[player.PlayerConnection]) -> None:
        # This is a wrapper around the main game loop that the driver runs
        # (it may or may not run in a background thread depending on the driver mode)
        # The wrapper is for error handling only.
        self._stop_mainloop = False
        num_critical_errors = 0
        time_of_last_critical_error = 0.0
        while not self._stop_mainloop:
            try:
                self.main_loop(conn)
            except KeyboardInterrupt:
                # a ctrl-c will exit the server
                print("* break - stopping server loop")
                if self.all_players:
                    print("  %d players are connected: %s" % (len(self.all_players), "; ".join(self.all_players)))
                try:
                    self._stop_mainloop = lang.yesno(input("Are you sure you want to exit the Tale driver, and kill the game? "))
                except ValueError as x:
                    print(x)
                    continue
            except Exception:
                # other exceptions are logged but don't break the server loop (hopefully the game can continue)
                # @todo only print it to the player that caused the error (if possible) + to the error log
                num_critical_errors += 1
                last, time_of_last_critical_error = time_of_last_critical_error, time.time()
                if time_of_last_critical_error - last > 1.0:
                    num_critical_errors = 1  # reset critical error count due to low frequency
                if num_critical_errors > 10:
                    msg = "aborting driver main loop due to excessive number of critical errors"
                    sys.stderr.write(msg + "\n\n")
                    self._stop_driver()
                    raise errors.TaleError(msg)
                print("ERROR IN DRIVER MAINLOOP:\n", "".join(util.format_traceback()), file=sys.stderr)
                for conn in self.all_players.values():
                    conn.critical_error()

    def main_loop(self, conn: Optional[player.PlayerConnection]):
        raise NotImplementedError

    def _stop_driver(self) -> None:
        """
        Stop the driver mainloop in an orderly fashion.
        Flushes any pending output to the players, then closes down.
        """
        self._stop_mainloop = True
        for conn in self.all_players.values():
            conn.write_output()
            conn.destroy()
        self.all_players.clear()
        time.sleep(0.1)

    def _continue_dialog(self, conn: player.PlayerConnection, dialog: Generator, message: str) -> None:
        # Notice that the try...except structure is very similar to
        # the one in _server_loop_process_player_input
        # That's no surprise because also in this async case, we need
        # to handle any parse errors and such that may be thrown from the
        # generator. The reguar player input function has to deal with
        # them as well, caused by normal player commands.
        try:
            why, what = dialog.send(message or None)
        except StopIteration:
            if conn.player:
                conn.write_output()   # immediately give feedback (if any) once the dialog ends
        except errors.ActionRefused as x:
            conn.player.remember_previous_parse()
            conn.player.tell(str(x))
            conn.write_output()
        except errors.ParseError as x:
            conn.player.tell(str(x))
            conn.write_output()
        else:
            if why in ("input", "input-noecho"):
                if isinstance(what, tuple):
                    prompt, validator = what
                else:
                    prompt, validator = what, None
                if prompt:
                    if not prompt.endswith(" "):
                        prompt += " "
                    conn.write_output()
                    conn.output_no_newline(prompt)  # the input prompt
                assert conn not in self.waiting_for_input, "can only run one async dialog at the same time"
                conn.io.dont_echo_next_cmd = why == "input-noecho"  # this avoids echoing of the password
                self.waiting_for_input[conn] = (dialog, validator, why != "input-noecho")
            else:
                raise ValueError("invalid generator wait reason: " + why)

    def print_game_intro(self, conn: Optional[player.PlayerConnection]) -> None:
        try:
            # print game banner as supplied by the game
            banner = self.resources["messages/banner.txt"].text
            if conn:
                conn.player.tell("<bright>%s</>" % banner, format=False)
                conn.player.tell("\n")
            else:
                print(banner)
        except IOError:
            # no banner provided by the game, print default game header
            if conn:
                o = conn.output
                o("")
                o("")
                o("<monospaced><bright>")
                o(("`%s'" % self.story.config.name).center(DEFAULT_SCREEN_WIDTH))
                o(("v" + self.story.config.version).center(DEFAULT_SCREEN_WIDTH))
                o("")
                o(("written by " + self.story.config.author).center(DEFAULT_SCREEN_WIDTH))
                if self.story.config.author_address:
                    o(self.story.config.author_address.center(DEFAULT_SCREEN_WIDTH))
                o("</></monospaced>")
                o("")
                o("")
        if not conn:
            print("\n")
            print("Tale library:", tale_version_str)
            print("MudLib:       %s, v%s" % (self.story.config.name, self.story.config.version))
            if self.story.config.author:
                print("Written by:   %s - %s" % (self.story.config.author, self.story.config.author_address or ""))
            print("Driver start:", time.ctime())
            print("\n")

    def _rename_player(self, player: player.Player, name_info: charbuilder.PlayerNaming) -> None:
        conn = self.all_players[player.name]
        del self.all_players[player.name]
        old_wiretap = player.get_wiretap()
        old_wiretap.destroy()
        self.all_players[name_info.name] = conn
        name_info.apply_to(player)

    def _server_loop_process_player_input(self, conn: player.PlayerConnection) -> None:
        p = conn.player
        assert p.input_is_available.is_set()
        for cmd in p.get_pending_input():
            if not cmd:
                continue
            try:
                p.tell("\n")
                self._process_player_command(cmd, conn)
                p.remember_previous_parse()
                # to avoid flooding/abuse, we stop the loop after processing one command.
                break
            except errors.UnknownVerbException as x:
                if x.verb in {"north", "east", "south", "west",
                              "northeast", "northwest", "southeast", "southwest",
                              "north east", "north west", "south east", "south west",
                              "up", "down"}:
                    p.tell("You can't go in that direction.")
                else:
                    p.tell("The verb `%s' is unrecognized." % x.verb)
                    if x.verb[0].isupper():
                        p.tell("Just type in lowercase (`%s')." % x.verb.lower())
            except errors.ActionRefused as x:
                p.remember_previous_parse()
                p.tell(str(x))
            except errors.ParseError as x:
                p.tell(str(x))

    def _server_tick(self) -> None:
        """
        Do everything that the server needs to do every tick (timer configurable in story)
        1) game clock
        2) deferreds
        3) pending pubsub events
        4) write buffered output
        5) verify validity and idle state of connected players
        6) remove idle wiretaps
        """
        self.game_clock.add_realtime(datetime.timedelta(seconds=self.story.config.server_tick_time))
        ctx = util.Context(self, self.game_clock, self.story.config, None)

        due_deferreds = []
        with self.deferreds_lock:
            while self.deferreds:
                deferred = self.deferreds[0]
                if deferred.due_gametime > self.game_clock.clock:
                    break
                due_deferreds.append(heapq.heappop(self.deferreds))
        for deferred in due_deferreds:
            try:
                deferred(ctx=ctx)  # call the deferred and provide a context object
            except StoryCompleted:
                raise    # handled elsewhere (IF)
            except Exception:
                print("\n* Exception while executing deferred action {0}:".format(deferred), file=sys.stderr)
                print("".join(util.format_traceback()), file=sys.stderr)
                print("(Please report this problem)", file=sys.stderr)
        del due_deferreds

        pubsub.sync()
        for name, conn in list(self.all_players.items()):
            if conn.player and conn.io and conn.player.location:
                self.disconnect_idling(conn)
                conn.write_output()
            else:
                # disconnect corrupt player connection
                self.disconnect_player(conn)
        # clean up idle wiretap topics
        topicinfo = pubsub.pending()
        for topicname in topicinfo:
            if isinstance(topicname, tuple) and topicname[0].startswith("wiretap-"):
                events, idle_time, subbers = topicinfo[topicname]
                if events == 0 and not subbers and idle_time > 30:
                    pubsub.topic(topicname).destroy()

    def disconnect_idling(self, conn: player.PlayerConnection) -> None:
        raise NotImplementedError

    def disconnect_player(self, conn: player.PlayerConnection) -> None:
        raise NotImplementedError

    def _process_player_command(self, cmd: str, conn: player.PlayerConnection) -> None:
        if not cmd:
            return
        if cmd and cmd[0] in cmds.abbreviations and not cmd[0].isalpha():
            # insert a space to separate the first char such as ' or ?
            cmd = cmd[0] + " " + cmd[1:]
        # check for an abbreviation, replace it with the full verb if present
        _verb, _sep, _rest = cmd.partition(" ")
        if _verb in cmds.abbreviations:
            _verb = cmds.abbreviations[_verb]
            cmd = "".join([_verb, _sep, _rest])

        player = conn.player
        # We pass in all 'external verbs' (non-soul verbs) so it will do the
        # parsing for us even if it's a verb the soul doesn't recognise by itself.
        command_verbs = self.commands.get(player.privileges)
        custom_verbs = set(self.current_custom_verbs(player))
        try:
            if _verb in self.commands.no_soul_parsing:
                # don't use the soul to parse it further
                player.turns += 1
                raise errors.NonSoulVerb(base.ParseResult(_verb, unparsed=_rest.strip()))
            else:
                # Parse the command by using the soul.
                all_verbs = set(command_verbs) | custom_verbs
                parsed = player.parse(cmd, external_verbs=all_verbs)
            # If parsing went without errors, it's a soul verb, handle it as a socialize action
            player.turns += 1
            player.do_socialize_cmd(parsed)
        except errors.NonSoulVerb as x:
            parsed = x.parsed
            if parsed.qualifier:
                # for now, qualifiers are only supported on soul-verbs (emotes).
                raise errors.ParseError("That action doesn't support qualifiers.")
            # Execute non-soul verb. First try directions, then the rest.
            player.turns += 1
            try:
                # Check if the verb is a custom verb and try to handle that.
                # If it remains unhandled, check if it is a normal verb, and handle that.
                # If it's not a normal verb, abort with "please be more specific".
                parse_error = "That doesn't make much sense."
                handled = False
                if parsed.verb in custom_verbs:
                    # @todo note: can't deal with yields directly, use errors.AsyncDialog in handle_verb to initiate a dialog
                    handled = player.location.handle_verb(parsed, player)
                    if handled:
                        topic_pending_actions.send(lambda actor=player: actor.location._notify_action_all(parsed, actor))
                    else:
                        parse_error = "Please be more specific."
                if not handled:
                    if parsed.verb in player.location.exits:
                        self.go_through_exit(player, parsed.verb)
                    elif parsed.verb in command_verbs:
                        # Here, one of the commands as annotated with @cmd (or @wizcmd) is executed
                        func = command_verbs[parsed.verb]
                        del command_verbs  # no longer needed
                        ctx = util.Context(self, self.game_clock, self.story.config, conn)
                        if getattr(func, "is_generator", False):
                            dialog = func(player, parsed, ctx)
                            topic_async_dialogs.send((conn, dialog))    # enqueue as async, and continue
                        else:
                            func(player, parsed, ctx)
                        if func.enable_notify_action:       # type: ignore
                            topic_pending_actions.send(lambda actor=player: actor.location._notify_action_all(parsed, actor))
                    else:
                        raise errors.ParseError(parse_error)
            except errors.RetrySoulVerb:
                # cmd decided it can't deal with the parsed stuff and that it needs to be retried as soul emote.
                player.validate_socialize_targets(parsed)
                player.do_socialize_cmd(parsed)
            except errors.RetryParse as x:
                return self._process_player_command(x.command, conn)   # try again but with new command string
            except errors.AsyncDialog as x:
                # the player command ended but signaled that an async dialog should be initiated
                topic_async_dialogs.send((conn, x.dialog))

    def go_through_exit(self, player: player.Player, direction: str, evoke: bool=True) -> None:
        xt = player.location.exits[direction]
        xt.allow_passage(player)
        if not xt.target.built:
            dynamic_story = typing.cast(DynamicStory, self.story)
            zone = dynamic_story.find_zone(location=player.location.name)
            # are we close to the edge of a zone? if so we need to build the next zone.
            new_zone = self.llm_util.get_neighbor_or_generate_zone(current_zone=zone, 
                                                        current_location=player.location, 
                                                        target_location=xt.target)
            if zone.name != new_zone.name:
                player.tell(f"You're entering {new_zone.name}:{new_zone.description}")
            
            # generate the location if it's not built yet. retry 5 times.
            for i in range(5):
                neighbor_locations = dynamic_story.neighbors_for_location(xt.target)
                new_locations, exits = self.llm_util.build_location(location=xt.target, 
                                                             exit_location_name=player.location.name, 
                                                             zone_info=new_zone.get_info(),
                                                             world_creatures=dynamic_story.catalogue._creatures,
                                                             world_items=dynamic_story.catalogue._items,
                                                             neighbors=neighbor_locations,)
                if new_locations:
                    break
            if not new_locations:
                raise errors.ActionRefused("Reached max attempts when building location: " + xt.target.name + ". You can try entering again.")
            for location in new_locations:
                # try to add location, and if it fails, remove exit to it
                result = dynamic_story.add_location(location, zone=new_zone.name)
                if not result:
                    for exit in exits:
                        if exit.name == location.name:
                            exits.remove(exit)
            for exit in exits:
                try:
                    xt.target.add_exits([exit])
                except errors.LocationIntegrityError:
                    # fail silently
                    pass
        elif random.random() < 0.2 and isinstance(self.story, DynamicStory):
            dynamic_story = typing.cast(DynamicStory, self.story)
            zone = dynamic_story.find_zone(location=xt.target.name)
            self.llm_util.generate_random_spawn(xt.target, zone.get_info())
                    
        if xt.enter_msg:
            player.tell(xt.enter_msg, end=True, evoke=False, short_len=True)
            player.tell("\n")
        player.move(xt.target, direction_names=[xt.name] + list(xt.aliases))
        player.look(evoke=evoke)

    def lookup_location(self, location_name: str) -> base.Location:
        location = self.zones
        modulename = "zones"
        for name in location_name.split('.'):
            modulename += "." + name
            if hasattr(location, name):
                location = getattr(location, name)
            else:
                try:
                    module = importlib.import_module(modulename)
                    location = module
                except ImportError:
                    if isinstance(self.story, DynamicStory):
                        dynamic_story = typing.cast(DynamicStory, self.story)
                        location = dynamic_story.find_location(location_name.split('.')[-1])
                    if not location:
                        raise errors.TaleError("Location not found: " + location_name)
        return location     # type: ignore

    def _load_zones(self, zone_names: Sequence[str]) -> ModuleType:
        # Pre-load the provided zones (essentially, load the named modules from the zones package)
        if not zone_names and "zones" not in sys.modules:
            raise errors.StoryConfigError("story config doesn't provide any zones to load and hasn't loaded any zones itself")
        for zone in zone_names or []:
            try:
                module = importlib.import_module("zones." + zone)
            except ImportError:
                if isinstance(self.story, DynamicStory):
                    return []
                raise errors.TaleError("zone not found: " + zone)
            if hasattr(module, "init"):
                # call the zone module initialization function
                module.init(self)       # type: ignore
        return importlib.import_module("zones")

    def current_custom_verbs(self, player: player.Player) -> Dict[str, str]:
        """returns dict of the currently recognised custom verbs (verb->helptext mapping)"""
        verbs = player.verbs.copy()
        verbs.update(player.location.verbs)
        for living in player.location.livings:
            verbs.update(living.verbs)
        for item in player.inventory:
            verbs.update(item.verbs)
        for item in player.location.items:
            verbs.update(item.verbs)
        for exit in set(player.location.exits.values()):
            verbs.update(exit.verbs)
        return verbs

    def current_verbs(self, player: player.Player) -> Dict[str, str]:
        """return a dict of all currently recognised verbs, and their help text"""
        normal_verbs = self.commands.get(player.privileges)
        verbs = {v: (f.__doc__ or "") for v, f in normal_verbs.items()}
        verbs.update(self.current_custom_verbs(player))
        return verbs

    def show_motd(self, player: player.Player, notify_no_motd: bool=False) -> None:
        raise NotImplementedError

    def search_player(self, name: str) -> Optional[player.Player]:
        """
        Look through all the logged in players for one with the given name.
        Returns None if no one is known with that name.
        """
        name = name.lower()
        conn = self.all_players.get(name)
        if not conn:
            for pname, conn in self.all_players.items():
                if name == pname.lower():
                    break
            return None
        return conn.player

    def do_wait(self, duration: datetime.timedelta) -> Tuple[bool, str]:
        # let time pass, duration is in game time (not real time).
        # We do let the game tick for the correct number of times.
        # @todo be able to detect if something happened during the wait
        assert self.story.config.server_mode == GameMode.IF
        if self.story.config.gametime_to_realtime == 0:
            # game is running with a 'frozen' clock
            # simply advance the clock, and perform a single server_tick
            self.game_clock.add_gametime(duration)
            self._server_tick()
            return True, ""      # uneventful
        num_ticks = int(duration.seconds / self.story.config.gametime_to_realtime / self.story.config.server_tick_time)
        if num_ticks < 1:
            return False, "It's no use waiting such a short while."
        for _ in range(num_ticks):
            self._server_tick()
        return True, ""     # wait was uneventful. (@todo return False if something happened)

    def do_check_savefile_free(self, player: player.Player) -> bool:
        raise NotImplementedError

    def do_save(self, player: player.Player) -> None:
        raise NotImplementedError

    def register_exit(self, exit: base.Exit) -> None:
        if exit.target in (base._limbo, None):
            self.unbound_exits.append(exit)

    DeferDueType = Union[datetime.datetime, float, Tuple[float, float, float]]

    def defer(self, due: DeferDueType, action: Callable, *vargs: Any, **kwargs: Any) -> Deferred:
        """
        Register a deferred callable action (optionally with arguments).
        The vargs and the kwargs all must be serializable.
        Note that the due time can be one of:
        -  datetime.datetime *in game time* (not real time!) when the deferred should trigger.
        -  float, meaning the number of real-time seconds after the current time (minimum: 0.1 sec)
        -  tuple(initial_secs, low_secs, high_secs), meaning it is periodical within the given time interval.
        The deferred gets a kwarg 'ctx' set to a Context object, if it has
        a 'ctx' argument in its signature. (If not, that's okay too)
        Receiving the context is often useful, for instance you can register a new
        deferred on the ctx.driver without having to access a global driver object.
        Triggering a deferred can not occur sooner than the server tick period!
        """
        assert callable(action)
        if self.game_clock is None:
            raise errors.TaleError("Attempt to register a deferred action while Driver hasn't been properly started yet. "
                                   "A possible cause is importing zone or npc module files that create MudObjects "
                                   "that use @call_periodically, before the driver has been fully started and loads these by itself.")
        if isinstance(due, datetime.datetime):
            assert due >= self.game_clock.clock
            deferred = Deferred(due, action, vargs, kwargs)
        elif isinstance(due, tuple):
            due, periodical_low, periodical_high = due
            if due < 0.1 or periodical_low < 0.1 or periodical_high < 0.1:
                raise ValueError("due time and periodical times must be >= 0.1  action: %s" % action)
            assert periodical_high >= periodical_low
            due = self.game_clock.plus_realtime(datetime.timedelta(seconds=due))
            deferred = Deferred(due, action, vargs, kwargs, periodical=(periodical_low, periodical_high))
        else:
            due = float(due)
            if due < 0.1:
                raise ValueError("due time must be >= 0.1  action: %s" % action)
            due = self.game_clock.plus_realtime(datetime.timedelta(seconds=due))
            deferred = Deferred(due, action, vargs, kwargs)
        self._enqueue_deferred(deferred)
        return deferred

    def _enqueue_deferred(self, deferred: Deferred) -> None:
        if "ctx" in deferred.kwargs:
            raise errors.TaleError("you cannot enqueue a Deferred that already has a 'ctx' kwarg (serialization issues)")
        with self.deferreds_lock:
            heapq.heappush(self.deferreds, deferred)

    def pubsub_event(self, topicname: pubsub.TopicNameType, event: Union[Callable, Tuple[player.PlayerConnection, str]]) -> None:
        if topicname == "driver-pending-actions":
            assert callable(event), "the driver-pending-actions events should be callables"
            event()
        elif topicname == "driver-pending-tells":
            assert callable(event), "the driver-pending-tells events should be callables"
            event()
        elif topicname == "driver-async-dialogs":
            if isinstance(event, tuple):
                conn, dialog = event
            else:
                raise TypeError("event must be tuple here")
            assert type(conn) is player.PlayerConnection
            assert inspect.isgenerator(dialog)
            self._continue_dialog(conn, dialog, "")     # type: ignore
        else:
            raise ValueError("unknown topic: " + str(topicname))

    def remove_deferreds(self, owner: str) -> None:
        with self.deferreds_lock:
            self.deferreds = [d for d in self.deferreds if d.owner is not owner]
            heapq.heapify(self.deferreds)

    def register_periodicals(self, obj: base.MudObject) -> None:
        for func, period in util.get_periodicals(obj).items():
            assert len(period) == 3
            mud_context.driver.defer(period, func)
            
    def load_character(self, player: player.Player, path: str):
        """Loads a character from a json file and inserts it into the player's location."""
        character_loader = CharacterLoader()
        char_data = character_loader.load_character(path)
        character = CharacterV2().from_json(char_data)
        npc = LivingNpc(name = character.name.lower(), 
                        gender = character.gender,
                        title = character.name, 
                        descr  = character.appearance, 
                        short_descr = character.appearance.split('.')[0], 
                        age =  character.age, 
                        personality = character.personality, 
                        race = character.race,
                        occupation = character.occupation)
        npc.following = player
        npc.stats.hp = character.hp
        player.location.insert(npc, None)
        

    @property
    def uptime(self) -> Tuple[int, int, int]:
        """gives the server uptime in a (hours, minutes, seconds) tuple"""
        realtime = datetime.datetime.now()
        realtime = realtime.replace(microsecond=0)
        uptime = realtime - self.server_started
        hours, seconds = divmod(uptime.total_seconds(), 3600)
        minutes, seconds = divmod(seconds, 60)
        return int(hours), int(minutes), int(seconds)
    
    def prepare_combat_prompt(self, 
                              attacker: LivingNpc, 
                              victim: LivingNpc, 
                              location_title: str, 
                              location_description: str, 
                              attacker_msg: str):
        """ TODO: A bad work around. Need to find a better way to do this."""
        attacker_name = lang.capital(attacker.title)
        victim_name = lang.capital(victim.title)

        if isinstance(attacker, player.Player):
            attacker_name += " (as 'You')"
            attacker_msg.replace(attacker_name, "you")
        if isinstance(victim, player.Player):
            victim_name += " (as 'You')"
            attacker_msg.replace(victim_name, "you")

        victim_info = {"name": victim_name, 
                       "health": victim.stats.hp / victim.stats.max_hp, 
                       "weapon": victim.wielding.title}

        attacker_info = {"name": attacker_name, 
                         "health": attacker.stats.hp / attacker.stats.max_hp, 
                         "weapon": attacker.wielding.title}

        return self.llm_util.combat_prompt.format(attacker=attacker_info, 
                                                    victim=victim_info,
                                                    attacker_msg=attacker_msg,
                                                    location=location_title,
                                                    location_description=location_description)
