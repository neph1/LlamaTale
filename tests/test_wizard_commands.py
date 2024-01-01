


import pytest
import tale
from tale.base import Location, ParseResult
from tale.cmds import wizard, wizcmd
from tale.errors import ParseError
from tale.llm.LivingNpc import LivingNpc
from tale.llm.llm_ext import DynamicStory
from tale.llm.llm_utils import LlmUtil
from tale.player import Player
from tale.story import StoryConfig
from tale.wearable import WearLocation
from tests.supportstuff import FakeDriver, FakeIoUtil


class TestEnrichCommand():
    
    context = tale._MudContext()
    context.config = StoryConfig()
    io_util = FakeIoUtil(response=['{"items":[{"name":"Enchanted Petals", "type":"Health", "value": 20, "description": "A handful of enchanted petals that can be used to heal wounds and cure ailments."}]}',
                                   '{"creatures": [   {   "name": "Whimsy Woozle",   "description": "A gentle, ethereal creature with a penchant for gardening and poetry. They tend to the area\'s lush fields and forests, filling the air with sweet melodies and the scent of blooming wildflowers. They are friendly and welcoming to all visitors.",   "level": 1   },   {   "name": "Lunar Lopster",   "description": "A mysterious crustacean with an affinity for the moon\'s gentle light. They roam the area at night, their glowing shells lighting the way through the darkness. They are neutral towards visitors, but may offer cryptic advice or guidance to those who seek it.",   "level": 2   },   {   "name": "Shadow Stag",   "description": "A sleek and elusive creature with a mischievous grin. They roam the area\'s forests, their dark forms blending into the shadows. They are hostile towards intruders, and will not hesitate to attack those who threaten their home.",   "level": 3   },   {   "name": "Moonflower",   "description": "A rare and beautiful flower that blooms only under the light of the full moon. They can be found in the area\'s forests, and are said to have powerful healing properties. They are very friendly towards visitors, and will offer their petals to those who show kindness and respect.",   "level": 4   },   {   "name": "Moonstone",   "description": "A rare and valuable mineral that can be found in the area\'s mountains. It glows with a soft, ethereal light, and is said to have powerful magical properties. It is highly sought after by collectors, and can be found in both the earth and the water.",   "level": 5   }]}'])
    llm_util = LlmUtil(io_util)
    story = DynamicStory()
    llm_util.set_story(story)

    test_player = Player('test', 'f')
    test_player.privileges.add('wizard')

    context.driver = FakeDriver()
    context.driver.llm_util = llm_util
    context.driver.story = story

    def test_enrich_no_variable(self):
        parse_result = ParseResult(verb='enrich', unparsed='')
        with pytest.raises(ParseError, match="You need to define 'items' or 'creatures'."):
            wizard.do_enrich(self.test_player, parse_result, self.context)
    
        assert(len(self.story._catalogue._items) == 0)

    def test_enrich_items(self):
        self.context.driver.llm_util.io_util.set_response('{"items":[{"name":"Enchanted Petals", "type":"Health", "value": 20, "description": "A handful of enchanted petals that can be used to heal wounds and cure ailments."}]}')
        parse_result = ParseResult(verb='enrich items', args=['items'])
        wizard.do_enrich(self.test_player, parse_result, self.context)

        assert(len(self.story._catalogue._items) == 1)

    def test_enrich_creatures(self):
        self.context.driver.llm_util.io_util.set_response('{"creatures": [   {   "name": "Whimsy Woozle",   "description": "A gentle, ethereal creature with a penchant for gardening and poetry. They tend to the area\'s lush fields and forests, filling the air with sweet melodies and the scent of blooming wildflowers. They are friendly and welcoming to all visitors.",   "level": 1   },   {   "name": "Lunar Lopster",   "description": "A mysterious crustacean with an affinity for the moon\'s gentle light. They roam the area at night, their glowing shells lighting the way through the darkness. They are neutral towards visitors, but may offer cryptic advice or guidance to those who seek it.",   "level": 2   },   {   "name": "Shadow Stag",   "description": "A sleek and elusive creature with a mischievous grin. They roam the area\'s forests, their dark forms blending into the shadows. They are hostile towards intruders, and will not hesitate to attack those who threaten their home.",   "level": 3   },   {   "name": "Moonflower",   "description": "A rare and beautiful flower that blooms only under the light of the full moon. They can be found in the area\'s forests, and are said to have powerful healing properties. They are very friendly towards visitors, and will offer their petals to those who show kindness and respect.",   "level": 4   },   {   "name": "Moonstone",   "description": "A rare and valuable mineral that can be found in the area\'s mountains. It glows with a soft, ethereal light, and is said to have powerful magical properties. It is highly sought after by collectors, and can be found in both the earth and the water.",   "level": 5   }]}')
        parse_result = ParseResult(verb='enrich creatures', args=['creatures'])
        wizard.do_enrich(self.test_player, parse_result, self.context)

        assert(len(self.story._catalogue._creatures) == 5)

    def test_load_character_from_data(self):
        parse_result = ParseResult(
            verb='load_character_from_data',
            unparsed='{"description": "test description", "appearance": "test appearance", "aliases":[], "age": "99", "race":"human", "occupation":"test occupation", "extensions": {}, "name": "test name", "personality": "test personality ", "scenario": "", "system_prompt": "", "wearing":"test clothes", "tags": []}')
        npc = wizard.do_load_character_from_data(self.test_player, parse_result, self.context) # type: LivingNpc
        assert(npc.name == 'test')
        assert(npc.description == 'test appearance')
        assert(npc.short_description == 'test appearance')
        assert(npc.occupation == 'test occupation')
        assert(npc.personality == 'test personality ')
        assert(npc.age == 99)
        assert(npc.get_wearable(WearLocation.TORSO) is not None)

    def test_set_visible(self):
        location = Location('test')
        player = Player('test', 'f')
        player.privileges.add('wizard')
        location.init_inventory([player])
        parse_result = ParseResult(verb='set_visible', args=['test', 'False'])
        wizard.do_set_visible(player, parse_result, self.context)
        assert(player.visible == False)

class TestEvents():

    test_player = Player('test', 'f')
    test_player.privileges.add('wizard')
    

    def test_add_event_no_parse(self):
        parse_result = ParseResult(verb='add_event', args=[])
        with pytest.raises(ParseError, match="You need to define an event"):
            wizard.do_add_event(self.test_player, parse_result, tale._MudContext())

    def test_add_event(self):
        context = tale.mud_context
        context.config = StoryConfig()
        io_util = FakeIoUtil(response='')
        llm_util = LlmUtil(io_util)
        story = DynamicStory()
        llm_util.set_story(story)
        context.driver = FakeDriver()
        context.driver.story = story
        context.driver.llm_util = llm_util
        event_string = 'a foreboding storm approaches'
        test_location = Location('test_location')
        story.add_location(test_location)
        test_npc = LivingNpc('test_npc', 'f', age=30)
        test_location.insert(test_npc, actor=None)
        test_location.insert(self.test_player, actor=None)
        parse_result = ParseResult(verb='add_event', args=[event_string], unparsed=event_string)
        wizard.do_add_event(self.test_player, parse_result, context)
        dumped = tale.llm.llm_cache.json_dump()
        events = dumped['events'].values()
        for event in events:
            if event == event_string:
                assert(True)
                return
        assert(False)