"""
Tests for the declarative beat-boundary effects (tale/scenario.py Effect model
and registry, tale/effects.py EffectRunner) and for their execution at beat
transitions in StoryContext.

The built-in vocabulary covered here: add_item, remove_item, spawn_npc,
move_npc, remove_npc, set_goal -- each mapped onto the existing StoryManager
operations.
"""
import types

import pytest

import tale.story_manager as sm
from tale import mud_context
from tale.base import Location, Living, Weapon
from tale.llm.dynamic_story import DynamicStory
from tale.scenario import (Beat, BeatStatus, Effect, Goal, NpcKilled,
                           get_effect_handler, known_effects, load_beats,
                           register_effect)
from tale.story_context import StoryContext
from tale.story_manager import StoryManager
from tale.zone import Zone
from tests.supportstuff import FakeDriver


def make_story():
    story = DynamicStory()
    story.config.name = "Test Story"
    story.add_zone(Zone("TestZone", "a test zone"))
    cave = Location("Cave")
    hall = Location("Hall")
    story.add_location(cave, "TestZone")
    story.add_location(hall, "TestZone")
    return story, cave, hall


def make_manager():
    """A StoryManager over a small world: zone TestZone with locations Cave and
    Hall, a live npc Corbin in the Cave, a catalogue creature 'goblin' and a
    catalogue item template 'torch' (a Weapon 'sword')."""
    story, cave, hall = make_story()
    mgr = StoryManager(story)
    mgr.add_creature({"name": "goblin", "type": "Mob", "gender": "m", "race": "human",
                      "level": 1, "descr": "A goblin"})
    mgr.add_item({"name": "torch", "type": "Other"})
    mgr.add_item({"name": "sword", "type": "Weapon", "weapon_type": "ONE_HANDED"})
    corbin = Living("Corbin", "f")
    cave.insert(corbin, None)
    story.world.add_npc(corbin)
    return mgr, story, cave, hall, corbin


class StubDriver:
    """A tiny driver stub exposing ``all_players`` (name -> connection with a
    ``.player``), as the real driver does."""
    def __init__(self, players):
        self.all_players = {p.name: types.SimpleNamespace(player=p) for p in players}


@pytest.fixture
def registered_manager():
    """Register a manager globally (for the lazy EffectRunner resolution) and
    restore the previous global afterwards, so other tests are unaffected."""
    mgr, story, cave, hall, corbin = make_manager()
    saved = sm._current
    sm.register(mgr)
    try:
        yield mgr, story, cave, hall, corbin
    finally:
        sm._current = saved


class TestEffectModel:

    def test_known_effects_are_the_builtin_vocabulary(self):
        assert known_effects() == ["add_item", "move_npc", "remove_item", "remove_npc", "set_goal", "spawn_npc"]

    def test_from_json_accepts_all_builtins(self):
        assert Effect.from_json({"effect": "add_item", "item": "brass key", "to": "player"}).to_json() == \
               {"effect": "add_item", "item": "brass key", "to": "player"}
        assert Effect.from_json({"effect": "add_item", "item": "key", "to": "Mrs. Corbin"}).args["to"] == "Mrs. Corbin"
        assert Effect.from_json({"effect": "remove_item", "item": "key", "from": "player"}).args["from"] == "player"
        assert Effect.from_json({"effect": "remove_item", "item": "key"}).args.get("from", "player") == "player"  # default
        assert Effect.from_json({"effect": "spawn_npc", "npc": "giant rat", "at": "cellar"}).to_json() == \
               {"effect": "spawn_npc", "npc": "giant rat", "at": "cellar"}
        assert Effect.from_json({"effect": "spawn_npc", "name": "giant rat", "at": "cellar"}).args["name"] == "giant rat"
        assert Effect.from_json({"effect": "move_npc", "npc": "corbin", "to": "cellar"}).to_json() == \
               {"effect": "move_npc", "npc": "corbin", "to": "cellar"}
        assert Effect.from_json({"effect": "remove_npc", "npc": "corbin"}).to_json() == \
               {"effect": "remove_npc", "npc": "corbin"}
        assert Effect.from_json({"effect": "set_goal", "npc": "corbin", "goal": "hide"}).to_json() == \
               {"effect": "set_goal", "npc": "corbin", "goal": "hide"}

    def test_from_json_rejects_malformed_effects(self):
        for bad in ["not a dict", {"item": "x"}, {"effect": ""}, {"effect": 42},
                    {"effect": "add_item"},                       # missing item
                    {"effect": "add_item", "item": ""},           # empty item
                    {"effect": "add_item", "item": "x", "nope": 1},  # unknown key
                    {"effect": "spawn_npc", "npc": "rat"},        # missing at
                    {"effect": "set_goal", "npc": "c"},           # missing goal
                    {"effect": "narrative_event", "text": "x"}]:  # not in the vocabulary yet
            with pytest.raises(ValueError):
                Effect.from_json(bad)

    def test_unknown_effect_rejected_unless_registered(self):
        with pytest.raises(ValueError):
            Effect.from_json({"effect": "unlock_flashback"})

        @register_effect("unlock_flashback")
        def _unlock(ctx, args):
            pass

        effect = Effect.from_json({"effect": "unlock_flashback", "chapter": 3})
        assert effect.effect == "unlock_flashback"
        assert effect.args == {"chapter": 3}
        assert get_effect_handler("unlock_flashback") is _unlock
        assert "unlock_flashback" in known_effects()

    def test_register_effect_rejects_empty_name(self):
        with pytest.raises(ValueError):
            register_effect("")

    def test_effect_round_trip_through_beat(self):
        beat = Beat.from_json({"id": "a", "description": "A",
                               "on_start": [{"effect": "set_goal", "npc": "corbin", "goal": "hide"}],
                               "on_end": [{"effect": "add_item", "item": "key", "to": "player"},
                                          {"effect": "remove_npc", "npc": "corbin"}]})
        assert beat.on_start[0].to_json() == {"effect": "set_goal", "npc": "corbin", "goal": "hide"}
        assert [e.effect for e in beat.on_end] == ["add_item", "remove_npc"]
        restored = Beat.from_json(beat.to_json())
        assert restored.to_json() == beat.to_json()
        assert restored.on_end[1].args == {"npc": "corbin"}

    def test_load_beats_validates_effects(self):
        beats = load_beats([{"id": "a", "description": "A",
                             "on_start": [{"effect": "move_npc", "npc": "c", "to": "hall"}]}])
        assert beats[0].on_start[0].effect == "move_npc"
        with pytest.raises(ValueError):
            load_beats([{"id": "a", "description": "A", "on_end": [{"effect": "explode"}]}])
        with pytest.raises(ValueError):
            load_beats([{"id": "a", "description": "A", "on_end": "add_item key"}])


class TestEffectRunnerBuiltins:
    """Each built-in effect against a live StoryManager world."""

    def test_add_item_to_location_adhoc(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import run_effects
        results = run_effects([Effect.from_json({"effect": "add_item", "item": "brass key", "to": "Cave"})], manager=mgr)
        assert results == [{"effect": "add_item", "success": True, "error": ""}]
        assert [item.name for item in cave.items] == ["brass key"]
        assert story.world.get_item("brass key") is not None  # registered in the world store, like spawn_item

    def test_add_item_uses_catalogue_template(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import run_effects
        run_effects([Effect.from_json({"effect": "add_item", "item": "SWORD", "to": "Hall"})], manager=mgr)  # case-insensitive
        sword = next(iter(hall.items))
        assert isinstance(sword, Weapon)  # loaded from the catalogue template, not a plain Item
        assert sword.name == "sword"

    def test_add_item_to_npc_and_player(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import run_effects
        hero = Living("Hero", "m")
        cave.insert(hero, None)
        mgr._driver = StubDriver([hero])
        results = run_effects([Effect.from_json({"effect": "add_item", "item": "torch", "to": "Corbin"}),
                               Effect.from_json({"effect": "add_item", "item": "torch", "to": "player"})], manager=mgr)
        assert all(r["success"] for r in results)
        assert [item.name for item in corbin.inventory] == ["torch"]
        assert [item.name for item in hero.inventory] == ["torch"]

    def test_add_item_unknown_target_is_an_error_result(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import run_effects
        results = run_effects([Effect.from_json({"effect": "add_item", "item": "key", "to": "Nowhere"})], manager=mgr)
        assert results[0]["success"] is False
        assert "Nowhere" in results[0]["error"]

    def test_remove_item_from_player_npc_and_location(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import run_effects
        hero = Living("Hero", "m")
        cave.insert(hero, None)
        mgr._driver = StubDriver([hero])
        assert mgr.give_item("torch", "player")[0]
        assert mgr.give_item("torch", "Corbin")[0]
        assert mgr.give_item("brass key", "Cave")[0]
        results = run_effects([Effect.from_json({"effect": "remove_item", "item": "torch", "from": "player"}),
                               Effect.from_json({"effect": "remove_item", "item": "torch", "from": "Corbin"}),
                               Effect.from_json({"effect": "remove_item", "item": "brass key", "from": "Cave"})], manager=mgr)
        assert all(r["success"] for r in results)
        assert list(hero.inventory) == []
        assert list(corbin.inventory) == []
        assert list(cave.items) == []
        assert "brass key" not in story.world.items  # also dropped from the world store

    def test_remove_item_not_found(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import run_effects
        results = run_effects([Effect.from_json({"effect": "remove_item", "item": "nope", "from": "Cave"})], manager=mgr)
        assert results[0]["success"] is False
        assert "nope" in results[0]["error"]

    def test_spawn_npc(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import run_effects
        results = run_effects([Effect.from_json({"effect": "spawn_npc", "npc": "Goblin", "at": "Hall"})], manager=mgr)
        assert results[0]["success"] is True  # case-insensitive creature and location lookup
        goblin = story.world.get_npc("goblin")
        assert goblin is not None
        assert goblin.location is hall
        assert goblin in hall.livings

    def test_spawn_npc_unknown_creature_or_location(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import run_effects
        results = run_effects([Effect.from_json({"effect": "spawn_npc", "npc": "dragon", "at": "Hall"}),
                               Effect.from_json({"effect": "spawn_npc", "npc": "goblin", "at": "Nowhere"})], manager=mgr)
        assert all(r["success"] is False for r in results)
        assert "dragon" in results[0]["error"]
        assert "Nowhere" in results[1]["error"]

    def test_move_npc(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import run_effects
        results = run_effects([Effect.from_json({"effect": "move_npc", "npc": "Corbin", "to": "Hall"})], manager=mgr)
        assert results[0]["success"] is True
        assert corbin.location is hall
        assert corbin in hall.livings and corbin not in cave.livings

    def test_move_npc_unknown(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import run_effects
        results = run_effects([Effect.from_json({"effect": "move_npc", "npc": "Nobody", "to": "Hall"})], manager=mgr)
        assert results[0]["success"] is False

    def test_remove_npc(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import run_effects
        results = run_effects([Effect.from_json({"effect": "remove_npc", "npc": "corbin"})], manager=mgr)
        assert results[0]["success"] is True
        assert "corbin" not in story.world.npcs
        assert corbin not in cave.livings
        results = run_effects([Effect.from_json({"effect": "remove_npc", "npc": "corbin"})], manager=mgr)
        assert results[0]["success"] is False

    def test_set_goal(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import run_effects
        results = run_effects([Effect.from_json({"effect": "set_goal", "npc": "Corbin", "goal": "hide in the cellar"})], manager=mgr)  # title lookup
        assert results[0]["success"] is True
        assert corbin.goal == "hide in the cellar"
        results = run_effects([Effect.from_json({"effect": "set_goal", "npc": "Nobody", "goal": "x"})], manager=mgr)
        assert results[0]["success"] is False

    def test_failing_effect_does_not_stop_the_rest(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import run_effects
        effects = [Effect.from_json({"effect": "set_goal", "npc": "Nobody", "goal": "x"}),
                   Effect.from_json({"effect": "add_item", "item": "brass key", "to": "Cave"})]
        results = run_effects(effects, manager=mgr)
        assert results[0]["success"] is False
        assert results[1]["success"] is True
        assert [item.name for item in cave.items] == ["brass key"]

    def test_unknown_effect_at_runtime_is_an_error_result(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import EffectRunner
        runner = EffectRunner(mgr)
        results = runner.run([Effect("totally_made_up", {})])
        assert results[0]["success"] is False
        assert "unknown effect" in results[0]["error"]

    def test_invalid_effect_dict_is_an_error_result(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import EffectRunner
        results = EffectRunner(mgr).run([{"effect": "add_item"}])  # missing item
        assert results[0]["success"] is False

    def test_custom_effect_handler(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import EffectRunner
        calls = []

        @register_effect("test_mark")
        def _mark(runner, args):
            calls.append((runner, args))
            runner.manager.set_npc_goal(args["npc"], args["goal"])

        results = EffectRunner(mgr).run([Effect.from_json({"effect": "test_mark", "npc": "corbin", "goal": "custom"})])
        assert results[0]["success"] is True
        assert calls[0][1]["effect"] == "test_mark"
        assert calls[0][0].manager is mgr
        assert corbin.goal == "custom"

    def test_runner_resolves_manager_from_global_registry(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.effects import EffectRunner
        runner = EffectRunner()  # no explicit manager
        assert runner.manager is mgr
        results = runner.run([Effect.from_json({"effect": "set_goal", "npc": "corbin", "goal": "via global"})])
        assert results[0]["success"] is True
        assert corbin.goal == "via global"


class TestStoryContextEffects:
    """Boundary effects firing at beat transitions in StoryContext."""

    def _context_with_manager(self, beats):
        mgr, story, cave, hall, corbin = make_manager()
        context = story.config.context
        context.set_beats(beats)
        return mgr, story, context, cave, hall, corbin

    def test_on_end_and_on_start_run_at_event_driven_transition(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        context = story.config.context
        context.set_beats([
            Beat("hunt", "Hunt the rat.", goals=[Goal("kill", "giant rat")],
                 on_end=[Effect.from_json({"effect": "add_item", "item": "rat skull", "to": "Cave"})]),
            Beat("after", "After.",
                 on_start=[Effect.from_json({"effect": "set_goal", "npc": "corbin", "goal": "relax"}),
                           Effect.from_json({"effect": "move_npc", "npc": "corbin", "to": "Hall"})]),
        ])
        assert context.active_beat().id == "hunt"
        completed = context.on_story_event(NpcKilled(npc="giant rat"))
        assert completed == ["hunt"]
        assert context.active_beat().id == "after"
        assert [item.name for item in cave.items] == ["rat skull"]
        assert corbin.goal == "relax"
        assert corbin.location is hall
        assert context.beats[0]._effects_run == {"on_end"}
        assert context.beats[1]._effects_run == {"on_start"}

    def test_boundary_effects_run_exactly_once(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        context = story.config.context
        context.set_beats([
            Beat("one", "One.", on_end=[Effect.from_json({"effect": "add_item", "item": "key", "to": "Cave"})]),
            Beat("two", "Two."),
        ])
        context.set_beat("two")   # completes "one" (on_end), activates "two"
        assert [item.name for item in cave.items] == ["key"]
        context.set_beat("two")   # already active: no transition, no re-run
        context._settle()
        assert [item.name for item in cave.items] == ["key"]
        assert context.beats[0]._effects_run == {"on_end"}

    def test_failing_effect_does_not_wedge_the_transition(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        context = story.config.context
        context.set_beats([
            Beat("one", "One.", goals=[Goal("kill", "rat")],
                 on_end=[Effect.from_json({"effect": "set_goal", "npc": "Nobody", "goal": "x"}),
                         Effect.from_json({"effect": "add_item", "item": "key", "to": "Cave"})]),
            Beat("two", "Two."),
        ])
        completed = context.on_story_event(NpcKilled(npc="rat"))
        assert completed == ["one"]   # the transition happened despite the failed effect
        assert context.active_beat().id == "two"
        assert [item.name for item in cave.items] == ["key"]  # the remaining effect still ran

    def test_pending_on_start_runs_when_manager_appears(self):
        # the story is initialized (beats activated) before any StoryManager exists
        story, cave, hall = make_story()
        context = story.config.context
        context.set_beats([Beat("arrival", "Arrive.",
                                on_start=[Effect.from_json({"effect": "add_item", "item": "key", "to": "Cave"})])])
        assert context.active_beat().id == "arrival"
        assert list(cave.items) == []  # no runner yet: pending, not lost, not run
        mgr = StoryManager(story)      # wires the runner and runs pending effects
        assert context.effect_runner is not None
        assert [item.name for item in cave.items] == ["key"]
        assert context.active_beat()._effects_run == {"on_start"}

    def test_save_load_preserves_effects_and_does_not_rerun_them(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        context = story.config.context
        context.set_beats([
            Beat("one", "One.", on_end=[Effect.from_json({"effect": "add_item", "item": "key", "to": "Cave"})]),
            Beat("two", "Two.", on_start=[Effect.from_json({"effect": "set_goal", "npc": "corbin", "goal": "g"})]),
        ])
        context.set_beat("two")
        assert [item.name for item in cave.items] == ["key"]
        import json
        restored = StoryContext().from_json(json.loads(json.dumps(context.to_json())))
        assert restored.beats[0].on_end[0].to_json() == {"effect": "add_item", "item": "key", "to": "Cave"}
        assert restored.beats[1].on_start[0].to_json() == {"effect": "set_goal", "npc": "corbin", "goal": "g"}
        assert [b.status for b in restored.beats] == [BeatStatus.COMPLETED, BeatStatus.ACTIVE]
        # restored statuses count as already-run: settling must not re-run boundaries
        assert restored.beats[0]._effects_run == {"on_end"}
        assert restored.beats[1]._effects_run == {"on_start"}
        restored._settle()
        assert [item.name for item in cave.items] == ["key"]

    def test_pubsub_event_drives_effects_via_manager(self, registered_manager):
        mgr, story, cave, hall, corbin = registered_manager
        from tale.scenario import publish_story_event, Interacted
        context = story.config.context
        context.set_beats([
            Beat("interview", "Talk.", goals=[Goal("interact", "corbin")],
                 on_end=[Effect.from_json({"effect": "remove_npc", "npc": "corbin"})]),
            Beat("after", "After."),
        ])
        publish_story_event(Interacted(npc="corbin", npc_title="Corbin"))
        assert context.active_beat().id == "after"
        assert "corbin" not in story.world.npcs


class TestBeatsTestStoryEffects:
    """The beats_test story authors effects on its beats; they parse and save."""

    def test_beats_test_story_config_parses_effects(self):
        import tale.parse_utils as parse_utils
        config = parse_utils.load_story_config(parse_utils.load_json('stories/beats_test/story_config.json'))
        by_id = {beat.id: beat for beat in config.beats}
        assert [e.to_json() for e in by_id["arrival"].on_start] == [
            {"effect": "set_goal", "npc": "Mrs. Corbin", "goal": "avoid all questions about the cellar"}]
        assert [e.effect for e in by_id["suspicion"].on_end] == ["add_item"]
        assert [e.effect for e in by_id["descent"].on_start] == ["move_npc"]

    def test_beats_test_story_round_trip_keeps_effects(self):
        import tale.parse_utils as parse_utils
        config = parse_utils.load_story_config(parse_utils.load_json('stories/beats_test/story_config.json'))
        stored = parse_utils.save_story_config(config)
        reloaded = parse_utils.load_story_config(stored)
        by_id = {beat.id: beat for beat in reloaded.beats}
        assert by_id["suspicion"].on_end[0].to_json() == {"effect": "add_item", "item": "torn diary page", "to": "player"}
