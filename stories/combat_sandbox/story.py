import pathlib
import sys
from typing import Optional, Generator

import tale
from tale import parse_utils
from tale.base import Location
from tale.driver import Driver
from tale.json_story import JsonStory
from tale.llm.llm_ext import DynamicStory
from tale.main import run_from_cmdline
from tale.player import Player, PlayerConnection
from tale.charbuilder import PlayerNaming
from tale.story import *
from tale.weapon_type import WeaponType
from tale.zone import Zone

class Story(JsonStory):

    driver = None  

    def __init__(self) -> None:
        super(Story, self).__init__('', parse_utils.load_story_config(parse_utils.load_json('story_config.json')))

    def init(self, driver: Driver) -> None:
        
        super(Story, self).init(driver)

    def welcome(self, player: Player) -> str:
        """welcome text when player enters a new game"""
        player.tell("<bright>Hello, %s! Welcome to %s.</>" % (player.title, self.config.name), end=True)
        player.tell("\n")
        return ""
    
    def init_player(self, player: Player) -> None:
        """
        Called by the game driver when it has created the player object (after successful login).
        You can set the hint texts on the player object, or change the state object, etc.
        """
        player.stats.set_weapon_skill(weapon_type=WeaponType.ONE_HANDED, value=45)
        player.stats.set_weapon_skill(weapon_type=WeaponType.TWO_HANDED, value=15)
        player.stats.set_weapon_skill(weapon_type=WeaponType.UNARMED, value=35)

if __name__ == "__main__":
    # story is invoked as a script, start it in the Tale Driver.
    gamedir = pathlib.Path(__file__).parent
    if gamedir.is_dir() or gamedir.is_file():
        cmdline_args = sys.argv[1:]
        cmdline_args.insert(0, "--game")
        cmdline_args.insert(1, str(gamedir))
        run_from_cmdline(cmdline_args)