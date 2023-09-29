import pytest
import json
from tale.base import Location
from tale.coord import Coord
from tale.json_story import JsonStory
from tale.llm.llm_utils import LlmUtil
from tale.zone import Zone
from tests.supportstuff import FakeIoUtil
import tale.parse_utils as parse_utils
from tale.driver_if import IFDriver

class TestLlmUtils():

    llm_util = LlmUtil(FakeIoUtil()) # type: LlmUtil

    test_text_valid = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"bartender", "to":"user"}, "sentiment":"cheerful"}'

    test_text_valid_no_to = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"bartender", "to":""}}'

    test_text_invalid = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"", "from":"bartender", "to":"user"}}'

    test_text_invalid_2 = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"", "to":"user"}}'

    actual_response_empty_result = '{   "thoughts": "No items were given, taken, dropped or put.",  "results": {}  }\n'

    actual_response_3 = '{\n    "thoughts": "\ud83d\ude0d Norhardt feels that he is close to finding something important after a long and dangerous journey through rough terrain and harsh weather, and it consumes him fully.",\n    "result": {\n        "item": "map",\n        "from": "Norhardt",\t\n        "to": "Arto"\n    }\n}'

    generated_location = '{"name": "Outside", "description": "A barren wasteland of snow and ice stretches as far as the eye can see. The wind howls through the mountains like a chorus of banshees, threatening to sweep away any unfortunate soul caught outside without shelter.", "exits": [{"name": "North Pass","short_desc": "The North Pass is treacherous mountain pass that leads deeper into the heart of the range","enter_msg":"You shuffle your feet through knee-deep drifts of snow, trying to keep your balance on the narrow path."}, {"name": "South Peak","short_Desc": "The South Peak offers breathtaking views of the surrounding landscape from its summit, but it\'s guarded by a pack of fierce winter wolves.","Enter_msg":"You must face off against the snarling beasts if you wish to reach the peak."}] ,"items": [{"name":"Woolly gloves", "type":"Wearable"}],"npcs": []}'
    
    generated_location_extra = '{"Outside": { "description": "A barren wasteland of snow and ice stretches", "exits": [{"name": "North Pass","short_desc": "The North Pass is treacherous mountain pass that leads deeper into the heart of the range","enter_msg":"You shuffle your feet through knee-deep drifts of snow, trying to keep your balance on the narrow path."}, {"name": "South Peak","short_Desc": "The South Peak offers breathtaking views of the surrounding landscape from its summit, but it\'s guarded by a pack of fierce winter wolves.","Enter_msg":"You must face off against the snarling beasts if you wish to reach the peak."}] ,"items": [{"name":"Woolly gloves", "type":"Wearable"}],"npcs": []}}'
    
    generated_zone = '{"name":"Test Zone", "description":"A test zone", "level":10, "mood":-2, "races":["human", "elf", "dwarf"], "items":["sword", "shield"]}'
    
    story = JsonStory('tests/files/test_story/', parse_utils.load_story_config(parse_utils.load_json('tests/files/test_story/test_story_config.json')))
    
    story.init(IFDriver())

    def test_validate_item_response_valid(self):
        items = json.loads('["ale"]')
        valid, result = self.llm_util._character.validate_item_response(json.loads(self.test_text_valid), 'bartender', 'user', items)
        assert(valid)
        assert(result["from"] and result["to"] and result["item"])

    def test_validate_item_response_valid_no_to(self):
        items = json.loads('["ale"]')
        valid, result = self.llm_util._character.validate_item_response(json.loads(self.test_text_valid_no_to), 'bartender', 'user', items)
        assert(valid)
        assert(result["from"] and result["item"] and not result["to"] )


    def test_validate_item_response_no_item(self):
        items = json.loads('["ale"]')
        valid, result  = self.llm_util._character.validate_item_response(json.loads(self.test_text_invalid), 'bartender', 'user', items)
        assert(not valid)
        assert(not result)

    def test_validate_item_response_no_from(self):
        items = json.loads('["ale"]')
        valid, result = self.llm_util._character.validate_item_response(json.loads(self.test_text_invalid_2), 'bartender', 'user', items)
        assert(not valid)
        assert(not result)

    def test_validate_item_response_invalid_item(self):
        items = json.loads('["water"]')
        valid, result = self.llm_util._character.validate_item_response(json.loads(self.test_text_valid), 'bartender', 'user', items)
        assert(not valid)
    
    def test_read_items(self):
        character_card = "[Norhardt; gender: m; age: 56; occupation: ; personality: An experienced explorer ; appearance: A grizzled old man, with parch; items:map]"
        items_array = character_card.split('items:')[1].split(']')[0]
        #items = json.loads(items_array)
        assert('map' in items_array)

    def test_generate_item_prompt(self):
        prompt = self.llm_util._character.generate_item_prompt('pre prompt', 'items', 'character1', 'character2')
        assert(prompt)

    def test_handle_response_no_result(self):
        response = '{"thoughts":"The character Norhardt did not give anything listed. The character Arto took nothing. But the author mentioned that they saw something big and fury near where they were walking so likely this creature got dropped there."}'
        result = json.loads(parse_utils.trim_response(json.dumps(json.loads(response))))
        assert(result)

    def test_validate_response_empty_result(self):
        valid, result  = self.llm_util._character.validate_item_response(json.loads(self.actual_response_empty_result), 'Norhardt', 'Arto', 'map')
        assert(not valid)
        assert(not result)

    def test_actual_response_3(self):
        valid, result  = self.llm_util._character.validate_item_response(json.loads(self.actual_response_3), 'Norhardt', 'Arto', 'map')
        assert(valid)
        assert(result)
        
    def test_validate_sentiment(self):
        sentiment = self.llm_util._character.validate_sentiment(json.loads(self.test_text_valid))
        assert(sentiment == 'cheerful')

    def test_validate_location(self):
        location = Location(name='Outside')
        location.built = False
        locations, exits = self.llm_util._world_building._validate_location(json.loads(self.generated_location), location_to_build=location, exit_location_name='Entrance')
        location.add_exits(exits)
        assert(location.description.startswith('A barren wasteland'))
        assert(len(location.exits) == 2)
        assert(location.exits['north pass'])
        assert(location.exits['south peak'])
        assert(len(location.items) == 1) # woolly gloves
        assert(len(locations) == 2)
        assert(locations[0].name == 'North Pass')
        assert(locations[1].name == 'South Peak')

    def test_evoke(self):
        evoke_string = 'test response'
        self.llm_util.io_util = FakeIoUtil(response=evoke_string)
        self.llm_util.set_story(self.story)
        result = self.llm_util.evoke(message='test evoke', player_io=None)
        assert(result)
        assert(self.llm_util._look_hashes[hash('test evoke')] == evoke_string)

    def test_generate_character(self):
        character_string = json.dumps(parse_utils.load_json('tests/files/test_character.json'))
        self.llm_util._character.io_util = FakeIoUtil(response = character_string)
        result = self.llm_util._character.generate_character(story_type='a test story')
        assert(result)

    def test_build_location(self):
        location = Location(name='Outside')
        exit_location_name = 'Cave entrance'
        self.llm_util._world_building.io_util.response = self.generated_location
        self.llm_util.set_story(self.story)
        
        locations = self.llm_util.build_location(location, exit_location_name, zone_info={})
        assert(len(locations) == 2)

    def test_build_location_extra_json(self):
        location = Location(name='Outside')
        exit_location_name = 'Cave entrance'
        self.llm_util._world_building.io_util.response = self.generated_location_extra
        self.llm_util.set_story(self.story)
        locations = self.llm_util.build_location(location, exit_location_name, zone_info={})
        assert(len(locations) == 2)

    def test_validate_zone(self):
        center = Coord(5, 0, 0)
        zone = self.llm_util._world_building.validate_zone(json.loads(self.generated_zone), center=center)
        assert(zone)
        assert(zone.name == 'Test Zone')
        assert(zone.description == 'A test zone')
        assert(zone.races == ['human', 'elf', 'dwarf'])
        assert(zone.items == ['sword', 'shield'])
        assert(zone.center == center)
        assert(zone.level == 10)
        assert(zone.mood == -2)

    def test_get_neighbor_or_generate_zone(self):
        """ Tests the get_neighbor_or_generate_zone method of llm_utils.
        """
        self.llm_util._world_building.io_util.response = self.generated_zone
        zone = Zone('Current zone', description='This is the current zone')
        zone.neighbors['east'] = Zone('East zone', description='This is the east zone')
        
        # near location, returning current zone
        current_location = Location(name='Test Location')
        current_location.world_location = Coord(0, 0, 0)
        target_location = Location(name='Target Location')
        target_location.world_location = Coord(1, 0, 0)
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the current zone')
        
        # far location, neighbor exists, returning east zone
        current_location.world_location = Coord(10, 0, 0)
        target_location.world_location = Coord(11, 0, 0)
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the east zone')
        
        # far location, neighbor does not exist, generating new zone
        self.llm_util.io_util.response = self.generated_zone
        self.llm_util.set_story(self.story)
        current_location.world_location = Coord(-10, 0, 0)
        target_location.world_location = Coord(-11, 0, 0)
        new_zone = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location)
        assert(self.story.get_zone(new_zone.name))
        assert(new_zone.get_info()['description'] == 'A test zone')

        # test add a zone with same name
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the current zone')
        
        # test with non valid json
        self.llm_util.io_util.response = '{"name":test}'
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the current zone')

        # test with valid json but not valid zone
        self.llm_util.io_util.response = '{}'
        zone_info = self.llm_util.get_neighbor_or_generate_zone(zone, current_location, target_location).get_info()
        assert(zone_info['description'] == 'This is the current zone')

    def test_perform_idle_action(self):
        # mostly testing that prompt works
        self.llm_util.set_story(self.story)
        self.llm_util._character.io_util.response = 'Walk to the left;Walk to the right;Jump up and down'
        location = Location(name='Test Location')
        actions = self.llm_util.perform_idle_action(character_name='Norhardt', location = location, character_card= '{}', sentiments= {}, last_action= '')
        assert(len(actions) == 3)
        assert(actions[0] == 'Walk to the left')
        assert(actions[1] == 'Walk to the right')
        assert(actions[2] == 'Jump up and down')

    def test_perform_travel_action(self):
        # mostly testing that prompt works
        self.llm_util._character.io_util.response = 'West'
        result = self.llm_util._character.perform_travel_action(character_name='Norhardt', location = Location(name='Test Location'), character_card= '{}', locations= [], directions= [])
        assert(result == 'West')

    def test_generate_start_location(self):
        self.llm_util._world_building.io_util.response='{"name": "Greenhaven", "exits": [{"direction": "north", "name": "Misty Meadows", "description": "A lush and misty area filled with rolling hills and sparkling streams. The air is crisp and refreshing, and the gentle chirping of birds can be heard throughout."}, {"direction": "south", "name": "Riverdale", "description": "A bustling town nestled near a winding river. The smell of freshly baked bread and roasting meats fills the air, and the sound of laughter and chatter can be heard from the local tavern."}, {"direction": "east", "name": "Forest of Shadows", "description": "A dark and eerie forest filled with twisted trees and mysterious creatures. The air is thick with an ominous energy, and the rustling of leaves can be heard in the distance."}], "items": [], "npcs": []}'
        location = Location(name='', descr='on a small road outside a village')
        new_locations, exits = self.llm_util._world_building.generate_start_location(location, 
                                                       story_type='',
                                                       story_context='', 
                                                       zone_info={},
                                                       world_info='',)
        location = Location(name=location.name, descr=location.description)
        assert(location.name == 'Greenhaven')
        assert(location.title == 'Greenhaven')
        assert(location.description == 'on a small road outside a village')
        assert(exits[0].name == 'misty meadows')
        assert(exits[1].name == 'riverdale')
        assert(new_locations[0].name == 'Misty Meadows')
        assert(new_locations[1].name == 'Riverdale')

    def test_generate_start_zone(self):
        # mostly for coverage
        self.llm_util._world_building.io_util.response = self.generated_zone

        result = self.llm_util._world_building.generate_start_zone(location_desc='',
                                                   story_type='',
                                                   story_context='', 
                                                   world_mood=0,
                                                   world_info='')
        assert(result.name == 'Test Zone')
        assert(result.races == ['human', 'elf', 'dwarf'])
