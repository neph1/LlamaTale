

from tale import parse_utils
from tale.dungeon.dungeon import DungeonEntrance
from tale.parse import parse_locations


class TestParseLocations():

    def test_load_locations(self):
        room_json = parse_utils.load_json("tests/files/test_locations.json")
        zones, exits = parse_locations.load_locations(room_json)
        room_one = zones['test house'].get_location('test room')
        assert(room_one.name == 'test room')
        assert(room_one.description == 'test room description')
        room_two = zones['test house'].get_location('test room 2')
        assert(room_two.name == 'test room 2')
        assert(room_two.description == 'test room 2 description')
        assert(len(room_two.exits) == 2)
        assert(room_two.exits['north'].target == room_one)
        assert(room_two.exits['test room'].target == room_one)

        assert(exits[0].__repr__().startswith("(<base.Exit to 'test room 2'"))

    def test_load_locations_dungeon_entrance(self):
        room_json = parse_utils.load_json("tests/files/test_dungeon_entrance.json")
        zones, exits = parse_locations.load_locations(room_json)
        room_one = zones['test dungeon entrance'].get_location('test room')
        assert(room_one.name == 'test room')
        assert(room_one.description == 'test room description')
        room_two = zones['test dungeon entrance'].get_location('dungeon')

        assert(isinstance(exits[0], DungeonEntrance))
        assert(isinstance(exits[1], DungeonEntrance) == False)
