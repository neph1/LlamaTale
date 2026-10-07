"""
Standalone MCP server test app for LlamaTale.

This launches the in-process MCP server (``tale/mcp/server.py``) *without*
loading any specific story. It wraps a bare :class:`DynamicStory` (the story
type the MCP server targets) in a :class:`StoryManager`, registers it, and
starts the streamable-HTTP MCP endpoint on ``127.0.0.1:<port>/mcp``.

That makes it easy to launch and test the MCP server in isolation, without
having to pick and start a full story first.

Usage
-----
Start the server and keep it running (connect with your own MCP client):

    python3 tests/mcp_test_app.py                 # port 8765
    python3 tests/mcp_test_app.py --port 9000     # custom port

Run a built-in round-trip self-test (connects with an MCP client, calls a set
of representative tools, prints a summary, and exits):

    python3 tests/mcp_test_app.py --self-test

Options
-------
--port N        Port for the MCP endpoint (default 8765).
--self-test     Run the built-in round-trip test and exit.
--no-seed       Do not add the small starter world (zone/location/item/creature).

The MCP endpoint is at ``http://127.0.0.1:<port>/mcp`` (note the ``/mcp`` path;
hitting ``http://127.0.0.1:<port>/`` returns 404).

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""
import argparse
import asyncio
import pathlib
import signal
import socket
import sys
import time

# make the repo root importable when run as ``python3 tests/mcp_test_app.py``
ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tale.llm.dynamic_story import DynamicStory          # noqa: E402
from tale.story_manager import StoryManager, register    # noqa: E402
from tale.zone import Zone                               # noqa: E402

try:
    from tale.mcp import server as mcp_server            # noqa: E402
except ImportError as e:
    print("ERROR: the 'mcp' package is not installed, so the MCP server cannot start.")
    print("       Install it with:  pip install mcp")
    print("       (underlying import error: %s)" % e)
    raise SystemExit(1)


def free_port() -> int:
    """Return a currently-free port on 127.0.0.1."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def port_in_use(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.3)
        try:
            s.connect(("127.0.0.1", port))
            return True
        except OSError:
            return False


def wait_for_port(port: int, timeout: float = 20.0) -> bool:
    """Wait until something is listening on 127.0.0.1:<port>."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_in_use(port):
            return True
        time.sleep(0.1)
    return False


def make_story(seed: bool = True) -> DynamicStory:
    """Create a bare DynamicStory (no specific story loaded).

    When ``seed`` is true, add a small starter world (one zone, one location,
    one catalogue item, one catalogue creature) so the full range of tools has
    something to operate on.
    """
    story = DynamicStory()
    story.config.name = "MCP Test Story"
    story.config.author = "LlamaTale MCP test app"
    story.config.type = "A minimal world for testing the MCP server"
    story.config.world_info = "A small test world"
    story.config.world_mood = 0
    if not seed:
        return story

    # one zone with one location
    zone = Zone("TestZone", "a test zone")
    story.add_zone(zone)
    from tale.base import Location
    from tale.coord import Coord
    loc = Location("TestRoom", descr="A test room")
    loc.world_location = Coord(0, 0, 0)
    story.add_location(loc, "TestZone")

    # one catalogue item and one catalogue creature
    story.catalogue.add_item({"name": "torch", "type": "Other", "value": 1})
    story.catalogue.add_creature({"name": "goblin", "type": "Mob", "gender": "m",
                                  "race": "human", "level": 1,
                                  "description": "A test goblin"})
    return story


def start(port: int, seed: bool = True):
    """Create the story + manager, register it, and start the MCP server thread.

    Returns the started thread.
    """
    story = make_story(seed=seed)
    manager = StoryManager(story)
    register(manager)
    thread = mcp_server.start_server(port=port)
    if thread is None:
        print("ERROR: the MCP server did not start (no manager registered?).")
        sys.exit(1)
    return thread


def print_banner(port: int) -> None:
    url = "http://127.0.0.1:%d/llamatale-mcp" % port
    print()
    print("=" * 64)
    print("  LlamaTale MCP test server is running")
    print("=" * 64)
    print("  MCP endpoint (streamable-HTTP):")
    print("      %s" % url)
    print()
    print("  NOTE: the path is '/mcp'. Hitting")
    print("      http://127.0.0.1:%d/   returns 404." % port)
    print()
    print("  Connect with any streamable-HTTP MCP client, e.g.::")
    print()
    print("      from mcp import ClientSession")
    print("      from mcp.client.streamable_http import streamablehttp_client")
    print()
    print("      async with streamablehttp_client('%s') as (r, w, _):" % url)
    print("          async with ClientSession(r, w) as session:")
    print("              await session.initialize()")
    print("              tools = await session.list_tools()")
    print()
    print("  Press Ctrl+C to stop.")
    print("=" * 64)
    print()


def run_forever() -> None:
    """Block until interrupted (keeps the daemon MCP thread alive)."""
    stop = {"flag": False}

    def _handle(signum, frame):
        stop["flag"] = True

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)
    try:
        while not stop["flag"]:
            time.sleep(0.5)
    finally:
        print("\nShutting down.")


# --- self-test -----------------------------------------------------------------

SELFTEST_TOOLS = [
    # (tool, arguments, description)
    ("get_config", {}, "read the story config"),
    ("add_zone", {"zone": {"name": "Zone2", "description": "a second zone"}}, "add a zone"),
    ("list_zones", {}, "list zones"),
    ("add_item", {"item": {"name": "sword", "type": "Weapon"}}, "add a catalogue item"),
    ("list_items", {}, "list catalogue items"),
    ("add_creature", {"creature": {"name": "orc", "type": "Mob", "level": 2}}, "add a catalogue creature"),
    ("list_creatures", {}, "list catalogue creatures"),
    ("add_location", {"location": {"name": "Room2", "descr": "a room",
                                   "world_location": [1, 0, 0]}, "zone": "TestZone"}, "add a location"),
    ("list_locations", {"zone": "TestZone"}, "list locations in a zone"),
    ("set_exits", {"zone": "TestZone", "name": "TestRoom",
                   "exits": [{"direction": "north", "name": "Room2"}]}, "set exits"),
    ("spawn_npc", {"creature_name": "goblin", "zone": "TestZone", "location_name": "TestRoom"}, "spawn an NPC"),
    ("list_world_npcs", {}, "list live world NPCs"),
    ("spawn_item", {"item_name": "torch", "zone": "TestZone", "location_name": "TestRoom"}, "spawn an item"),
    ("list_world_items", {}, "list live world items"),
    ("set_story_context", {"base_story": "A test adventure"}, "set the base plot"),
    ("advance_story_section", {"section": "The beginning"}, "advance the story"),
    ("set_start_location", {"zone": "TestZone", "name": "TestRoom"}, "set the start location"),
]


async def _selftest(port: int) -> int:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    url = "http://127.0.0.1:%d/mcp" % port
    passed, failed = 0, 0
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
            print("Connected to %s" % url)
            print("Exposed tools (%d): %s" % (len(names), ", ".join(names)))
            print()
            for tool, args, desc in SELFTEST_TOOLS:
                try:
                    result = await session.call_tool(tool, args)
                    if result.isError:
                        detail = result.content[0].text[:160].replace("\n", " ") if result.content else ""
                        print("  FAIL  %-20s %s\n        %s" % (tool, desc, detail))
                        failed += 1
                    else:
                        print("  ok    %-20s %s" % (tool, desc))
                        passed += 1
                except Exception as e:
                    print("  FAIL  %-20s %s\n        %s: %s" % (tool, desc, type(e).__name__, e))
                    failed += 1
    print()
    print("Self-test: %d passed, %d failed." % (passed, failed))
    return 1 if failed else 0


def run_selftest(port: int, seed: bool) -> int:
    start(port=port, seed=seed)
    if not wait_for_port(port):
        print("ERROR: the MCP server did not start listening on port %d." % port)
        return 2
    try:
        return asyncio.run(_selftest(port))
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Self-test error: %s: %s" % (type(e).__name__, e))
        return 2


# --- main ----------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Launch the LlamaTale in-process MCP server without loading a specific story.")
    parser.add_argument("--port", type=int, default=mcp_server.DEFAULT_MCP_PORT,
                        help="port for the MCP endpoint (default %(default)s)")
    parser.add_argument("--self-test", action="store_true",
                        help="run the built-in round-trip test and exit")
    parser.add_argument("--no-seed", action="store_true",
                        help="do not add the small starter world")
    args = parser.parse_args()

    seed = not args.no_seed
    port = args.port

    if port_in_use(port) and not args.self_test:
        print("WARNING: port %d is already in use. The MCP server may fail to bind." % port)
        alt = free_port()
        print("Hint: try --port %d (a free port)." % alt)

    if args.self_test:
        return run_selftest(port=port, seed=seed)

    start(port=port, seed=seed)
    if not wait_for_port(port):
        print("ERROR: the MCP server did not start listening on port %d." % port)
        return 2
    print_banner(port)
    run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
