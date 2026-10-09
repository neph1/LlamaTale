"""
In-process MCP server exposing the live StoryManager as MCP tools.

An agent can build and modify a LlamaTale story/world by calling these tools
against a running story. The server runs on a background thread using the
streamable-HTTP transport on ``127.0.0.1:<port>`` (started by the driver with
the ``--mcp`` flag).

Each tool is a thin wrapper: it calls the corresponding
:meth:`~tale.story_manager.StoryManager` method (which guards state mutations
with its own lock) and returns the result as JSON.

'Tale' mud driver, mudlib and interactive fiction framework
"""
import json
import threading
from typing import Optional

from mcp.server.fastmcp import FastMCP

import tale.story_manager as story_manager

__all__ = ["create_server", "start_server", "DEFAULT_MCP_PORT"]

DEFAULT_MCP_PORT = 8765


def _json(value) -> str:
    """Serialize a value to a single JSON string.

    FastMCP turns a *list* return value into one content item per element, which
    would fragment a JSON array across many content blocks. Returning a JSON
    string instead keeps the whole result in a single text content for the agent.
    """
    return json.dumps(value, indent=2, default=str)


def _result(success, error) -> dict:
    """Convert a StoryManager ``(success, error)`` tuple into the JSON-friendly
    ``{"success": bool, "error": str}`` dict the agent sees. Named fields keep
    the outcome self-documenting (a positional tuple would be ambiguous)."""
    return {"success": success, "error": error}


def create_server(manager, port: int = DEFAULT_MCP_PORT) -> FastMCP:
    """Create a :class:`FastMCP` server exposing the given ``manager`` as tools."""
    mcp = FastMCP(
        "LlamaTale StoryManager",
        instructions=(
            "Tools for building and modifying a LlamaTale story/world. "
            "Cover story config, zones, locations, catalogue items/creatures, "
            "live world contents, story progression, persistence, and "
            "LLM-backed generation. Locations and zones are identified by name; "
            "a location is addressed as (zone, name)."
        ),
        host="127.0.0.1",
        stateless_http=True, 
        streamable_http_path='/llamatale-mcp',
        port=port,
    )

    # -- config ----------------------------------------------------------------

    @mcp.tool()
    def get_config() -> dict:
        """Return the story config as a JSON-friendly dict."""
        return manager.get_config()

    @mcp.tool()
    def set_config(fields: dict) -> None:
        """Set story config fields. Pass a dict of fields to change, e.g.
        ``{"name": "...", "world_mood": 3, "type": "..."}``. Supported fields
        include name, author, type, world_info, world_mood, context,
        startlocation_player, startlocation_wizard, and more."""
        manager.set_config(**fields)

    # -- zones -----------------------------------------------------------------


    @mcp.tool()
    def zone_example() -> dict:
        """Return an example zone dict with all fields."""
        return manager.zone_example()

    @mcp.tool()
    def add_zone(zone: dict) -> dict:
        """
        Add a zone (given as a dict) to the story.
        Returns {"success": bool, "error": str}: success is True when the zone
        was added; error describes what went wrong otherwise (e.g. a missing
        field or a duplicate zone name).
        Required fields: name, description. 
        
        Optional fields:
        description = description
        locations = dict()  # type: dict[str, Location]
        level = 1 # average level of the zone
        races = [] # type list[str] # common races to be encountered in the zone
        items = [] # type list[str] # common items to find in the zone
        mood = 0 # defines friendliness or hostility of the zone. > 0 is friendly
        size = 5 # roughly the 'radius' of the zone.
        size_z = 3 # height of the zone
        neighbors = dict() # type: dict[str, Zone] # north, east, south or west
        center = Coord(0,0,0) # The world coordinates of the center of the zone.
        name = name
        lore = "" # Any lore or backstory for the zone.
        dungeon_config = None  # type: DungeonConfig # If this zone is a dungeon, the config for generating it.
        dungeon = None  # type: Dungeon
        
        """
        return _result(*manager.add_zone(zone))

    @mcp.tool()
    def get_zone(name: str) -> dict:
        """Return the info dict for a zone by name."""
        return manager.get_zone(name)

    @mcp.tool()
    def list_zones() -> str:
        """Return info dicts for all zones in the story (as a JSON array)."""
        return _json(manager.list_zones())

    @mcp.tool()
    def remove_zone(name: str) -> bool:
        """Remove a zone by name. Returns True if removed."""
        return manager.remove_zone(name)

    @mcp.tool()
    def link_zones(a: str, b: str, direction: str) -> bool:
        """Link zone ``a`` to zone ``b`` in ``direction`` (and back the other
        way). Returns True if both zones exist and were linked."""
        return manager.link_zones(a, b, direction)

    # -- locations -------------------------------------------------------------

    @mcp.tool()
    def location_example() -> dict:
        """Return an example location dict with all fields."""
        return manager.location_example()
    
    @mcp.tool()
    def add_location(location: dict, zone: str = '') -> dict:
        """Add a location (given as a dict) to a zone. The dict needs at least a
        ``name`` and optionally ``descr``, ``short_descr``, ``world_location``
        (x, y, z coordinates in a 3-tuple) and ``items``. 
        Template: {"name": "", "description":"", "exits":[], "items":[], "npcs":[], "indoors":"true or false"}
        Returns {"success": bool, "error": str}: success is True when the
        location was added; error describes what went wrong otherwise (e.g. a
        missing field, an unknown zone, or a duplicate location name)."""
        return _result(*manager.add_location(location, zone))

    @mcp.tool()
    def get_location(zone: str, name: str) -> dict:
        """Return the serialized dict for a location in a zone."""
        return manager.get_location(zone, name)

    @mcp.tool()
    def list_locations(zone: str) -> str:
        """Return serialized dicts for all locations in a zone (as a JSON array)."""
        return _json(manager.list_locations(zone))

    @mcp.tool()
    def remove_location(zone: str, name: str) -> bool:
        """Remove a location from a zone (and from the live world). Returns True
        if removed."""
        return manager.remove_location(zone, name)

    @mcp.tool()
    def set_exits(zone: str, name: str, exits: list) -> bool:
        """Set exits on a location. Each exit is a dict with ``direction``,
        ``name`` (target location name) and optional ``short_descr``/
        ``long_descr``. Missing target locations are created so exits are always
        Template: [{"direction":"", "name":"name of new location", "short_descr":"exit description"}]
        bound. Returns True on success."""
        return manager.set_exits(zone, name, exits)

    @mcp.tool()
    def exit_example() -> dict:
        """Return an example exit dict with all fields."""
        return manager.exit_example()

    # -- catalogue (world items & creatures) -----------------------------------

    @mcp.tool()
    def add_item(item: dict) -> bool:
        """
        Add a world item (as a dict) to the catalogue. Returns True if added.
        Template: {"name":"", "type":"", "short_descr":"", "level":int, "value":int}
        """
        return manager.add_item(item)

    @mcp.tool()
    def add_creature(creature: dict) -> bool:
        """
        Add a world creature (as a dict) to the catalogue. Returns True if
        added.
        Template: {"name":"", "body":"", "mass":int(kg), "hp":int, "type":"Npc or Mob", "level":int, "aggressive":bool, "unarmed_attack":One of [FISTS, CLAWS, BITE, TAIL, HOOVES, HORN, TUSKS, BEAK, TALON], "short_descr":""}
        """
        return manager.add_creature(creature)

    @mcp.tool()
    def list_items() -> str:
        """Return all catalogue items as dicts (as a JSON array)."""
        return _json(manager.list_items())

    @mcp.tool()
    def list_creatures() -> str:
        """Return all catalogue creatures as dicts (as a JSON array)."""
        return _json(manager.list_creatures())

    @mcp.tool()
    def remove_item(name: str) -> bool:
        """Remove an item from the catalogue by name. Returns True if removed."""
        return manager.remove_item(name)

    @mcp.tool()
    def remove_creature(name: str) -> bool:
        """Remove a creature from the catalogue by name. Returns True if
        removed."""
        return manager.remove_creature(name)

    # -- world contents (live objects) -----------------------------------------

    @mcp.tool()
    def spawn_npc(creature_name: str, zone: str, location_name: str) -> bool:
        """Spawn a live NPC (from the catalogue) in a location. Returns True on
        success."""
        return manager.spawn_npc(creature_name, zone, location_name)

    @mcp.tool()
    def spawn_item(item_name: str, zone: str, location_name: str) -> bool:
        """Spawn a live item (from the catalogue) in a location. Returns True on
        success."""
        return manager.spawn_item(item_name, zone, location_name)

    @mcp.tool()
    def list_world_npcs() -> dict:
        """Return all live NPCs in the world as a dict keyed by name."""
        return manager.list_world_npcs()

    @mcp.tool()
    def list_world_items() -> str:
        """Return all live items found in world locations as dicts (as a JSON array)."""
        return _json(manager.list_world_items())

    # -- world live-object store (real Living/Item objects, not catalogue dicts) --

    @mcp.tool()
    def add_world_npc(npc: dict) -> dict:
        """Add a live NPC (given as a dict) to the world's live-object store.
        Creates a real Living object (unlike the catalogue's plain dicts) and
        adds it to the world store without inserting it into a location. This is
        for *preparing* a story before it is played. Template:
        {"name":"", "type":"Npc or Mob", "race":"", "gender":"m or f", "level":int,
        "description":"", "short_descr":""}
        Returns {"success": bool, "error": str}: success is True when the NPC
        was added; error describes what went wrong otherwise (e.g. a missing
        field or a duplicate NPC name)."""
        return _result(*manager.add_world_npc(npc))

    @mcp.tool()
    def add_world_item(item: dict) -> dict:
        """Add a live item (given as a dict) to the world's live-object store.
        Creates a real Item object (unlike the catalogue's plain dicts) and adds
        it to the world store without inserting it into a location. This is for
        *preparing* a story before it is played. Template:
        {"name":"", "type":"", "description":"", "short_descr":"", "value":int}
        Returns {"success": bool, "error": str}: success is True when the item
        was added; error describes what went wrong otherwise (e.g. a missing
        field or a duplicate item name)."""
        return _result(*manager.add_world_item(item))

    @mcp.tool()
    def get_world_npc(name: str) -> dict:
        """Return the serialized dict for a live NPC in the world's store (or an
        empty dict if not found)."""
        return manager.get_world_npc(name)

    @mcp.tool()
    def get_world_item(name: str) -> dict:
        """Return the serialized dict for a live item in the world's store (or an
        empty dict if not found)."""
        return manager.get_world_item(name)

    # -- story progression -----------------------------------------------------

    @mcp.tool()
    def set_story_context(base_story: str) -> None:
        """Set the base plot of the story context."""
        manager.set_story_context(base_story)

    @mcp.tool()
    def advance_story_section(section: str) -> None:
        """Advance the story context to a new section."""
        manager.advance_story_section(section)

    @mcp.tool()
    def set_start_location(zone: str, name: str) -> None:
        """Set the player/wizard start location to ``zone.name``."""
        manager.set_start_location(zone, name)

    # -- persistence -----------------------------------------------------------

    @mcp.tool()
    def save(path: str) -> None:
        """Save the story to disk at ``path``."""
        manager.save(path)

    @mcp.tool()
    def load(path: str) -> None:
        """Load a story from a saved directory at ``path``, replacing the current
        state."""
        manager.load(path)

    # -- LLM-backed generation -------------------------------------------------

    @mcp.tool()
    def generate_world_items(count: int = 7) -> str:
        """Generate world items via the LLM, add them to the catalogue, and
        return them as a JSON array of dicts."""
        return _json(manager.generate_world_items(count=count))

    @mcp.tool()
    def generate_world_creatures(count: int = 5) -> str:
        """Generate world creatures via the LLM, add them to the catalogue, and
        return them as a JSON array of dicts."""
        return _json(manager.generate_world_creatures(count=count))

    @mcp.tool()
    def generate_start_zone(location_desc: str) -> dict:
        """Generate a starting zone via the LLM, add it to the story, and return
        it as an info dict."""
        return manager.generate_start_zone(location_desc)

    @mcp.tool()
    def generate_location(zone: str, name: str, exit_name: str) -> dict:
        """Generate a location (via the LLM) adjacent to the existing location
        ``zone.name``, apply it to the story, and return the serialized source
        location dict (with its new exits)."""
        return manager.generate_location(zone, name, exit_name)

    return mcp


def start_server(port: int = DEFAULT_MCP_PORT) -> Optional[threading.Thread]:
    """Start the MCP server on a background daemon thread.

    Obtains the live :class:`StoryManager` from the module registry, creates the
    FastMCP server, and runs it on ``127.0.0.1:<port>``. Returns the started
    thread, or ``None`` if no manager is registered.
    """
    try:
        manager = story_manager.current()
    except RuntimeError as e:
        print("MCP server: %s; not starting the MCP server" % e)
        return None
    mcp = create_server(manager, port)

    def _run() -> None:
        try:
            import asyncio
            import uvicorn
            app = mcp.streamable_http_app()
            config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="info")
            server = uvicorn.Server(config)
            asyncio.run(server.serve())
        except Exception as e:   # pragma: no cover - defensive
            print("MCP server thread crashed: %s" % e)

    thread = threading.Thread(target=_run, name="mcp-server", daemon=True)
    thread.start()
    print("MCP server started on 127.0.0.1:%d/llama-tale-mcp (streamable-HTTP)" % port)
    return thread
