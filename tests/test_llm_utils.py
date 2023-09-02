import pytest
import json
from tale.base import Location
from tale.json_story import JsonStory
from tale.llm_utils import LlmUtil
from tests.supportstuff import FakeIoUtil
import tale.parse_utils as parse_utils
from tale.driver_if import IFDriver

class TestLlmUtils():

    llm_util = LlmUtil()

    test_text_valid = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"bartender", "to":"user"}, "sentiment":"cheerful"}'

    test_text_valid_no_to = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"bartender", "to":""}}'

    test_text_invalid = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"", "from":"bartender", "to":"user"}}'

    test_text_invalid_2 = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"", "to":"user"}}'

    actual_response_empty_result = '{   "thoughts": "No items were given, taken, dropped or put.",  "results": {}  }\n'

    actual_response_3 = '{\n    "thoughts": "\ud83d\ude0d Norhardt feels that he is close to finding something important after a long and dangerous journey through rough terrain and harsh weather, and it consumes him fully.",\n    "result": {\n        "item": "map",\n        "from": "Norhardt",\t\n        "to": "Arto"\n    }\n}'

    generated_location = '{"name": "Outside","description": "A barren wasteland of snow and ice stretches as far as the eye can see. The wind howls through the mountains like a chorus of banshees, threatening to sweep away any unfortunate soul caught outside without shelter.", "exits": [{"name": "North Pass","short_desc": "The North Pass is treacherous mountain pass that leads deeper into the heart of the range","enter_msg":"You shuffle your feet through knee-deep drifts of snow, trying to keep your balance on the narrow path."}, {"name": "South Peak","short_Desc": "The South Peak offers breathtaking views of the surrounding landscape from its summit, but it\'s guarded by a pack of fierce winter wolves.","Enter_msg":"You must face off against the snarling beasts if you wish to reach the peak."}] ,"items": [{"name":"Woolly gloves", "type":"Wearable"}],"npcs": []}'
    
    story = JsonStory('tests/files/test_story/', parse_utils.load_story_config(parse_utils.load_json('tests/files/test_story/test_story_config.json')))
    
    story.init(IFDriver())

    def test_validate_item_response_valid(self):
        items = json.loads('["ale"]')
        valid, result = self.llm_util.validate_item_response(json.loads(self.test_text_valid), 'bartender', 'user', items)
        assert(valid)
        assert(result["from"] and result["to"] and result["item"])

    def test_validate_item_response_valid_no_to(self):
        items = json.loads('["ale"]')
        valid, result = self.llm_util.validate_item_response(json.loads(self.test_text_valid_no_to), 'bartender', 'user', items)
        assert(valid)
        assert(result["from"] and result["item"] and not result["to"] )


    def test_validate_item_response_no_item(self):
        items = json.loads('["ale"]')
        valid, result  = self.llm_util.validate_item_response(json.loads(self.test_text_invalid), 'bartender', 'user', items)
        assert(not valid)
        assert(not result)

    def test_validate_item_response_no_from(self):
        items = json.loads('["ale"]')
        valid, result = self.llm_util.validate_item_response(json.loads(self.test_text_invalid_2), 'bartender', 'user', items)
        assert(not valid)
        assert(not result)

    def test_validate_item_response_invalid_item(self):
        items = json.loads('["water"]')
        valid, result = self.llm_util.validate_item_response(json.loads(self.test_text_valid), 'bartender', 'user', items)
        assert(not valid)
    
    def test_read_items(self):
        character_card = "[Norhardt; gender: m; age: 56; occupation: ; personality: An experienced explorer ; appearance: A grizzled old man, with parch; items:map]"
        items_array = character_card.split('items:')[1].split(']')[0]
        #items = json.loads(items_array)
        assert('map' in items_array)

    def test_generate_item_prompt(self):
        prompt = self.llm_util.generate_item_prompt('pre prompt', 'items', 'character1', 'character2')
        assert(prompt)

    def test_handle_response_no_result(self):
        response = '{"thoughts":"The character Norhardt did not give anything listed. The character Arto took nothing. But the author mentioned that they saw something big and fury near where they were walking so likely this creature got dropped there."}'
        result = json.loads(parse_utils.trim_response(json.dumps(json.loads(response))))
        assert(result)

    def test_validate_response_empty_result(self):
        valid, result  = self.llm_util.validate_item_response(json.loads(self.actual_response_empty_result), 'Norhardt', 'Arto', 'map')
        assert(not valid)
        assert(not result)

    def test_actual_response_3(self):
        valid, result  = self.llm_util.validate_item_response(json.loads(self.actual_response_3), 'Norhardt', 'Arto', 'map')
        assert(valid)
        assert(result)
        
    def test_validate_sentiment(self):
        sentiment = self.llm_util.validate_sentiment(json.loads(self.test_text_valid))
        assert(sentiment == 'cheerful')

    def test_validate_location(self):
        location = Location(name='Outside')
        location.built = False
        locations = self.llm_util.validate_location(json.loads(self.generated_location), location_to_build=location, exit_location_name='Entrance')
        assert(location.description.startswith('A barren wasteland'))
        assert(len(location.exits) == 2)
        assert(location.exits['north pass'])
        assert(location.exits['south peak'])
        assert(len(location.items) == 1) # woolly gloves
        assert(len(locations) == 2)
        assert(locations[0].name == 'north pass')
        assert(locations[1].name == 'south peak')

    def test_evoke(self):
        evoke_string = 'test response'
        self.llm_util.io_util = FakeIoUtil(response=evoke_string)
        self.llm_util.set_story(self.story)
        result = self.llm_util.evoke(message='test evoke', player_io=None)
        assert(result)
        assert(self.llm_util._look_hashes[hash('test evoke')] == evoke_string)

    def test_generate_character(self):
        character_string = json.dumps(parse_utils.load_json('tests/files/test_character.json'))
        self.llm_util.io_util = FakeIoUtil(response=character_string)
        result = self.llm_util.generate_character()
        assert(result)

    def test_build_location(self):
        location = Location(name='Outside')
        exit_location_name = 'Cave entrance'
        self.llm_util.set_story(self.story)
        self.llm_util.io_util = FakeIoUtil(response=self.generated_location)
        locations = self.llm_util.build_location(location, exit_location_name)
        assert(len(locations) == 2)
