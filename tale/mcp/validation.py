"""
Validation layer for the MCP story-building tools.

Complex objects (Zone, Location, NPC, Item) are built from plain dicts. These
functions validate the dict and create the data object, returning a descriptive
error explaining what went wrong if the input is malformed. They are used by the
StoryManager mutation methods so the agent gets a specific error instead of a
bare failure.

Each function returns a ``(object, error)`` tuple: ``(object, None)`` on
success, or ``(None, error_message)`` on failure.

'Tale' mud driver, mudlib and interactive fiction framework
"""
from typing import Optional, Tuple

from tale.base import Item, Living, Location
from tale.coord import Coord
from tale.load_items import load_item
from tale.zone import Zone

import tale.parse_utils as parse_utils

__all__ = ["validate_zone", "validate_location", "validate_npc", "validate_item"]


def _require_name(data: dict, kind: str) -> Optional[str]:
    """Return an error string if ``data`` is not a dict with a non-empty string
    ``name`` field, or ``None`` if it is well-formed."""
    if not isinstance(data, dict):
        return f"{kind} must be a dict"
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return f"missing required field 'name' (a non-empty string) for {kind}"
    return None


def validate_zone(zone: dict) -> Tuple[Optional[Zone], Optional[str]]:
    """Validate and create a Zone from a dict.

    Returns ``(zone, None)`` on success, or ``(None, error_message)`` on failure.
    """
    error = _require_name(zone, "zone")
    if error:
        return None, error
    try:
        z = Zone.from_json(zone)
    except Exception as exc:
        return None, f"failed to build Zone: {exc}"
    return z, None


def validate_location(location: dict) -> Tuple[Optional[Location], Optional[str]]:
    """Validate and create a Location from a dict.

    The dict needs at least a ``name`` and optionally ``descr``, ``short_descr``,
    ``world_location`` (a 3-tuple) and ``items``. Returns ``(location, None)`` on
    success, or ``(None, error_message)`` on failure.
    """
    error = _require_name(location, "location")
    if error:
        return None, error
    try:
        loc = Location(location["name"], descr=location.get("descr", ""))
        loc.short_description = location.get("short_descr", loc.short_description)
        description = location.get("description", "")
        if description:
            loc.description = description
        world_location = location.get("world_location")
        if world_location:
            loc.world_location = Coord(world_location[0], world_location[1], world_location[2])
        loc.built = location.get("built", True)
        for item in location.get("items", []):
            item = validate_item(item)
            if isinstance(item, dict):
                loc.insert(load_item(item), None)
    except Exception as exc:
        return None, f"failed to build Location: {exc}"
    return loc, None


def validate_npc(npc: dict, world_items: list = None) -> Tuple[Optional[Living], Optional[str]]:
    """Validate and create a Living (NPC) from a dict.

    Returns ``(npc, None)`` on success, or ``(None, error_message)`` on failure.
    ``world_items`` (catalogue item dicts) are used to stock trader NPCs.
    """
    error = _require_name(npc, "npc")
    if error:
        return None, error
    try:
        loaded = parse_utils.load_npcs([npc], world_items=world_items or [])
    except Exception as exc:
        return None, f"failed to build NPC: {exc}"
    if not loaded:
        return None, f"failed to build NPC '{npc['name']}' (no NPC was created)"
    npc_obj = next(iter(loaded.values()))
    return npc_obj, None


def validate_item(item: dict) -> Tuple[Optional[Item], Optional[str]]:
    """Validate and create an Item from a dict.

    Returns ``(item, None)`` on success, or ``(None, error_message)`` on failure.
    """
    error = _require_name(item, "item")
    if error:
        return None, error
    try:
        item_obj = load_item(item)
    except Exception as exc:
        return None, f"failed to build Item: {exc}"
    return item_obj, None
