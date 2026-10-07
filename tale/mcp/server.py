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
Copyright by Irmen de Jong (irmen@razorvine.net)
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
    def add_zone(zone: dict) -> bool:
        """Add a zone (given as a dict) to the story. Returns True if added."""
        return manager.add_zone(zone)

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
    def add_location(location: dict, zone: str = '') -> bool:
        """Add a location (given as a dict) to a zone. The dict needs at least a
        ``name`` and optionally ``descr``, ``short_descr``, ``world_location``
        (a 3-tuple) and ``items``. Returns True if added."""
        return manager.add_location(location, zone)

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
        bound. Returns True on success."""
        return manager.set_exits(zone, name, exits)

    # -- catalogue (world items & creatures) -----------------------------------

    @mcp.tool()
    def add_item(item: dict) -> bool:
        """Add a world item (as a dict) to the catalogue. Returns True if added."""
        return manager.add_item(item)

    @mcp.tool()
    def add_creature(creature: dict) -> bool:
        """Add a world creature (as a dict) to the catalogue. Returns True if
        added."""
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
