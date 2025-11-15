"""
Tests for the reusable Dungeon class.
"""

import datetime
from mock import MagicMock

from tale import parse_utils, util
from tale.base import Location
from tale.coord import Coord
from tale.driver_if import IFDriver
from tale.dungeon.DungeonEntrance import DungeonEntrance
from tale.dungeon.dungeon import Dungeon
from tale.dungeon.dungeon_generator import Cell, Connection, Layout, LayoutGenerator, MobPopulator, ItemPopulator
from tale.json_story import JsonStory
from tale.llm.llm_utils import LlmUtil
from tale.zone import Zone
from tests.supportstuff import FakeIoUtil


class TestDungeon:
    """Test the reusable Dungeon class."""

    def setup_method(self):
        """Set up test fixtures."""
        driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
        
        self.llm_util = LlmUtil(FakeIoUtil(response=['''{
        "0": {
        "index": 0,
        "name": "Entrance to dungeon",
        "description": "A dark entrance."
        },
        "1": {
        "index": 1,
        "name": "Hallway",
        "description": "A long hallway."
        },
        "2": {
        "index": 2,
        "name": "Room",
        "description": "A small room."
        }
        }''']))
        
        driver.llm_util = self.llm_util
        
        self.story = JsonStory(
            'tests/files/empty_world/',
            parse_utils.load_story_config(parse_utils.load_json('tests/files/empty_world/story_config.json'))
        )
        self.llm_util.set_story(self.story)
        self.story.init(driver=driver)

    def get_mock_layout(self) -> Layout:
        """Create a mock layout for testing."""
        layout = Layout(Coord(0, 0, 0))
        coords = [Coord(0, 0, 0), Coord(1, 0, 0), Coord(2, 0, 0)]
        for coord in coords:
            cell = Cell(coord=coord)
            layout.cells[coord.as_tuple()] = cell
        
        layout.cells[Coord(0, 0, 0).as_tuple()].is_dungeon_entrance = True
        layout.cells[Coord(1, 0, 0).as_tuple()].is_room = True
        layout.cells[Coord(2, 0, 0).as_tuple()].is_room = True
        layout.cells[Coord(2, 0, 0).as_tuple()].leaf = True
        
        layout.cells[Coord(1, 0, 0).as_tuple()].parent = Coord(0, 0, 0)
        layout.cells[Coord(2, 0, 0).as_tuple()].parent = Coord(1, 0, 0)
        
        connection = Connection(Coord(1, 0, 0), Coord(0, 0, 0))
        layout.connections.add(connection)
        
        return layout

    def test_dungeon_creation(self):
        """Test creating a dungeon."""
        mock_layout_generator = MagicMock()
        mock_layout_generator.generate.return_value = self.get_mock_layout()
        
        dungeon = Dungeon(
            name="Test Dungeon",
            story=self.story,
            layout_generator=mock_layout_generator,
            mob_populator=MobPopulator(),
            item_populator=ItemPopulator(),
            max_depth=3
        )
        
        assert dungeon.name == "Test Dungeon"
        assert dungeon.max_depth == 3
        assert len(dungeon.zones) == 0

    def test_dungeon_generate_level(self):
        """Test generating a dungeon level."""
        mock_layout_generator = MagicMock()
        mock_layout_generator.generate.return_value = self.get_mock_layout()
        
        dungeon = Dungeon(
            name="Test Dungeon",
            story=self.story,
            layout_generator=mock_layout_generator,
            mob_populator=MobPopulator(),
            item_populator=ItemPopulator(),
            max_depth=3
        )
        
        zone = Zone("test_level_0", "Test Level 0")
        zone.level = 1
        zone.center = Coord(0, 0, 0)
        zone.races = ["bat"]
        zone.items = ["torch"]
        
        self.story.add_zone(zone)
        
        result = dungeon.generate_level(zone, depth=0)
        
        assert result is True
        assert len(zone.locations) == 3
        assert len(dungeon.zones) == 1

    def test_dungeon_entrance(self):
        """Test creating and binding a dungeon entrance."""
        mock_layout_generator = MagicMock()
        mock_layout_generator.generate.return_value = self.get_mock_layout()
        
        
        # Create a location to add the entrance to
        location = Location("Test Location", "A test location")
        location.world_location = Coord(0, 0, 0)
        
        # Create the entrance
        entrance = DungeonEntrance(
            directions=["test dungeon", "down"],
            short_descr="A dark entrance",
            target_location=location,
        )
        entrance.bind(location)

        dungeon = entrance.build_dungeon(self.story, self.llm_util)
        
        # Verify the dungeon was created
        assert entrance.target is not None
        assert len(dungeon.zones) == 1
        assert dungeon.zones[0].name == "test dungeon_level_0"

    def test_dungeon_get_entrance_location(self):
        """Test getting the entrance location of a dungeon."""
        mock_layout_generator = MagicMock()
        mock_layout_generator.generate.return_value = self.get_mock_layout()
        
        dungeon = Dungeon(
            name="Test Dungeon",
            story=self.story,
            layout_generator=mock_layout_generator,
            mob_populator=MobPopulator(),
            item_populator=ItemPopulator(),
            max_depth=3
        )
        
        zone = Zone("test_level_0", "Test Level 0")
        zone.level = 1
        zone.center = Coord(0, 0, 0)
        zone.races = ["bat"]
        zone.items = ["torch"]
        
        self.story.add_zone(zone)
        dungeon.generate_level(zone, depth=0)
        
        entrance_location = dungeon.get_entrance_location()
        
        assert entrance_location is not None
        assert entrance_location.name in zone.locations
