import json
from tale import mud_context, util
from tale.base import Exit, Location
from tale.coord import Coord
from tale.driver_if import IFDriver
from tale.story import GameMode, MoneyType
from tale.zone import Zone
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
        assert(len(npcs) == 3)

        npc = npcs['Kobbo']
        assert(npc.title == 'Kobbo the King')
        assert(npc.location == locations['Royal grotto'])
        assert(npc.aliases.pop() == 'kobbo')
        npc2 = npcs['generated name']
        assert(npc2.name == 'generated name')
        assert(npc2.title == 'generated name')
        assert(npc2.aliases.pop() == 'generated')
        npc3 = npcs['name']
        assert(npc3.name == 'name')


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
        assert(new_locations[0].name == 'Glacier')
        assert(new_locations[1].name == 'Cave')
        assert(new_locations[2].name == 'Forest')
        assert(len(parsed_exits) == 3)
        assert(parsed_exits[0].name == 'glacier')
        assert(parsed_exits[1].name == 'cave')
        assert(parsed_exits[2].name == 'forest')
        assert(parsed_exits[0].short_description == 'A treacherous path leads up to the icy expanse, the sound of creaking ice echoing in the distance.')
        assert(parsed_exits[1].short_description == 'A dark opening in the side of the mountain, rumored to be home to a mysterious creature.')
        assert(parsed_exits[2].short_description == 'A dense thicket of trees looms in the distance, their branches swaying in the wind.')
        assert(parsed_exits[0].enter_msg == 'You enter the glacier')

    def test_parse_generated_exits_duplicate_direction(self):
        exits = json.loads('{"exits": [{"name": "The Glacier", "direction": "north", "short_descr": "A treacherous path."}, {"name": "The Cave", "direction": "north", "short_descr": "A dark opening."}]}')
        exit_location_name = 'Entrance'
        location = Location(name='Outside')
        new_locations, parsed_exits = parse_utils.parse_generated_exits(json_result=exits, 
                                                                        exit_location_name=exit_location_name, 
                                                                        location=location)
        assert(len(parsed_exits) == 2)
        assert(parsed_exits[0].names == ['glacier', 'north'])
        assert(parsed_exits[0].short_description == 'To the north a treacherous path.')
        assert(parsed_exits[1].names == ['cave', 'south'])
        assert(parsed_exits[1].short_description == 'To the south a dark opening.')

    def test_coordinates_from_direction(self):
        coord = Coord(0,0,0)
        assert(parse_utils.coordinates_from_direction(coord, 'north') == Coord(0,1,0))
        assert(parse_utils.coordinates_from_direction(coord, 'south') == Coord(0,-1,0))
        assert(parse_utils.coordinates_from_direction(coord, 'east') == Coord(1,0,0))
        assert(parse_utils.coordinates_from_direction(coord, 'west') == Coord(-1,0,0))
        assert(parse_utils.coordinates_from_direction(coord, 'up') == Coord(0,0,1))
        assert(parse_utils.coordinates_from_direction(coord, 'down') == Coord(0,0,-1))
        assert(parse_utils.coordinates_from_direction(coord, 'hubwards') == Coord(0,0,0))

    def test_parse_generated_exits_duplicate_name(self):
        """ Test that location with same name can't be added (and replace an existing location)"""
        zone = Zone('test zone')
        zone.add_location(Location('Glacier', 'A dark cave entrance'))

        exits = json.loads('{"exits": [{"name": "Glacier", "direction": "north", "short_descr": "A treacherous path."}]}')
        exit_location_name = 'Entrance'
        location = Location(name='Outside')
        zone.add_location(location)
        new_locations, parsed_exits = parse_utils.parse_generated_exits(json_result=exits, 
                                                                        exit_location_name=exit_location_name, 
                                                                        location=location)
        for loc in new_locations:
            zone.add_location(loc)
        
        assert(len(zone.locations) == 2)

    def test_replace_items_with_world_items(self):
        items = ["sword", "shield", "helmet"]
        world_items = {"sword": {"name": "sword", "type": "weapon", "value": 100}, "shield": {"name": "shield", "type": "armor", "value": 60}, "boots": {"name": "boots", "type": "armor", "value": 50}}

        replaced_items = parse_utils.replace_items_with_world_items(items, world_items)
        assert(len(replaced_items) == 2)
        assert(replaced_items[0]["name"] == "sword")
        assert(replaced_items[0]["value"] == 100)
        assert(replaced_items[1]["name"] == "shield")
        assert(replaced_items[1]["value"] == 60)
        

    def test_replace_creature_with_world_creature(self):
        creatures = ["kobold", "goblin", {"name":"urgokh", "race":"orc"}]
        # creatures have the following format: {"name":"", "body":"", "mass":int(kg), "hp":int, "level":int, "unarmed_attack":One of [FISTS, CLAWS, BITE, TAIL, HOOVES, HORN, TUSKS, BEAK, TALON], "short_descr":""}
        world_creatures = {"kobold": {"name": "kobold", "body":"Humanoid", "mass":40, "hp":5, "level":1, "unarmed_attack": "FISTS", "short_descr":"A typical kobold"} }
        replaced_creatures = parse_utils.replace_creature_with_world_creature(creatures, world_creatures)
        assert(len(replaced_creatures) == 2)
        assert(replaced_creatures[0]["name"] == "kobold")
        assert(replaced_creatures[0]["body"] == "Humanoid")
        assert(replaced_creatures[0]["mass"] == 40)
        assert(replaced_creatures[0]["hp"] == 5)
        assert(replaced_creatures[0]["level"] == 1)
        assert(replaced_creatures[0]["unarmed_attack"] == "FISTS")
        assert(replaced_creatures[0]["short_descr"] == "A typical kobold")
        assert(replaced_creatures[1] == {'name': 'urgokh', 'race': 'orc'})
          
