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

    def __init__(self) -> None:
        config = parse_utils.load_story_config(parse_utils.load_json('story_config.json'))
        super(Story, self).__init__('', config)
        self.dungeon = None

    def init(self, driver: Driver) -> None:
        """Initialize the story and create the dungeon."""
        super(Story, self).init(driver)
        
        # Create a dungeon
        self.dungeon = Dungeon(
            name="Ancient Crypt",
            story=self,
            llm_util=driver.llm_util,
            layout_generator=LayoutGenerator(),
            mob_populator=MobPopulator(),
            item_populator=ItemPopulator(),
            max_depth=3
        )
        
        # Create the town zone with a normal location
        self._create_town()
        
    def _create_town(self):
        """Create a simple town with a dungeon entrance."""
        # Create town zone
        town_zone = Zone("town", "A peaceful town")
        town_zone.level = 1
        town_zone.center = Coord(0, 0, 0)
        town_zone.races = ["human"]
        town_zone.items = ["torch", "Sword"]
        
        # Create town square location
        town_square = Location(
            "Town Square",
            "A bustling town square with a fountain in the center. "
            "To the north, you see an old stone archway leading down into darkness."
        )
        town_square.world_location = Coord(0, 0, 0)
        
        # Add location to zone
        town_zone.add_location(town_square)
        self.add_zone(town_zone)
        self.add_location(town_square, zone="town")
        
        # Create a dungeon entrance in the town square
        dungeon_entrance = DungeonEntrance(
            directions=["north", "down", "crypt"],
            dungeon=self.dungeon,
            short_descr="An ancient stone archway descends into darkness.",
            long_descr="The archway is covered in moss and strange runes. "
                      "A cold wind blows from the depths below."
        )
        
        # Bind the entrance to the location (this will generate the first dungeon level)
        dungeon_entrance.bind(town_square)
        town_square.add_exits([dungeon_entrance])

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
