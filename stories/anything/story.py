import pathlib
import random
import sys
from typing import Generator

import tale
from tale import lang
from tale import parse_utils
from tale.driver import Driver
from tale.json_story import JsonStory
from tale.magic import MagicType
from tale.main import run_from_cmdline
from tale.player import Player, PlayerConnection
from tale.charbuilder import PlayerNaming
from tale.story import *
from tale.weapon_type import WeaponType

class Story(JsonStory):


    def __init__(self) -> None:
        super(Story, self).__init__('', parse_utils.load_story_config(parse_utils.load_json('story_config.json')))

    def init(self, driver: Driver) -> None:
        super(Story, self).init(driver)

    def init_player(self, player: Player) -> None:
        """
        Called by the game driver when it has created the player object (after successful login).
        You can set the hint texts on the player object, or change the state object, etc.
        """
        player.stats.set_weapon_skill(weapon_type=WeaponType.ONE_HANDED_RANGED, value=random.randint(10, 30))
        player.stats.set_weapon_skill(weapon_type=WeaponType.TWO_HANDED_RANGED, value=random.randint(10, 30))
        player.stats.set_weapon_skill(weapon_type=WeaponType.ONE_HANDED, value=random.randint(10, 30))
        player.stats.set_weapon_skill(weapon_type=WeaponType.TWO_HANDED, value=random.randint(10, 30))
        player.stats.set_weapon_skill(weapon_type=WeaponType.UNARMED, value=random.randint(20, 30))
        player.stats.magic_skills[MagicType.HEAL] = 30
        player.stats.magic_skills[MagicType.BOLT] = 30
        player.stats.magic_skills[MagicType.DRAIN] = 30
        player.stats.magic_skills[MagicType.REJUVENATE] = 30
        pass

    def create_account_dialog(self, playerconnection: PlayerConnection, playernaming: PlayerNaming) -> Generator:
        """
        Override to add extra dialog options to the character creation process.
        Because there's no actual player yet, you receive PlayerConnection and PlayerNaming arguments.
        Write stuff to the user via playerconnection.output(...)
        Ask questions using the yield "input", "question?"  mechanism.
        Return True to declare all is well, and False to abort the player creation process.
        """
        ranged = yield "input", ("Do you prefer ranged over close combat? (yes/no)", lang.yesno)
        if ranged:
            playerconnection.player.stats.set_weapon_skill(weapon_type=WeaponType.ONE_HANDED_RANGED, value=random.randint(20, 40))
            playerconnection.player.stats.set_weapon_skill(weapon_type=WeaponType.TWO_HANDED_RANGED, value=random.randint(20, 40))
        else:
            playerconnection.player.stats.set_weapon_skill(weapon_type=WeaponType.ONE_HANDED, value=random.randint(20, 40))
            playerconnection.player.stats.set_weapon_skill(weapon_type=WeaponType.TWO_HANDED, value=random.randint(20, 40))
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


if __name__ == "__main__":
    # story is invoked as a script, start it in the Tale Driver.
    gamedir = pathlib.Path(__file__).parent
    if gamedir.is_dir() or gamedir.is_file():
        cmdline_args = sys.argv[1:]
        cmdline_args.insert(0, "--game")
        cmdline_args.insert(1, str(gamedir))
        run_from_cmdline(cmdline_args)
