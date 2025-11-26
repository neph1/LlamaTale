"""
Mud driver (multi user server).

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import time
import threading
from typing import Union, Generator, Dict, Tuple, Optional, Any

from .story import GameMode
from . import accounts
from . import base
from . import charbuilder
from . import driver
from . import errors
from . import lang
from . import pubsub
from . import util
from .player import PlayerConnection, Player
from .tio.mud_browser_io import TaleMudFastAPIApp


class MudDriver(driver.Driver):
    """
    The Mud 'driver'.
    Multi-user server variant of the single player Driver.
    """
    def __init__(self, restricted=False) -> None:
        super().__init__()
        self.game_mode = GameMode.MUD
        self.restricted = restricted   # restricted mud mode? (no new players allowed)
        self.mud_accounts = None   # type: accounts.MudAccounts

    def start_main_loop(self):
        # Driver runs as main thread, FastAPI webserver runs in background thread
        accounts_db_file = self.user_resources.validate_path("useraccounts.sqlite")
        self.mud_accounts = accounts.MudAccounts(accounts_db_file)
        base._limbo.init_inventory([LimboReaper()])  # add the grim reaper to Limbo
        fastapi_server = TaleMudFastAPIApp.create_app_server(self, use_ssl=False, ssl_certs=None)    # you can enable SSL here
        fastapi_thread = threading.Thread(name="fastapi", target=fastapi_server.run, 
                                          args=(self.story.config.mud_host, self.story.config.mud_port))
        fastapi_thread.daemon = True
        fastapi_thread.start()
        self.print_game_intro(None)
        if self.restricted:
            print("\n* Restricted mode: no new players allowed *\n")
        protocol = "https" if fastapi_server.use_ssl else "http"
        hostname = self.story.config.mud_host
        port = self.story.config.mud_port
        if hostname.startswith("127.0"):
            hostname = "localhost"
        print("Access the game on this web server url (WebSocket):   %s://%s:%d/tale/" % (protocol, hostname, port), end="\n\n")
        self._main_loop_wrapper(None)   # this doesn't return!

    def show_motd(self, player: Player, notify_no_motd: bool=False) -> None:
        """Prints the Message-Of-The-Day file, if present."""
        try:
            message = self.resources["messages/motd.txt"].text.rstrip()
        except IOError:
            message = ""
        if message:
            player.tell("<bright>Message-of-the-day:</>", end=True)
            player.tell("\n")
            player.tell(message, end=True, format=True)  # for now, the motd is displayed *with* formatting
            player.tell("\n")
            player.tell("\n")
        elif notify_no_motd:
            player.tell("There's currently no message-of-the-day.", end=True)
            player.tell("\n")

    def do_check_savefile_free(self, player: Player) -> bool:
        raise errors.ActionRefused("Currently, saving is not supported in MUD mode.")

    def do_save(self, player: Player) -> None:
        raise errors.ActionRefused("Currently, saving is not supported in MUD mode.")

    def connect_player(self, player_io_type: str, line_delay: int) -> PlayerConnection:
        if player_io_type != "web":
            raise ValueError("mud connections can only be done via web interface")
        connection = PlayerConnection()
        connect_name = "<connecting_%d>" % id(connection)  # unique temporary name
        new_player = Player(connect_name, "n", race="elemental", descr="This player is still connecting to the game.")
        connection.player = new_player
        from .tio.mud_browser_io import MudHttpIo
        connection.io = MudHttpIo(connection)
        self.all_players[new_player.name] = connection
        connection.clear_screen()
        self.print_game_intro(connection)
        connection.output("\n")
        # check if we have at least 1 admin user
        if len(self.mud_accounts.all_accounts(having_privilege="wizard")) == 0:
            # there is no wizard, create a dialog to construct the initial admin user
            driver.topic_async_dialogs.send((connection, self._login_dialog_mud_create_admin(connection)))
            return connection
        # create the login dialog
        driver.topic_async_dialogs.send((connection, self._login_dialog_mud(connection)))
        return connection

    def disconnect_idling(self, conn: PlayerConnection) -> None:
        idle_limit = 3 * 60 * 60 if "wizard" in conn.player.privileges else 30 * 60
        if conn.idle_time > idle_limit:
            idle_limit_minutes = int(idle_limit / 60)
            conn.player.tell("\n")
            conn.player.tell("<it><rev>Automatic logout:  You have been logged out because "
                             "you've been idle for too long (%d minutes)</>" % idle_limit_minutes, end=True)
            conn.player.tell("\n")
            conn.player.tell_others("{Actor} has been idling around for too long.")
            self.disconnect_player(conn)  # remove players who stay idle too long

    def disconnect_player(self, conn_or_player: Union[PlayerConnection, Player]) -> None:
        # note: conn can be corrupt/disconnected. conn.player, conn.io or conn.player.location can be None.
        if isinstance(conn_or_player, PlayerConnection):
            name = conn_or_player.player.name
            conn = conn_or_player
        elif isinstance(conn_or_player, Player):
            name = conn_or_player.name
            conn = self.all_players[name]
        else:
            raise TypeError("connection or player object expected")
        assert self.all_players[name] is conn
        if conn.player.location:
            conn.player.tell_others("{Actor} suddenly shimmers and fades from sight. %s left the game."
                                    % lang.capital(conn.player.subjective))
        del self.all_players[name]
        conn.write_output()
        # wait a bit to allow the player's screen to display the last goodbye message before killing the connection
        self.defer(1, conn.destroy)

    def _login_dialog_mud_create_admin(self, conn: PlayerConnection) -> Generator:
        conn.write_output()
        conn.output("<bright>Welcome. There is no admin user registered. "
                    "You'll have to create the initial admin user to be able to start the mud.</>")
        while True:
            conn.output("Creating new admin user.")
            name = yield "input", ("Please type in the admin's player name.", accounts.MudAccounts.accept_name)
            while True:
                password = yield "input-noecho", ("Please type in the admin password.", accounts.MudAccounts.accept_password)
                password2 = yield "input-noecho", ("Please retype the admin password.", accounts.MudAccounts.accept_password)
                if password != password2:
                    conn.output("<it>The passwords don't match! Please try again.</>")
                else:
                    break
            email = yield "input", ("Please type in the admin's email address.", accounts.MudAccounts.accept_email)
            conn.output("You can choose one of the following races: ", lang.join(self.story.config.playable_races))
            race = yield "input", ("Player race?", charbuilder.ValidRaceValidator(self.story.config.playable_races))
            gender = yield "input", ("What is the gender of your character (m/f)?", lang.validate_gender_mf)
            # review the account
            conn.player.tell("<bright>Please review the admin character.</>", end=True)
            conn.player.tell("<dim> name:</> %s,  <dim>gender:</> %s,  <dim>race:</> %s,  <dim>email:</> %s" %
                             (name, lang.GENDERS[gender], race, email), end=True)
            if not (yield "input", ("You cannot change your name later. Do you want to create this admin account?", lang.yesno)):
                conn.player.tell("<it>Okay, lets try that again then.</>", end=True)
                conn.player.tell("-- -- -- --", end=True)
                conn.write_output()
                continue
            else:
                break
        stats = base.Stats.from_race(race, gender=gender[0])
        self.mud_accounts.create(name, password, email, stats, privileges={"wizard"})
        conn.output("<it>Okay, your admin account is ready. You can try logging in.</it>\n")
        conn.output("\n")
        yield from self._login_dialog_mud(conn)  # continue with the normal login dialog

    def _login_dialog_mud(self, conn: PlayerConnection) -> Generator:
        conn.write_output()
        conn.output("<bright>Welcome. We would like to know your player name before you can continue.</>")
        conn.output("<dim>If you are not yet known with us, you can simply type in a new name. "
                    "Otherwise use the name you registered with.</>\n")
        conn.output("\n")
        successful_login = False
        while not successful_login:
            existing_player = None
            account = None
            name = yield "input", ("Please type in your player name.", accounts.MudAccounts.accept_name)

            # see if it is a new player or a name we already know.
            try:
                account = self.mud_accounts.get(name)
            except LookupError:
                if self.restricted:
                    conn.player.tell("<bright>We're sorry, the mud is running in restricted mode at the moment. "
                                     "It is not allowed to create new characters right now. Please try again later.</bright>")
                    continue
                conn.player.tell("`%s' is the name of a new character." % name)
                if not (yield "input", ("Do you want to create a new character with this name?", lang.yesno)):
                    conn.player.tell("<it>Okay, let's try that again.</>", end=True)
                    conn.player.tell("-- -- -- --", end=True)
                    conn.write_output()
                    continue
                # self-service account creation
                conn.player.tell("\n")
                builder = charbuilder.MudCharacterBuilder(conn, name, self.story.config)
                name_info = yield from builder.build_character()
                if not name_info:
                    continue
                result = yield from self.story.create_account_dialog(conn, name_info)   # story can customize more things
                if not result:
                    conn.player.tell("\n<bright>Your account has not been created!</>", end=True)
                    conn.player.tell("-- -- -- --", end=True)
                    continue
                self.mud_accounts.create(name_info.name, name_info.password, name_info.email, name_info.stats)
                self.mud_accounts.save_story_data(name_info.name, name_info.story_data)
                del name_info
                conn.player.tell("\n<bright>Your new account has been created!</>  Go ahead and log in with it.", end=True)
                conn.player.tell("-- -- -- --", end=True)
                continue

            # ask and validate the password.
            try:
                password = yield "input-noecho", "Please type in your password."
                self.mud_accounts.valid_password(name, password)
                del password
            except ValueError as x:
                conn.output("<it>%s</it>" % x)
                continue

            # try to get the account and see if it is banned or not.
            account = self.mud_accounts.get(name)
            if account.banned:
                conn.player.tell("\n<bright>You have been banned by an admin!</>  Try logging in later or get in touch.", end=True)
                conn.player.tell("\n")
                del account
                continue

            # check if player is already logged in from somewhere else.
            existing_player = self.search_player(account.name)
            if existing_player:
                conn.player.tell("That player is already logged in elsewhere. Their current location is " + existing_player.location.name)
                conn.player.tell("and their idle time is %d seconds." % existing_player.idle_time)
                if existing_player.idle_time < 30:
                    conn.player.tell("They are still active.")
                    del account
                    continue
                if not (yield "input", ("Do you want to kick them out and take over?", lang.yesno)):
                    conn.player.tell("Okay, leaving them in peace.")
                    del account
                    continue
                else:
                    successful_login = True     # login ok, replacing the existing player
                    break
            else:
                successful_login = True    # login ok, regular login
                break

        if not successful_login or not account or account.banned:  # safeguard
            raise errors.SecurityViolation("unsuccessful login should have been handled")

        # login was succesful!!!

        if existing_player:
            # take the place of already logged in player (that was disconnected perhaps?)
            existing_player.tell("\n")
            existing_player.tell("<it><rev>You are kicked from the game. Your account is now logged in from elsewhere.</>")
            existing_player.tell("\n")
            state = {}
            for name, value in vars(existing_player).items():
                if not name.startswith("_") and name not in ("vnum", "soul", "input_is_available", "teleported_from", "transcript"):
                    state[name] = value
            state["title"] = existing_player.title
            state["description"] = existing_player.description
            state["short_description"] = existing_player.short_description
            state["inventory"] = existing_player.inventory
            state["extra_desc"] = existing_player.extra_desc
            self.disconnect_player(existing_player)
            ctx = util.Context(self, self.game_clock, self.story.config, None)
            existing_player.destroy(ctx)
            del existing_player
            self._overwrite_player(conn.player, state)
            conn.output("\n")
        else:
            self.mud_accounts.logged_in(account.name)
            # for a normal log in, set the connecting player to the proper account name, and move them to the starting location.
            name_info = charbuilder.PlayerNaming()
            name_info.name = account.name
            name_info.gender = account.stats.gender
            name_info.stats = account.stats
            self._rename_player(conn.player, name_info)
            conn.player.privileges = account.privileges
            conn.player.story_data = account.story_data
            conn.output("\n")
            if "wizard" in conn.player.privileges:
                conn.player.move(self.lookup_location(self.story.config.startlocation_wizard))
            else:
                conn.player.move(self.lookup_location(self.story.config.startlocation_player))

        prompt = self.story.welcome(conn.player)
        if prompt:
            yield "input", "\n" + prompt
        self.story.init_player(conn.player)
        self.mud_accounts.save_story_data(conn.player.name, conn.player.story_data)
        conn.output("\n")
        self.show_motd(conn.player, True)
        conn.player.look(short=False)  # force a 'look' command to get our bearings
        # after this, the generator (dialog) ends and we drop down into the regular command loop

    def _overwrite_player(self, player: Player, state: Dict[str, Any]) -> None:
        location = state.pop("location")
        player.privileges = state.pop("privileges")
        name_info = charbuilder.PlayerNaming()
        name_info.name = state.pop("name")
        name_info.title = state.pop("title")
        name_info.gender = state.pop("gender")
        name_info.description = state.pop("description")
        name_info.short_description = state.pop("short_description")
        name_info.stats = state.pop("stats")
        name_info.money = state.pop("money")
        name_info.wizard = "wizard" in player.privileges
        self._rename_player(player, name_info)
        player.aliases = state.pop("aliases")
        player.known_locations = state.pop("known_locations")
        player.story_data = state.pop("story_data")
        player.turns = state.pop("turns")
        for keyword, description in state.pop("extra_desc").items():
            player.add_extradesc({keyword}, description)
        player.init_inventory(state.pop("inventory"))
        player.move(location, silent=True)
        player.location.tell("%s appears again. Is %s a different person, you wonder?" %
                             (lang.capital(player.title), player.subjective), exclude_living=player)

    def main_loop(self, conn: Optional[PlayerConnection]) -> None:
        """
        The game loop, for the multiplayer MUD mode.
        Until the server is shut down, it processes player input, and prints the resulting output.
        """
        loop_duration = 0.0
        previous_server_tick = 0.0
        while not self._stop_mainloop:
            pubsub.sync("driver-async-dialogs")
            for conn in self.all_players.values():
                conn.write_output()
                if conn not in self.waiting_for_input:
                    conn.write_input_prompt()

            # server tick goes on a timer
            wait_time = max(0.01, self.story.config.server_tick_time - loop_duration)
            while wait_time > 0:
                if any(conn.player.input_is_available.is_set() for conn in self.all_players.values()):
                    # there was player input, abort the wait loop and deal with it
                    break
                sub_wait = min(0.1, wait_time)  # keep things responsive
                time.sleep(sub_wait)
                wait_time -= sub_wait

            loop_start = time.time()
            for conn in list(self.all_players.values()):
                if conn.player.input_is_available.is_set():
                    conn.need_new_input_prompt = True
                    try:
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
                        self.story.goodbye(conn.player)
                        driver.topic_pending_tells.send(lambda conn=conn: self.disconnect_player(conn))
                    except Exception:
                        tb = "".join(util.format_traceback())
                        txt = "\n<bright><rev>* internal error (please report this):</>\n" + tb
                        conn.player.tell(txt, format=False)
                        conn.player.tell("<rev><it>Please report this problem.</>")
            try:
                pubsub.sync("driver-pending-tells")
                # server TICK
                now = time.time()
                if now - previous_server_tick >= self.story.config.server_tick_time:
                    self._server_tick()
                    previous_server_tick = now
                loop_duration = time.time() - loop_start
                self.server_loop_durations.append(loop_duration)
            except errors.StoryCompleted:
                print("StoryCompleted raised! But that should never happen in a MUD!")
                conn.player.tell("<rev>StoryCompleted event in MUD mode - should NOT happen</> - Please report this error")
                raise


class LimboReaper(base.Living):
    """The Grim Reaper hangs about in Limbo, and makes sure no one stays there for too long."""
    def __init__(self) -> None:
        super().__init__(
            "reaper", "m", race="elemental", title="Grim Reaper",
            descr="He wears black robes with a hood. Where a face should be, there is only nothingness. "
                  "He is carrying a large ominous scythe that looks very, very sharp.",
            short_descr="A figure clad in black, carrying a scythe, is also present.")
        self.aliases = {"figure", "death"}
        self.candidates = {}    # type: Dict[base.Living, Tuple[float, int]]  # living (usually a player) --> (first_seen, texts shown)

    def notify_action(self, parsed: base.ParseResult, actor: base.Living) -> None:
        if self is actor:
            return
        if parsed.verb == "say":
            actor.tell("%s just stares blankly at you, not saying a word." % lang.capital(self.title))
        else:
            actor.tell("%s stares blankly at you." % lang.capital(self.title))

    @util.call_periodically(3)
    def do_reap_souls(self, ctx: util.Context) -> None:
        # consider all livings currently in Limbo or having their location set to Limbo
        if self.location is not base._limbo:
            # we somehow got misplaced, teleport back to limbo
            self.tell_others("{Actor} looks around in wonder and says, \"I'm not supposed to be here.\"")
            self.move(base._limbo, self)
            return
        in_limbo = {living for living in self.location.livings if living is not self}
        in_limbo.update({conn.player for conn in ctx.driver.all_players.values() if conn.player.location is base._limbo})
        now = time.time()
        for candidate in in_limbo:
            if candidate not in self.candidates:
                self.candidates[candidate] = (now, 0)   # a new player first seen
        for candidate in list(self.candidates):
            if candidate not in in_limbo:
                del self.candidates[candidate]   # player no longer present in limbo
                continue
            first_seen, shown = self.candidates[candidate]
            duration = now - first_seen
            # Depending on how long the candidate is being observed, show increasingly threateningly warnings,
            # and eventually killing the candidate (and closing their connection).
            # For wizard players, this is not done and only a short notification is printed.
            if "wizard" in candidate.privileges and duration >= 2 and shown < 1:
                candidate.tell(self.title + " whispers: \"Hello there wizard. Please don't stay for too long.\"")
                shown = 99999
            if duration >= 30 and shown < 1:
                candidate.tell(self.title + " whispers: \"Greetings. Be aware that you must not linger here... Decide swiftly...\"")
                shown = 1
            elif duration >= 50 and shown < 2:
                candidate.tell(self.title + " looms over you and warns: \"You really cannot stay here much longer!\"")
                shown = 2
            elif duration >= 60 and shown < 3:
                candidate.tell(self.title + " menacingly raises his scythe!")
                shown = 3
            elif duration >= 63 and shown < 4:
                candidate.tell(self.title + " swings down his scythe and slices your soul cleanly in half. You have been destroyed.")
                shown = 4
            elif duration >= 64 and "wizard" not in candidate.privileges:
                try:
                    conn = ctx.driver.all_players[candidate.name]
                except KeyError:
                    pass   # already gone
                else:
                    ctx.driver.disconnect_player(conn)
            self.candidates[candidate] = (first_seen, shown)
