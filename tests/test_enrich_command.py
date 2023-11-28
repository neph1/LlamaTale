


import pytest
import tale
from tale.base import ParseResult
from tale.cmds import wizard, wizcmd
from tale.errors import ParseError
from tale.llm.llm_ext import DynamicStory
from tale.llm.llm_utils import LlmUtil
from tale.player import Player
from tale.story import StoryConfig
from tests.supportstuff import FakeDriver, FakeIoUtil


class TestEnrichCommand():
    
    tale.mud_context.config = StoryConfig()
    llm_util = LlmUtil(FakeIoUtil(response=['{"items":[{"name":"Enchanted Petals", "type":"Health", "value": 20, "description": "A handful of enchanted petals that can be used to heal wounds and cure ailments."}]}', 
                                            {"creatures": [   {   "name": "Whimsy Woozle",   "description": "A gentle, ethereal creature with a penchant for gardening and poetry. They tend to the area\'s lush fields and forests, filling the air with sweet melodies and the scent of blooming wildflowers. They are friendly and welcoming to all visitors.",   "level": 1   },   {   "name": "Lunar Lopster",   "description": "A mysterious crustacean with an affinity for the moon\'s gentle light. They roam the area at night, their glowing shells lighting the way through the darkness. They are neutral towards visitors, but may offer cryptic advice or guidance to those who seek it.",   "level": 2   },   {   "name": "Shadow Stag",   "description": "A sleek and elusive creature with a mischievous grin. They roam the area\'s forests, their dark forms blending into the shadows. They are hostile towards intruders, and will not hesitate to attack those who threaten their home.",   "level": 3   },   {   "name": "Moonflower",   "description": "A rare and beautiful flower that blooms only under the light of the full moon. They can be found in the area\'s forests, and are said to have powerful healing properties. They are very friendly towards visitors, and will offer their petals to those who show kindness and respect.",   "level": 4   },   {   "name": "Moonstone",   "description": "A rare and valuable mineral that can be found in the area\'s mountains. It glows with a soft, ethereal light, and is said to have powerful magical properties. It is highly sought after by collectors, and can be found in both the earth and the water.",   "level": 5   }]}]))
    story = DynamicStory()
    llm_util.set_story(story)

    test_player = Player('test', 'f')
    test_player.privileges.add('wizard')

    tale.mud_context.driver = FakeDriver()
    tale.mud_context.driver.llm_util = llm_util
    tale.mud_context.driver.story = story

    def test_enrich_no_variable(self):
        parse_result = ParseResult(verb='enrich', unparsed='')
        with pytest.raises(ParseError, match="You need to define 'items' or 'creatures'."):
            wizard.do_enrich(self.test_player, parse_result, tale.mud_context)
    
        assert(len(self.story._catalogue._items) == 0)

    def test_enrich_items(self):
        
        parse_result = ParseResult(verb='enrich items', args=['items'])
        wizard.do_enrich(self.test_player, parse_result, tale.mud_context)

        assert(len(self.story._catalogue._items) == 1)

    def test_enrich_creatures(self):
        parse_result = ParseResult(verb='enrich creatures', args=['creatures'])
        wizard.do_enrich(self.test_player, parse_result, tale.mud_context)

        assert(len(self.story._catalogue._creatures) == 5)