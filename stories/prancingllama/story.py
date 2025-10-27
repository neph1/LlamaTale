import pathlib
import sys
from typing import Optional, Generator

import tale
from tale.base import Location
from tale.cmds import spells
from tale.driver import Driver
from tale.llm.dynamic_story import DynamicStory
from tale.skills.magic import MagicType
from tale.main import run_from_cmdline
from tale.player import Player, PlayerConnection
from tale.charbuilder import PlayerNaming
from tale.skills.skills import SkillType
from tale.story import *
from tale.skills.weapon_type import WeaponType
from tale.story_context import StoryContext
from tale.zone import Zone

class Story(DynamicStory):

    config = StoryConfig()
    config.name = "The Prancing Llama"
    config.author = "Rickard Edén, github.com/neph1/LlamaTale"
    config.author_address = "rickard@mindemia.com"
    config.version = tale.__version__
    config.supported_modes = {GameMode.IF, GameMode.MUD}
    config.player_money = 10.5
    config.playable_races = {"human"}
    config.money_type = MoneyType.FANTASY
    config.server_tick_method = TickMethod.TIMER
    config.server_tick_time = 0.5
    config.gametime_to_realtime = 5
    config.display_gametime = True
    config.startlocation_player = "prancingllama.entrance"
    config.startlocation_wizard = "prancingllama.entrance"
    config.zones = ["prancingllama"]
    config.context = StoryContext(base_story="The final outpost high up in a cold, craggy mountain range. A drama unfolds between those avoiding the cold and those seeking the cold. And what is lurking underneath the snow covered peaks and uncharted valleys?")
    config.type = "A low level fantasy adventure with focus of character building and interaction."
    config.custom_resources = True
    
    
    def init(self, driver: Driver) -> None:
        """Called by the game driver when it is done with its initial initialization."""
        self.driver = driver
        self._zones = dict() # type: {str, Zone}
        self._zones["The Prancing Llama"] = Zone("The Prancing Llama", description="A cold, craggy mountain range. Snow covered peaks and uncharted valleys hide and attract all manners of creatures.")
        import zones.prancingllama
        for location in zones.prancingllama.all_locations:
            self._zones["The Prancing Llama"].add_location(location)
        self._catalogue._creatures = ["human", "giant rat", "bat", "balrog", "dwarf", "elf", "gnome", "halfling", "hobbit", "kobold", "orc", "troll", "vampire", "werewolf", "zombie"]
        self._catalogue._items = ["woolly gloves", "ice pick", "fur cap", "rusty sword", "lantern", "food rations"]

    def init_player(self, player: Player) -> None:
        """
        Called by the game driver when it has created the player object (after successful login).
        You can set the hint texts on the player object, or change the state object, etc.
        """
        player.stats.weapon_skills.set(weapon_type=WeaponType.ONE_HANDED, value=25)
        player.stats.weapon_skills.set(weapon_type=WeaponType.TWO_HANDED, value=15)
        player.stats.weapon_skills.set(weapon_type=WeaponType.UNARMED, value=35)
        player.stats.magic_skills.set(MagicType.HEAL, 30)
        player.stats.skills.set(SkillType.HIDE, 25)
        player.stats.skills.set(SkillType.SEARCH, 25)
        player.stats.skills.set(SkillType.PICK_LOCK, 25)

    def create_account_dialog(self, playerconnection: PlayerConnection, playernaming: PlayerNaming) -> Generator:
        """
        Override to add extra dialog options to the character creation process.
        Because there's no actual player yet, you receive PlayerConnection and PlayerNaming arguments.
        Write stuff to the user via playerconnection.output(...)
        Ask questions using the yield "input", "question?"  mechanism.
        Return True to declare all is well, and False to abort the player creation process.
        """
        occupation = yield "input", "Custom creation question: What is your trade?"
        playernaming.story_data["occupation"] = str(occupation)    # will be stored in the database (mud)
        return True

    def welcome(self, player: Player) -> str:
        """welcome text when player enters a new game"""
        player.tell("<bright>Hello, %s! Welcome to %s.</>" % (player.title, self.config.name), end=True)
        player.tell("\n")
        player.tell(self.driver.resources["messages/welcome.txt"].text)
        player.tell("\n")
        return ""

    def welcome_savegame(self, player: Player) -> str:
        """welcome text when player enters the game after loading a saved game"""
        player.tell("<bright>Hello %s, welcome back to %s.</>" % (player.title, self.config.name), end=True)
        player.tell("\n")
        player.tell(self.driver.resources["messages/welcome.txt"].text)
        player.tell("\n")
        return ""

    def goodbye(self, player: Player) -> None:
        """goodbye text when player quits the game"""
        player.tell("Goodbye, %s. Please come back again soon." % player.title)
        player.tell("\n")

    def races_for_zone(self, zone: str) -> list[str]:
        return self._catalogue._creatures

    def items_for_zone(self, zone: str) -> list[str]:
        return self._catalogue._items

    def zone_info(self, zone_name: str, location: str) -> dict:
        zone_info = super.zone_info(zone_name, location)
        zone_info['races'] = self.races_for_zone(zone_name)
        zone_info['items'] = self.items_for_zone(zone_name)
        return zone_info

if __name__ == "__main__":
    # story is invoked as a script, start it in the Tale Driver.
    gamedir = pathlib.Path(__file__).parent
    if gamedir.is_dir() or gamedir.is_file():
        cmdline_args = sys.argv[1:]
        cmdline_args.insert(0, "--game")
        cmdline_args.insert(1, str(gamedir))
        run_from_cmdline(cmdline_args)
