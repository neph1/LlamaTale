"""
Test the dungeon example story.
"""

import datetime
from mock import MagicMock

from tale import parse_utils, util
from tale.coord import Coord
from tale.driver_if import IFDriver
from tale.dungeon.dungeon_generator import LayoutGenerator, MobPopulator, ItemPopulator
from tale.llm.llm_utils import LlmUtil
from tests.supportstuff import FakeIoUtil


class TestDungeonExampleStory:
    """Test the dungeon example story."""

    def test_load_dungeon_example_story(self):
        """Test that the dungeon example story loads correctly."""
        # Import story locally to avoid module-level issues
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../stories/dungeon_example'))
        
        from stories.dungeon_example.story import Story
        
        driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
        
        # Set up fake LLM responses for room descriptions
        llm_util = LlmUtil(FakeIoUtil(response=['''{
        "0": {
        "index": 0,
        "name": "Entrance to dungeon",
        "description": "A dark and ominous entrance to the ancient crypt."
        },
        "1": {
        "index": 1,
        "name": "Hallway",
        "description": "A long hallway filled with cobwebs."
        },
        "2": {
        "index": 2,
        "name": "Crypt Chamber",
        "description": "An old burial chamber."
        }
        }''']))
        
        driver.llm_util = llm_util
        
        story = Story()
        llm_util.set_story(story)
        story.init(driver=driver)
        
        # Verify the story loaded
        assert story.config.name == "Town of Mysteries"
        
        # Verify the town zone was created
        assert "town" in story._zones
        town_zone = story._zones["town"]
        assert town_zone.name == "town"
        
        # Verify the town square exists
        town_square = town_zone.get_location("Town Square")
        assert town_square is not None
        assert town_square.world_location == Coord(0, 0, 0)
        
        # Verify the dungeon entrance exists
        exits = town_square.exits
        assert len(exits) > 0
        
        # The dungeon entrance should be accessible via one of these directions
        dungeon_exit = None
        for direction in ["north", "down", "crypt"]:
            if direction in exits:
                dungeon_exit = exits[direction]
                break
        
        assert dungeon_exit is not None, "Dungeon entrance not found in town square"
        
        # Verify the dungeon was created
        assert story.dungeon is not None
        assert story.dungeon.name == "Ancient Crypt"
        assert story.dungeon.max_depth == 3
        
        # Verify the first dungeon level was generated
        assert len(story.dungeon.zones) == 1
        dungeon_zone = story.dungeon.zones[0]
        assert dungeon_zone.name == "Ancient Crypt_level_0"
        
        # Verify dungeon has locations
        assert len(dungeon_zone.locations) > 0
        
        print(f"Story loaded successfully with {len(town_zone.locations)} town location(s)")
        print(f"Dungeon has {len(dungeon_zone.locations)} location(s) in level 0")
