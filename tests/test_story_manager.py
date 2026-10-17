""" Tests for the StoryManager modification layer (tale/story_manager.py). """

import os
import shutil
import tempfile
import types

import pytest

from tale import pubsub, mud_context
from tale.base import Location, Living, Door
from tale.coord import Coord
from tale.errors import SecurityViolation
from tale.llm.dynamic_story import DynamicStory
from tale.llm.LivingNpc import LivingNpc
from tale.llm.responses.LocationResponse import LocationResponse
from tale.story import StoryConfig
from tale.story_context import StoryContext
from tale.story_manager import StoryManager, register, current, get
from tale.zone import Zone
from tests.supportstuff import FakeDriver


def make_story():
    story = DynamicStory()
    story.config.name = "Test Story"
    story.add_zone(Zone("TestZone", "a test zone"))
    return story


class TestRegistry():

    def test_register_and_current(self):
        story = make_story()
        mgr = StoryManager(story)
        register(mgr)
        assert current() is mgr
        assert get() is mgr

    def test_current_without_register_raises(self):
        # the global may already be set by another test; save and reset it
        import tale.story_manager as sm
        saved = sm._current
        sm._current = None
        try:
            with pytest.raises(RuntimeError):
                current()
        finally:
            sm._current = saved


class TestConfig():

    def test_get_config_defaults(self):
        mgr = StoryManager(make_story())
        config = mgr.get_config()
        assert config["name"] == "Test Story"
        assert config["supported_modes"] == ["IF"]
        assert config["world_mood"] == 0

    def test_set_config(self):
        mgr = StoryManager(make_story())
        mgr.set_config(name="New Name", world_info="A world", world_mood=4)
        assert mgr.story.config.name == "New Name"
        assert mgr.story.config.world_info == "A world"
        assert mgr.story.config.world_mood == 4
        config = mgr.get_config()
        assert config["name"] == "New Name"
        assert config["world_mood"] == 4

    def test_set_config_context_wraps_string(self):
        mgr = StoryManager(make_story())
        mgr.set_config(context="Once upon a time")
        assert isinstance(mgr.story.config.context, StoryContext)
        assert mgr.story.config.context.base_story == "Once upon a time"

    def test_set_config_supported_modes(self):
        mgr = StoryManager(make_story())
        mgr.set_config(supported_modes=["if", "mud"])
        modes = mgr.story.config.supported_modes
        assert {"IF", "MUD"} == {m.name for m in modes}


class TestZones():

    def test_add_and_get_zone(self):
        mgr = StoryManager(make_story())
        ok, error = mgr.add_zone({"name": "SecondZone", "description": "second", "level": 3})
        assert ok is True
        assert error == ""
        info = mgr.get_zone("SecondZone")
        assert info["name"] == "SecondZone"
        assert info["level"] == 3

    def test_list_zones(self):
        mgr = StoryManager(make_story())
        mgr.add_zone({"name": "SecondZone", "description": "second"})
        names = {z["name"] for z in mgr.list_zones()}
        assert set(mgr.story._zones.keys()) == {"TestZone", "SecondZone"}

    def test_remove_zone(self):
        mgr = StoryManager(make_story())
        assert mgr.remove_zone("TestZone") is True
        assert mgr.remove_zone("TestZone") is False
        assert "TestZone" not in mgr.story._zones

    def test_link_zones(self):
        mgr = StoryManager(make_story())
        mgr.add_zone({"name": "SecondZone", "description": "second"})
        assert mgr.link_zones("TestZone", "SecondZone", "north") is True
        assert mgr.story.get_zone("SecondZone").neighbors["south"] is mgr.story.get_zone("TestZone")
        assert mgr.story.get_zone("TestZone").neighbors["north"] is mgr.story.get_zone("SecondZone")


class TestLocations():

    def test_add_location(self):
        mgr = StoryManager(make_story())
        ok, error = mgr.add_location({"name": "Room", "descr": "A room", "world_location": [0, 0, 0]}, "TestZone")
        assert ok is True
        assert error == ""
        loc = mgr.story.get_location("TestZone", "Room")
        assert loc is not None
        assert loc.description == "A room"
        assert loc.world_location.as_tuple() == (0, 0, 0)

    def test_add_location_requires_name(self):
        mgr = StoryManager(make_story())
        ok, error = mgr.add_location({"descr": "no name"}, "TestZone")
        assert ok is False
        assert "name" in error

    def test_get_location(self):
        mgr = StoryManager(make_story())
        mgr.add_location({"name": "Room", "descr": "A room", "world_location": [1, 2, 3]}, "TestZone")
        info = mgr.get_location("TestZone", "Room")
        assert info["name"] == "Room"
        assert info["world_location"] == [1, 2, 3]
        assert info["descr"] == "A room"

    def test_list_locations(self):
        mgr = StoryManager(make_story())
        mgr.add_location({"name": "Room", "descr": "A room"}, "TestZone")
        mgr.add_location({"name": "Hall", "descr": "A hall"}, "TestZone")
        names = {loc["name"] for loc in mgr.list_locations("TestZone")}
        assert names == {"Room", "Hall"}

    def test_remove_location(self):
        mgr = StoryManager(make_story())
        mgr.add_location({"name": "Room", "descr": "A room"}, "TestZone")
        assert mgr.remove_location("TestZone", "Room") is True
        assert mgr.story.get_location("TestZone", "Room") is None
        assert mgr.remove_location("TestZone", "Room") is False

    def test_set_exits_creates_destination(self):
        mgr = StoryManager(make_story())
        mgr.add_location({"name": "Room", "descr": "A room", "world_location": [0, 0, 0]}, "TestZone")
        assert mgr.set_exits("TestZone", "Room", [
            {"direction": "north", "name": "Forest", "short_descr": "A forest"},
        ]) is True
        loc = mgr.story.get_location("TestZone", "Room")
        assert "north" in loc.exits
        assert loc.exits["north"].target.name == "Forest"
        # the destination location was created
        assert mgr.story.find_location("Forest") is not None

    def test_set_exits_skips_occupied_direction(self):
        mgr = StoryManager(make_story())
        mgr.add_location({"name": "Room", "descr": "A room", "world_location": [0, 0, 0]}, "TestZone")
        mgr.set_exits("TestZone", "Room", [{"direction": "north", "name": "Forest"}])
        # second north exit should be skipped
        mgr.set_exits("TestZone", "Room", [{"direction": "north", "name": "Lake"}])
        assert mgr.story.get_location("TestZone", "Room").exits["north"].target.name == "Forest"

    def test_set_exits_unknown_zone(self):
        mgr = StoryManager(make_story())
        assert mgr.set_exits("Nope", "Room", []) is False

    def test_add_location_complex(self):
        mgr = StoryManager(make_story())
        ok, error = mgr.add_location({
          "name": "The Ancient Oak",
          "description": "A massive oak with gnarled roots that seem to pulse with ancient energy.",
          "short_descr": "A towering, moss-covered tree at the edge of the Whispering Woods.",
          "world_location": [1, 2, 3],
          "items": ["ancient_key"],
          "npcs": [],
          "indoors": "false"
        }, "TestZone")
        assert ok is True
        assert error == ""
        loc = mgr.story.get_location("TestZone", "The Ancient Oak")
        assert loc is not None
        assert loc.description == "A massive oak with gnarled roots that seem to pulse with ancient energy."
        assert loc.world_location.as_tuple() == (1, 2, 3)


class TestCatalogue():

    def test_add_and_list_items(self):
        mgr = StoryManager(make_story())
        assert mgr.add_item({"name": "sword", "type": "Weapon"}) is True
        assert mgr.add_item({"name": "sword", "type": "Weapon"}) is False  # duplicate
        names = [i["name"] for i in mgr.list_items()]
        assert "sword" in names

    def test_add_and_list_creatures(self):
        mgr = StoryManager(make_story())
        assert mgr.add_creature({"name": "goblin", "type": "Mob", "level": 1}) is True
        names = [c["name"] for c in mgr.list_creatures()]
        assert "goblin" in names

    def test_remove_item_and_creature(self):
        mgr = StoryManager(make_story())
        mgr.add_item({"name": "sword"})
        mgr.add_creature({"name": "goblin"})
        assert mgr.remove_item("sword") is True
        assert mgr.remove_item("sword") is False
        assert mgr.remove_creature("goblin") is True
        assert "sword" not in [i["name"] for i in mgr.list_items()]
        assert "goblin" not in [c["name"] for c in mgr.list_creatures()]


class TestWorldContents():

    def _seed(self, mgr):
        mgr.add_creature({"name": "goblin", "type": "Mob", "gender": "m", "race": "human",
                          "level": 1, "description": "A goblin"})
        mgr.add_item({"name": "torch", "type": "Other"})
        mgr.add_location({"name": "Cave", "descr": "A cave", "world_location": [0, 0, 0]}, "TestZone")

    def test_spawn_npc(self):
        mgr = StoryManager(make_story())
        self._seed(mgr)
        assert mgr.spawn_npc("goblin", "TestZone", "Cave") is True
        assert mgr.spawn_npc("goblin", "TestZone", "Cave") is True  # spawn again is fine
        npcs = mgr.list_world_npcs()
        assert npcs["Goblin"] is not None
        assert mgr.story.world.get_npc("goblin") is not None

    def test_spawn_item(self):
        mgr = StoryManager(make_story())
        self._seed(mgr)
        assert mgr.spawn_item("torch", "TestZone", "Cave") is True
        items = mgr.list_world_items()
        assert any(i["name"] == "torch" for i in items)

    def test_spawn_unknown_creature(self):
        mgr = StoryManager(make_story())
        mgr.add_location({"name": "Cave", "descr": "A cave"}, "TestZone")
        assert mgr.spawn_npc("nonexistent", "TestZone", "Cave") is False

    def test_spawn_to_unknown_location(self):
        mgr = StoryManager(make_story())
        mgr.add_creature({"name": "goblin", "type": "Mob", "gender": "m", "race": "human",
                          "level": 1, "description": "A goblin"})
        assert mgr.spawn_npc("goblin", "TestZone", "Nope") is False


class TestWorldStore():
    """Tests for adding/getting live NPCs and items to/from the world's
    live-object store (real Living/Item objects, not catalogue dicts)."""

    def test_add_and_get_world_npc(self):
        mgr = StoryManager(make_story())
        ok, error = mgr.add_world_npc({"name": "Goblin", "type": "Mob", "race": "human",
                                       "gender": "m", "level": 1, "description": "A goblin"})
        assert ok is True
        assert error == ""
        npc = mgr.get_world_npc("Goblin")
        assert npc["name"] == "Goblin"
        # the NPC is in the world's live store (keyed lowercase)
        assert mgr.story.world.get_npc("goblin") is not None

    def test_add_world_npc_duplicate(self):
        mgr = StoryManager(make_story())
        ok, error = mgr.add_world_npc({"name": "Goblin", "type": "Mob"})
        assert ok is True
        assert error == ""
        ok, error = mgr.add_world_npc({"name": "Goblin", "type": "Mob"})
        assert ok is False  # duplicate
        assert "already exists" in error

    def test_add_world_npc_not_loaded(self):
        mgr = StoryManager(make_story())
        # a dict that cannot be loaded into a Living
        ok, error = mgr.add_world_npc({"type": "Mob"})
        assert ok is False  # missing name
        assert "name" in error

    def test_get_world_npc_not_found(self):
        mgr = StoryManager(make_story())
        assert mgr.get_world_npc("Nope") == {}

    def test_add_and_get_world_item(self):
        mgr = StoryManager(make_story())
        ok, error = mgr.add_world_item({"name": "Torch", "type": "Other"})
        assert ok is True
        assert error == ""
        item = mgr.get_world_item("Torch")
        assert item["name"] == "torch"
        # the item is in the world's live store (keyed lowercase)
        assert mgr.story.world.get_item("torch") is not None

    def test_add_world_item_duplicate(self):
        mgr = StoryManager(make_story())
        ok, error = mgr.add_world_item({"name": "Torch", "type": "Other"})
        assert ok is True
        assert error == ""
        ok, error = mgr.add_world_item({"name": "Torch", "type": "Other"})
        assert ok is False  # duplicate
        assert "already exists" in error

    def test_add_world_item_not_loaded(self):
        mgr = StoryManager(make_story())
        # a dict that cannot be loaded into an Item
        ok, error = mgr.add_world_item({"type": "Other"})
        assert ok is False  # missing name
        assert "name" in error

    def test_get_world_item_not_found(self):
        mgr = StoryManager(make_story())
        assert mgr.get_world_item("Nope") == {}


class TestStoryProgression():

    def test_set_story_context(self):
        mgr = StoryManager(make_story())
        mgr.set_story_context("A grand adventure")
        assert isinstance(mgr.story.config.context, StoryContext)
        assert mgr.story.config.context.base_story == "A grand adventure"

    def test_advance_story_section(self):
        mgr = StoryManager(make_story())
        mgr.set_story_context("Base plot")
        mgr.advance_story_section("The beginning")
        assert mgr.story.config.context.current_section == "The beginning"

    def test_set_start_location(self):
        mgr = StoryManager(make_story())
        mgr.set_start_location("TestZone", "Cave")
        assert mgr.story.config.startlocation_player == "TestZone.Cave"
        assert mgr.story.config.startlocation_wizard == "TestZone.Cave"


class TestPersistence():

    def test_load_fixture(self):
        mgr = StoryManager(make_story())
        mgr.load("tests/files/world_story/")
        assert mgr.story.get_zone("Cave") is not None
        entrance = mgr.story.get_location("Cave", "Cave entrance")
        assert entrance is not None
        # the catalogue was loaded from the fixture
        assert len(mgr.story.catalogue.get_creatures()) >= 1

    def test_save_absolute_path_allowed(self):
        # the MCP server routes saves through StoryManager, which allows
        # (validated) absolute paths
        mgr = StoryManager(make_story())
        target = tempfile.mkdtemp(prefix='llamatale_mgr_save_')
        try:
            mgr.save(target)
            assert os.path.exists(os.path.join(target, 'world.json'))
            assert os.path.exists(os.path.join(target, 'story_config.json'))
        finally:
            shutil.rmtree(target, ignore_errors=True)

    def test_save_forbidden_absolute_path(self):
        mgr = StoryManager(make_story())
        for path in ('/', '/etc', '/usr/local/saves'):
            with pytest.raises(SecurityViolation):
                mgr.save(path)


class TestLlmGeneration():
    """Tests for the optional LLM-backed generation methods, using a fake llm_util."""

    class FakeLlmUtil:
        def __init__(self):
            self.build_calls = 0

        def generate_world_items(self, count=7):
            return types.SimpleNamespace(valid=True, items=[{"name": "wand", "type": "Weapon", "value": 100}])

        def generate_world_creatures(self, count=5):
            return types.SimpleNamespace(valid=True, creatures=[{"name": "dragon", "level": 9}])

        def generate_start_zone(self, **kwargs):
            return Zone("GeneratedZone", "a generated zone")

        def build_location(self, location, exit_location_name, zone_info, neighbors=None, zone=None):
            self.build_calls += 1
            json_result = {
                "name": location.name,
                "description": location.description,
                "exits": [{"direction": "north", "name": "Generated Room", "description": "A generated room"}],
                "npcs": [{"name": "Wise Old Man", "type": "Npc", "gender": "m", "race": "human",
                          "level": 3, "description": "A wise old man"}],
            }
            response = LocationResponse(json_result, location, location.name)
            return response, None

    def test_generate_world_items_requires_llm(self):
        mgr = StoryManager(make_story(), llm_util=None)
        with pytest.raises(RuntimeError):
            mgr.generate_world_items()

    def test_generate_world_items(self):
        mgr = StoryManager(make_story(), llm_util=self.FakeLlmUtil())
        items = mgr.generate_world_items(count=9)
        assert items[0]["name"] == "wand"

    def test_generate_world_creatures(self):
        mgr = StoryManager(make_story(), llm_util=self.FakeLlmUtil())
        creatures = mgr.generate_world_creatures()
        assert creatures[0]["name"] == "dragon"

    def test_generate_start_zone(self):
        mgr = StoryManager(make_story(), llm_util=self.FakeLlmUtil())
        info = mgr.generate_start_zone("a road")
        assert info["description"] == "a generated zone"

    def test_generate_location_applies(self):
        story = make_story()
        mgr = StoryManager(story, llm_util=self.FakeLlmUtil())
        mgr.add_location({"name": "Start", "descr": "You are at start", "world_location": [0, 0, 0]}, "TestZone")
        loc = story.get_location("TestZone", "Start")
        result = mgr.generate_location("TestZone", "Start", "north")
        # the result is the serialized source location
        assert result["name"] == "Start"
        # the fake llm_util recorded a build call
        assert mgr._llm_util.build_calls == 1
        # the generated destination location was added
        assert story.find_location("Generated Room") is not None
        # the exit was added to the source location
        assert "north" in loc.exits
        # the npc was added to the live world
        assert story.world.get_npc("Wise Old Man") is not None

    def test_generate_location_without_llm_raises(self):
        mgr = StoryManager(make_story(), llm_util=None)
        with pytest.raises(RuntimeError):
            mgr.generate_location("TestZone", "Start", "north")


class TestNarrativeStage4():
    """Tests for the Stage 4 LLM-driven narrative methods (npc_act,
    trigger_narrative_event), using a fake llm_util.

    ``npc_act`` delegates to ``LivingNpc.idle_action``, which pulls the LLM
    from ``mud_context.driver.llm_util`` (mirroring how the real driver wires
    the same object into both the StoryManager and the mud context).
    """

    class FakeLlmUtil:
        def __init__(self):
            self.perform_idle_action_calls = 0
            self.narrative_event_calls = 0
            self.narrative_text = "A shadow stirs in the corner."
            self.last_location = None

        def perform_idle_action(self, **kwargs):
            self.perform_idle_action_calls += 1
            return ["The goblin scratches itself idly."]

        def generate_narrative_event(self, location):
            self.narrative_event_calls += 1
            self.last_location = location
            return self.narrative_text

    def setup_method(self):
        self._saved = (mud_context.config, mud_context.driver)
        mud_context.config = StoryConfig()
        mud_context.config.server_tick_method = 'TIMER'
        mud_context.driver = FakeDriver()

    def teardown_method(self):
        mud_context.config, mud_context.driver = self._saved

    def _seed_location(self, mgr):
        mgr.add_location({"name": "Cave", "descr": "A cave",
                          "short_descr": "A cave", "world_location": [0, 0, 0]}, "TestZone")

    def _spawn_npc(self, mgr, name="Goblin", location="Cave"):
        npc = LivingNpc(name=name, gender="m", age=30, personality="")
        mgr.story.get_location("TestZone", location).insert(npc, None)
        mgr.story.world.add_npc(npc)
        return npc

    def test_npc_act(self):
        fake = self.FakeLlmUtil()
        mud_context.driver.llm_util = fake
        mgr = StoryManager(make_story(), llm_util=fake)
        self._seed_location(mgr)
        npc = self._spawn_npc(mgr)
        result = mgr.npc_act("Goblin")
        assert result == {"action": "The goblin scratches itself idly."}
        # idle_action() was invoked and recorded the performed action
        assert fake.perform_idle_action_calls == 1
        assert npc.action_history == ["The goblin scratches itself idly."]

    def test_npc_act_case_insensitive(self):
        fake = self.FakeLlmUtil()
        mud_context.driver.llm_util = fake
        mgr = StoryManager(make_story(), llm_util=fake)
        self._seed_location(mgr)
        self._spawn_npc(mgr, name="goblin")
        assert mgr.npc_act("GOBLIN") == {"action": "The goblin scratches itself idly."}

    def test_npc_act_unknown(self):
        fake = self.FakeLlmUtil()
        mud_context.driver.llm_util = fake
        mgr = StoryManager(make_story(), llm_util=fake)
        assert mgr.npc_act("Nobody") == {}

    def test_npc_act_requires_llm(self):
        mgr = StoryManager(make_story(), llm_util=None)
        self._seed_location(mgr)
        self._spawn_npc(mgr)
        assert mgr.npc_act("Goblin") == {}

    def test_trigger_narrative_event(self):
        fake = self.FakeLlmUtil()
        mgr = StoryManager(make_story(), llm_util=fake)
        self._seed_location(mgr)
        text = mgr.trigger_narrative_event("TestZone", "Cave")
        assert text == "A shadow stirs in the corner."
        assert fake.narrative_event_calls == 1
        # the fake received the live location object
        assert fake.last_location.name == "Cave"

    def test_trigger_narrative_event_unknown(self):
        mgr = StoryManager(make_story(), llm_util=self.FakeLlmUtil())
        assert mgr.trigger_narrative_event("TestZone", "Nope") == ""

    def test_trigger_narrative_event_requires_llm(self):
        mgr = StoryManager(make_story(), llm_util=None)
        self._seed_location(mgr)
        assert mgr.trigger_narrative_event("TestZone", "Cave") == ""

class TestLiveState():
    """Tests for the Stage 1 read-only live-state reads (players, NPCs,
    locations, story progress, and the world map)."""

    class StubDriver:
        """A tiny driver stub exposing ``all_players`` (name -> connection with
        a ``.player``), as the real driver does."""
        def __init__(self, players):
            self.all_players = {p.name: types.SimpleNamespace(player=p) for p in players}

    def _seed(self, mgr):
        """A location with a live NPC and a live item."""
        mgr.add_location({"name": "Cave", "descr": "A cave", "short_descr": "A cave",
                          "world_location": [0, 0, 0]}, "TestZone")
        # for a Mob, the long description comes from 'descr' (description -> short)
        mgr.add_creature({"name": "goblin", "type": "Mob", "gender": "m", "race": "human",
                          "level": 2, "descr": "A goblin"})
        assert mgr.spawn_npc("goblin", "TestZone", "Cave") is True
        mgr.add_item({"name": "torch", "type": "Other"})
        assert mgr.spawn_item("torch", "TestZone", "Cave") is True
        return mgr.story.get_location("TestZone", "Cave")

    def test_list_players_no_driver(self):
        mgr = StoryManager(make_story())
        assert mgr.list_players() == []

    def test_list_players(self):
        mgr = StoryManager(make_story())
        cave = self._seed(mgr)
        hero = Living("Hero", "m")
        hero.location = cave
        hero.idle_time = 1.5
        mgr._driver = self.StubDriver([hero])
        players = mgr.list_players()
        assert len(players) == 1
        p = players[0]
        assert p["name"] == "hero"
        assert p["location"] == {"zone": "TestZone", "name": "Cave"}
        assert p["alive"] is True
        assert p["hp"] == hero.stats.hp
        assert p["idle_time"] == 1.5

    def test_get_player(self):
        mgr = StoryManager(make_story())
        cave = self._seed(mgr)
        hero = Living("Hero", "m")
        hero.location = cave
        mgr._driver = self.StubDriver([hero])
        info = mgr.get_player("HERO")   # case-insensitive
        assert info["name"] == "hero"
        assert info["title"] == "Hero"
        assert info["location"] == {"zone": "TestZone", "name": "Cave"}
        assert info["alive"] is True
        assert info["hp"] == hero.stats.hp
        assert "level" in info["stats"]
        assert info["inventory"] == []

    def test_get_player_not_found(self):
        mgr = StoryManager(make_story())
        hero = Living("Hero", "m")
        mgr._driver = self.StubDriver([hero])
        assert mgr.get_player("Nope") == {}   # driver present, no such player
        # no driver at all -> {}
        assert StoryManager(make_story()).get_player("Hero") == {}

    def test_get_npc(self):
        mgr = StoryManager(make_story())
        cave = self._seed(mgr)
        info = mgr.get_npc("Goblin")
        assert info["name"] == "goblin"
        assert info["description"] == "A goblin"
        assert info["alive"] is True
        assert info["level"] == 2
        assert "hp" in info["stats"]
        # a plain Living has no goal/action_history -> defaults
        assert info["goal"] is None
        assert info["action_history"] == []

    def test_get_npc_not_found(self):
        mgr = StoryManager(make_story())
        assert mgr.get_npc("Nope") == {}

    def test_get_location_live(self):
        mgr = StoryManager(make_story())
        cave = self._seed(mgr)
        hero = Living("Hero", "m")
        cave.insert(hero, None)   # adds to cave.livings and sets hero.location
        mgr._driver = self.StubDriver([hero])
        info = mgr.get_location_live("TestZone", "Cave")
        assert info["name"] == "Cave"
        assert info["description"] == "A cave"
        assert info["short_descr"] == "A cave"
        assert info["indoors"] is False
        assert info["world_location"] == [0, 0, 0]
        # one player (Hero) and one NPC (goblin)
        living_names = {l["name"]: l for l in info["livings"]}
        assert set(living_names) == {"hero", "goblin"}
        assert living_names["hero"]["is_player"] is True
        assert living_names["goblin"]["is_player"] is False
        assert living_names["goblin"]["alive"] is True
        # the spawned item is present
        assert any(i["name"] == "torch" for i in info["items"])

    def test_get_location_live_not_found(self):
        mgr = StoryManager(make_story())
        assert mgr.get_location_live("TestZone", "Nope") == {}
        assert mgr.get_location_live("Nope", "Cave") == {}

    def test_get_story_state(self):
        mgr = StoryManager(make_story())
        story = mgr.story
        story.config.type = "A fantasy adventure"
        story.config.world_info = "A world of magic"
        story.config.world_mood = 3
        story.config.context = StoryContext("Base plot")
        story.config.context.set_current_section("The beginning")
        state = mgr.get_story_state()
        assert state["name"] == "Test Story"
        assert state["type"] == "A fantasy adventure"
        assert state["world_info"] == "A world of magic"
        assert state["world_mood"] == 3
        assert state["current_section"] == "The beginning"
        assert state["progress"] == 0.0
        assert "Base plot" in state["story"]

    def test_get_world_map(self):
        mgr = StoryManager(make_story())
        self._seed(mgr)
        world_map = mgr.get_world_map()
        assert "TestZone" in world_map
        cave = world_map["TestZone"]["Cave"]
        assert cave["indoors"] is False
        assert cave["npc_count"] == 1
        assert cave["item_count"] == 1
        assert cave["exits"] == []

    def test_world_map_multiple_locations(self):
        mgr = StoryManager(make_story())
        mgr.add_location({"name": "Room", "descr": "A room", "world_location": [0, 0, 0]}, "TestZone")
        mgr.add_location({"name": "Hall", "descr": "A hall", "world_location": [1, 0, 0]}, "TestZone")
        mgr.set_exits("TestZone", "Room", [{"direction": "north", "name": "Hall"}])
        world_map = mgr.get_world_map()
        # an exit is keyed by the direction *and* the target name (an alias),
        # and the map sorts the keys
        assert world_map["TestZone"]["Room"]["exits"] == ["hall", "north"]


class TestEventPolling():
    """Tests for the Stage 2 event ring buffer (``StoryEvents``) and the
    ``StoryManager`` polling/subscription wiring."""

    class StubDriver:
        """A tiny driver stub exposing ``all_players`` (name -> connection with
        a ``.player``), as the real driver does."""
        def __init__(self, players):
            self.all_players = {p.name: types.SimpleNamespace(player=p) for p in players}

    @staticmethod
    def _flush():
        """Deliver pending pubsub events to subscribers.

        ``Location.tell``/``Living.tell`` send their wiretap event with
        ``synchronous=False``; the driver delivers it to subscribers (our
        ``StoryEvents`` listener) during ``pubsub.sync()`` each tick. In the
        test there is no driver, so we call ``sync()`` after each ``tell``.
        """
        pubsub.sync()

    # --- StoryEvents unit tests ----------------------------------------------

    def test_storyevents_only_captures_wiretap(self):
        from tale.mcp.events import StoryEvents
        ev = StoryEvents()
        ev.pubsub_event(("wiretap-location", "Cave#1"), ("Cave", "A door creaks."))
        ev.pubsub_event(("wiretap-living", "goblin#2"), ("goblin", "I'm hungry."))
        # non-wiretap topics are ignored
        ev.pubsub_event("driver-pending-tells", ("hero", "go north"))
        ev.pubsub_event(("wiretap-location", "Cave#1"), ("Cave", None))   # still wiretap
        events = ev.since(0)
        assert len(events) == 3
        assert events[0]["kind"] == "wiretap-location"
        assert events[0]["source"] == "Cave"
        assert events[0]["text"] == "A door creaks."
        assert events[1]["kind"] == "wiretap-living"
        assert events[1]["source"] == "goblin"
        assert events[1]["text"] == "I'm hungry."
        # indexes are monotonically increasing
        assert [e["index"] for e in events] == [1, 2, 3]

    def test_storyevents_since_filters(self):
        from tale.mcp.events import StoryEvents
        ev = StoryEvents()
        for i in range(1, 5):
            ev.pubsub_event(("wiretap-location", "Cave#1"), ("Cave", "msg %d" % i))
        # only newer records
        since_2 = ev.since(2)
        assert [e["text"] for e in since_2] == ["msg 3", "msg 4"]
        assert since_2[0]["index"] == 3
        # cursor is the latest index
        assert ev.cursor == 4
        # since the latest -> empty
        assert ev.since(4) == []

    def test_storyevents_maxlen_ring(self):
        from tale.mcp.events import StoryEvents
        ev = StoryEvents(maxlen=2)
        for i in range(1, 6):
            ev.pubsub_event(("wiretap-location", "Cave#1"), ("Cave", "msg %d" % i))
        # only the two most recent survive; indexes keep increasing
        events = ev.since(0)
        assert [e["text"] for e in events] == ["msg 4", "msg 5"]
        assert [e["index"] for e in events] == [4, 5]
        # the cursor still reflects the total count (used to avoid re-reading)
        assert ev.cursor == 5

    # --- StoryManager polling / subscription wiring ---------------------------

    def test_poll_empty_when_no_events(self):
        mgr = StoryManager(make_story())
        assert mgr.poll_events() == []
        assert mgr._events.cursor == 0

    def test_poll_captures_location_tell(self):
        mgr = StoryManager(make_story())
        mgr.add_location({"name": "Cave", "descr": "A cave", "world_location": [0, 0, 0]}, "TestZone")
        location = mgr.story.get_location("TestZone", "Cave")
        # the manager subscribed to the location's wiretap on creation
        location.tell("A door creaks open.")
        self._flush()
        events = mgr.poll_events(0)
        assert len(events) == 1
        e = events[0]
        assert e["kind"] == "wiretap-location"
        assert e["source"] == "Cave"
        assert e["text"] == "A door creaks open."
        assert e["index"] == 1
        assert e["time"] > 0

    def test_poll_since_returns_only_newer(self):
        mgr = StoryManager(make_story())
        mgr.add_location({"name": "Cave", "descr": "A cave", "world_location": [0, 0, 0]}, "TestZone")
        location = mgr.story.get_location("TestZone", "Cave")
        location.tell("first")
        location.tell("second")
        self._flush()
        # cursor at 1 -> only the second event
        events = mgr.poll_events(1)
        assert [e["text"] for e in events] == ["second"]
        assert events[0]["index"] == 2
        # the full history is still available from 0
        assert [e["text"] for e in mgr.poll_events(0)] == ["first", "second"]

    def test_poll_new_location_subscribed(self):
        mgr = StoryManager(make_story())
        # create the manager, then add a location *after* construction
        mgr.add_location({"name": "Room", "descr": "A room", "world_location": [0, 0, 0]}, "TestZone")
        location = mgr.story.get_location("TestZone", "Room")
        location.tell("A gust of wind.")
        self._flush()
        events = mgr.poll_events(0)
        assert len(events) == 1
        assert events[0]["source"] == "Room"

    def test_poll_captures_npc_tell(self):
        mgr = StoryManager(make_story())
        mgr.add_location({"name": "Cave", "descr": "A cave", "world_location": [0, 0, 0]}, "TestZone")
        mgr.add_creature({"name": "goblin", "type": "Mob", "gender": "m", "race": "human",
                          "level": 1, "description": "A goblin"})
        assert mgr.spawn_npc("goblin", "TestZone", "Cave") is True
        npc = mgr.story.world.get_npc("goblin")
        npc.tell("I'm hungry.")
        self._flush()
        events = mgr.poll_events(0)
        assert any(e["kind"] == "wiretap-living" and e["source"] == "goblin"
                   and e["text"] == "I'm hungry." for e in events)

    def test_poll_captures_player_tell(self):
        mgr = StoryManager(make_story())
        mgr.add_location({"name": "Cave", "descr": "A cave", "world_location": [0, 0, 0]}, "TestZone")
        cave = mgr.story.get_location("TestZone", "Cave")
        hero = Living("Hero", "m")
        hero.location = cave
        mgr._driver = self.StubDriver([hero])
        # re-subscribe to pick up the player's wiretap
        mgr._subscribe_events()
        hero.tell("I look around.")
        self._flush()
        events = mgr.poll_events(0)
        assert any(e["kind"] == "wiretap-living" and e["source"] == "hero"
                   and e["text"] == "I look around." for e in events)

    def test_reset_events_clears(self):
        mgr = StoryManager(make_story())
        mgr.add_location({"name": "Cave", "descr": "A cave", "world_location": [0, 0, 0]}, "TestZone")
        location = mgr.story.get_location("TestZone", "Cave")
        location.tell("one")
        location.tell("two")
        self._flush()
        assert len(mgr.poll_events(0)) == 2
        mgr.reset_events()
        assert mgr.poll_events(0) == []
        assert mgr._events.cursor == 0
        # after reset the manager is still subscribed (new events are captured)
        location.tell("three")
        self._flush()
        events = mgr.poll_events(0)
        assert [e["text"] for e in events] == ["three"]
        assert events[0]["index"] == 1

    def test_events_are_json_serializable(self):
        import json
        mgr = StoryManager(make_story())
        mgr.add_location({"name": "Cave", "descr": "A cave", "world_location": [0, 0, 0]}, "TestZone")
        location = mgr.story.get_location("TestZone", "Cave")
        location.tell("A door creaks.")
        self._flush()
        # the MCP wrapper serializes the list to a single JSON string
        json.dumps(mgr.poll_events(0), indent=2, default=str)


class TestLiveMutations():
    """Tests for the Stage 3 live-world mutations (descriptions, exits, NPC
    movement/actions and goals)."""

    def setup_method(self):
        # Stage 3 NPC movement/actions need a mud_context with a config (for
        # look/show_exits_in_look) and a driver (for combat prompts).
        saved = (mud_context.config, mud_context.driver)
        mud_context.config = StoryConfig()
        mud_context.driver = FakeDriver()
        self._saved = saved

    def teardown_method(self):
        mud_context.config, mud_context.driver = self._saved

    def _seed(self, story=None):
        """A story with Cave<->Hall (plain exits), a locked Door to NorthRoom,
        a goblin NPC in Cave, an orc NPC in Hall and a torch item in Cave."""
        if story is None:
            story = make_story()
        story.config.name = "Test Story"
        mgr = StoryManager(story)
        mgr.add_location({"name": "Cave", "descr": "A cave", "short_descr": "A cave",
                          "world_location": [0, 0, 0]}, "TestZone")
        mgr.add_location({"name": "Hall", "descr": "A hall", "short_descr": "A hall",
                          "world_location": [1, 0, 0]}, "TestZone")
        mgr.set_exits("TestZone", "Cave", [{"direction": "east", "name": "Hall"}])
        # a locked door from Cave to NorthRoom
        mgr.add_location({"name": "NorthRoom", "descr": "A room to the north",
                          "short_descr": "North room", "world_location": [0, 1, 0]}, "TestZone")
        door = Door("north", mgr.story.get_location("TestZone", "NorthRoom"),
                    "a door", "A door to the north", locked=True, opened=False)
        cave = mgr.story.get_location("TestZone", "Cave")
        cave.add_exits([door])
        # live NPCs and an item
        mgr.add_creature({"name": "goblin", "type": "Mob", "gender": "m", "race": "human",
                          "level": 2, "descr": "A goblin"})
        assert mgr.spawn_npc("goblin", "TestZone", "Cave") is True
        mgr.add_creature({"name": "orc", "type": "Mob", "gender": "m", "race": "human",
                          "level": 2, "descr": "An orc"})
        assert mgr.spawn_npc("orc", "TestZone", "Hall") is True
        mgr.add_item({"name": "torch", "type": "Other"})
        assert mgr.spawn_item("torch", "TestZone", "Cave") is True
        return mgr

    def test_find_living(self):
        mgr = self._seed()
        assert mgr._find_living("goblin").name == "goblin"
        assert mgr._find_living("Goblin").name == "goblin"   # case-insensitive
        assert mgr._find_living("orc").name == "orc"
        assert mgr._find_living("nonexistent") is None

    def test_set_location_description(self):
        mgr = self._seed()
        ok, err = mgr.set_location_description("TestZone", "Cave", "A dark, dank cave.",
                                                short_descr="A dark cave.")
        assert ok is True and err == ""
        cave = mgr.story.get_location("TestZone", "Cave")
        assert cave.description == "A dark, dank cave."
        assert cave.short_description == "A dark cave."

    def test_set_location_description_short_descr_optional(self):
        mgr = self._seed()
        ok, err = mgr.set_location_description("TestZone", "Cave", "A dark, dank cave.")
        assert ok is True and err == ""
        # short description is left untouched when not provided
        cave = mgr.story.get_location("TestZone", "Cave")
        assert cave.description == "A dark, dank cave."
        assert cave.short_description == "A cave"

    def test_set_location_description_unknown_zone(self):
        mgr = self._seed()
        ok, err = mgr.set_location_description("Nope", "Cave", "desc")
        assert ok is False and "zone 'Nope'" in err

    def test_set_location_description_unknown_location(self):
        mgr = self._seed()
        ok, err = mgr.set_location_description("TestZone", "Nope", "desc")
        assert ok is False and "location 'Nope'" in err

    def test_add_exit_creates_location_and_return_exit(self):
        mgr = self._seed()
        ok, err = mgr.add_exit("TestZone", "Cave", "down", "Forest")
        assert ok is True and err == ""
        forest = mgr.story.get_location("TestZone", "Forest")
        # the exit in the new location points back to Cave
        assert "cave" in forest.exits
        cave = mgr.story.get_location("TestZone", "Cave")
        assert "forest" in cave.exits and "north" in cave.exits

    def test_add_exit_existing_target_in_direction(self):
        mgr = self._seed()
        ok, err = mgr.add_exit("TestZone", "Cave", "east", "Hall")
        assert ok is False and "already exists" in err

    def test_add_exit_missing_target_name(self):
        mgr = self._seed()
        ok, err = mgr.add_exit("TestZone", "Cave", "east", "")
        assert ok is False and "target" in err

    def test_remove_exit(self):
        mgr = self._seed()
        ok, err = mgr.remove_exit("TestZone", "Cave", "east")
        assert ok is True and err == ""
        assert "east" not in mgr.story.get_location("TestZone", "Cave").exits

    def test_remove_exit_unknown(self):
        mgr = self._seed()
        ok, err = mgr.remove_exit("TestZone", "Cave", "northeast")
        assert ok is False and "no exit" in err

    def test_set_exit_state_door(self):
        mgr = self._seed()
        door = mgr.story.get_location("TestZone", "Cave").exits["north"]
        assert door.opened is False
        ok, err = mgr.set_exit_state("TestZone", "Cave", "north", True)
        assert ok is True and err == ""
        assert door.opened is True
        ok, err = mgr.set_exit_state("TestZone", "Cave", "north", False)
        assert ok is True and err == ""
        assert door.opened is False

    def test_set_exit_state_plain_exit_closes(self):
        mgr = self._seed()
        ok, err = mgr.set_exit_state("TestZone", "Cave", "east", False)
        assert ok is True and err == ""
        # closing a plain exit removes it
        assert "east" not in mgr.story.get_location("TestZone", "Cave").exits

    def test_set_exit_state_plain_exit_reopen_missing(self):
        mgr = self._seed()
        # first close, then trying to reopen a removed plain exit fails
        mgr.set_exit_state("TestZone", "Cave", "east", False)
        ok, err = mgr.set_exit_state("TestZone", "Cave", "east", True)
        assert ok is False and "no exit" in err

    def test_move_npc(self):
        mgr = self._seed()
        goblin = mgr.story.world.get_npc("goblin")
        assert goblin.location.name == "Cave"
        ok, err = mgr.move_npc("goblin", "TestZone", "Hall")
        assert ok is True and err == ""
        assert goblin.location.name == "Hall"

    def test_move_npc_unknown_living(self):
        mgr = self._seed()
        ok, err = mgr.move_npc("noone", "TestZone", "Hall")
        assert ok is False and "not found" in err

    def test_move_npc_unknown_location(self):
        mgr = self._seed()
        ok, err = mgr.move_npc("goblin", "TestZone", "Nope")
        assert ok is False and "not found" in err

    def test_npc_say(self):
        mgr = self._seed()
        ok, err = mgr.npc_say("goblin", "Halt, traveller!")
        assert ok is True and err == ""

    def test_npc_say_missing_text(self):
        mgr = self._seed()
        ok, err = mgr.npc_say("goblin", "")
        assert ok is False and "text is required" in err

    def test_npc_say_unknown_target(self):
        mgr = self._seed()
        ok, err = mgr.npc_say("goblin", "hi", target="noone")
        assert ok is False and "not found" in err

    def test_npc_attack(self):
        mgr = self._seed()
        ok, err = mgr.npc_attack("goblin", "orc")
        assert ok is True and err == ""

    def test_npc_attack_unknown_target(self):
        mgr = self._seed()
        ok, err = mgr.npc_attack("goblin", "noone")
        assert ok is False and "not found" in err

    def test_npc_attack_missing_target(self):
        mgr = self._seed()
        ok, err = mgr.npc_attack("goblin", "")
        assert ok is False and "target_name" in err

    def test_set_npc_goal(self):
        mgr = self._seed()
        goblin = mgr.story.world.get_npc("goblin")
        ok, err = mgr.set_npc_goal("goblin", "Guard the cave.")
        assert ok is True and err == ""
        assert goblin.goal == "Guard the cave."

    def test_set_npc_goal_unknown_living(self):
        mgr = self._seed()
        ok, err = mgr.set_npc_goal("noone", "some goal")
        assert ok is False and "not found" in err

    def test_npc_do_move(self):
        mgr = self._seed()
        goblin = mgr.story.world.get_npc("goblin")
        assert goblin.location.name == "Cave"
        ok, err = mgr.npc_do("goblin", {"action": "move", "target": "hall"})
        assert ok is True and err == ""
        assert goblin.location.name == "Hall"

    def test_npc_do_take(self):
        mgr = self._seed()
        ok, err = mgr.npc_do("goblin", {"action": "take", "item": "torch"})
        assert ok is True and err == ""
        # the item is now in the npc's location
        torch = mgr.story.world.get_item("torch")
        assert torch.location.name == "Cave"

    def test_npc_do_unknown_living(self):
        mgr = self._seed()
        ok, err = mgr.npc_do("noone", {"action": "move", "target": "Hall"})
        assert ok is False and "not found" in err

    def test_npc_do_missing_action(self):
        mgr = self._seed()
        ok, err = mgr.npc_do("goblin", {})
        assert ok is False and "action" in err
