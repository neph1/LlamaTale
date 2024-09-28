import pytest
import tale
from tale.base import Location, ParseResult
from tale.cmds import spells
from tale.errors import ActionRefused
from tale.llm.LivingNpc import LivingNpc
from tale.llm.llm_ext import DynamicStory
from tale.llm.llm_utils import LlmUtil
from tale.skills.magic import MagicType
from tale.player import Player
from tale.story import StoryConfig
from tests.supportstuff import FakeDriver, FakeIoUtil


class TestHeal:

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
        self.player = Player('player', 'f')
        self.location = Location('test_location')
        self.location.insert(self.player, actor=None)

    def test_heal(self):
        self.player.stats.magic_skills.set(MagicType.HEAL, 100)
        npc = LivingNpc('test', 'f', age=30)
        npc.stats.hp = 0
        self.player.location.insert(npc, actor=None)
        self.player.stats.magic_points = 10
        parse_result = ParseResult(verb='heal', args=['test'])
        result = spells.do_heal(self.player, parse_result, None)
        assert self.player.stats.magic_points == 8
        assert npc.stats.hp == 5

    def test_heal_fail(self):
        self.player.stats.magic_skills.set(MagicType.HEAL, -1)
        npc = LivingNpc('test', 'f', age=30)
        npc.stats.hp = 0
        self.player.location.insert(npc, actor=None)
        self.player.stats.magic_points = 10
        parse_result = ParseResult(verb='heal', args=['test'])
        result = spells.do_heal(self.player, parse_result, None)
        assert self.player.stats.magic_points == 8
        assert npc.stats.hp == 0

    def test_heal_refused(self):
        parse_result = ParseResult(verb='heal', args=['test'])
        with pytest.raises(ActionRefused, match="Can't target that"):
            spells.do_heal(self.player, parse_result, None)

        npc = LivingNpc('test', 'f', age=30)
        npc.stats.hp = 0
        self.player.location.insert(npc, actor=None)
        with pytest.raises(ActionRefused, match="You don't know how to heal"):
            spells.do_heal(self.player, parse_result, None)

        self.player.stats.magic_skills.set(MagicType.HEAL, 10)
        self.player.stats.magic_points = 0

        with pytest.raises(ActionRefused, match="You don't have enough magic points"):
            spells.do_heal(self.player, parse_result, None)


class TestBolt:

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
        self.player = Player('player', 'f')
        self.location = Location('test_location')
        self.location.insert(self.player, actor=None)

    def test_bolt(self):
        self.player.stats.magic_skills.set(MagicType.BOLT, 100)
        npc = LivingNpc('test', 'f', age=30)
        npc.stats.hp = 5
        self.player.location.insert(npc, actor=None)
        self.player.stats.magic_points = 10
        parse_result = ParseResult(verb='bolt', args=['test'])
        result = spells.do_bolt(self.player, parse_result, None)
        assert self.player.stats.magic_points == 7
        assert npc.stats.hp < 5

class TestDrain:

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
        self.player = Player('player', 'f')
        self.location = Location('test_location')
        self.location.insert(self.player, actor=None)

    def test_drain(self):
        self.player.stats.magic_skills.set(MagicType.DRAIN, 100)
        npc = LivingNpc('test', 'f', age=30)
        npc.stats.action_points = 5
        npc.stats.magic_points = 5
        self.player.location.insert(npc, actor=None)
        self.player.stats.magic_points = 10
        parse_result = ParseResult(verb='drain', args=['test'])
        result = spells.do_drain(self.player, parse_result, None)
        assert self.player.stats.magic_points > 7
        assert npc.stats.action_points < 5
        assert npc.stats.magic_points < 5

class TestRejuvenate:

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
        self.player = Player('player', 'f')
        self.location = Location('test_location')
        self.location.insert(self.player, actor=None)

    def test_rejuvenate(self):
        self.player.stats.magic_skills.set(MagicType.REJUVENATE, 100)
        npc = LivingNpc('test', 'f', age=30)
        npc.stats.hp = 0
        self.player.location.insert(npc, actor=None)
        self.player.stats.magic_points = 10
        parse_result = ParseResult(verb='rejuvenate', args=['test'])
        result = spells.do_rejuvenate(self.player, parse_result, None)
        assert self.player.stats.magic_points == 8
        assert npc.stats.hp == 5

    def test_rejuvenate_fail(self):
        self.player.stats.magic_skills.set(MagicType.REJUVENATE, -1)
        npc = LivingNpc('test', 'f', age=30)
        npc.stats.hp = 0
        self.player.location.insert(npc, actor=None)
        self.player.stats.magic_points = 10
        parse_result = ParseResult(verb='heal', args=['test'])
        result = spells.do_rejuvenate(self.player, parse_result, None)
        assert self.player.stats.magic_points == 8
        assert npc.stats.hp == 0

    def test_rejuvenate_refused(self):
        parse_result = ParseResult(verb='heal', args=['test'])

        with pytest.raises(ActionRefused, match="Can't target that"):
            spells.do_hide(self.player, parse_result, None)

        npc = LivingNpc('test', 'f', age=30)
        npc.stats.hp = 0
        self.player.location.insert(npc, actor=None)

        with pytest.raises(ActionRefused, match="You don't know how to rejuvenate"):
            spells.do_rejuvenate(self.player, parse_result, None)

        self.player.stats.magic_skills.set(MagicType.REJUVENATE, 10)
        self.player.stats.magic_points = 0

        with pytest.raises(ActionRefused, match="You don't have enough magic points"):
            spells.do_rejuvenate(self.player, parse_result, None)

class TestHide:

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
        self.player = Player('player', 'f')
        self.location = Location('test_location')
        self.location.insert(self.player, actor=None)

    def test_hide(self):
        self.player.stats.magic_skills.set(MagicType.HIDE, 100)
        self.player.stats.magic_points = 10
        parse_result = ParseResult(verb='hide', args=['self'])
        result = spells.do_hide(self.player, parse_result, None)
        assert self.player.stats.magic_points == 7
        assert self.player.hidden == True

    def test_hide_fail(self):
        self.player.stats.magic_skills.set(MagicType.HIDE, -1)
        self.player.stats.magic_points = 10
        parse_result = ParseResult(verb='hide', args=['self'])
        result = spells.do_hide(self.player, parse_result, None)
        assert self.player.stats.magic_points == 7

    def test_hide_refused(self):
        parse_result = ParseResult(verb='hide', args=['test'])

        self.player.stats.magic_points = 10

        with pytest.raises(ActionRefused, match="Can't target that"):
            spells.do_hide(self.player, parse_result, None)

        npc = LivingNpc('test', 'f', age=30)
        npc.stats.hp = 0
        self.player.location.insert(npc, actor=None)

        with pytest.raises(ActionRefused, match="You don't know the 'hide' spell."):
            spells.do_hide(self.player, parse_result, None)
        
        self.player.stats.magic_skills.set(MagicType.HIDE, 10)
        self.player.stats.magic_points = 0

        with pytest.raises(ActionRefused, match="You don't have enough magic points"):
            spells.do_hide(self.player, parse_result, None)


class TestReveal:

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
        self.player = Player('player', 'f')
        self.location = Location('test_location')
        self.location.insert(self.player, actor=None)

    def test_reveal(self):
        self.player.stats.magic_skills.set(MagicType.REVEAL, 100)
        npc = LivingNpc('test', 'f', age=30)
        npc.hidden = True
        self.player.location.insert(npc, actor=None)
        self.player.stats.magic_points = 1000
        parse_result = ParseResult(verb='reveal', args=['100'])
        result = spells.do_reveal(self.player, parse_result, None)
        assert self.player.stats.magic_points == 700
        assert npc.hidden == False

    def test_reveal_fail(self):
        self.player.stats.magic_skills.set(MagicType.REVEAL, -1)
        npc = LivingNpc('test', 'f', age=30)
        npc.hidden = True
        self.player.location.insert(npc, actor=None)
        self.player.stats.magic_points = 10
        parse_result = ParseResult(verb='reveal', args=[])
        result = spells.do_reveal(self.player, parse_result, None)
        assert self.player.stats.magic_points == 7
        assert npc.hidden == True

    def test_reveal_refused(self):
        parse_result = ParseResult(verb='reveal', args=[])
        with pytest.raises(ActionRefused, match="You don't know the 'reveal' spell."):
            spells.do_reveal(self.player, parse_result, None)
        
        self.player.stats.magic_skills.set(MagicType.REVEAL, 10)
        self.player.stats.magic_points = 0

        with pytest.raises(ActionRefused, match="You don't have enough magic points"):
            spells.do_reveal(self.player, parse_result, None)