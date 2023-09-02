import pytest
import json
from tale import mud_context, util
from tale.base import Exit, Location, Zone
from tale.driver_if import IFDriver
from tale.story import GameMode, MoneyType
import tale.parse_utils as parse_utils


class TestParseUtils():
    
    def test_load_json(self):
        assert(parse_utils.load_json("tests/files/test.json"))
        
    def test_load_locations(self):
        room_json = parse_utils.load_json("tests/files/test_locations.json")
        zones, exits = parse_utils.load_locations(room_json)
        assert(zones['test house'].get_location('test room'))
        assert(zones['test house'].get_location('test room 2'))
        assert(exits[0].__repr__().startswith("(<base.Exit to 'test room 2'"))

    def test_load_items(self):
        zones = {}
        zones['Room 1'] = Location('Room 1', 'A small room perfect for testing')
        zones['House 1'] = Zone('House 1')
        zones['House 1'].add_location(Location('Room 2', 'Another testing room'))
        mud_context.driver = IFDriver()
        mud_context.driver.moneyfmt = util.MoneyFormatter.create_for(MoneyType.MODERN)
        items_json = parse_utils.load_json("tests/files/test_items.json")
        items = parse_utils.load_items(items_json, zones)
        assert(len(items) == 4)
        item = items['Box 1']
        assert(item.title == 'Box 1')
        assert(item.short_description == 'A small bejewelled box')
        assert(item.location == zones['Room 1'])
        item = items['Note 1']
        assert(item.text == 'This is a note')
        item = items['Money 1']
        assert(item.value == 100)
        assert(item.location == zones['House 1'].get_location('Room 2'))
        assert(items['Hoodie'])

    def test_load_generated_items(self):
        items_string = '{"items": [{"name":"Woolly gloves", "type":"Wearable"}]}'
        items = json.loads(items_string)
        assert(len(items) == 1)
        loaded_items = parse_utils.load_items(items['items'])
        assert(len(loaded_items) == 1)
        assert(loaded_items['Woolly gloves'])

        
    def test_load_npcs(self):
        locations = {}
        locations['Royal grotto'] = Location('Royal grotto', 'A small grotto, fit for a kobold king')
        npcs_json = parse_utils.load_json("tests/files/test_npcs.json")
        npcs = parse_utils.load_npcs(npcs_json, locations)
        assert(len(npcs) == 2)
        npc = npcs['Kobbo']
        assert(npc.title == 'Kobbo the King')
        assert(npc.location == locations['Royal grotto'])
        npc2 = npcs['generated name']
        assert(npc2.name == 'generated')
        assert(npc2.title == 'generated name')
        
    def test_load_story_config(self):
        config_json = parse_utils.load_json("tests/files/test_story_config.json")
        config = parse_utils.load_story_config(config_json)
        assert(config)
        assert(config.name == 'Test Story Config 1')
        assert(config.money_type == MoneyType.NOTHING)
        assert(config.supported_modes == {GameMode.IF})
        assert(config.zones == ["test zone"])
        
    def test_connect_location_to_exit(self):
        """ This simulates a room having been generated before"""

        cave_entrance = Location('Cave entrance', 'A dark cave entrance')
        new_location = Location('Royal grotto', 'A small grotto, fit for a kobold king')
        exit_to = Exit(directions=['north', 'Royal grotto'], target_location=new_location, short_descr='There\'s an opening that leads deeper into the cave', enter_msg='You enter the small crevice')
        cave_entrance.add_exits([exit_to])
        # the room has now been 'built' and is being added to story
        parse_utils.connect_location_to_exit(new_location, cave_entrance, exit_to)
        assert(len(cave_entrance.exits) == 2)
        assert(cave_entrance.exits['north'].target == new_location)
        assert(cave_entrance.exits['Royal grotto'].target == new_location)
        assert(len(new_location.exits) == 2)
        
        assert(new_location.exits['south'].target == cave_entrance)
        assert(new_location.exits['cave entrance'].target == cave_entrance)
        assert(new_location.exits['cave entrance'].short_description == f'You can see {cave_entrance.name}')

    def test_opposite_direction(self):
        assert(parse_utils.opposite_direction('north') == 'south')
        assert(parse_utils.opposite_direction('south') == 'north')
        assert(parse_utils.opposite_direction('east') == 'west')
        assert(parse_utils.opposite_direction('west') == 'east')
        assert(parse_utils.opposite_direction('up') == 'down')
        assert(parse_utils.opposite_direction('down') == 'up')
        assert(parse_utils.opposite_direction('in') == 'out')
        assert(parse_utils.opposite_direction('out') == 'in')
        assert(parse_utils.opposite_direction('hubwards') == None)

    def test_parse_generated_exits(self):
        exits = json.loads('{"exits": [{"name": "The Glacier", "short_descr": "A treacherous path leads up to the icy expanse, the sound of creaking ice echoing in the distance.", "enter_msg":"You enter the glacier"}, {"name": "The Cave", "short_descr": "A dark opening in the side of the mountain, rumored to be home to a mysterious creature."}, {"name": "The Forest", "short_descr": "A dense thicket of trees looms in the distance, their branches swaying in the wind."}]}')
        exit_location_name = 'Entrance'
        location = Location(name='Outside')
        new_locations, parsed_exits = parse_utils.parse_generated_exits(json_result=exits, 
                                                                        exit_location_name=exit_location_name, 
                                                                        location=location)
        assert(len(new_locations) == 3)
        assert(new_locations[0].name == 'glacier')
        assert(new_locations[1].name == 'cave')
        assert(new_locations[2].name == 'forest')
        assert(len(parsed_exits) == 3)
        assert(parsed_exits[0].name == 'glacier')
        assert(parsed_exits[1].name == 'cave')
        assert(parsed_exits[2].name == 'forest')
        assert(parsed_exits[0].short_description == 'A treacherous path leads up to the icy expanse, the sound of creaking ice echoing in the distance.')
        assert(parsed_exits[1].short_description == 'A dark opening in the side of the mountain, rumored to be home to a mysterious creature.')
        assert(parsed_exits[2].short_description == 'A dense thicket of trees looms in the distance, their branches swaying in the wind.')
        assert(parsed_exits[0].enter_msg == 'You enter the glacier')



        
          
