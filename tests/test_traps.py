"""
Unittests for the trap system (tale/traps.py)
"""

import json
import unittest
from unittest import mock

from tale import mud_context, pubsub, traps
from tale.base import Location, Exit, Item, Living, Container, Door, ParseResult
from tale.demo.story import Story as DemoStory
from tale.errors import ActionRefused
from tale.items.basic import Boxlike
from tale.load_items import load_item
from tale.parse_utils import location_from_json
from tale.skills.skills import SkillType, Skills
from tale.traps import Trap, TrapItem, TrapState, TrapTrigger, TrapOutcome
from tests.supportstuff import FakeDriver


class TestTrapBasics(unittest.TestCase):
    def setUp(self):
        mud_context.driver = FakeDriver()
        mud_context.config = DemoStory().config
        mud_context.resources = mud_context.driver.resources
        self.hall = Location("Main hall", "A very large hall.")
        self.attic = Location("Attic", "A dark attic.")
        self.hall.add_exits([Exit("up", self.attic, "A ladder leads up.")])
        self.player = Living("player", "m")
        self.hall.insert(self.player, None)

    def test_new_skills_exist(self):
        skills = Skills()
        self.assertEqual(skills.get(SkillType.DODGE), 0)
        self.assertEqual(skills.get(SkillType.SET_TRAP), 0)
        self.assertEqual(skills.get(SkillType.DISARM_TRAP), 0)

    def test_attach_get_remove(self):
        trap = traps.attach(self.hall, {"level": 3, "trigger": "ENTER", "effect": "DAMAGE"})
        self.assertIsInstance(trap, Trap)
        self.assertEqual(trap.level, 3)
        self.assertEqual(trap.trigger, TrapTrigger.ENTER)
        self.assertEqual(trap.state, TrapState.ARMED)
        # stored as builtins-only dict in story_data, so it survives serialization as-is
        self.assertIsInstance(self.hall.story_data["trap"], dict)
        json.dumps(self.hall.story_data)
        fetched = traps.get(self.hall)
        self.assertEqual(fetched, trap)
        traps.remove(self.hall)
        self.assertIsNone(traps.get(self.hall))

    def test_trap_json_roundtrip(self):
        trap = Trap(level=4, trigger=TrapTrigger.MOVE, effect="RESTRAIN",
                    effect_params={"ticks": 5}, state=TrapState.REVEALED, reset=True,
                    owner="wizard", hidden=False, descr="a snare", llm_hint="humiliate",
                    effect_hint="yanked off feet")
        clone = Trap.from_json(json.loads(json.dumps(trap.to_json())))
        self.assertEqual(clone, trap)

    def test_attach_clamps_level(self):
        trap = traps.attach(self.hall, {"level": 99, "trigger": "ENTER", "effect": "DAMAGE"})
        self.assertEqual(trap.level, 10)
        trap = traps.attach(self.hall, {"level": -3, "trigger": "ENTER", "effect": "DAMAGE"})
        self.assertEqual(trap.level, 1)

    def test_attach_rejects_malformed(self):
        with self.assertRaises(ValueError):
            traps.attach(self.hall, {"level": 2, "trigger": "ENTER", "effect": "EXPLODE"})
        with self.assertRaises(ValueError):
            traps.attach(self.hall, {"level": 2, "trigger": "DANCE", "effect": "DAMAGE"})
        with self.assertRaises(ValueError):
            traps.attach(self.hall, {"level": 2, "trigger": "ENTER", "effect": "SPELL",
                                     "effect_params": {"spell": "FIREBALL"}})
        with self.assertRaises(ValueError):
            traps.attach(self.hall, "not a dict")

    def test_trigger_must_be_valid_for_object(self):
        potion = Item("potion")
        with self.assertRaises(ValueError):  # no ENTER trap on a potion
            traps.attach(potion, {"level": 1, "trigger": "ENTER", "effect": "DAMAGE"})
        traps.attach(potion, {"level": 1, "trigger": "MOVE", "effect": "DAMAGE"})  # ok
        box = Boxlike("chest")
        traps.attach(box, {"level": 1, "trigger": "OPEN", "effect": "ALARM"})  # ok
        with self.assertRaises(ValueError):  # no OPEN trap on a plain location
            traps.attach(self.hall, {"level": 1, "trigger": "OPEN", "effect": "ALARM"})

    def test_band_for_roll(self):
        self.assertEqual(traps.band_for_roll(11), TrapOutcome.ESCAPE)
        self.assertEqual(traps.band_for_roll(10), TrapOutcome.PARTIAL)
        self.assertEqual(traps.band_for_roll(1), TrapOutcome.PARTIAL)
        self.assertEqual(traps.band_for_roll(0), TrapOutcome.FULL)
        self.assertEqual(traps.band_for_roll(-10), TrapOutcome.FULL)
        self.assertEqual(traps.band_for_roll(-11), TrapOutcome.COMPLICATION)

    def test_dodge_roll_follows_spell_idiom(self):
        trap = Trap(level=3, trigger=TrapTrigger.ENTER, effect="DAMAGE")
        self.player.stats.skills.set(SkillType.DODGE, 10)
        with mock.patch("tale.traps.random.randint", return_value=50):
            roll = traps.dodge_roll(self.player, trap)
        self.assertEqual(roll, 50 + 10 - 30)


class TestTrapResolution(unittest.TestCase):
    def setUp(self):
        mud_context.driver = FakeDriver()
        mud_context.config = DemoStory().config
        mud_context.resources = mud_context.driver.resources
        self.hall = Location("Main hall", "A very large hall.")
        self.player = Living("player", "m")
        self.hall.insert(self.player, None)
        self.trap = traps.attach(self.hall, {"level": 2, "trigger": "ENTER", "effect": "DAMAGE"})

    def _resolve_with_roll(self, roll):
        with mock.patch("tale.traps.dodge_roll", return_value=roll):
            return traps.resolve(self.hall, self.player)

    def test_clean_escape_stays_armed(self):
        outcome = self._resolve_with_roll(50)
        self.assertEqual(outcome, TrapOutcome.ESCAPE)
        self.assertEqual(traps.get(self.hall).state, TrapState.ARMED)

    def test_partial_reveals_trap(self):
        outcome = self._resolve_with_roll(5)
        self.assertEqual(outcome, TrapOutcome.PARTIAL)
        self.assertEqual(traps.get(self.hall).state, TrapState.REVEALED)

    def test_full_and_complication_spring_trap(self):
        self.assertEqual(self._resolve_with_roll(-5), TrapOutcome.FULL)
        self.assertEqual(traps.get(self.hall).state, TrapState.SPRUNG)
        # one-shot trap: does not fire again
        self.assertIsNone(traps.resolve(self.hall, self.player))
        # complication band
        traps.attach(self.hall, {"level": 2, "trigger": "ENTER", "effect": "DAMAGE"})
        self.assertEqual(self._resolve_with_roll(-15), TrapOutcome.COMPLICATION)
        self.assertEqual(traps.get(self.hall).state, TrapState.SPRUNG)

    def test_reset_trap_rearms_on_next_trigger(self):
        traps.attach(self.hall, {"level": 2, "trigger": "ENTER", "effect": "DAMAGE", "reset": True})
        self._resolve_with_roll(-5)
        self.assertEqual(traps.get(self.hall).state, TrapState.SPRUNG)
        with mock.patch("tale.traps.dodge_roll", return_value=50):  # clean escape, reset trap re-armed first
            traps.trigger_enter(self.hall, self.player)
        self.assertEqual(traps.get(self.hall).state, TrapState.ARMED)

    def test_owner_never_triggers(self):
        traps.attach(self.hall, {"level": 9, "trigger": "ENTER", "effect": "DAMAGE", "owner": "player"})
        self.assertIsNone(traps.resolve(self.hall, self.player))
        self.assertEqual(traps.get(self.hall).state, TrapState.ARMED)

    def test_damage_effect(self):
        hp_before = self.player.stats.hp
        with mock.patch("tale.traps.dodge_roll", return_value=-5), \
             mock.patch("tale.traps.random.randint", return_value=4):
            traps.resolve(self.hall, self.player)
        self.assertEqual(self.player.stats.hp, hp_before - 4)

    def test_restrain_effect_and_escape(self):
        traps.attach(self.hall, {"level": 2, "trigger": "ENTER", "effect": "RESTRAIN",
                                 "effect_params": {"ticks": 3}})
        with mock.patch("tale.traps.dodge_roll", return_value=-5):
            traps.resolve(self.hall, self.player)
        self.assertEqual(self.player.stats.action_points, 0)
        self.assertIn("restrained", self.player.story_data)
        # failed escape throw keeps the living restrained, successful one breaks free
        with mock.patch("tale.traps.random.randint", return_value=1):  # roll = 1 + 0 - 20 < 1
            traps.tick_restrain(self.player)
        self.assertIn("restrained", self.player.story_data)
        self.assertEqual(self.player.stats.action_points, 0)
        self.player.stats.skills.set(SkillType.DODGE, 100)
        with mock.patch("tale.traps.random.randint", return_value=50):  # roll = 50 + 100 - 20 >= 1
            traps.tick_restrain(self.player)
        self.assertNotIn("restrained", self.player.story_data)

    def test_door_effect_closes_and_locks(self):
        street = Location("Street", "An endless street.")
        d1, d2 = Door.connect(self.hall, "east", "A door to the east.", "", street, "west", "A door to the west.", "",
                              opened=True)
        self.assertTrue(d1.opened)
        traps.attach(self.hall, {"level": 2, "trigger": "ENTER", "effect": "DOOR",
                                 "effect_params": {"lock": True}})
        with mock.patch("tale.traps.dodge_roll", return_value=-5):
            traps.resolve(self.hall, self.player)
        self.assertFalse(d1.opened)
        self.assertTrue(d1.locked)
        self.assertFalse(d2.opened)
        self.assertTrue(d2.locked)

    def test_alarm_effect_messages_nearby(self):
        street = Location("Street", "An endless street.")
        self.hall.add_exits([Exit("east", street, "A way east.")])
        traps.attach(self.hall, {"level": 1, "trigger": "ENTER", "effect": "ALARM",
                                 "effect_params": {"message": "Alarum!"}})
        class Tap(pubsub.Listener):
            def __init__(self):
                self.msgs = []
            def pubsub_event(self, topicname, event):
                self.msgs.append(event)
        tap = Tap()
        street.get_wiretap().subscribe(tap)
        with mock.patch("tale.traps.dodge_roll", return_value=-5):
            traps.resolve(self.hall, self.player)
        street.get_wiretap().sync()  # pubsub is store-and-forward
        self.assertTrue(any("Alarum!" in str(m) for m in tap.msgs))

    def test_spell_effect_skips_caster_checks(self):
        traps.attach(self.hall, {"level": 2, "trigger": "ENTER", "effect": "SPELL",
                                 "effect_params": {"spell": "BOLT", "spell_level": 4}})
        from tale.skills.magic import MagicType
        self.assertFalse(self.player.stats.magic_skills.get(MagicType.BOLT))  # no caster skill needed
        hp_before = self.player.stats.hp
        with mock.patch("tale.traps.dodge_roll", return_value=-5), \
             mock.patch("tale.traps.random.randint", return_value=3):
            traps.resolve(self.hall, self.player)
        self.assertEqual(self.player.stats.hp, hp_before - 3)


class TestTrapTriggers(unittest.TestCase):
    def setUp(self):
        mud_context.driver = FakeDriver()
        mud_context.config = DemoStory().config
        mud_context.resources = mud_context.driver.resources
        self.hall = Location("Main hall", "A very large hall.")
        self.attic = Location("Attic", "A dark attic.")
        self.door = Door("door", self.attic, "A heavy door.", opened=False)
        self.hall.add_exits([self.door])
        self.player = Living("player", "m")
        self.hall.insert(self.player, None)

    def test_enter_trigger_via_notify_arrived(self):
        traps.attach(self.hall, {"level": 2, "trigger": "ENTER", "effect": "DAMAGE"})
        with mock.patch("tale.traps.dodge_roll", return_value=-5):
            self.hall.notify_player_arrived(self.player, None)
            self.assertEqual(traps.get(self.hall).state, TrapState.SPRUNG)
            traps.remove(self.hall)
            traps.attach(self.hall, {"level": 2, "trigger": "ENTER", "effect": "DAMAGE"})
            self.hall.notify_npc_arrived(self.player, None)
            self.assertEqual(traps.get(self.hall).state, TrapState.SPRUNG)

    def test_open_trigger_on_boxlike_and_door(self):
        chest = Boxlike("chest")
        self.hall.insert(chest, None)
        traps.attach(chest, {"level": 2, "trigger": "OPEN", "effect": "DAMAGE"})
        with mock.patch("tale.traps.dodge_roll", return_value=-5):
            chest.open(self.player)
        self.assertEqual(traps.get(chest).state, TrapState.SPRUNG)

        traps.attach(self.door, {"level": 2, "trigger": "OPEN", "effect": "DAMAGE"})
        with mock.patch("tale.traps.dodge_roll", return_value=-5):
            self.door.open(self.player)
        self.assertEqual(traps.get(self.door).state, TrapState.SPRUNG)

    def test_move_trigger_on_pickup(self):
        bag = Container("bag")
        self.hall.insert(bag, None)
        snare = Item("snare")
        self.hall.insert(snare, None)
        traps.attach(snare, {"level": 2, "trigger": "MOVE", "effect": "DAMAGE"})
        with mock.patch("tale.traps.dodge_roll", return_value=-5):
            snare.move(bag, actor=self.player)
        self.assertEqual(traps.get(snare).state, TrapState.SPRUNG)

    def test_touch_trigger_via_handle_verb(self):
        statue = Item("statue")
        statue.verbs = {"touch": "Touch the statue."}
        self.hall.insert(statue, None)
        traps.attach(statue, {"level": 2, "trigger": "TOUCH", "effect": "DAMAGE"})
        with mock.patch("tale.traps.dodge_roll", return_value=-5):
            handled = self.hall.handle_verb(ParseResult("touch", args=["statue"]), self.player)
        self.assertTrue(handled)
        self.assertEqual(traps.get(statue).state, TrapState.SPRUNG)


class TestSearchAndDisarm(unittest.TestCase):
    def setUp(self):
        mud_context.driver = FakeDriver()
        mud_context.config = DemoStory().config
        mud_context.resources = mud_context.driver.resources
        self.hall = Location("Main hall", "A very large hall.")
        self.player = Living("player", "m")
        self.hall.insert(self.player, None)
        traps.attach(self.hall, {"level": 2, "trigger": "ENTER", "effect": "DAMAGE",
                                 "hidden": True, "descr": "A cunningly hidden wire."})

    def test_search_reveals_hidden_trap(self):
        self.player.stats.skills.set(SkillType.SEARCH, 100)
        with mock.patch("tale.traps.random.randint", return_value=50):  # roll = 50 + 100 - 20 >= 1
            found = traps.search_reveal(self.player)
        self.assertEqual(found, [self.hall])
        self.assertEqual(traps.get(self.hall).state, TrapState.REVEALED)
        self.assertIn("trap", self.hall.extra_desc)

    def test_search_fails_against_high_level(self):
        traps.attach(self.hall, {"level": 10, "trigger": "ENTER", "effect": "DAMAGE"})
        with mock.patch("tale.traps.random.randint", return_value=1):  # roll = 1 + 0 - 100 < 1
            found = traps.search_reveal(self.player)
        self.assertEqual(found, [])
        self.assertEqual(traps.get(self.hall).state, TrapState.ARMED)

    def test_search_hidden_command_reveals_trap(self):
        self.player.stats.skills.set(SkillType.SEARCH, 100)
        with mock.patch("tale.traps.random.randint", return_value=50):
            self.player.search_hidden()
        self.assertEqual(traps.get(self.hall).state, TrapState.REVEALED)

    def test_disarm_success(self):
        traps.get(self.hall).state  # ensure present
        trap = traps.get(self.hall)
        trap.state = TrapState.REVEALED
        traps.attach(self.hall, trap)
        self.player.stats.skills.set(SkillType.DISARM_TRAP, 100)
        with mock.patch("tale.traps.random.randint", return_value=50):  # roll >= 1
            result = traps.disarm(self.hall, self.player)
        self.assertEqual(result, "disarmed")
        self.assertEqual(traps.get(self.hall).state, TrapState.DISARMED)

    def test_disarm_failure_can_spring_trap(self):
        trap = traps.get(self.hall)
        trap.state = TrapState.REVEALED
        traps.attach(self.hall, trap)
        # disarm roll < 1 (fail), then 50% spring coin <= 50, then damage roll
        with mock.patch("tale.traps.random.randint", side_effect=[1, 10, 2]):
            result = traps.disarm(self.hall, self.player)
        self.assertEqual(result, "sprung")
        self.assertEqual(traps.get(self.hall).state, TrapState.SPRUNG)

    def test_disarm_failure_may_stay_revealed(self):
        trap = traps.get(self.hall)
        trap.state = TrapState.REVEALED
        traps.attach(self.hall, trap)
        with mock.patch("tale.traps.random.randint", side_effect=[1, 99]):  # fail, no spring
            result = traps.disarm(self.hall, self.player)
        self.assertEqual(result, "failed")
        self.assertEqual(traps.get(self.hall).state, TrapState.REVEALED)

    def test_disarm_owner_exempt_from_springing(self):
        trap = traps.attach(self.hall, {"level": 2, "trigger": "ENTER", "effect": "DAMAGE",
                                        "owner": "player"})
        trap.state = TrapState.REVEALED
        traps.attach(self.hall, trap)
        with mock.patch("tale.traps.random.randint", return_value=1):  # disarm roll fails
            result = traps.disarm(self.hall, self.player)
        self.assertEqual(result, "failed")
        self.assertEqual(traps.get(self.hall).state, TrapState.REVEALED)

    def test_disarm_without_trap_refused(self):
        empty = Location("Empty room")
        with self.assertRaises(ActionRefused):
            traps.disarm(empty, self.player)
        with self.assertRaises(ActionRefused):  # hidden and not yet revealed
            traps.disarm(self.hall, self.player)


class TestTrapItemAndLoading(unittest.TestCase):
    def setUp(self):
        mud_context.driver = FakeDriver()
        mud_context.config = DemoStory().config
        mud_context.resources = mud_context.driver.resources

    def test_trap_item_from_json_dict(self):
        item = load_item({
            "name": "snare trap", "type": "Trap",
            "trap": {"level": 2, "trigger": "MOVE", "effect": "RESTRAIN", "reset": False,
                     "hidden": True,
                     "llm_hint": "This snare is meant to humiliate, not harm.",
                     "effect_hint": "On full effect the target is yanked off their feet."},
        })
        self.assertIsInstance(item, TrapItem)
        trap = traps.get(item)
        self.assertIsNotNone(trap)
        self.assertEqual(trap.effect, "RESTRAIN")
        self.assertEqual(trap.llm_hint, "This snare is meant to humiliate, not harm.")
        d = item.to_dict()
        self.assertEqual(d["type"], "Trap")
        self.assertEqual(d["trap"]["trigger"], "MOVE")

    def test_trap_block_on_regular_item(self):
        item = load_item({"name": "chest", "type": "Boxlike",
                          "trap": {"level": 3, "trigger": "OPEN", "effect": "ALARM"}})
        trap = traps.get(item)
        self.assertIsNotNone(trap)
        self.assertEqual(trap.trigger, TrapTrigger.OPEN)

    def test_malformed_trap_dict_rejected_at_load(self):
        with self.assertRaises(ValueError):
            load_item({"name": "bad trap", "type": "Trap",
                       "trap": {"level": 2, "trigger": "MOVE", "effect": "EXPLODE"}})
        with self.assertRaises(ValueError):  # ENTER trap on a potion is invalid
            load_item({"name": "potion", "trap": {"level": 1, "trigger": "ENTER", "effect": "DAMAGE"}})

    def test_location_from_json_with_trap(self):
        loc = location_from_json({"name": "Cellar", "descr": "Dark.",
                                  "trap": {"level": 4, "trigger": "ENTER", "effect": "RESTRAIN"}})
        trap = traps.get(loc)
        self.assertIsNotNone(trap)
        self.assertEqual(trap.level, 4)
        with self.assertRaises(ValueError):
            location_from_json({"name": "Cellar", "trap": {"level": 4, "trigger": "OPEN", "effect": "DAMAGE"}})

    def test_trap_item_move_trigger_fires(self):
        hall = Location("Main hall", "A hall.")
        player = Living("player", "m")
        hall.insert(player, None)
        item = load_item({"name": "beartrap", "type": "Trap",
                          "trap": {"level": 2, "trigger": "MOVE", "effect": "DAMAGE"}})
        hall.insert(item, None)
        with mock.patch("tale.traps.dodge_roll", return_value=-5):
            item.move(player, actor=player)
        self.assertEqual(traps.get(item).state, TrapState.SPRUNG)

    def test_persistence_roundtrip_via_story_data(self):
        hall = Location("Main hall", "A hall.")
        traps.attach(hall, {"level": 5, "trigger": "ENTER", "effect": "SPELL",
                            "effect_params": {"spell": "BOLT", "spell_level": 3},
                            "owner": "wizard", "llm_hint": "hint", "effect_hint": "band hint"})
        # simulate a savegame round trip: story_data must be plain JSON-able builtins
        reloaded = Location("Main hall", "A hall.")
        reloaded.story_data = json.loads(json.dumps(hall.story_data))
        trap = traps.get(reloaded)
        self.assertEqual(trap.level, 5)
        self.assertEqual(trap.effect, "SPELL")
        self.assertEqual(trap.effect_params, {"spell": "BOLT", "spell_level": 3})
        self.assertEqual(trap.owner, "wizard")
        self.assertEqual(trap.llm_hint, "hint")
