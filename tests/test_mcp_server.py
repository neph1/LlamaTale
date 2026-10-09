""" Tests for the in-process MCP server (tale/mcp/server.py).

Covers:
- server creation and the full set of exposed tools,
- each tool wrapping the corresponding StoryManager method,
- list-style tools returning a single JSON string (not fragmented content),
- a full MCP protocol round-trip via the in-memory client session,
- start_server() (background thread + listening port),
- the --mcp / --mcp-port commandline flags being passed to the driver.
"""

import asyncio
import json
import socket
import time
import types

import pytest

from tale.llm.dynamic_story import DynamicStory
from tale.llm.responses.LocationResponse import LocationResponse
from tale.story_manager import StoryManager
from tale.zone import Zone

from tale.mcp.server import create_server, start_server, DEFAULT_MCP_PORT


def make_story():
    story = DynamicStory()
    story.config.name = "Test Story"
    story.add_zone(Zone("TestZone", "a test zone"))
    return story


def make_manager(llm_util=None):
    return StoryManager(make_story(), llm_util=llm_util)


# --- tool call helpers ---------------------------------------------------------

def call_tool(mcp, name, arguments=None):
    """Call an MCP tool directly. Returns (list of text contents, structured result)."""
    result = asyncio.run(mcp.call_tool(name, arguments or {}))
    if isinstance(result, tuple):
        blocks, structured = result
    else:
        blocks, structured = result, None
    texts = [b.text for b in blocks if getattr(b, "type", None) == "text"]
    return texts, structured


def tool_json(mcp, name, arguments=None):
    """Call a tool whose result is JSON (a dict, or a JSON string) and parse it."""
    texts, _ = call_tool(mcp, name, arguments)
    assert texts, "expected a text content from tool %s" % name
    return json.loads(texts[0])


def tool_bool(mcp, name, arguments=None):
    """Call a tool that returns a bool and return the actual bool."""
    _, structured = call_tool(mcp, name, arguments)
    assert structured is not None and "result" in structured, \
        "expected a structured bool result from tool %s" % name
    assert isinstance(structured["result"], bool)
    return structured["result"]


def tool_result(mcp, name, arguments=None):
    """Call a tool that returns a {"success": bool, "error": str} dict.

    FastMCP serializes a dict return to a single JSON text content (no
    structured result), so parse that. Returns the ``(success, error)`` pair."""
    texts, _ = call_tool(mcp, name, arguments)
    assert texts, "expected a text content from tool %s" % name
    result = json.loads(texts[0])
    assert isinstance(result, dict) and "success" in result and "error" in result, \
        "expected a {success, error} dict from tool %s, got %r" % (name, result)
    return result["success"], result["error"]


class FakeLlmUtil:
    """A fake llm_util for the LLM-backed generation tools (same shape as the
    real LlmUtil responses)."""

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


# --- server creation -----------------------------------------------------------

class TestServerCreation():

    # the full set of tools from the plan (stories/worlds scope)
    EXPECTED_TOOLS = {
        "get_config", "set_config",
        "zone_example", "add_zone", "get_zone", "list_zones", "remove_zone", "link_zones",
        "location_example", "add_location", "get_location", "list_locations", "remove_location",
        "set_exits", "exit_example",
        "add_item", "add_creature", "list_items", "list_creatures", "remove_item", "remove_creature",
        "spawn_npc", "spawn_item", "list_world_npcs", "list_world_items",
        "add_world_npc", "add_world_item", "get_world_npc", "get_world_item",
        "set_story_context", "advance_story_section", "set_start_location",
        "save", "load",
        "generate_world_items", "generate_world_creatures", "generate_start_zone", "generate_location",
    }

    def test_create_server_returns_fastmcp(self):
        from mcp.server.fastmcp import FastMCP
        mcp = create_server(make_manager())
        assert isinstance(mcp, FastMCP)

    def test_exposes_all_expected_tools(self):
        mcp = create_server(make_manager())
        names = {t.name for t in asyncio.run(mcp.list_tools())}
        assert self.EXPECTED_TOOLS == names

    def test_default_port(self):
        assert DEFAULT_MCP_PORT == 8765


# --- config tools --------------------------------------------------------------

class TestConfigTools():

    def test_get_config(self):
        mcp = create_server(make_manager())
        config = tool_json(mcp, "get_config")
        assert config["name"] == "Test Story"
        assert config["supported_modes"] == ["IF"]

    def test_set_config(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        call_tool(mcp, "set_config", {"fields": {"name": "New Name", "world_mood": 4}})
        assert mgr.story.config.name == "New Name"
        assert mgr.story.config.world_mood == 4
        config = tool_json(mcp, "get_config")
        assert config["name"] == "New Name"


# --- zone tools ----------------------------------------------------------------

class TestZoneTools():

    def test_add_zone(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        success, error = tool_result(mcp, "add_zone", {"zone": {"name": "Z2", "description": "d", "level": 2}})
        assert success is True
        assert error == ""
        assert mgr.story.get_zone("Z2") is not None

    def test_get_zone(self):
        mcp = create_server(make_manager())
        info = tool_json(mcp, "get_zone", {"name": "TestZone"})
        assert info["name"] == "TestZone"

    def test_list_zones_returns_json_array(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        mgr.add_zone({"name": "Z2", "description": "d"})
        zones = tool_json(mcp, "list_zones")
        assert isinstance(zones, list)
        assert {z["name"] for z in zones} == {"TestZone", "Z2"}

    def test_remove_zone(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        assert tool_bool(mcp, "remove_zone", {"name": "TestZone"}) is True
        assert tool_bool(mcp, "remove_zone", {"name": "TestZone"}) is False

    def test_link_zones(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        mgr.add_zone({"name": "Z2", "description": "d"})
        assert tool_bool(mcp, "link_zones", {"a": "TestZone", "b": "Z2", "direction": "north"}) is True
        assert mgr.story.get_zone("Z2").neighbors["south"] is mgr.story.get_zone("TestZone")


# --- location tools ------------------------------------------------------------

class TestLocationTools():

    def test_add_location(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        success, error = tool_result(mcp, "add_location", {
            "location": {"name": "Room", "descr": "A room", "world_location": [0, 0, 0]},
            "zone": "TestZone",
        })
        assert success is True
        assert error == ""
        assert mgr.story.get_location("TestZone", "Room") is not None

    def test_get_location(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        mgr.add_location({"name": "Room", "descr": "A room", "world_location": [1, 2, 3]}, "TestZone")
        info = tool_json(mcp, "get_location", {"zone": "TestZone", "name": "Room"})
        assert info["name"] == "Room"
        assert info["world_location"] == [1, 2, 3]

    def test_list_locations_returns_json_array(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        mgr.add_location({"name": "Room", "descr": "A room"}, "TestZone")
        mgr.add_location({"name": "Hall", "descr": "A hall"}, "TestZone")
        locs = tool_json(mcp, "list_locations", {"zone": "TestZone"})
        assert {l["name"] for l in locs} == {"Room", "Hall"}

    def test_remove_location(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        mgr.add_location({"name": "Room", "descr": "A room"}, "TestZone")
        assert tool_bool(mcp, "remove_location", {"zone": "TestZone", "name": "Room"}) is True
        assert mgr.story.get_location("TestZone", "Room") is None

    def test_set_exits(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        mgr.add_location({"name": "Room", "descr": "A room", "world_location": [0, 0, 0]}, "TestZone")
        assert tool_bool(mcp, "set_exits", {
            "zone": "TestZone", "name": "Room",
            "exits": [{"direction": "north", "name": "Forest"}],
        }) is True
        loc = mgr.story.get_location("TestZone", "Room")
        assert "north" in loc.exits
        assert loc.exits["north"].target.name == "Forest"


# --- catalogue tools -----------------------------------------------------------

class TestCatalogueTools():

    def test_add_item(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        assert tool_bool(mcp, "add_item", {"item": {"name": "sword", "type": "Weapon"}}) is True
        assert tool_bool(mcp, "add_item", {"item": {"name": "sword", "type": "Weapon"}}) is False  # duplicate

    def test_add_creature(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        assert tool_bool(mcp, "add_creature", {"creature": {"name": "goblin", "type": "Mob", "level": 1}}) is True

    def test_list_items(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        mgr.add_item({"name": "sword"})
        items = tool_json(mcp, "list_items")
        assert any(i["name"] == "sword" for i in items)

    def test_list_creatures(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        mgr.add_creature({"name": "goblin"})
        creatures = tool_json(mcp, "list_creatures")
        assert any(c["name"] == "goblin" for c in creatures)

    def test_remove_item(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        mgr.add_item({"name": "sword"})
        assert tool_bool(mcp, "remove_item", {"name": "sword"}) is True
        assert tool_bool(mcp, "remove_item", {"name": "sword"}) is False

    def test_remove_creature(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        mgr.add_creature({"name": "goblin"})
        assert tool_bool(mcp, "remove_creature", {"name": "goblin"}) is True
        assert tool_bool(mcp, "remove_creature", {"name": "goblin"}) is False


# --- world contents tools ------------------------------------------------------

class TestWorldContentsTools():

    def _seed(self, mgr):
        mgr.add_creature({"name": "goblin", "type": "Mob", "gender": "m", "race": "human",
                          "level": 1, "description": "A goblin"})
        mgr.add_item({"name": "torch", "type": "Other"})
        mgr.add_location({"name": "Cave", "descr": "A cave", "world_location": [0, 0, 0]}, "TestZone")

    def test_spawn_npc(self):
        mgr = make_manager()
        self._seed(mgr)
        mcp = create_server(mgr)
        assert tool_bool(mcp, "spawn_npc", {"creature_name": "goblin", "zone": "TestZone", "location_name": "Cave"}) is True
        npcs = tool_json(mcp, "list_world_npcs")
        assert "Goblin" in npcs

    def test_spawn_item(self):
        mgr = make_manager()
        self._seed(mgr)
        mcp = create_server(mgr)
        assert tool_bool(mcp, "spawn_item", {"item_name": "torch", "zone": "TestZone", "location_name": "Cave"}) is True
        items = tool_json(mcp, "list_world_items")
        assert any(i["name"] == "torch" for i in items)

    def test_spawn_unknown_creature(self):
        mgr = make_manager()
        mgr.add_location({"name": "Cave", "descr": "A cave"}, "TestZone")
        mcp = create_server(mgr)
        assert tool_bool(mcp, "spawn_npc", {"creature_name": "nope", "zone": "TestZone", "location_name": "Cave"}) is False


# --- world live-object store tools ---------------------------------------------

class TestWorldStoreTools():
    """Tests for the world live-object store tools (add/get live NPCs and items,
    as real Living/Item objects rather than catalogue dicts)."""

    def test_add_world_npc(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        success, error = tool_result(mcp, "add_world_npc", {
            "npc": {"name": "Goblin", "type": "Mob", "race": "human", "gender": "m", "level": 1},
        })
        assert success is True
        assert error == ""
        assert mgr.story.world.get_npc("goblin") is not None

    def test_add_world_npc_duplicate(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        success, error = tool_result(mcp, "add_world_npc", {"npc": {"name": "Goblin", "type": "Mob"}})
        assert success is True
        assert error == ""
        success, error = tool_result(mcp, "add_world_npc", {"npc": {"name": "Goblin", "type": "Mob"}})
        assert success is False
        assert "already exists" in error

    def test_get_world_npc(self):
        mgr = make_manager()
        mgr.add_world_npc({"name": "Goblin", "type": "Mob", "race": "human", "gender": "m", "level": 1})
        mcp = create_server(mgr)
        npc = tool_json(mcp, "get_world_npc", {"name": "Goblin"})
        assert npc["name"] == "Goblin"

    def test_get_world_npc_not_found(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        assert tool_json(mcp, "get_world_npc", {"name": "Nope"}) == {}

    def test_add_world_item(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        success, error = tool_result(mcp, "add_world_item", {"item": {"name": "Torch", "type": "Other"}})
        assert success is True
        assert error == ""
        assert mgr.story.world.get_item("torch") is not None

    def test_add_world_item_duplicate(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        success, error = tool_result(mcp, "add_world_item", {"item": {"name": "Torch", "type": "Other"}})
        assert success is True
        assert error == ""
        success, error = tool_result(mcp, "add_world_item", {"item": {"name": "Torch", "type": "Other"}})
        assert success is False
        assert "already exists" in error

    def test_get_world_item(self):
        mgr = make_manager()
        mgr.add_world_item({"name": "Torch", "type": "Other"})
        mcp = create_server(mgr)
        item = tool_json(mcp, "get_world_item", {"name": "Torch"})
        assert item["name"] == "torch"

    def test_get_world_item_not_found(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        assert tool_json(mcp, "get_world_item", {"name": "Nope"}) == {}


# --- validation feedback -------------------------------------------------------

class TestValidationFeedback():
    """The add_* tools return a *descriptive* error (not a bare failure) when
    the input is malformed or the object already exists, so the agent can fix
    its input. Covers zone, location, world NPC and world item."""

    def test_add_zone_missing_name(self):
        mcp = create_server(make_manager())
        success, error = tool_result(mcp, "add_zone", {"zone": {"description": "no name"}})
        assert success is False
        assert "name" in error

    def test_add_zone_duplicate(self):
        mcp = create_server(make_manager())
        success, error = tool_result(mcp, "add_zone", {"zone": {"name": "TestZone", "description": "d"}})
        assert success is False
        assert "already exists" in error

    def test_add_zone_not_a_dict(self):
        # exercised at the manager level (the MCP schema would reject a
        # non-dict argument before the validation layer sees it)
        mgr = make_manager()
        success, error = mgr.add_zone("not a dict")
        assert success is False
        assert "dict" in error

    def test_add_location_missing_name(self):
        mcp = create_server(make_manager())
        success, error = tool_result(mcp, "add_location", {
            "location": {"descr": "no name"}, "zone": "TestZone",
        })
        assert success is False
        assert "name" in error

    def test_add_location_unknown_zone(self):
        mcp = create_server(make_manager())
        success, error = tool_result(mcp, "add_location", {
            "location": {"name": "Room", "descr": "a room"}, "zone": "Nope",
        })
        assert success is False
        assert "zone" in error and "not found" in error

    def test_add_location_duplicate(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        mgr.add_location({"name": "Room", "descr": "a room"}, "TestZone")
        success, error = tool_result(mcp, "add_location", {
            "location": {"name": "Room", "descr": "a room"}, "zone": "TestZone",
        })
        assert success is False
        assert "already exists" in error

    def test_add_world_npc_missing_name(self):
        mcp = create_server(make_manager())
        success, error = tool_result(mcp, "add_world_npc", {"npc": {"type": "Mob"}})
        assert success is False
        assert "name" in error

    def test_add_world_item_missing_name(self):
        mcp = create_server(make_manager())
        success, error = tool_result(mcp, "add_world_item", {"item": {"type": "Other"}})
        assert success is False
        assert "name" in error


# --- story progression tools ---------------------------------------------------

class TestProgressionTools():

    def test_set_story_context(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        call_tool(mcp, "set_story_context", {"base_story": "A grand adventure"})
        assert mgr.story.config.context.base_story == "A grand adventure"

    def test_advance_story_section(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        mgr.set_story_context("Base plot")
        call_tool(mcp, "advance_story_section", {"section": "The beginning"})
        assert mgr.story.config.context.current_section == "The beginning"

    def test_set_start_location(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        call_tool(mcp, "set_start_location", {"zone": "TestZone", "name": "Cave"})
        assert mgr.story.config.startlocation_player == "TestZone.Cave"
        assert mgr.story.config.startlocation_wizard == "TestZone.Cave"


# --- persistence tools ---------------------------------------------------------

class TestPersistenceTools():

    def test_save(self, tmp_path, monkeypatch):
        # DynamicStory.save copies story.py from the cwd; provide a fake one
        (tmp_path / "story.py").write_text("# fake story\n")
        monkeypatch.chdir(tmp_path)
        mgr = make_manager()
        mgr.add_location({"name": "Room", "descr": "A room"}, "TestZone")
        mcp = create_server(mgr)
        call_tool(mcp, "save", {"path": str(tmp_path / "saved")})
        saved = tmp_path / "saved"
        assert (saved / "world.json").exists()
        assert (saved / "story_config.json").exists()
        world = json.loads((saved / "world.json").read_text())
        assert "TestZone" in world["zones"]

    def test_load(self):
        mgr = make_manager()
        mcp = create_server(mgr)
        call_tool(mcp, "load", {"path": "tests/files/world_story/"})
        assert mgr.story.get_zone("Cave") is not None
        assert mgr.story.get_location("Cave", "Cave entrance") is not None
        assert len(mgr.story.catalogue.get_creatures()) >= 1


# --- LLM-backed generation tools -----------------------------------------------

class TestLlmGenerationTools():

    def test_generate_world_items(self):
        mgr = make_manager(llm_util=FakeLlmUtil())
        mcp = create_server(mgr)
        items = tool_json(mcp, "generate_world_items", {"count": 3})
        assert items[0]["name"] == "wand"
        # the generated items were added to the catalogue
        assert any(i["name"] == "wand" for i in mgr.story.catalogue.get_items())

    def test_generate_world_creatures(self):
        mgr = make_manager(llm_util=FakeLlmUtil())
        mcp = create_server(mgr)
        creatures = tool_json(mcp, "generate_world_creatures")
        assert creatures[0]["name"] == "dragon"
        assert any(c["name"] == "dragon" for c in mgr.story.catalogue.get_creatures())

    def test_generate_start_zone(self):
        mgr = make_manager(llm_util=FakeLlmUtil())
        mcp = create_server(mgr)
        info = tool_json(mcp, "generate_start_zone", {"location_desc": "a road"})
        assert info["name"] == "GeneratedZone"
        assert mgr.story.get_zone("GeneratedZone") is not None

    def test_generate_location(self):
        mgr = make_manager(llm_util=FakeLlmUtil())
        mgr.add_location({"name": "Start", "descr": "You are at start", "world_location": [0, 0, 0]}, "TestZone")
        mcp = create_server(mgr)
        info = tool_json(mcp, "generate_location", {"zone": "TestZone", "name": "Start", "exit_name": "north"})
        assert info["name"] == "Start"
        # the generated destination location was added and the exit bound
        assert mgr.story.find_location("Generated Room") is not None
        assert "north" in mgr.story.get_location("TestZone", "Start").exits


# --- full MCP protocol round-trip ----------------------------------------------

class TestMcpProtocolRoundTrip():
    """Full MCP protocol round-trip using the in-memory client session."""

    def test_list_and_call_tools_via_client(self):
        from mcp.shared.memory import create_connected_server_and_client_session
        mgr = make_manager()
        mcp = create_server(mgr)

        async def _run():
            async with create_connected_server_and_client_session(mcp) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {t.name for t in tools.tools}
                assert "get_config" in names
                assert "add_zone" in names

                result = await session.call_tool("get_config", {})
                assert not result.isError
                config = json.loads(result.content[0].text)
                assert config["name"] == "Test Story"

                result = await session.call_tool("add_zone", {"zone": {"name": "Z2", "description": "d"}})
                assert not result.isError
                zone_result = json.loads(result.content[0].text)
                assert zone_result["success"] is True
                assert zone_result["error"] == ""

                result = await session.call_tool("list_zones", {})
                assert not result.isError
                zones = json.loads(result.content[0].text)
                assert {z["name"] for z in zones} == {"TestZone", "Z2"}

        asyncio.run(_run())

    def test_list_tool_returns_single_text_content(self):
        """List-style tools must return one JSON string content item, not one
        content item per element (which would fragment the JSON array)."""
        from mcp.shared.memory import create_connected_server_and_client_session
        mgr = make_manager()
        mgr.add_zone({"name": "Z2", "description": "d"})
        mcp = create_server(mgr)

        async def _run():
            async with create_connected_server_and_client_session(mcp) as session:
                await session.initialize()
                result = await session.call_tool("list_zones", {})
                assert not result.isError
                assert len(result.content) == 1
                zones = json.loads(result.content[0].text)
                assert {z["name"] for z in zones} == {"TestZone", "Z2"}

        asyncio.run(_run())


# --- start_server ----------------------------------------------------------------

def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(port, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as s:
            s.settimeout(0.5)
            try:
                s.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.1)
    return False


class TestStartServer():

    def _set_current(self, mgr):
        import tale.story_manager as sm
        saved = sm._current
        sm._current = mgr
        return saved

    def test_without_manager_returns_none(self):
        import tale.story_manager as sm
        saved = sm._current
        sm._current = None
        try:
            assert start_server() is None
        finally:
            sm._current = saved

    def test_starts_thread_and_listens(self):
        import tale.story_manager as sm
        mgr = make_manager()
        saved = self._set_current(mgr)
        try:
            port = _free_port()
            thread = start_server(port=port)
            assert thread is not None
            assert thread.name == "mcp-server"
            assert _wait_for_port(port), "MCP server did not start listening on %d" % port
        finally:
            sm._current = saved


# --- commandline flags -----------------------------------------------------------

class TestMainFlags():
    """The --mcp / --mcp-port flags are passed from the commandline to the driver."""

    def _run(self, monkeypatch, cmdline):
        import tale.driver_if
        import tale.main
        started = {}

        class FakeDriver:
            def __init__(self, *args, **kwargs):
                pass

            def start(self, game):
                started["game"] = game
                started["mcp_enabled"] = self.mcp_enabled
                started["mcp_port"] = self.mcp_port

        monkeypatch.setattr(tale.driver_if, "IFDriver", FakeDriver)
        tale.main.run_from_cmdline(cmdline)
        return started

    def test_mcp_flags(self, monkeypatch):
        started = self._run(monkeypatch, ["-g", "somegame", "--mcp", "--mcp-port", "9999"])
        assert started["game"] == "somegame"
        assert started["mcp_enabled"] is True
        assert started["mcp_port"] == 9999

    def test_mcp_defaults(self, monkeypatch):
        started = self._run(monkeypatch, ["-g", "somegame"])
        assert started["mcp_enabled"] is False
        assert started["mcp_port"] == 8765
