
import cmd
import pytest
import tale
from tale import wearable
from tale.base import Item, Location, ParseResult, Weapon, Wearable
from tale.cmds import normal
from tale.errors import ActionRefused, ParseError
from tale.llm.LivingNpc import LivingNpc
from tale.llm.llm_ext import DynamicStory
from tale.llm.llm_utils import LlmUtil
from tale.player import Player
from tale.skills.skills import SkillType
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

    def test_wear_wrong_args(self):
        parse_result = ParseResult(verb='wear', args=[])
        with pytest.raises(ParseError, match="You need to specify the item to wear"):
            normal.do_wear(self.test_player, parse_result, self.context)

        parse_result = ParseResult(verb='wear', args=['fancy gloves'])
        with pytest.raises(ActionRefused, match="You don't have that item"):
            normal.do_wear(self.test_player, parse_result, self.context)

        parse_result = ParseResult(verb='wear', args=['fancy gloves', 'upper arm'])
        with pytest.raises(ActionRefused, match="Invalid location"):
            normal.do_wear(self.test_player, parse_result, self.context)

    def test_wear_part(self):
        item = Wearable('test hat', descr='a fancy test hat')
        self.io_util.set_response('test_hat worn')
        parse_result = ParseResult(verb='wear', args=['test hat', 'head'])
        self.test_player.insert(item, actor=None)
        normal.do_wear(self.test_player, parse_result, self.context)
        assert item in self.test_player.get_worn_items()

    def test_wield(self):
        item = Weapon('test sword', descr='a fancy test sword')
        self.io_util.set_response('test_sword wielded')
        parse_result = ParseResult(verb='wield', args=['test sword'])
        self.test_player.insert(item, actor=None)
        normal.do_wield(self.test_player, parse_result, self.context)
        assert self.test_player.wielding == item

        parse_result = ParseResult(verb='unwield', args=['test sword'])
        normal.do_unwield(self.test_player, parse_result, self.context)
        assert self.test_player.wielding != item

    def test_request_follow(self):
        self.io_util.set_response('{"response":"no"')
        test_npc = LivingNpc('test_npc', 'f')
        location = Location('test_room')
        location.init_inventory([self.test_player, test_npc])
        normal.do_request_follow(self.test_player, ParseResult(verb='request_follow', args=['test_npc', 'to infinity, and beyond']), self.context)
        assert test_npc.notify_action

    def test_unfollow(self):
        test_npc = LivingNpc('test_npc', 'f')
        test_npc.following = self.test_player
        location = Location('test_room')
        location.init_inventory([self.test_player, test_npc])
        normal.do_unfollow(self.test_player, ParseResult(verb='unfollow', args=['test_npc']), self.context)
        assert not test_npc.following

    def test_hide(self):
        self.test_player.stats.skills[SkillType.HIDE] = 100
        self.test_player.stats.action_points = 1
        normal.do_hide(self.test_player, ParseResult(verb='hide', args=[]), self.context)
        assert self.test_player.hidden
        
        with pytest.raises(ActionRefused, match="You're already hidden. If you want to reveal yourself, use 'unhide'."):
            normal.do_hide(self.test_player, ParseResult(verb='hide', args=[]), self.context)

        self.test_player.hidden = False

        with pytest.raises(ActionRefused, match="You don't have enough action points to hide."):
            normal.do_hide(self.test_player, ParseResult(verb='hide', args=[]), self.context)

        self.test_player.hidden = False

        self.test_player.stats.skills[SkillType.HIDE] = 0
        self.test_player.stats.action_points = 1
        normal.do_hide(self.test_player, ParseResult(verb='hide', args=[]), self.context)
        assert not self.test_player.hidden

    def test_unhide(self):
        self.test_player.hidden = True
        normal.do_unhide(self.test_player, ParseResult(verb='unhide', args=[]), self.context)
        assert not self.test_player.hidden

        with pytest.raises(ActionRefused, match="You're not hidden."):
            normal.do_unhide(self.test_player, ParseResult(verb='unhide', args=[]), self.context)

    def test_search_hidden(self):

        test_npc = LivingNpc('test_npc', 'f')
        test_npc.hidden = True
        test_npc.stats.skills[SkillType.HIDE] = 100
        location = Location('test_room')
        location.init_inventory([self.test_player, test_npc])

        self.test_player.stats.skills[SkillType.SEARCH] = 0
        self.test_player.stats.action_points = 1

        normal.do_search_hidden(self.test_player, ParseResult(verb='search', args=[]), self.context)

        assert test_npc.hidden

        self.test_player.stats.skills[SkillType.SEARCH] = 100
        test_npc.stats.skills[SkillType.HIDE] = 0
        self.test_player.stats.action_points = 1

        normal.do_search_hidden(self.test_player, ParseResult(verb='search', args=[]), self.context)

        assert not test_npc.hidden