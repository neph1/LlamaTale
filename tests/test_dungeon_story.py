

import datetime
from mock import MagicMock

from stories.dungeon.story import Story
from tale import util, zone
from tale.base import Location
from tale.coord import Coord
from tale.driver_if import IFDriver
from tale.dungeon.dungeon_generator import Cell, Layout
from tale.item_spawner import ItemSpawner
from tale.llm.llm_utils import LlmUtil
from tale.mob_spawner import MobSpawner
from tale.zone import Zone
from tests.supportstuff import FakeIoUtil


class TestDungeonStory():

    def test_load_story(self):
        driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
        self.llm_util = LlmUtil(FakeIoUtil(response=['''{
        "0": {
        "index": 0,
        "name": "Entrance to dungeon",
        "description": "A dark and ominous entrance to the dungeon, guarded by a fearsome dragon."
        },
        "1": {
        "index": 1,
        "name": "Hallway",
        "description": "A long and winding hallway, lined with ancient tapestries and mysterious artifacts."
        },
        "2": {
        "index": 2,
        "name": "Small room",
        "description": "A small and dimly lit room, filled with strange and exotic plants."
        },
        "3": {
        "index": 3,
        "name": "Hallway",
        "description": "A narrow and winding hallway, with flickering torches casting eerie shadows on the walls."
        }
        }'''])) # type: LlmUtil
        
        driver.llm_util = self.llm_util

        mock_layout_generator = MagicMock(type='LayoutGenerator')
        mock_layout_generator.generate.return_value = self.get_layout()

        mock_mob_spawner = MagicMock(type='MobPopulator')
        mock_mob_spawner.populate.return_value = self.setup_mob_spawner()

        mock_item_spawner = MagicMock(type='ItemPopulator')
        mock_item_spawner.populate.return_value = self.setup_item_spawner()

        self.story = Story(layout_generator=mock_layout_generator, mob_populator=mock_mob_spawner, item_populator=mock_item_spawner)
        
        self.llm_util.set_story(self.story)
        self.story.init(driver=driver)

    def get_layout(self) -> Layout:

        layout = Layout(Coord(0, 0, 0))
        coords = [Coord(0, 0, 0), Coord(1, 0, 0), Coord(2, 0, 0), Coord(3, 0, 0)]
        for coord in coords:
            cell = Cell(coord=coord)
            layout.cells[coord.as_tuple()] = cell
        layout.cells[Coord(0, 0, 0).as_tuple()].is_entrance = True

        layout.cells[Coord(1, 0, 0).as_tuple()].is_room = True
        layout.cells[Coord(2, 0, 0).as_tuple()].is_room = True
        layout.cells[Coord(3, 0, 0).as_tuple()].leaf = True
        layout.cells[Coord(3, 0, 0).as_tuple()].is_exit = True
        layout.cells[Coord(3, 0, 0).as_tuple()].parent = Coord(2, 0, 0)
        layout.cells[Coord(2, 0, 0).as_tuple()].parent = Coord(1, 0, 0)
        layout.cells[Coord(1, 0, 0).as_tuple()].parent = Coord(0, 0, 0)

        return layout
    
    def setup_mob_spawner(self):
        location = Location(name="Test Location")
        mob = dict(gender='m', name='bat', aggressive=True)
        return MobSpawner(mob, location, spawn_rate=2, spawn_limit=3)
    
    def setup_item_spawner(self):
        zone = Zone(name='test zone')
        items = [dict(name='torch', description='test description')]
        return ItemSpawner(items, item_probabilities=[0.2], zone=zone, spawn_rate=2)

    def test_prepare_locations_second_zone(self):
        layout = self.get_layout()
        first_zone = False
        locations = self.story._prepare_locations(layout, first_zone)
        assert len(locations) == 4
        assert 'Room with staircase leading up' in locations[0]

    def test_describe_rooms_dict(self):
        layout = self.get_layout()
        test_zone = Zone(name='test zone')
        self.story._zones[test_zone.name] = test_zone
        rooms = self.story._prepare_locations(layout)
        locations = self.story._describe_rooms(test_zone, layout, rooms)

        assert len(locations) == 4
        assert test_zone.get_location('hallway').description == 'A narrow and winding hallway, with flickering torches casting eerie shadows on the walls.'
