import pytest
import json
from tale.base import Item
from tale.llm_utils import LlmUtil

class TestLlmUtils():

    llm_util = LlmUtil()

    test_text_valid = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"bartender", "to":"user"}}'

    test_text_valid_no_to = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"bartender", "to":""}}'

    test_text_invalid = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"", "from":"bartender", "to":"user"}}'

    test_text_invalid_2 = '{"thoughts": "It seems that an item (the flagon of ale) has been given by the barkeep to the user. The text explicitly states \'the barkeep presents you with a flagon of frothy ale\'. Therefore, the item has been given by the barkeep to the user.", "result": {"item":"ale", "from":"", "to":"user"}}'

    def test_validate_item_response_valid(self):
        items = json.loads('["ale"]')
        valid, result = self.llm_util.validate_item_response(self.test_text_valid, 'bartender', 'user', items)
        assert(valid)
        assert(result["from"] and result["to"] and result["item"])

    def test_validate_item_response_valid_no_to(self):
        items = json.loads('["ale"]')
        valid, result = self.llm_util.validate_item_response(self.test_text_valid_no_to, 'bartender', 'user', items)
        assert(valid)
        assert(result["from"] and result["item"] and not result["to"] )


    def test_validate_item_response_no_item(self):
        items = json.loads('["ale"]')
        valid, result  = self.llm_util.validate_item_response(self.test_text_invalid, 'bartender', 'user', items)
        assert(not valid)
        assert(not result)

    def test_validate_item_response_no_from(self):
        items = json.loads('["ale"]')
        valid, result = self.llm_util.validate_item_response(self.test_text_invalid_2, 'bartender', 'user', items)
        assert(not valid)
        assert(not result)

    def test_validate_item_response_invalid_item(self):
        items = json.loads('["water"]')
        valid, result = self.llm_util.validate_item_response(self.test_text_valid, 'bartender', 'user', items)
        assert(not valid)
