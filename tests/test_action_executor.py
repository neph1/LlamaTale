import types

from tale import mud_context
from tale.base import Exit, Item, Location, Wearable, Weapon
from tale.llm.LivingNpc import LivingNpc
from tale.llm.dynamic_story import DynamicStory
from tale.skills.skills import SkillType
from tale.wearable import WearLocation
from tests.supportstuff import MsgTraceNPC


def make_action(**kwargs):
    defaults = dict(goal='', thoughts='', action='', target='', text='', item='')
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


class EdibleItem(Item):
    def __init__(self, name, short_descr, descr=''):
        super().__init__(name, short_descr, descr=descr)
        self.consumed_by = None

    def consume(self, actor):
        self.consumed_by = actor


class TestActionExecutor():

    def setup_method(self):
        mud_context.config = DynamicStory().config
        self.location = Location("test_room")
        self.npc = LivingNpc(name='test', gender='m', age=42, personality='')
        self.trace = MsgTraceNPC("fritz", "m", race="human")
        self.location.init_inventory([self.npc, self.trace])

    def test_execute_sets_goal(self):
        result = self.npc.action_executor.execute(make_action(goal='be merry'))
        assert self.npc.goal == 'be merry'
        assert result == []

    def test_thoughts_output_when_enabled(self):
        self.npc.output_thoughts = True
        self.npc.action_executor.execute(make_action(thoughts='hmm, interesting'))
        assert any('thinks:' in m and 'hmm, interesting' in m for m in self.trace.messages)

    def test_thoughts_not_output_when_disabled(self):
        self.npc.action_executor.execute(make_action(thoughts='secret'))
        assert not any('secret' in m for m in self.trace.messages)

    def test_say_text_is_deferred_quoted(self):
        result = self.npc.action_executor.execute(make_action(action='say', text='hello there'))
        assert result == ['"hello there"']
        assert 'test says: "hello there"' in self.npc.memory.observed_events()

    def test_say_to_target_tells_target_directly(self):
        target = MsgTraceNPC("actor", "f", race="human")
        self.location.insert(target)
        result = self.npc.action_executor.execute(make_action(action='say', target='actor', text='hi actor'))
        assert result == []
        assert 'hi actor' in target.messages

    def test_emote_is_unquoted_narration(self):
        result = self.npc.action_executor.execute(make_action(action='emote', text='waves happily'))
        assert result == ['test waves happily']

    def test_move_by_exit_name(self):
        location2 = Location("room 2")
        Exit.connect(self.location, 'north', '', None, location2, 'south', '', None)
        self.npc.action_executor.execute(make_action(action='move', target='north'))
        assert self.npc.location == location2

    def test_move_by_target_location_name_fallback(self):
        location2 = Location("room 2")
        Exit.connect(self.location, 'north', '', None, location2, 'south', '', None)
        # the LLM named the destination location, not the exit direction
        self.npc.action_executor.execute(make_action(action='move', target='room 2'))
        assert self.npc.location == location2

    def test_move_unknown_target_stays(self):
        self.npc.action_executor.execute(make_action(action='move', target='nowhere'))
        assert self.npc.location == self.location

    def test_take(self):
        item = Item(name="test item", short_descr="test item", descr="A test item.")
        self.location.insert(item)
        result = self.npc.action_executor.execute(make_action(action='take', item='test item'))
        assert result == ['test takes test item']
        assert self.npc.search_item('test item', include_location=False) == item

    def test_wield(self):
        sword = Weapon("sword", "sword", descr="Sharp.")
        self.npc.init_inventory([sword])
        result = self.npc.action_executor.execute(make_action(action='wield', item='sword'))
        assert result == ['test wields sword']
        assert self.npc.wielding == sword

    def test_wield_non_weapon_fails_silently(self):
        apple = Item("apple", "apple", descr="Tasty.")
        self.npc.init_inventory([apple])
        result = self.npc.action_executor.execute(make_action(action='wield', item='apple'))
        assert result == []
        assert self.npc.wielding == self.npc.stats.unarmed_attack

    def test_wear_and_remove(self):
        hat = Wearable("hat", wear_location=WearLocation.HEAD, short_descr="hat", descr="A big hat.")
        self.location.insert(hat)  # wearable picks up items from the location
        result = self.npc.action_executor.execute(make_action(action='wear', item='hat'))
        assert result == ['test wears hat']
        assert self.npc.get_wearable(WearLocation.HEAD) == hat

        result = self.npc.action_executor.execute(make_action(action='remove', item='hat'))
        assert result == ['test removes hat']
        assert self.npc.get_wearable(WearLocation.HEAD) is None

    def test_eat_consumable(self):
        apple = EdibleItem("apple", "apple", descr="Tasty.")
        self.npc.init_inventory([apple])
        result = self.npc.action_executor.execute(make_action(action='eat', item='apple'))
        assert result == ['test eats apple']
        assert apple.consumed_by == self.npc

    def test_eat_non_consumable_fails_silently(self):
        rock = Item("rock", "rock", descr="Inedible.")
        self.npc.init_inventory([rock])
        result = self.npc.action_executor.execute(make_action(action='eat', item='rock'))
        assert result == []

    def test_hide_unhide(self):
        self.location.remove(self.trace, self.trace)  # can't hide with others around
        self.npc.stats.skills.set(SkillType.HIDE, 100)
        self.npc.stats.action_points = 2
        self.npc.action_executor.execute(make_action(action='hide'))
        assert self.npc.hidden
        self.npc.action_executor.execute(make_action(action='unhide'))
        assert not self.npc.hidden

    def test_unknown_action_falls_back_to_narration(self):
        result = self.npc.action_executor.execute(make_action(action='dance'))
        assert result == ['test dance']

    def test_no_action_returns_text_only(self):
        result = self.npc.action_executor.execute(make_action(text='just talking'))
        assert result == ['"just talking"']

    def test_living_npc_parse_action_delegates(self):
        # story_manager calls npc._parse_action directly
        self.location.remove(self.trace, self.trace)
        self.npc.stats.skills.set(SkillType.HIDE, 100)
        self.npc.stats.action_points = 1
        result = self.npc._parse_action(make_action(action='hide'))
        assert self.npc.hidden
        assert result == []
