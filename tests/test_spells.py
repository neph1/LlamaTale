

import pytest
from tale import magic
import tale
from tale.base import Location, ParseResult
from tale.cmds import spells
from tale.errors import ActionRefused
from tale.llm.LivingNpc import LivingNpc
from tale.llm.llm_ext import DynamicStory
from tale.llm.llm_utils import LlmUtil
from tale.magic import MagicSkill, MagicType
from tale.player import Player
from tale.story import StoryConfig
from tests.supportstuff import FakeDriver, FakeIoUtil


class TestSpells:

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
        self.player.stats.magic_skills[MagicType.HEAL] = MagicSkill(magic.spells[MagicType.HEAL], 100)
        npc = LivingNpc('test', 'f', age=30)
        npc.stats.hp = 0
        self.player.location.insert(npc, actor=None)
        self.player.stats.magic_points = 10
        parse_result = ParseResult(verb='heal', args=['test'])
        result = spells.do_heal(self.player, parse_result, None)
        assert self.player.stats.magic_points == 8
        assert npc.stats.hp == 5

    def test_heal_fail(self):
        self.player.stats.magic_skills[MagicType.HEAL] = MagicSkill(magic.spells[MagicType.HEAL], 0)
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
        with pytest.raises(ActionRefused, match="You don't know how to heal"):
            spells.do_heal(self.player, parse_result, None)
        
        self.player.stats.magic_skills[MagicType.HEAL] = MagicSkill(MagicType.HEAL, 10)
        self.player.stats.magic_points = 0

        npc = LivingNpc('test', 'f', age=30)
        npc.stats.hp = 0
        self.player.location.insert(npc, actor=None)

        with pytest.raises(ActionRefused, match="You don't have enough magic points"):
            spells.do_heal(self.player, parse_result, None)
