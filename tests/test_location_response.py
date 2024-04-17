

import datetime
import json
from tale import parse_utils, util
from tale.base import Location
from tale.driver_if import IFDriver
from tale.llm.responses.LocationResponse import LocationResponse


class TestLocationResponse():

    driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
    driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
    item_types = ["Weapon", "Wearable", "Health", "Money", "Trash", "Food", "Drink", "Key"]
    
    generated_location = '{"name": "Outside", "description": "A barren wasteland of snow and ice stretches as far as the eye can see. The wind howls through the mountains like a chorus of banshees, threatening to sweep away any unfortunate soul caught outside without shelter.", "exits": [{"name": "North Pass","short_desc": "The North Pass is treacherous mountain pass that leads deeper into the heart of the range","enter_msg":"You shuffle your feet through knee-deep drifts of snow, trying to keep your balance on the narrow path."}, {"name": "South Peak","short_Desc": "The South Peak offers breathtaking views of the surrounding landscape from its summit, but it\'s guarded by a pack of fierce winter wolves.","Enter_msg":"You must face off against the snarling beasts if you wish to reach the peak."}] ,"items": [{"name":"Woolly gloves", "type":"Wearable"}],"npcs": [{"name":"wolf", "body":"Creature", "unarmed_attack":"BITE", "hp":10, "level":10}]}'
    
    def test_validate_location(self):
        location = Location(name='Outside')
        location.built = False
        result = LocationResponse(json_result=json.loads(self.generated_location), location=location, exit_location_name='Entrance')
        locations = result.new_locations
        exits = result.exits
        
        location.add_exits(exits)
        assert(location.description.startswith('A barren wasteland'))
        assert(len(location.exits) == 2)
        assert(location.exits['north pass'])
        assert(location.exits['south peak'])
        assert(len(location.items) == 1) # woolly gloves
        assert(len(location.livings) == 1) # wolf
        assert(len(locations) == 2)
        assert(locations[0].name == 'North Pass')
        assert(locations[1].name == 'South Peak')

    def test_validate_location_with_world_objects(self):
        location = Location(name='Outside')
        location.built = False
        loc = json.loads(self.generated_location)
        loc["npcs"] = ["wolf"]
        world_creatures = [{"name": "wolf", "body": "Creature", "unarmed_attack": "BITE", "hp":10, "level":10}]
        result = LocationResponse(json_result=loc, location=location, exit_location_name='Entrance', world_creatures=world_creatures)
        locations = result.new_locations
        exits = result.exits
        
        location.add_exits(exits)
        assert(location.description.startswith('A barren wasteland'))
        assert(len(location.exits) == 2)
        assert(location.exits['north pass'])
        assert(location.exits['south peak'])
        assert(len(location.items) == 1) # woolly gloves
        assert(len(location.livings) == 1) # wolf
        assert(len(locations) == 2)
        assert(locations[0].name == 'North Pass')
        assert(locations[1].name == 'South Peak')


    def test_validate_items(self):
        items = [{"name": "sword", "type": "Weapon", "value": 100}, {"type": "Armor", "value": 60}, {"name": "boots"}]
        location_response = LocationResponse.empty()
        location_response.item_types = self.item_types
        valid = location_response._validate_items(items)
        assert(len(valid) == 2)
        sword = valid[0]
        assert(sword['name'])
        assert(sword['name'] == 'sword')
        assert(sword['type'] == 'Weapon')
        boots = valid[1]
        assert(boots['name'] == 'boots')
        assert(boots['type'] == 'Other')

    def test_generated_location(self):
        generated_location = '{"name": "Blighted Depths", "exits": [{"direction": "Northwest", "name": "Dank Caverns", "short_descr": "A damp tunnel leads deeper into unknown territory."}, {"direction": "Southeast", "name": "Moldy Den", "short_descr": "The path winds through mushroom-filled darkness."}, {"direction": "Southwest", "name": "Fungal Forest", "short_descr": "Vast fungal growth obscures your view beyond the clearing."}], "level": 10, "mood": -3, "races": [], "size": 5, "center": [0, 0, 0], "description": "In the Blighted Depths, stagnant air hangs thick with mold spores and decaying matter. The floor is a slick layer of slime that covers overgrown roots, while above you looms an enormous web strung between the cavern\'s columns.", "items": [], "npcs": [{"name": "Luminae", "sentiment": "Neutral", "race": "Undead Elf", "gender": "She", "level": 9, "aggressive": False, "description": "A spectral elven woman floats aimlessly in the murky depths. Her eyes are vacant as she moves through the caverns, seemingly lost.", "appearance": "Her hair flows like smoke around her translucent form, which appears to be wrapped in cobwebs. She wears tattered robes and holds a staff carved from bone."}]} '
        location = Location(name='Blighted Depths')
        location.built = False
        result = LocationResponse(json_result=json.loads(parse_utils.sanitize_json(generated_location)), location=location, exit_location_name='')
        locations = result.new_locations
        exits = result.exits

        assert(location.description.startswith('In the Blighted Depths,'))
        assert(len(exits) == 3)
        assert(exits[0].name == 'dank caverns')
        assert(exits[1].name == 'moldy den')
        assert(exits[2].name == 'fungal forest')
        assert(len(location.items) == 0)
        assert(len(location.livings) == 1)
        assert(len(locations) == 3)
        assert(locations[0].name == 'Dank Caverns')
        assert(locations[1].name == 'Moldy Den')
        assert(locations[2].name == 'Fungal Forest')