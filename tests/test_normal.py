
import cmd
import pytest
import tale
from tale.base import Item, Location, ParseResult
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
    test_player = Player('player', 'f')
    location = Location('test_location')
    location.insert(test_player, actor=None)
    io_util = FakeIoUtil(response=[])
    llm_util = LlmUtil(io_util)
    story = DynamicStory()
    llm_util.set_story(story)

    context.driver = FakeDriver()
    context.driver.llm_util = llm_util
    context.driver.story = story

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

        