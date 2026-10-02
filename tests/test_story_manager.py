""" Tests for the StoryManager modification layer (tale/story_manager.py). """

import types
import pytest

from tale.base import Location
from tale.coord import Coord
from tale.llm.dynamic_story import DynamicStory
from tale.llm.responses.LocationResponse import LocationResponse
from tale.story_context import StoryContext
from tale.story_manager import StoryManager, register, current, get
from tale.zone import Zone


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
        ok = mgr.add_zone({"name": "SecondZone", "description": "second", "level": 3})
        assert ok is True
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
        assert mgr.add_location({"name": "Room", "descr": "A room", "world_location": [0, 0, 0]}, "TestZone") is True
        loc = mgr.story.get_location("TestZone", "Room")
        assert loc is not None
        assert loc.description == "A room"
        assert loc.world_location.as_tuple() == (0, 0, 0)

    def test_add_location_requires_name(self):
        mgr = StoryManager(make_story())
        assert mgr.add_location({"descr": "no name"}, "TestZone") is False

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
        result = mgr.generate_location(loc, "TestZone", "north")
        assert story.build_calls if hasattr(story, "build_calls") else True
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
            mgr.generate_location(Location("Start", "x"), "TestZone", "north")
