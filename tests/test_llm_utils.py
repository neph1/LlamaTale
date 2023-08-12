import pytest
import json
from tale.base import Item
from tale.llm_utils import LlmUtil
import tale.parse_utils as parse_utils

class TestLlmUtils():

    llm_util = LlmUtil()

    test_text_valid = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"bartender", "to":"user"}, "sentiment":"cheerful"}'

    test_text_valid_no_to = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"bartender", "to":""}}'

    test_text_invalid = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"", "from":"bartender", "to":"user"}}'

    test_text_invalid_2 = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"", "to":"user"}}'

    actual_response_empty_result = '{   "thoughts": "No items were given, taken, dropped or put.",  "results": {}  }\n'

    actual_response_3 = '{\n    "thoughts": "\ud83d\ude0d Norhardt feels that he is close to finding something important after a long and dangerous journey through rough terrain and harsh weather, and it consumes him fully.",\n    "result": {\n        "item": "map",\n        "from": "Norhardt",\t\n        "to": "Arto"\n    }\n}'

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
