"""
Story configuration and base classes to create your own story with.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import datetime
import enum
from typing import Optional, Any, List, Set, Generator
from packaging.version import Version

from . import __version__ as tale_version_str
from .errors import StoryConfigError

__all__ = ["TickMethod", "GameMode", "MoneyType", "StoryBase", "StoryConfig"]


class TickMethod(enum.Enum):
    COMMAND = "command"
    TIMER = "timer"


class GameMode(enum.Enum):
    IF = "if"
    MUD = "mud"


class MoneyType(enum.Enum):
    FANTASY = "fantasy"
    MODERN = "modern"
    NOTHING = None  # type: str

    def __bool__(self):
        return bool(self.value)


class StoryConfig:
    """
    Story configuration settings.
    The reason this is in a separate class, is that these settings are all simple values
    and are serializable, so they can be saved to disk as part of a save game file.
    """
    def __init__(self) -> None:
        self.name = ""                       # the name of the story
        self.author = ""                     # the story's author name
        self.author_address = ""             # the author's email address
        self.version = "1.10"                # arbitrary but is used to check savegames for compatibility
        self.requires_tale = "4.0"           # tale library required to run the game
        self.supported_modes = {GameMode.IF}    # what driver modes (if/mud) are supported by this story
        self.player_name = ""                # set a name to create a prebuilt player, None to use the character builder
        self.player_gender = ""              # m/f (n is technically possible, but not preferred)
        self.player_race = "human"           # default is "human" ofcourse, but you can select something else if you want
        self.player_money = 0.0              # starting money
        self.playable_races = set()          # type: Set[str]  # if specified, specify a subset of the allowed playable races
        self.money_type = MoneyType.NOTHING  # money type modern/fantasy/nothing
        self.server_tick_method = TickMethod.COMMAND   # command (waits for player entry) or timer (async timer driven)
        self.server_tick_time = 5.0          # time between server ticks (in seconds) (usually 1.0 for 'timer' tick method)
        self.gametime_to_realtime = 1        # meaning: game time is X times real time (only used with "timer" tick method) (>=0)
        self.max_wait_hours = 2              # the max. number of hours (gametime) the player is allowed to wait (>=0)
        self.display_gametime = False        # enable/disable display of the game time at certain moments
        self.display_race = False            # display race and bodytype when examining a creature?
        self.epoch = None                    # type: Optional[datetime.datetime]  # start date/time of the game clock
        self.startlocation_player = ""       # name of the location where a player starts the game in
        self.startlocation_wizard = ""       # name of the location where a wizard player starts the game in
        self.savegames_enabled = False        # allow savegames?
        self.show_exits_in_look = True       # with the look command, also show exit descriptions automatically?
        self.license_file = ""               # game license file, if applicable
        self.mud_host = ""                   # for mud mode: hostname to bind the server on. Use "[...]" for IPV6 connectivity.
        self.mud_port = 0                    # for mud mode: port number to bind the server on
        self.zones = []                      # type: List[str]  # names of zone modules to load, in this order
        self.server_mode = GameMode.IF       # the actual game mode the server is operating in (will be set at startup time)
        self.items = ""                      # items to populate the world with. only used by json loading
        self.npcs = ""                       # npcs to populate the world with. only used by json loading
        self.context = ""                    # context to giving background for the story.
        self.type = ""                       # brief description of the setting and type of story, for LLM context
        self.world_info = ""                 # brief description of the world, for LLM context
        self.world_mood = 0                  # how safe is the world? 5 is a happy place, -5 is nightmare mode.
        
    def __eq__(self, other: Any) -> bool:
        return isinstance(other, StoryConfig) and vars(self) == vars(other)


class StoryBase:
    """base class for tale story classes."""
    config = StoryConfig()

    def init(self, driver) -> None:
        """
        Called by the game driver when it is done with its initial initialization.
        """
        pass

    def create_account_dialog(self, playerconnection, playernaming) -> Generator:
        """
        Override to add extra dialog options to the character creation process.
        Because there's no actual player yet, you receive PlayerConnection and PlayerNaming arguments.
        Write stuff to the user via playerconnection.output(...)
        Ask questions using the yield "input", "question?"  mechanism.
        Return True to declare all is well, and False to abort the player creation process.
        """
        return True
        yield

    def init_player(self, player) -> None:
        """
        Called by the game driver when it has created the player object (after successful login).
        You can set the hint texts on the player object, or change the state object, etc.
        For an IF game there is only one player. For a MUD game there will be many players,
        and every player that logs in can be further initialized here.
        """
        pass

    def welcome(self, player) -> str:
        """
        Welcome text when player enters a new game
        If you return a non-empty string, it is used as an input prompt before continuing (a pause).
        """
        player.tell("<bright>Welcome to `%s'.</>" % self.config.name, end=True)
        player.tell("\n")
        return "<bright>Press enter to start.</>"

    def welcome_savegame(self, player) -> str:
        """
        Welcome text when player enters the game after loading a saved game
        If you return a non-empty string, it is used as an input prompt before continuing (a pause).
        """
        player.tell("<bright>Welcome back to `%s'.</>" % self.config.name, end=True)
        player.tell("\n")
        return "<bright>Press enter to continue where you were before.</>"

    def goodbye(self, player) -> None:
        """goodbye text when player quits the game"""
        player.tell("Goodbye! We hope you enjoyed playing.")
        player.tell("\n")

    def _verify(self, driver) -> None:
        """verify correctness and compatibility of the story configuration"""
        if not isinstance(self.config, StoryConfig):
            raise StoryConfigError("Story class must have config attribute of type StoryConfig, containing the story config settings")
        if not self.config.name:
            raise StoryConfigError("Story's config must specify story name, and other config items")
        if not (type(self.config.supported_modes) is set and all(type(m) is GameMode for m in self.config.supported_modes)):
            raise StoryConfigError("Story's config supported_modes is of invalid type")
        if type(self.config.money_type) is not MoneyType:
            raise StoryConfigError("Story's config money_type is of invalid type")
        if type(self.config.server_tick_method) is not TickMethod:
            raise StoryConfigError("Story's config server_tick_method is of invalid type")
        tale_version = Version(tale_version_str)
        tale_version_required = Version(self.config.requires_tale)
        if tale_version < tale_version_required:
            raise StoryConfigError("This game requires tale " + self.config.requires_tale + ", but " + tale_version_str + " is installed.")
