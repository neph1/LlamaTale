import datetime
from tale import parse_utils, util
from tale.base import Location
from tale.coord import Coord
from tale.driver_if import IFDriver
from tale.dungeon.dungeon_generator import Cell, Connection, ItemPopulator, MobPopulator, Layout, LayoutGenerator, Key
from tale.json_story import JsonStory
from tale.story import MoneyType
from tale.zone import Zone


class TestDungeonGenerator:

    def test_generate_dungeon_with_seed(self):
        dungeon_generator = LayoutGenerator(seed=1)

        layout = dungeon_generator.generate()

        dungeon_generator.print()

        assert len(layout.cells) > 0
        assert len(layout.connections) > 0
        assert len(layout.keys) > 0
        assert dungeon_generator.exit_coord is not None

        # generate a couple of layouts

        dungeon_generator = LayoutGenerator(seed=42)

        assert dungeon_generator.generate()

        dungeon_generator = LayoutGenerator(seed=510)

        assert dungeon_generator.generate()



    def test_add_cell(self):
        dungeon_generator = LayoutGenerator()
        dungeon_generator._generate_cell(Coord(1, 1, 0))
        assert len(dungeon_generator.layout.cells) == 1

    def test_place_key(self):
        dungeon_generator = LayoutGenerator(seed=1, start_coord=Coord(0, 0, 0))
        coords = [Coord(0, 0, 0), Coord(1, 0, 0), Coord(2, 0, 0), Coord(3, 0, 0)]
        for coord in coords:
            cell = Cell(coord=coord)
            dungeon_generator.layout.cells[coord.as_tuple()] = cell
        dungeon_generator._get_cell(Coord(1, 0, 0)).leaf = True
        door = Connection(Coord(2, 0, 0), Coord(1, 0, 0), door=True)
        key = dungeon_generator._place_key(door)
        assert key.__str__() == 'Key: (1, 0, 0) -> (2, 0, 0)'
        assert key.key_code == door.key_code
        assert len(dungeon_generator.layout.keys) == 1


    def test_num_neighbors_to_add(self):
        dungeon_generator = LayoutGenerator()
        num_neighbors = dungeon_generator._num_neighbors_to_add(Coord(1, 1, 0))
        assert num_neighbors >= 0 and num_neighbors <= 3

    def test_get_cell(self):
        dungeon_generator = LayoutGenerator(start_coord=Coord(0, 0, 0))
        dungeon_generator._generate_cell(Coord(1, 1, 0))
        cell = dungeon_generator._get_cell(Coord(1, 1, 0))
        assert cell is not None

    def test_set_exit(self):
        dungeon_generator = LayoutGenerator()
        dungeon_generator.generate()
        assert dungeon_generator.exit_coord is not None

        assert dungeon_generator.add_connector_cell(dungeon_generator.exit_coord) is not None

    def test_print(self, capsys):
        dungeon_generator = LayoutGenerator()
        dungeon_generator.generate()
        dungeon_generator.print()
        captured = capsys.readouterr()
        assert len(captured.out) > 0

class TestDungeonPopulator():

    def setup_method(self):
        driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
        driver.moneyfmt = util.MoneyFormatter.create_for(MoneyType.MODERN)
        self.layout = Layout(Coord(0, 0, 0))
        coords = [Coord(0, 0, 0), Coord(1, 0, 0), Coord(2, 0, 0), Coord(3, 0, 0)]
        for coord in coords:
            cell = Cell(coord=coord)
            self.layout.cells[coord.as_tuple()] = cell
        self.layout.cells[Coord(3, 0, 0).as_tuple()].leaf = True
        door = Connection(Coord(3, 0, 0), Coord(2, 0, 0), door=True)
        self.layout.doors = [door]
        key = Key(Coord(1, 0, 0), door)
        self.layout.keys = [key]

        self.story = JsonStory('tests/files/world_story/', parse_utils.load_story_config(parse_utils.load_json('tests/files/world_story/story_config.json')))
        self.story.init(driver=driver)
        self.zone = self.story.get_zone('Cave')
        for cell in list(self.layout.cells.values()):
            location = Location(name="test location")
            location.world_location = cell.coord
            self.story.add_location(location=location)
            self.zone.add_location(location=location)
            

    def test_populate_mobs(self):
        self.zone.level = 5
        populator = MobPopulator()

        spawners = populator.populate(zone=self.zone, layout=self.layout, story=self.story)

        assert len(spawners) > 0
        assert spawners[0].mob_type['name'] in ['bat', 'wolf']
        assert spawners[0].mob_type['level'] == 5

    def test_populate_items(self):
        self.zone.level = 3
        populator = ItemPopulator()

        spawners = populator.populate(zone=self.zone, story=self.story)

        assert len(spawners) == populator.max_items
        assert spawners[0].items[0]['name'] in ['torch', 'Sword', ]

    def test_populate_items_only_one(self):
        self.zone.level = 3
        populator = ItemPopulator()
        self.zone.items = ['Sword']
        spawners = populator.populate(zone=self.zone, story=self.story)

        assert len(spawners) == populator.max_items
        assert spawners[0].items[0]['name'] in ['Sword']
