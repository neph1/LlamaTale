
import cmd
import pytest
import tale
from tale import wearable
from tale.base import Item, Location, ParseResult, Wearable
from tale.cmds import normal
from tale.errors import ParseError
from tale.llm.LivingNpc import LivingNpc
from tale.llm.llm_ext import DynamicStory
from tale.llm.llm_utils import LlmUtil
from tale.player import Player
from tale.story import StoryConfig
from tests.supportstuff import FakeDriver, FakeIoUtil


class TestExamineCommand():
    
    context = tale.mud_context
    context.config = StoryConfig()
    
    io_util = FakeIoUtil(response=[])
    io_util.stream = False
    llm_util = LlmUtil(io_util)
    story = DynamicStory()
    llm_util.set_story(story)

    def setup_method(self):
        tale.mud_context.driver = FakeDriver()
        tale.mud_context.driver.story = DynamicStory()
        tale.mud_context.driver.llm_util = self.llm_util
        self.test_player = Player('player', 'f')
        self.location = Location('test_location')
        self.location.insert(self.test_player, actor=None)

    def test_examine_nothing(self):
        parse_result = ParseResult(verb='examine', unparsed='')

        with pytest.raises(ParseError, match="Examine what or who?"):
            normal.do_examine(self.test_player, parse_result, self.context)

    def test_examine_living(self):
        npc = LivingNpc('test', 'f', age=30)
        self.io_util.set_response('test examined')
        parse_result = ParseResult(verb='examine', args=['test'])
        self.location.insert(npc, actor=None)
        result = normal.do_examine(self.test_player, parse_result, self.context)
        assert result == True

    def test_examine_living_what(self):
        npc = LivingNpc('test', 'f', age=30)
        self.io_util.set_response('test test2 examined')
        parse_result = ParseResult(verb='examine', args=['test', 'test2'])
        self.location.insert(npc, actor=None)
        result = normal.do_examine(self.test_player, parse_result, self.context)
        assert result == True

    def test_examine_item(self):
        item = Item('test_item', descr='test item description')
        self.io_util.set_response('test examined')
        parse_result = ParseResult(verb='examine', args=['test_item'])
        self.location.insert(item, actor=None)
        result = normal.do_examine(self.test_player, parse_result, self.context)
        assert result == True

    def test_examine_item_what(self):
        item = Item('test_item', descr='test item description')
        self.io_util.set_response('test examined')
        parse_result = ParseResult(verb='examine', args=['test_item', 'what'])
        self.location.insert(item, actor=None)
        result = normal.do_examine(self.test_player, parse_result, self.context)
        assert result == True

    def test_wear(self):
        item = Wearable('test dress', descr='a fancy test dress')
        item2 = Wearable('test boots', descr='a fancy test boots')
        self.io_util.set_response('test_dress worn')
        parse_result = ParseResult(verb='wear', args=['test dress'])
        self.test_player.insert(item, actor=None)
        self.test_player.insert(item2, actor=None)
        normal.do_wear(self.test_player, parse_result, self.context)
        assert item in self.test_player.get_worn_items()

        parse_result = ParseResult(verb='remove', args=['torso'])
        normal.do_remove(self.test_player, parse_result, self.context)
        assert not item in self.test_player.get_worn_items()

        parse_result = ParseResult(verb='wear', args=['test boots'])
        normal.do_wear(self.test_player, parse_result, self.context)
        assert item2 in self.test_player.get_worn_items()

        parse_result = ParseResult(verb='remove', args=['test boots'])
        normal.do_remove(self.test_player, parse_result, self.context)
        assert not item2 in self.test_player.get_worn_items()

    def test_wear_part(self):
        item = Wearable('test hat', descr='a fancy test hat')
        self.io_util.set_response('test_hat worn')
        parse_result = ParseResult(verb='wear', args=['test hat', 'head'])
        self.test_player.insert(item, actor=None)
        normal.do_wear(self.test_player, parse_result, self.context)
        assert item in self.test_player.get_worn_items()
