"""Tests for the stealth rework: hide stance, location concealment, passive perception.

Dice are seeded by monkeypatching tale.stealth._d100 so contest bands are deterministic.
"""

import random

import pytest

import tale
from tale import mud_context, stealth
from tale.base import Door, Exit, Location, Living, ParseResult
from tale.cmds import wizard
from tale.llm.LivingNpc import LivingNpc
from tale.llm.dynamic_story import DynamicStory
from tale.player import Player
from tale.savegames import TaleSerializer, TaleDeserializer
from tale.skills import spells as skill_spells
from tale.skills.magic import MagicType
from tale.skills.skills import SkillType
from tale.story import StoryConfig
from tests.supportstuff import FakeDriver, MsgTraceNPC


def seed_dice(monkeypatch, values):
    """Make stealth._d100 return the given values in order (hider roll, then searcher roll, ...)."""
    it = iter(values)
    monkeypatch.setattr(stealth, "_d100", lambda: next(it))


class TestStealth:

    def setup_method(self):
        mud_context.config = StoryConfig()
        mud_context.driver = FakeDriver()
        mud_context.driver.story = DynamicStory()
        self.room = Location("warehouse")
        self.hider = MsgTraceNPC("hider", "m", race="human")
        self.watcher = MsgTraceNPC("watcher", "m", race="human")
        self.room.init_inventory([self.hider, self.watcher])
        self.hider.stats.skills.set(SkillType.HIDE, 0)
        self.watcher.stats.skills.set(SkillType.PERCEPTION, 0)

    def test_band_boundaries(self):
        assert stealth.band_for_margin(20) == stealth.DetectionBand.UNNOTICED
        assert stealth.band_for_margin(100) == stealth.DetectionBand.UNNOTICED
        assert stealth.band_for_margin(19) == stealth.DetectionBand.TRACES
        assert stealth.band_for_margin(0) == stealth.DetectionBand.TRACES
        assert stealth.band_for_margin(-1) == stealth.DetectionBand.DETECTED

    def test_contest_detected_breaks_stance(self, monkeypatch):
        self.hider.hidden = True
        seed_dice(monkeypatch, [50, 90])  # margin -40 -> detected
        result = stealth.resolve_contest(self.hider, self.watcher)
        assert result.band == stealth.DetectionBand.DETECTED
        assert not self.hider.hidden
        assert any("spot" in m and "hider" in m for m in self.watcher.messages)
        assert any("spots you" in m for m in self.hider.messages)
        assert any("reveals hider" in m for m in self.hider.messages)  # room-wide reveal message

    def test_contest_traces_keeps_stance_and_injects_fact(self, monkeypatch):
        self.hider.hidden = True
        seed_dice(monkeypatch, [50, 50])  # margin 0 -> traces
        result = stealth.resolve_contest(self.hider, self.watcher)
        assert result.band == stealth.DetectionBand.TRACES
        assert self.hider.hidden
        assert any(k in m for m in self.watcher.messages for k in ("movement", "rustling", "shifts", "scraping"))
        assert not any("spot" in m for m in self.watcher.messages)

    def test_contest_unnoticed_no_event(self, monkeypatch):
        self.hider.hidden = True
        seed_dice(monkeypatch, [90, 50])  # margin +40 -> unnoticed
        result = stealth.resolve_contest(self.hider, self.watcher)
        assert result.band == stealth.DetectionBand.UNNOTICED
        assert self.hider.hidden
        assert self.watcher.messages == []

    def test_contest_uses_concealment_of_location(self, monkeypatch):
        self.hider.hidden = True
        self.room.concealment = 4  # +20 modifier
        seed_dice(monkeypatch, [50, 50])  # margin 0 + 20 = 20 -> unnoticed in tier 4...
        result = stealth.resolve_contest(self.hider, self.watcher)
        assert result.band == stealth.DetectionBand.UNNOTICED
        assert result.margin == 20
        self.room.concealment = 0  # ...but traces in tier 0 with the same dice
        seed_dice(monkeypatch, [50, 50])
        result = stealth.resolve_contest(self.hider, self.watcher)
        assert result.band == stealth.DetectionBand.TRACES

    def test_concealment_clamped(self):
        assert stealth.clamp_concealment(9) == 4
        assert stealth.clamp_concealment(-3) == 0
        self.room.concealment = 7
        assert stealth.concealment_modifier(self.room) == 20

    def test_hide_entry_contest_won_with_observers(self, monkeypatch):
        seed_dice(monkeypatch, [90, 50])  # margin +40 -> contest won
        self.hider.stats.action_points = 1
        self.hider.hide()
        assert self.hider.hidden
        assert self.hider.stats.action_points == 0

    def test_hide_entry_contest_lost_fumbles(self, monkeypatch):
        seed_dice(monkeypatch, [50, 90])  # margin -40 -> detected -> stance refused
        self.hider.stats.action_points = 1
        self.hider.hide()
        assert not self.hider.hidden
        assert any("fumble" in m for m in self.hider.messages)
        assert any("tries to hide but is spotted" in m for m in self.watcher.messages)

    def test_hide_uncontested_when_alone(self):
        self.room.remove(self.watcher, self.watcher)
        self.hider.stats.action_points = 1
        self.hider.hide()
        assert self.hider.hidden

    def test_unhide_is_free(self):
        self.hider.hidden = True
        self.hider.stats.action_points = 0
        self.hider.hide(False)
        assert not self.hider.hidden
        assert self.hider.stats.action_points == 0

    def test_search_hidden_active_contest(self, monkeypatch):
        self.hider.hidden = True
        self.watcher.stats.skills.set(SkillType.PERCEPTION, 100)
        self.watcher.stats.action_points = 1
        seed_dice(monkeypatch, [50, 50])  # hider 50 vs searcher 50+100+SEARCH_BONUS -> detected
        self.watcher.search_hidden()
        assert not self.hider.hidden
        assert self.watcher.stats.action_points == 0

    def test_entry_contest_on_move_detects_hidden_occupant(self, monkeypatch):
        room2 = Location("hall")
        Exit.connect(self.room, "north", "", None, room2, "south", "", None)
        self.hider.hidden = True
        self.watcher.stats.skills.set(SkillType.PERCEPTION, 100)
        self.watcher.move(room2, direction_names=["north"])  # no hidden occupants there
        assert self.hider.hidden
        seed_dice(monkeypatch, [50, 50])  # watcher re-enters: contest vs hidden hider -> detected
        self.watcher.move(self.room, direction_names=["south"])
        assert not self.hider.hidden

    def test_entry_contest_hidden_entrant_vs_occupants(self, monkeypatch):
        room2 = Location("hall")
        Exit.connect(self.room, "north", "", None, room2, "south", "", None)
        self.room.remove(self.watcher, self.watcher)
        room2.insert(self.watcher, actor=None)
        self.watcher.stats.skills.set(SkillType.PERCEPTION, 100)
        self.hider.hidden = True
        seed_dice(monkeypatch, [50, 50])  # hidden hider moves into watcher's room -> detected
        self.hider.move(room2, direction_names=["north"])
        assert not self.hider.hidden

    def test_adjacent_perception_glimpse_is_direction_only(self, monkeypatch):
        room_a = Location("room_a")
        room_b = Location("room_b")
        room_c = Location("room_c")
        Exit.connect(room_a, "east", "", None, room_b, "west", "", None)
        Exit.connect(room_b, "east", "", None, room_c, "west", "", None)
        observer = MsgTraceNPC("observer", "f", race="human")
        observer.stats.skills.set(SkillType.PERCEPTION, 20)  # 20*5=100 -> any roll notices
        room_a.insert(observer, actor=None)
        mover = MsgTraceNPC("mover", "m", race="human")
        room_b.insert(mover, actor=None)
        seed_dice(monkeypatch, [10, 10])
        mover.move(room_c, direction_names=["east"])
        glimpses = [m for m in observer.messages if "east" in m]
        assert glimpses, observer.messages
        assert all("mover" not in m for m in glimpses)  # direction only, never identity

    def test_adjacent_perception_failure_is_silent(self, monkeypatch):
        room_a = Location("room_a")
        room_b = Location("room_b")
        room_x = Location("room_x")
        Exit.connect(room_a, "east", "", None, room_b, "west", "", None)
        Exit.connect(room_b, "north", "", None, room_x, "south", "", None)
        observer = MsgTraceNPC("observer", "f", race="human")
        observer.stats.skills.set(SkillType.PERCEPTION, 0)  # never notices
        room_a.insert(observer, actor=None)
        mover = MsgTraceNPC("mover", "m", race="human")
        room_b.insert(mover, actor=None)
        seed_dice(monkeypatch, [50] * 10)
        mover.move(room_x, direction_names=["north"])
        assert observer.messages == []

    def test_adjacent_perception_never_reveals_hidden_mover(self, monkeypatch):
        room_a = Location("room_a")
        room_b = Location("room_b")
        room_c = Location("room_c")
        Exit.connect(room_a, "east", "", None, room_b, "west", "", None)
        Exit.connect(room_b, "east", "", None, room_c, "west", "", None)
        observer = MsgTraceNPC("observer", "f", race="human")
        observer.stats.skills.set(SkillType.PERCEPTION, 20)
        room_a.insert(observer, actor=None)
        mover = MsgTraceNPC("mover", "m", race="human")
        mover.hidden = True
        room_b.insert(mover, actor=None)
        seed_dice(monkeypatch, [10] * 10)
        mover.move(room_c, direction_names=["east"])
        assert observer.messages == []

    def test_risky_action_talk_while_hidden(self, monkeypatch):
        self.hider.hidden = True
        self.watcher.stats.skills.set(SkillType.PERCEPTION, 100)
        seed_dice(monkeypatch, [50, 50])  # hider 50-30 penalty vs searcher 50+100 -> detected
        results = stealth.risky_action(self.hider, hider_penalty=stealth.TALK_WHILE_HIDDEN_PENALTY)
        assert results[0].band == stealth.DetectionBand.DETECTED
        assert not self.hider.hidden

    def test_pick_lock_fumble_while_hidden_triggers_contest(self, monkeypatch):
        hall = Location("hall")
        door = Door("north", hall, "a locked door", locked=True, opened=False)
        self.hider.hidden = True
        self.hider.stats.skills.set(SkillType.PICK_LOCK, 0)  # always fumbles
        self.hider.stats.action_points = 1
        self.watcher.stats.skills.set(SkillType.PERCEPTION, 100)
        monkeypatch.setattr(random, "randint", lambda a, b: 100)  # pick_lock roll fails
        seed_dice(monkeypatch, [50, 50])  # contest: hider 50 vs watcher 50+100+bonus -> detected
        self.hider.pick_lock(door)
        assert not self.hider.hidden

    def test_hidden_action_ap_surcharge(self):
        self.hider.stats.action_points = 5
        stealth.charge_hidden_action(self.hider)
        assert self.hider.stats.action_points == 5  # not hidden: no surcharge
        self.hider.hidden = True
        stealth.charge_hidden_action(self.hider)
        assert self.hider.stats.action_points == 4
        self.hider.stats.action_points = 0
        stealth.charge_hidden_action(self.hider)
        assert self.hider.stats.action_points == 0  # floors at 0

    def test_replenish_blocked_while_hidden(self):
        driver = mud_context.driver
        player = Player("p", "f")
        player.hidden = True
        player.stats.action_points = 3
        player.stats.hp = 1

        class Conn:
            pass
        conn = Conn()
        conn.player = player
        driver.all_players = {"p": conn}
        driver.replenish()
        assert player.stats.action_points == 3
        assert player.stats.hp == 1
        player.hidden = False
        driver.replenish()
        assert player.stats.action_points == 4
        assert player.stats.hp == 2

    def test_cast_hide_sets_stance_without_throw(self):
        caster = MsgTraceNPC("caster", "m", race="human")
        caster.stats.magic_skills.set(MagicType.HIDE, 100)
        caster.stats.magic_points = 10
        target = MsgTraceNPC("target", "f", race="human")
        self.room.insert(caster, actor=None)
        self.room.insert(target, actor=None)
        target.stats.skills.set(SkillType.HIDE, 0)
        skill_spells.cast_hide(caster, target, 1)
        assert target.hidden  # no contest, magic bypasses the skill throw

    def test_cast_reveal_near_guaranteed(self, monkeypatch):
        caster = MsgTraceNPC("caster", "m", race="human")
        caster.stats.magic_skills.set(MagicType.REVEAL, 100)
        caster.stats.magic_points = 10
        self.room.insert(caster, actor=None)
        self.hider.hidden = True
        caster.stats.skills.set(SkillType.PERCEPTION, 0)
        seed_dice(monkeypatch, [50, 50])  # reveal bonus 100+level*10 -> detected
        skill_spells.cast_reveal(caster, 1)
        assert not self.hider.hidden

    def test_hidden_living_absent_from_look_and_self_marker(self):
        self.hider.hidden = True
        paragraphs = "\n".join(self.room.look(exclude_living=self.watcher))
        assert "hider" not in paragraphs
        own = "\n".join(self.room.look(exclude_living=self.hider))
        assert "[hidden]" in own  # the hidden entity sees its own stance marker
        assert self.hider.title == "hider"  # no [hidden] tag in the title itself
        assert self.hider.status_title == "hider [hidden]"

    def test_stance_and_concealment_survive_serialization(self):
        ser = TaleSerializer()
        deser = TaleDeserializer()
        p = Player("julie", "f")
        living = Living("sneak", "m")
        living.hidden = True
        loc = Location("cellar")
        loc.concealment = 3
        data = ser.serialize(None, p, [living, loc], [], [], [], [], None)
        stuff = deser.deserialize(data)
        by_name = {x["name"]: x for x in stuff["items"]}
        assert by_name["sneak"]["hidden"] is True
        assert by_name["cellar"]["concealment"] == 3

    def test_wizard_set_concealment(self):
        player = Player("wiz", "f")
        player.privileges.add("wizard")
        self.room.insert(player, actor=None)
        ctx = tale.util.Context(mud_context.driver, mud_context.driver.game_clock, StoryConfig(), None)
        wizard.do_set_concealment(player, ParseResult(verb="!set_concealment", args=["here", "3"]), ctx)
        assert self.room.concealment == 3
        wizard.do_set_concealment(player, ParseResult(verb="!set_concealment", args=["here", "9"]), ctx)
        assert self.room.concealment == 4  # clamped to the 0-4 range
        with pytest.raises(Exception):
            wizard.do_set_concealment(player, ParseResult(verb="!set_concealment", args=["here"]), ctx)

    def test_wizard_perceive_sweep(self, monkeypatch):
        player = Player("wiz", "f")
        player.privileges.add("wizard")
        self.room.insert(player, actor=None)
        self.hider.hidden = True
        # sweep contest: hider 50 vs player 50+10 (default perception) -> detected
        seed_dice(monkeypatch, [50, 50])
        ctx = tale.util.Context(mud_context.driver, mud_context.driver.game_clock, StoryConfig(), None)
        wizard.do_perceive(player, ParseResult(verb="!perceive", args=[]), ctx)
        assert not self.hider.hidden

    def test_npc_observer_gets_grounded_fact_in_action_context(self, monkeypatch):
        npc_observer = LivingNpc("guard", "m", occupation="guard", parse_occupation=True)
        npc_observer.stats.skills.set(SkillType.PERCEPTION, 0)  # neutralize the occupation bonus
        assert npc_observer.stats.skills.get(SkillType.PERCEPTION) == 0
        self.room.insert(npc_observer, actor=None)
        self.hider.hidden = True
        seed_dice(monkeypatch, [50, 50])  # margin 0 vs perception 0 -> traces
        stealth.resolve_contest(self.hider, npc_observer)
        assert self.hider.hidden
        events = npc_observer.memory.observed_events()
        assert any(k in events for k in ("movement", "rustling", "shifts", "scraping"))
