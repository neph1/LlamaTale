"""
Single user driver (for interactive fiction).

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import sys
import time
import threading
from typing import Generator, Optional, Union
from .story import GameMode, TickMethod, StoryConfig
from . import base
from . import charbuilder
from . import driver
from . import errors
from . import lang
from . import pubsub
from . import util
from . import savegames
from .player import PlayerConnection, Player
from .tio import DEFAULT_SCREEN_DELAY
from .tio import iobase
from .llm_utils import LlmUtil
from tale.load_character import CharacterLoader

class IFDriver(driver.Driver):
    """
    The Single user 'driver'.
    Used to control interactive fiction where there's only one 'player'.
    """
    def __init__(self, *, screen_delay: int=DEFAULT_SCREEN_DELAY, gui: bool=False, web: bool=False, wizard_override: bool=False, character_to_load: str='') -> None:
        super().__init__()
        self.game_mode = GameMode.IF
        if screen_delay < 0 or screen_delay > 100:
            raise ValueError("invalid delay, valid range is 0-100")
        self.screen_delay = screen_delay
        self.io_type = "console"
        if gui:
            self.io_type = "gui"
        if web:
            self.io_type = "web"
        self.wizard_override = wizard_override
        if character_to_load:
            character_loader = CharacterLoader()
            if '.json' in character_to_load:
                self.loaded_character = character_loader.load_from_json(character_to_load)
            elif '.png' in character_to_load or '.jpg' in character_to_load:
                self.loaded_character = character_loader.load_image(character_to_load)
            else:
                print("Failed to load character, must be .json, .jpg or .png")
                self.loaded_character = None
        else:
            self.loaded_character = None

    def start_main_loop(self):
        if self.io_type == "web":
            print("starting '{0}'  v {1}".format(self.story.config.name, self.story.config.version))
            if self.story.config.author_address:
                print("written by {0} - {1}".format(self.story.config.author, self.story.config.author_address))
            else:
                print("written by", self.story.config.author)
        connection = self.connect_player(self.io_type, self.screen_delay)
        self.llm_util.connection = connection
        if self.wizard_override:
            connection.player.privileges.add("wizard")
        # create the login dialog
        driver.topic_async_dialogs.send((connection, self._login_dialog_if(connection)))
        # the driver mainloop runs in a background thread, the io-loop/gui-event-loop runs in the main thread
        driver_thread = threading.Thread(name="driver", target=self._main_loop_wrapper, args=(connection,))
        driver_thread.daemon = True
        driver_thread.start()
        connection.singleplayer_mainloop()     # this doesn't return! (unless you CTRL-C it)
        self._stop_mainloop = True
        connection.destroy()

    def show_motd(self, player: Player, notify_no_motd: bool=False) -> None:
        pass   # no motd in IF mode

    def do_check_savefile_free(self, player: Player) -> bool:
        if not self.story.config.savegames_enabled:
            raise errors.ActionRefused("It is not possible to save your progress.")
        savegame_filename = util.storyname_to_filename(self.story.config.name) + ".savegame"
        try:
            _ = self.user_resources[savegame_filename]
            return False
        except FileNotFoundError:
            return True

    def do_save(self, player: Player) -> None:
        if not self.story.config.savegames_enabled:
            raise errors.ActionRefused("It is not possible to save your progress.")
        serializer = savegames.TaleSerializer()
        all_locations = [loc for loc in base.MudObjRegistry.all_locations.values()]
        all_items = [i for i in base.MudObjRegistry.all_items.values() if i.contained_in]
        all_livings = [l for l in base.MudObjRegistry.all_livings.values() if l.location]
        all_exits = list(base.MudObjRegistry.all_exits.values())
        savedata = serializer.serialize(self.story.config, player, all_items, all_livings, all_locations, all_exits,
                                        self.deferreds, self.game_clock)
        del all_locations, all_exits, all_items, all_livings
        self.user_resources[util.storyname_to_filename(self.story.config.name) + ".savegame"] = savedata
        player.tell("Game saved.")
        if self.story.config.display_gametime:
            player.tell("Game time: %s" % self.game_clock)
        player.tell("\n")

    def connect_player(self, player_io_type: str, line_delay: int) -> PlayerConnection:
        connection = PlayerConnection()
        connect_name = "<connecting_%d>" % id(connection)  # unique temporary name
        new_player = Player(connect_name, "n", race="elemental", descr="This player is still connecting to the game.")
        if player_io_type == "gui":
            from .tio.tkinter_io import TkinterIo
            io = TkinterIo(self.story.config, connection)  # type: iobase.IoAdapterBase
        elif player_io_type == "web":
            from .tio.if_browser_io import HttpIo, TaleWsgiApp
            wsgi_server = TaleWsgiApp.create_app_server(self, connection, use_ssl=False, ssl_certs=None)
            # you can enable SSL by using the following:
            # wsgi_server = TaleWsgiApp.create_app_server(self, connection, use_ssl=True,
            #                   ssl_certs=("certs/localhost_cert.pem", "certs/localhost_key.pem", ""))
            io = HttpIo(connection, wsgi_server)
        elif player_io_type == "console":
            from .tio.console_io import ConsoleIo
            io = ConsoleIo(connection)
            io.install_tab_completion(self)
        else:
            raise ValueError("invalid io type, must be one of: gui web console")
        connection.player = new_player
        connection.io = io
        self.all_players[new_player.name] = connection
        new_player.output_line_delay = line_delay
        connection.clear_screen()
        self.print_game_intro(connection)
        return connection

    def _login_dialog_if(self, conn: PlayerConnection) -> Generator:
        # Interactive fiction (singleplayer): create a player. This is a generator function (async input).
        # Initialize it directly from the story's configuration, load a saved game,
        # or let the user create a new player manually.
        # Be sure to always reference conn.player here (and not get a cached copy),
        # because it will get replaced when loading a saved game!
        if not self.story.config.savegames_enabled:
            load_saved_game = False
        else:
            conn.player.tell("\n")
            load_saved_game = yield "input", ("Do you want to load a saved game ('<bright>n</>' will start a new game)?", lang.yesno)
        conn.player.tell("\n")
        if load_saved_game:
            loaded_player = self._load_saved_game(conn.player)
            if loaded_player:
                # switch active player objects and remove the player placeholder used while connecting
                old_player, conn.player = conn.player, loaded_player
                old_player.destroy(util.Context(self, self.game_clock, self.story.config, conn))
                del old_player
                conn.player.tell("\n")
                prompt = self.story.welcome_savegame(conn.player)
                if prompt:
                    yield "input", "\n" + prompt
                conn.player.tell("\n")
            else:
                load_saved_game = False

        if load_saved_game:
            self.story.init_player(conn.player)
            conn.player.look(short=False)   # force a 'look' command to get our bearings
            return

        if self.loaded_character:
            name_info = charbuilder.PlayerNaming()
            name_info.name = self.loaded_character.get('name')
            name_info.stats.race = self.loaded_character.get('race', 'human')
            name_info.gender = self.loaded_character.get('gender', 'm')
            name_info.money = self.loaded_character.get('money', 0.0)
            name_info.wizard = "wizard" in conn.player.privileges
        elif self.story.config.player_name:
            # story config provides a name etc.
            name_info = charbuilder.PlayerNaming()
            name_info.name = self.story.config.player_name
            name_info.stats.race = self.story.config.player_race
            name_info.gender = self.story.config.player_gender
            name_info.money = self.story.config.player_money or 0.0
            name_info.wizard = "wizard" in conn.player.privileges
        else:
            # No story player config: create a character with the builder
            # This is unusual though, normally any 'if' story should provide a player config
            builder = charbuilder.IFCharacterBuilder(conn, self.story.config)
            name_info = yield from builder.build_character()
            if not name_info:
                conn.output("\nUser was undecided when creating player character.\n")
                self._stop_driver()
                raise SystemExit(0)
            result = yield from self.story.create_account_dialog(conn, name_info)   # story can customize more things
            if not result:
                conn.output("\nStory aborted player creation dialog.\n")
                self._stop_driver()
                raise SystemExit(0)

        player = conn.player
        self._rename_player(player, name_info)
        player.tell("\n")
        # move the player to the starting location:
        if "wizard" in player.privileges:
            player.move(self.lookup_location(self.story.config.startlocation_wizard))
        else:
            player.move(self.lookup_location(self.story.config.startlocation_player))
        player.tell("\n")
        prompt = self.story.welcome(player)

        self.llm_util.story_type = self.story.config.type
        self.llm_util.story_background = self.story.config.context
        
        if prompt:
            conn.input_direct("\n" + prompt)   # blocks  (note: cannot use yield here)
        player.tell("\n")
        self.story.init_player(player)
        player.look(short=False)  # force a 'look' command to get our bearings
        conn.write_output()

    def disconnect_idling(self, conn: PlayerConnection):
        pass

    def disconnect_player(self, conn: PlayerConnection):
        raise errors.TaleError("Disconnecting a player should not happen in single player IF mode. Please report this bug.")

    def main_loop(self, conn: Optional[PlayerConnection]) -> None:
        """
        The game loop, for the single player Interactive Fiction game mode.
        Until the game is exited, it processes player input, and prints the resulting output.
        """
        assert conn
        conn.write_output()
        loop_duration = 0.0
        previous_server_tick = 0.0

        def story_completed():
            self._stop_mainloop = True
            conn.player.tell("\n")
            conn.input_direct("\n\nPress enter to exit. ")  # blocking
            conn.player.tell("\n")
            self._stop_driver()

        while not self._stop_mainloop:
            pubsub.sync("driver-async-dialogs")
            if conn not in self.waiting_for_input:
                conn.write_input_prompt()
            if self.story.config.server_tick_method == TickMethod.COMMAND:
                conn.player.input_is_available.wait()   # blocking wait until playered entered something
                has_input = True
            elif self.story.config.server_tick_method == TickMethod.TIMER:
                # server tick goes on a timer, wait a limited time for player input before going on
                input_wait_time = max(0.01, self.story.config.server_tick_time - loop_duration)
                has_input = conn.player.input_is_available.wait(input_wait_time)
            else:
                raise ValueError("invalid tick method")

            loop_start = time.time()
            if has_input:
                conn.need_new_input_prompt = True
                try:
                    if not conn.player:
                        continue
                    if conn in self.waiting_for_input:
                        # this connection is processing direct input, rather than regular commands
                        dialog, validator, echo_input = self.waiting_for_input.pop(conn)
                        response = conn.player.get_pending_input()[0]
                        if validator:
                            try:
                                response = validator(response)
                            except ValueError as x:
                                prompt = conn.last_output_line
                                conn.io.dont_echo_next_cmd = not echo_input
                                conn.output(str(x) or "That is not a valid answer.")
                                conn.output_no_newline(prompt)   # print the input prompt again
                                self.waiting_for_input[conn] = (dialog, validator, echo_input)   # reschedule
                                continue
                        self._continue_dialog(conn, dialog, response)
                    else:
                        # normal command processing
                        self._server_loop_process_player_input(conn)
                except (KeyboardInterrupt, EOFError):
                    continue
                except errors.SessionExit:
                    self._stop_mainloop = True
                    self.story.goodbye(conn.player)
                    self._stop_driver()
                    break
                except errors.StoryCompleted:
                    story_completed()
                    break
                except Exception:
                    txt = "\n<bright><rev>* internal error (please report this):</>\n" + "".join(util.format_traceback())
                    if conn.player:
                        conn.player.tell(txt, format=False)
                        conn.player.tell("<rev><it>Please report this problem.</>")
                    else:
                        print("ERROR IN SINGLE PLAYER DRIVER LOOP:", file=sys.stderr)
                        print(txt, file=sys.stderr)
                    del txt
            try:
                # sync pubsub pending tells
                pubsub.sync("driver-pending-tells")
                # server TICK
                now = time.time()
                if now - previous_server_tick >= self.story.config.server_tick_time:
                    self._server_tick()
                    previous_server_tick = now
                if self.story.config.server_tick_method == TickMethod.COMMAND:
                    # Even though the server tick may be skipped, the pubsub events
                    # should be processed every player command no matter what.
                    pubsub.sync()
            except errors.StoryCompleted:
                # completing the story can also be done from a deferred action or pubsub event
                story_completed()
                break
            loop_duration = time.time() - loop_start
            self.server_loop_durations.append(loop_duration)
            conn.write_output()

    def _load_saved_game(self, existing_player: Player) -> Optional[Player]:
        # at this time, game loading/saving is only supported in single player IF mode.
        assert len(self.all_players) == 1
        conn = list(self.all_players.values())[0]
        try:
            savegame = self.user_resources[util.storyname_to_filename(self.story.config.name) + ".savegame"].data
            deserializer = savegames.TaleDeserializer()
            state = deserializer.deserialize(savegame)
            del savegame
        except (ValueError, TypeError) as x:
            print("There was a problem loading the saved game data:")
            print(type(x).__name__, x)
            self._stop_driver()
            raise SystemExit(10)
        except FileNotFoundError:
            existing_player.tell("No saved game data found.", end=True)
            return None
        except IOError as x:
            existing_player.tell("Failed to load save game data: " + str(x), end=True)
            return None
        else:
            savegame_version = state["story_config"]["version"]
            if savegame_version != self.story.config.version:
                existing_player.tell("\n")
                existing_player.tell("<it>Note: the saved game data is from a different version of the game and may cause problems.</>")
                existing_player.tell("We'll attempt to load it anyway. (Current game version: %s / Saved game data version: %s). "
                                     % (self.story.config.version, savegame_version), end=True)
            objects_finder = SavegameExistingObjectsFinder()

            clock = deserializer.recreate_classes(state.pop("clock"), None)
            assert isinstance(clock, util.GameDateTime)
            self.game_clock = clock

            story_config = deserializer.recreate_classes(state.pop("story_config"), None)
            assert isinstance(story_config, StoryConfig)
            self.story.config = story_config

            exits_data = list(sorted(state.pop("exits"), key=lambda d: d.get("vnum")))
            saved_exits = deserializer.recreate_classes(exits_data, objects_finder)
            assert all(isinstance(e, base.Exit) for e in saved_exits)

            items_data = list(sorted(state.pop("items"), key=lambda d: d.get("vnum")))
            saved_items_info = deserializer.recreate_classes(items_data, objects_finder)
            # link items contained in other items
            for item_info in saved_items_info:
                item = item_info["item"]
                assert isinstance(item, base.Item)
                if item_info["contains"]:
                    if isinstance(item, base.Container):
                        contained = {objects_finder.resolve_item_ref(*i_ref) for i_ref in item_info["contains"]}
                        item.init_inventory(contained)
                    else:
                        raise errors.TaleError("can't put stuff in an item that isn't a Container")

            loc_data = list(sorted(state.pop("locations"), key=lambda d: d.get("vnum")))
            saved_locs = deserializer.recreate_classes(loc_data, objects_finder)
            assert all(isinstance(l, base.Location) for l in saved_locs)

            livings_data = list(sorted(state.pop("livings"), key=lambda d: d.get("vnum")))
            saved_livings_info = deserializer.recreate_classes(livings_data, objects_finder)
            for living_info in saved_livings_info:
                living = living_info["living"]
                assert isinstance(living, base.Living)
                if living_info["inventory"]:
                    contained = {objects_finder.resolve_item_ref(*i_ref) for i_ref in living_info["inventory"]}
                    living.init_inventory(contained)
                loc = objects_finder.resolve_location_ref(*living_info["location"])
                if living.location and living.location is not loc:
                    living.location.remove(living, living)
                # we can't yet set following because it might still point to a non-existing player object. Do that later.
                loc.insert(living, living)

            saved_player_info = deserializer.recreate_classes(state.pop("player"), None)
            saved_player = saved_player_info["player"]
            assert isinstance(saved_player, Player)
            base.MudObjRegistry.all_livings[saved_player.vnum] = saved_player   # overwrite intermediate player object
            contained = {objects_finder.resolve_item_ref(*i_ref) for i_ref in saved_player_info["inventory"]}
            for thing in contained:
                if thing.contained_in and thing.contained_in is not saved_player:
                    # remove the item from its original location, the player now has it in its pocketses
                    thing.contained_in.remove(thing, None)
            saved_player.init_inventory(contained)
            loc = objects_finder.resolve_location_ref(*saved_player_info["location"])
            if saved_player.location and saved_player.location is not loc:
                saved_player.location.remove(saved_player, saved_player)
            loc.insert(saved_player, saved_player)
            saved_player.known_locations = {objects_finder.resolve_location_ref(*loc_info) for loc_info in saved_player_info["known_locs"]}
            if saved_player_info["following"]:
                saved_player.following = objects_finder.resolve_living_ref(*saved_player_info["following"])
            self.all_players = {saved_player.name: conn}

            # creatures that follow other creatures (or the player).
            # hook this up here at the end otherwise it may point to a non-existing player object.
            for living_info in saved_livings_info:
                if living_info["following"]:
                    living = living_info["living"]
                    assert isinstance(living, base.Living)
                    living.following = objects_finder.resolve_living_ref(*living_info["following"])

            saved_deferreds = deserializer.recreate_classes(state.pop("deferreds"), objects_finder)
            assert all(isinstance(d, driver.Deferred) for d in saved_deferreds)
            self.deferreds = []
            for d in saved_deferreds:
                self._enqueue_deferred(d)

            # done, check
            assert len(state) == 0, "everything must have been converted"

            self.waiting_for_input = {}   # can't keep the old waiters around
            saved_player.tell("\n")
            saved_player.tell("Game loaded.")
            if self.story.config.display_gametime:
                saved_player.tell("Game time: %s" % self.game_clock)
                saved_player.tell("\n")
            if self.wizard_override:
                saved_player.privileges.add("wizard")
            return saved_player


class SavegameExistingObjectsFinder:
    def resolve_ref(self, vnum: int, name: str, classname: str, baseclassname: str) -> base.MudObject:
        if baseclassname == "tale.base.Item":
            return self.resolve_item_ref(vnum, name, classname, baseclassname)
        elif baseclassname == "tale.base.Location":
            return self.resolve_location_ref(vnum, name, classname, baseclassname)
        elif baseclassname == "tale.base.Living":
            return self.resolve_living_ref(vnum, name, classname, baseclassname)
        else:
            raise errors.TaleError("invalid base class for resolve_ref: " + baseclassname)

    def resolve_location_ref(self, vnum: int, name: str, classname: str, baseclassname: str) -> base.Location:
        loc = base.MudObjRegistry.all_locations.get(vnum, None)
        if not loc:
            raise LookupError("location vnum not found: " + str(vnum))
        if loc.name != name or savegames.qual_baseclassname(loc) != baseclassname:
            raise errors.TaleError("location inconsistency for vnum " + str(vnum))
        return loc

    def resolve_living_ref(self, vnum: int, name: str, classname: str, baseclassname: str) -> base.Living:
        liv = base.MudObjRegistry.all_livings.get(vnum, None)
        if not liv:
            raise LookupError("living vnum not found: " + str(vnum))
        if liv.name != name:
            if savegames.qual_baseclassname(liv) != baseclassname:
                if baseclassname == "tale.player.Player":
                    return liv  # special case when the living is the Player
                raise errors.TaleError("living inconsistency for vnum " + str(vnum))
        return liv

    def resolve_item_ref(self, vnum: int, name: str, classname: str, baseclassname: str) -> base.Item:
        item = base.MudObjRegistry.all_items.get(vnum, None)
        if not item:
            raise LookupError("item vnum not found: " + str(vnum))
        if item.name != name or savegames.qual_baseclassname(item) != baseclassname:
            raise errors.TaleError("item inconsistency for vnum " + str(vnum))
        return item

    def resolve_exit(self, vnum: int, name: str, classname: str, baseclassname: str) -> Union[base.Exit, base.Door]:
        assert baseclassname == "tale.base.Exit"
        exit = base.MudObjRegistry.all_exits[vnum]
        if exit.name != name or savegames.qual_baseclassname(exit) != baseclassname:
            raise errors.TaleError("exit/door inconsistency for vnum " + str(vnum))
        return exit
