"""
Example story demonstrating a dungeon entrance in a normal location.

This story shows how dungeons can be integrated into any story,
not just dungeon-specific stories.
"""

import pathlib
import sys

from tale import parse_utils
from tale.base import Location
from tale.coord import Coord
from tale.driver import Driver
from tale.dungeon.dungeon import Dungeon, DungeonEntrance
from tale.dungeon.dungeon_generator import ItemPopulator, LayoutGenerator, MobPopulator
from tale.json_story import JsonStory
from tale.main import run_from_cmdline
from tale.player import Player
from tale.zone import Zone


class Story(JsonStory):
    """Example story with a normal location that has a dungeon entrance."""

    driver = None

    def __init__(self, path: str = '') -> None:
        if not path:
            # If no path provided, use the directory containing this file
            import os
            path = os.path.dirname(os.path.abspath(__file__)) + '/'
        config = parse_utils.load_story_config(parse_utils.load_json(path + 'story_config.json'))
        super(Story, self).__init__(path, config)
        self.dungeon = None

    def init(self, driver: Driver) -> None:
        """Initialize the story and create the dungeon."""
        super(Story, self).init(driver)
        
    def welcome(self, player: Player) -> str:
        """Welcome text when player enters a new game."""
        player.tell("<bright>Welcome to the Town of Mysteries!</>", end=True)
        player.tell("\n")
        player.tell("You stand in the town square. Locals speak of an ancient crypt "
                   "beneath the town, filled with treasures and dangers.")
        player.tell("\n")
        return ""

    def welcome_savegame(self, player: Player) -> str:
        """Welcome text when player loads a saved game."""
        player.tell("<bright>Welcome back to the Town of Mysteries!</>", end=True)
        player.tell("\n")
        return ""

    def goodbye(self, player: Player) -> None:
        """Goodbye text when player quits the game."""
        player.tell("Farewell, brave adventurer. May we meet again!")
        player.tell("\n")


if __name__ == "__main__":
    # Story is invoked as a script, start it in the Tale Driver.
    gamedir = pathlib.Path(__file__).parent
    if gamedir.is_dir() or gamedir.is_file():
        cmdline_args = sys.argv[1:]
        cmdline_args.insert(0, "--game")
        cmdline_args.insert(1, str(gamedir))
        run_from_cmdline(cmdline_args)
