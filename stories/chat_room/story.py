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
from tale.skills.weapon_type import WeaponType
from tale.zone import Zone

class Story(JsonStory):

    driver = None  

    def __init__(self) -> None:
        super(Story, self).__init__('', parse_utils.load_story_config(parse_utils.load_json('story_config.json')))

    def init(self, driver: Driver) -> None:
        
        super(Story, self).init(driver)


if __name__ == "__main__":
    # story is invoked as a script, start it in the Tale Driver.
    gamedir = pathlib.Path(__file__).parent
    if gamedir.is_dir() or gamedir.is_file():
        cmdline_args = sys.argv[1:]
        cmdline_args.insert(0, "--game")
        cmdline_args.insert(1, str(gamedir))
        run_from_cmdline(cmdline_args)