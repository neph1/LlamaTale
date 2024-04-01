

import datetime
from mock import MagicMock

from stories.dungeon.story import DungeonStory
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

    def setup_method(self):
        driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
        self.llm_util = LlmUtil(FakeIoUtil(response='[{"index": 0, "name": "room1", "descr": "description1"}, {"index": 1, "name": "room2", "descr": "description2"}, {"index": 2, "name": "room3", "descr": "description3"}, {"index": 3, "name": "room4", "descr": "description4"}]')) # type: LlmUtil
        
        driver.llm_util = self.llm_util

        mock_layout_generator = MagicMock(type='LayoutGenerator')
        mock_layout_generator.generate.return_value = self.get_layout()

        mock_mob_spawner = MagicMock(type='MobPoulator')
        mock_mob_spawner.populate.return_value = self.setup_mob_spawner()

        mock_item_spawner = MagicMock(type='ItemPopulator')
        mock_item_spawner.populate.return_value = self.setup_item_spawner()

        self.story = DungeonStory(layout_generator=mock_layout_generator, mob_populator=mock_mob_spawner, item_populator=mock_item_spawner)
        
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
    
    def test_prepare_locations(self):
        layout = self.get_layout()
        first_zone = True
        locations = self.story._prepare_locations(layout, first_zone)
        assert len(locations) == 4
        assert 'Entrance to dungeon' in locations[0]
        assert '"name": ""' in locations[1]
        assert '"name": ""' in locations[2]
        assert 'Room with starcase leading down' in locations[3]

    def test_prepare_locations_second_zone(self):
        layout = self.get_layout()
        first_zone = False
        locations = self.story._prepare_locations(layout, first_zone)
        assert len(locations) == 4
        assert 'Room with starcase leading up' in locations[0]

    def test_add_zone(self):
        
        zone = Zone(name='test zone') # type: zone.Zone
        # Call the add_zone method
        result = self.story.add_zone(zone)

        # Assert that the add_zone method returned True
        assert result == True

        assert zone.get_location('room1').description == 'description1'

        assert zone.get_location('room2').description == 'description2'

        assert zone.get_location('room1').exits['room2']
        assert zone.get_location('room2').exits['room1']
        assert zone.get_location('room2').exits['room3']
        assert zone.get_location('room3').exits['room2']
        assert zone.get_location('room4').exits['room3']

        assert self.story.world.mob_spawners[0].mob_type['name'] == 'bat'

        assert self.story.world.item_spawners[0].items[0]['name'] == 'torch'