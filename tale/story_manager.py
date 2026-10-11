"""
StoryManager - a single modification layer over a DynamicStory.

Both the MCP server (the agent) and the LLM path (via tale.llm.WorldBuilding)
route story modifications through this class. It exposes a JSON-friendly
mutation API: plain dicts in, dicts/bools out.

This module lives in the tale/ root (not tale/llm/) because it is about story
*state*, not about LLM generation, and it is the stable hook that the MCP
server depends on.

'Tale' mud driver, mudlib and interactive fiction framework
"""

import os
import random
import threading
from typing import Any, Optional

from tale.base import Location, Exit, Door
from tale.coord import Coord
from tale.errors import LocationIntegrityError
from tale.items.basic import Note
from tale.llm.LivingNpc import LivingNpc
from tale.llm.responses.ActionResponse import ActionResponse
from tale.npc_defs import StationaryNpc
from tale.story import GameMode
from tale.story_context import StoryContext
from tale.zone import Zone

import tale.parse_utils as parse_utils
from tale.load_items import load_item, load_items
from tale.mcp.validation import validate_zone, validate_location, validate_npc, validate_item
from tale.mcp.events import StoryEvents

__all__ = ["StoryManager", "register", "current", "get"]


# --- module-level registry for in-process access ------------------------------

_current: Optional["StoryManager"] = None


def register(manager: "StoryManager") -> None:
    """Register the live StoryManager so in-process code can obtain it."""
    global _current
    _current = manager


def current() -> "StoryManager":
    """Return the live StoryManager (raises if none has been registered)."""
    if _current is None:
        raise RuntimeError("no StoryManager is registered; the driver has not created one yet")
    return _current


def get() -> "StoryManager":
    """Alias for :func:`current`."""
    return current()


class StoryManager:
    """Modification layer over a :class:`~tale.llm.dynamic_story.DynamicStory`.

    Wraps a DynamicStory and exposes a JSON-friendly mutation API. All state
    mutations are guarded by a lock so that calls arriving on other threads
    (for instance the MCP server's threads) are safe.
    """

    def __init__(self, story, llm_util=None, driver=None) -> None:
        from tale.llm.dynamic_story import WorldInfo, Catalogue
        self._story = story
        self._llm_util = llm_util
        self._driver = driver
        self._lock = threading.Lock()
        # make sure the story has the live-world and catalogue objects it needs
        # (a bare DynamicStory creates them in __init__, but a reconstructed one
        # may not have them yet).
        if not hasattr(story, "_world") or story._world is None:
            story._world = WorldInfo()
        if not hasattr(story, "_catalogue") or story._catalogue is None:
            story._catalogue = Catalogue()
        # Stage 2: a manager-owned ring buffer of wiretap events, subscribed to
        # the live world's wiretap topics so an agent can poll what is happening.
        self._events = StoryEvents(maxlen=500)
        self._subscribe_events()

    # -- helpers ----------------------------------------------------------------

    @property
    def story(self):
        """The wrapped DynamicStory."""
        return self._story

    # -- event polling (Stage 2) ------------------------------------------------
    # A manager-owned :class:`StoryEvents` listener is subscribed to the wiretap
    # pubsub topic of every known location, live NPC and connected player. It
    # buffers the structured messages the LLM reasons over (see
    # Location.tell / Living.tell), so an agent can poll what is happening in
    # the live world without touching base.py.

    def _subscribe_events(self) -> None:
        """(Re)subscribe the event listener to every known wiretap topic.

        Subscribes to the wiretap of every location in the live world, every
        live NPC in the world store, and (if a driver is present) every
        connected player. Re-subscribing is idempotent (a topic keeps a single
        weakref to the listener), so this is safe to call whenever new
        locations/NPCs appear.
        """
        for location in self._story._world._locations.values():
            location.get_wiretap().subscribe(self._events)
        for npc in self._story.world.npcs.values():
            npc.get_wiretap().subscribe(self._events)
        driver = self._driver
        if driver:
            for conn in driver.all_players.values():
                conn.player.get_wiretap().subscribe(self._events)

    def poll_events(self, since: int = 0) -> list:
        """Wiretap events with ``index > since`` (newest last).

        Each event is ``{"index", "time", "kind", "source", "text"}`` where
        ``kind`` is ``"wiretap-location"`` or ``"wiretap-living"``. Poll with
        the highest ``index`` you have seen to avoid re-reading old events.
        """
        return self._events.since(since)

    def reset_events(self) -> None:
        """Drop the buffered events and reset the cursor (fresh start)."""
        self._events = StoryEvents(maxlen=500)
        self._subscribe_events()

    # -- case-insensitive lookups ------------------------------------------------
    # Location names are stored with whatever case they were created with, but
    # the serialized form (save_locations) capitalizes them. To keep the API
    # stable across save/load and so an agent can use the names it sees in the
    # list/get tools, all lookups below are case-insensitive.

    def _zone(self, name: str):
        """Find a zone by name, case-insensitively."""
        if name in self._story._zones:
            return self._story._zones[name]
        lower = name.lower()
        for key, zone in self._story._zones.items():
            if key.lower() == lower:
                return zone
        return None

    def _zone_location(self, zone: str, name: str):
        """Find a location in a zone, case-insensitively. Returns (zone_obj, location)."""
        zone_obj = self._zone(zone)
        if not zone_obj:
            return None, None
        if name in zone_obj.locations:
            return zone_obj, zone_obj.locations[name]
        lower = name.lower()
        for key, loc in zone_obj.locations.items():
            if key.lower() == lower:
                return zone_obj, loc
        return zone_obj, None

    def _find_location(self, name: str):
        """Find a location in any zone, case-insensitively."""
        lower = name.lower()
        for zone in self._story._zones.values():
            for key, loc in zone.locations.items():
                if key.lower() == lower:
                    return loc
        return None

    def _location_dict(self, zone: str, name: str) -> dict:
        _zone_obj, location = self._zone_location(zone, name)
        if location is None:
            return {}
        info = parse_utils.save_locations([location])[0]
        # tuples are not JSON-friendly; serialize the coord as a list
        info['world_location'] = list(info['world_location'])
        return info

    # -- config -----------------------------------------------------------------

    def get_config(self) -> dict:
        """Return the story config as a JSON-friendly dict."""
        config = self._story.config
        context = config.context
        return dict(
            name=config.name,
            author=config.author,
            author_address=config.author_address,
            version=config.version,
            supported_modes=[m.name for m in config.supported_modes],
            player_name=config.player_name,
            player_gender=config.player_gender,
            player_race=config.player_race,
            player_money=config.player_money,
            money_type=config.money_type.name,
            server_tick_method=config.server_tick_method.name,
            server_tick_time=config.server_tick_time,
            gametime_to_realtime=config.gametime_to_realtime,
            max_wait_hours=config.max_wait_hours,
            display_gametime=config.display_gametime,
            startlocation_player=config.startlocation_player,
            startlocation_wizard=config.startlocation_wizard,
            savegames_enabled=config.savegames_enabled,
            show_exits_in_look=config.show_exits_in_look,
            context=context.to_json() if isinstance(context, StoryContext) else context,
            type=config.type,
            world_info=config.world_info,
            world_mood=config.world_mood,
            custom_resources=config.custom_resources,
            day_night=config.day_night,
            random_events=config.random_events,
            mud_host=config.mud_host,
            mud_port=config.mud_port,
            zones=list(config.zones),
        )

    def set_config(self, **fields) -> None:
        """Set the given config fields. ``supported_modes`` accepts a list of
        mode names; ``context`` accepts a base-story string."""
        with self._lock:
            config = self._story.config
            modes = fields.pop("supported_modes", None)
            if modes is not None:
                config.supported_modes = {GameMode(m) if isinstance(m, str) else m for m in modes}
            context = fields.pop("context", None)
            if context is not None:
                config.context = StoryContext(context) if isinstance(context, str) else context
            for key, value in fields.items():
                if hasattr(config, key):
                    setattr(config, key, value)

    # -- zones ------------------------------------------------------------------

    def zone_example(self) -> dict:
        """Return an example zone dict with all fields."""
        example_zone = Zone("Example Zone", descr="This is an example zone.")
        example_zone.locations["Example Location"] = Location(
            "Example Location",
            descr="This is an example location.",
            short_descr="An example location.",
            world_location=Coord(0, 0, 0),
        )
        return example_zone.get_info()

    def add_zone(self, zone: dict) -> tuple:
        """Add a zone (given as a dict) to the story.

        Returns ``(success, error_message)``: ``(True, "")`` on success, or
        ``(False, "what went wrong")`` on failure.
        """
        with self._lock:
            z, error = validate_zone(zone)
            if error:
                return False, error
            if not self._story.add_zone(z):
                return False, f"zone '{z.name}' already exists"
            return True, ""

    def get_zone(self, name: str) -> dict:
        """Return the info dict for a zone (or an empty dict if not found)."""
        zone = self._zone(name)
        return zone.get_info() if zone else {}

    def list_zones(self) -> list:
        """Return info dicts for all zones."""
        return [z.get_info() for z in self._story._zones.values()]

    def remove_zone(self, name: str) -> bool:
        """Remove a zone by name."""
        with self._lock:
            zone = self._zone(name)
            if zone is None:
                return False
            del self._story._zones[zone.name]
            return True

    def link_zones(self, a: str, b: str, direction: str) -> bool:
        """Link zone ``a`` to zone ``b`` in ``direction`` (and back the other way)."""
        with self._lock:
            za = self._zone(a)
            zb = self._zone(b)
            if za is None or zb is None:
                return False
            direction = parse_utils.validate_direction(direction) or direction
            za.neighbors[direction] = zb
            zb.neighbors[parse_utils.opposite_direction(direction)] = za
            return True

    # -- locations --------------------------------------------------------------

    def location_example(self) -> dict:
        """Return an example location dict with all fields."""
        example_loc = Location(
            "Example Location",
            descr="This is an example location.",
            short_descr="An example location.",
            world_location=Coord(0, 0, 0),
        )
        return parse_utils.save_locations([example_loc])[0]

    def add_location(self, location: dict, zone: str = '') -> tuple:
        """Add a location (given as a dict) to a zone.

        The dict needs at least a ``name`` and optionally ``descr``,
        ``short_descr``, ``world_location`` (a 3-tuple) and ``items``.

        Returns ``(success, error_message)``: ``(True, "")`` on success, or
        ``(False, "what went wrong")`` on failure.
        """
        with self._lock:
            loc, error = validate_location(location)
            if error:
                return False, error
            if zone and self._zone(zone) is None:
                return False, f"zone '{zone}' not found"
            if not self._story.add_location(loc, zone):
                return False, f"location '{loc.name}' already exists"
            self._subscribe_events()   # subscribe to the new location's wiretap
            return True, ""

    def get_location(self, zone: str, name: str) -> dict:
        """Return the serialized dict for a location."""
        return self._location_dict(zone, name)

    def list_locations(self, zone: str) -> list:
        """Return serialized dicts for all locations in a zone (or [] if the zone is missing)."""
        zone_obj = self._zone(zone)
        if not zone_obj:
            return []
        return parse_utils.save_locations(zone_obj.locations.values())

    def remove_location(self, zone: str, name: str) -> bool:
        """Remove a location from a zone (and from the live world)."""
        with self._lock:
            zone_obj, loc = self._zone_location(zone, name)
            if not zone_obj or loc is None:
                return False
            zone_obj.remove_location(loc.name)
            self._story._world._locations.pop(loc.name, None)
            self._story._world._grid.pop(loc.world_location.as_tuple(), None)
            return True

    def set_exits(self, zone: str, name: str, exits: list) -> bool:
        """Set exits on a location.

        Each exit is a dict with ``direction``, ``name`` (target location name)
        and optional ``short_descr``/``long_descr``. If the target location does
        not exist yet, a new (empty) location is created for it so the exit is
        always fully bound. Exits follow the same convention as the rest of the
        codebase (see ``parse_generated_exits``): an exit is named after the
        target location (with the direction as an alias), and the target gets a
        return exit in the opposite direction. This is also the format that
        ``save_locations``/``load_locations`` round-trip.
        """
        with self._lock:
            if self._zone(zone) is None:
                return False
            _zone_obj, location = self._zone_location(zone, name)
            if location is None:
                return False
            new_exits = []
            for exit in exits:
                direction = parse_utils.validate_direction(exit.get('direction', ''))
                if not direction:
                    continue
                target_name = exit.get('name')
                if not target_name:
                    continue
                if target_name.lower() in location.exits or direction in location.exits:
                    continue
                target = self._find_location(target_name)
                if target is None:
                    new_loc = Location(target_name)
                    new_loc.world_location = parse_utils.coordinates_from_direction(
                        location.world_location, direction)
                    new_loc.built = False
                    self._story.add_location(new_loc, zone)
                    target = new_loc
                short_descr = exit.get('short_descr', f"To the {direction} you see {target_name}.")
                long_descr = exit.get('long_descr', short_descr)
                new_exits.append(Exit(directions=[target.name, direction], target_location=target,
                                      short_descr=short_descr, long_descr=long_descr))
                # give the target a return exit in the opposite direction, if it doesn't have one yet
                opposite = parse_utils.opposite_direction(direction)
                if opposite and location.name not in target.exits and opposite not in target.exits:
                    target.add_exits([Exit(directions=[location.name, opposite], target_location=location,
                                           short_descr=f"To the {opposite} you see {location.name}.")])
            if new_exits:
                location.add_exits(new_exits)
                self._subscribe_events()   # new target locations were created above
            return True

    def exit_example(self) -> dict:
        """Return an example exit dict with all fields."""
        return {
            "direction": "direction to exit location (e.g. 'north', 'up', 'down')",
            "name": "Name of location to exit to",
            "short_descr": "To the north you see Example Location.",
            "long_descr": "Can include a more detailed description of the exit itself.",
        }

    # -- catalogue (world items & creatures as dicts) ---------------------------

    def item_example(self) -> dict:
        """Return an example world item dict with all fields."""
        return {
            "name": "example item",
            "type": "Money, Weapon, Armor, Food, Drink, Container, Key, Tool, Other",
            "description": "This is an example item.",
            "short_description": "An example item.",
            "weight": 1.0,
            "value": 10,
        }

    def creature_example(self) -> dict:
        """Return an example world creature dict with all fields."""
        return {
            "name": "example creature",
            "description": "This is an example creature.",
            "short_description": "An example creature.",
            "race": "One of the races in the world",
            "gender": "m, f, n",
            "level": 1,
            "health": 100,
            "attack": 10,
            "defense": 5,
        }

    def add_item(self, item: dict) -> bool:
        """Add a world item to the catalogue (as a dict)."""
        with self._lock:
            return self._story.catalogue.add_item(item)

    def add_creature(self, creature: dict) -> bool:
        """Add a world creature to the catalogue (as a dict)."""
        with self._lock:
            return self._story.catalogue.add_creature(creature)

    def list_items(self) -> list:
        """Return all catalogue items as dicts."""
        return list(self._story.catalogue.get_items())

    def list_creatures(self) -> list:
        """Return all catalogue creatures as dicts."""
        return list(self._story.catalogue.get_creatures())

    def remove_item(self, name: str) -> bool:
        """Remove an item from the catalogue by name."""
        with self._lock:
            items = self._story.catalogue._items
            for i, item in enumerate(items):
                if item['name'] == name:
                    del items[i]
                    return True
            return False

    def remove_creature(self, name: str) -> bool:
        """Remove a creature from the catalogue by name."""
        with self._lock:
            creatures = self._story.catalogue._creatures
            for i, creature in enumerate(creatures):
                if creature['name'] == name:
                    del creatures[i]
                    return True
            return False

    # -- world contents (live objects) ------------------------------------------

    def spawn_npc(self, creature_name: str, zone: str, location_name: str) -> bool:
        """Spawn a live NPC (from the catalogue) in a location."""
        with self._lock:
            creature = self._story.catalogue.get_creature(creature_name)
            if not creature:
                return False
            _zone_obj, location = self._zone_location(zone, location_name)
            if location is None:
                return False
            npcs = parse_utils.load_npcs([creature], world_items=self._story.catalogue.get_items())
            npc = next(iter(npcs.values()))
            location.insert(npc, None)
            self._story.world.add_npc(npc)
            self._subscribe_events()   # subscribe to the new NPC's wiretap
            return True

    def spawn_item(self, item_name: str, zone: str, location_name: str) -> bool:
        """Spawn a live item (from the catalogue) in a location."""
        with self._lock:
            item = self._story.catalogue.get_item(item_name)
            if not item:
                return False
            _zone_obj, location = self._zone_location(zone, location_name)
            if location is None:
                return False
            loaded = load_item(item)
            location.insert(loaded, None)
            self._story.world.add_item(loaded)
            return True

    def list_world_npcs(self) -> dict:
        """Return all live NPCs in the world as a dict keyed by name."""
        npcs = parse_utils.save_npcs(self._story.world.npcs.values())
        return {info['name']: info for info in npcs.values()}

    def list_world_items(self) -> list:
        """Return all live items found in world locations as dicts."""
        items = []
        for location in self._story.world._locations.values():
            items.extend(parse_utils.save_items(location.items))
        return items

    # -- world live-object store (real Living/Item objects, not catalogue dicts) --
    # The WorldInfo object holds real Living/Item objects (with stats, inventory,
    # etc.), unlike the Catalogue which holds plain dicts. These methods let an
    # agent populate that live store directly, which is about *preparing* a story
    # before it is played rather than mutating a running one. The objects are not
    # inserted into a location (use spawn_npc/spawn_item for that).

    def add_world_npc(self, npc: dict) -> tuple:
        """Add a live NPC (given as a dict) to the world's live-object store.

        Creates a real Living object (unlike the catalogue's plain dicts) and
        adds it to the world store without inserting it into a location.

        Returns ``(success, error_message)``: ``(True, "")`` on success, or
        ``(False, "what went wrong")`` on failure.
        """
        with self._lock:
            npc_obj, error = validate_npc(npc, world_items=self._story.catalogue.get_items())
            if error:
                return False, error
            if not self._story.world.add_npc(npc_obj):
                return False, f"npc '{npc_obj.name}' already exists"
            self._subscribe_events()   # subscribe to the new NPC's wiretap
            return True, ""

    def add_world_item(self, item: dict) -> tuple:
        """Add a live item (given as a dict) to the world's live-object store.

        Creates a real Item object (unlike the catalogue's plain dicts) and adds
        it to the world store without inserting it into a location.

        Returns ``(success, error_message)``: ``(True, "")`` on success, or
        ``(False, "what went wrong")`` on failure.
        """
        with self._lock:
            item_obj, error = validate_item(item)
            if error:
                return False, error
            if not self._story.world.add_item(item_obj):
                return False, f"item '{item_obj.name}' already exists"
            return True, ""

    def get_world_npc(self, name: str) -> dict:
        """Return the serialized dict for a live NPC in the world's store (or an
        empty dict if not found)."""
        try:
            npc = self._story.world.get_npc(name)
        except KeyError:
            return {}
        npcs = parse_utils.save_npcs([npc])
        return next(iter(npcs.values()))

    def get_world_item(self, name: str) -> dict:
        """Return the serialized dict for a live item in the world's store (or an
        empty dict if not found)."""
        try:
            item = self._story.world.get_item(name)
        except KeyError:
            return {}
        items = parse_utils.save_items([item])
        return items[0]

    # -- live state reads (Stage 1) --------------------------------------------
    # Read-only views of the *live* world (players, NPCs, locations, story
    # progress, and a world map). These follow the existing read convention:
    # no lock, JSON-friendly dicts/lists out. They mirror the structured state
    # the LLM reasons over (see tale.llm.contexts.ActionContext) so an agent's
    # decisions stay coherent with the narrative.

    def _location_zone_name(self, location) -> dict:
        """Map a live Location to ``{"zone": zone_name, "name": location_name}``
        (or an empty dict for a None location)."""
        if location is None:
            return {}
        zone = self._story.find_zone(location.name)
        return {"zone": zone.name, "name": location.name} if zone else {"zone": None, "name": location.name}

    def _stats_dict(self, stats) -> dict:
        """JSON-friendly dict of the numeric attributes of a :class:`Stats`."""
        return {
            "level": stats.level,
            "hp": stats.hp,
            "max_hp": stats.max_hp,
            "xp": stats.xp,
            "ac": stats.ac,
            "wc": stats.wc,
            "race": stats.race,
            "gender": stats.gender,
            "strength": stats.strength,
            "dexterity": stats.dexterity,
            "perception": stats.perception,
            "intelligence": stats.intelligence,
        }

    def _player_names(self) -> set:
        """The set of player names connected via the driver (empty if no driver)."""
        driver = self._driver
        if not driver:
            return set()
        return {conn.player.name for conn in driver.all_players.values()}

    def list_players(self) -> list:
        """[{name, location:{zone,name}|None, hp:int, alive:bool, idle_time:float}]

        One entry per connected player. Returns an empty list when there is no
        driver. Note: combat is transient (a single round via ``start_attack``),
        so there is no persistent ``in_combat`` flag to expose.
        """
        players = []
        driver = self._driver
        if not driver:
            return players
        for conn in driver.all_players.values():
            player = conn.player
            players.append({
                "name": player.name,
                "location": self._location_zone_name(player.location),
                "hp": player.stats.hp,
                "alive": player.alive,
                "idle_time": getattr(player, "idle_time", 0.0),
            })
        return players

    def get_player(self, name: str) -> dict:
        """Full player state (case-insensitive name lookup): name, title,
        location, inventory, stats, hp, alive, idle_time. Returns an empty dict
        if the player is not found or there is no driver."""
        driver = self._driver
        if not driver:
            return {}
        lower = name.lower()
        for conn in driver.all_players.values():
            player = conn.player
            if player.name.lower() == lower:
                return {
                    "name": player.name,
                    "title": player.title,
                    "location": self._location_zone_name(player.location),
                    "inventory": sorted(item.name for item in player.inventory),
                    "stats": self._stats_dict(player.stats),
                    "hp": player.stats.hp,
                    "alive": player.alive,
                    "idle_time": getattr(player, "idle_time", 0.0),
                }
        return {}

    def get_npc(self, name: str) -> dict:
        """Full state of a live NPC in the world's store (or an empty dict if
        not found): name, title, short_description, description,
        location:{zone,name}, alive, visible, hidden, goal, level, stats,
        action_history, planned_actions."""
        try:
            npc = self._story.world.get_npc(name)
        except KeyError:
            return {}
        return {
            "name": npc.name,
            "title": npc.title,
            "short_description": npc.short_description,
            "description": npc.description,
            "location": self._location_zone_name(npc.location),
            "alive": npc.alive,
            "visible": npc.visible,
            "hidden": npc.hidden,
            "goal": getattr(npc, "goal", None),
            "level": npc.stats.level,
            "stats": self._stats_dict(npc.stats),
            "action_history": getattr(npc, "action_history", []),
            "planned_actions": getattr(npc, "planned_actions", []),
        }

    def get_location_live(self, zone: str, name: str) -> dict:
        """The structured live state of a location (mirrors ActionContext):
        name, description, short_descr, indoors, world_location:[x,y,z],
        exits:{direction: target_name},
        livings:[{name, short_descr, alive, visible, is_player}],
        items:[{name, look_description, visible}]. Returns an empty dict if the
        location is not found."""
        _zone_obj, location = self._zone_location(zone, name)
        if location is None:
            return {}
        player_names = self._player_names()
        livings = []
        for living in location.livings:
            livings.append({
                "name": living.name,
                "short_descr": living.short_description,
                "alive": living.alive,
                "visible": living.visible,
                "is_player": living.name in player_names,
            })
        items = []
        for item in location.items:
            items.append({
                "name": item.name,
                "look_description": item.look_description,
                "visible": item.visible,
            })
        world_location = location.world_location
        return {
            "name": location.name,
            "description": location.description,
            "short_descr": location.short_description,
            "indoors": location.indoors,
            "world_location": list(world_location.as_tuple()) if world_location else [0, 0, 0],
            "exits": {direction: exit.target.name for direction, exit in location.exits.items()},
            "livings": livings,
            "items": items,
        }

    def get_story_state(self) -> dict:
        """The story's narrative state: story (the context string with past
        sections), current_section, past_sections, progress, length, name,
        type, world_info, world_mood."""
        config = self._story.config
        context = config.context
        if isinstance(context, StoryContext):
            return {
                "story": context.to_context_with_past(),
                "current_section": context.current_section,
                "past_sections": list(context.past_sections),
                "progress": context.progress,
                "length": context.length,
                "name": config.name,
                "type": config.type,
                "world_info": config.world_info,
                "world_mood": config.world_mood,
            }
        # the context may be a bare base-story string (not yet a StoryContext)
        return {
            "story": context if isinstance(context, str) else str(context),
            "current_section": "",
            "past_sections": [],
            "progress": 0.0,
            "length": 0.0,
            "name": config.name,
            "type": config.type,
            "world_info": config.world_info,
            "world_mood": config.world_mood,
        }

    def get_world_map(self) -> dict:
        """{zone_name: {location_name: {indoors, npc_count, item_count,
        exits:[directions]}}} - a compact map of the whole world."""
        result = {}
        for zone_name, zone in self._story._zones.items():
            locations = {}
            for loc_name, location in zone.locations.items():
                locations[loc_name] = {
                    "indoors": location.indoors,
                    "npc_count": len(location.livings),
                    "item_count": len(location.items),
                    "exits": sorted(location.exits.keys()),
                }
            result[zone_name] = locations
        return result

    # -- story progression ------------------------------------------------------

    def set_story_context(self, base_story: str) -> None:
        """Set the base plot of the story context."""
        with self._lock:
            self._story.config.context = StoryContext(base_story)

    def advance_story_section(self, section: str) -> None:
        """Advance the story context to a new section."""
        with self._lock:
            context = self._story.config.context
            if isinstance(context, StoryContext):
                context.set_current_section(section)

    def set_start_location(self, zone: str, name: str) -> None:
        """Set the player/wizard start location to ``zone.name``.

        Uses the location's stored name (case as created) so the driver's
        start-location lookup finds it after a save/load round-trip.
        """
        with self._lock:
            _zone_obj, location = self._zone_location(zone, name)
            location_name = location.name if location else name
            location = f"{zone}.{location_name}"
            self._story.config.startlocation_player = location
            self._story.config.startlocation_wizard = location

    # -- persistence ------------------------------------------------------------

    def save(self, path: str) -> None:
        """Save the story to disk (see :meth:`DynamicStory.save`).

        This API is used by the MCP server, so absolute paths are allowed;
        they are still validated by ``DynamicStory.save``.
        """
        self._story.save(path, allow_absolute=True)

    def load(self, path: str) -> None:
        """Load a story from a saved directory, replacing the current state.

        Reads ``world.json``, ``story_config.json`` and (if present) ``llm_cache.json``
        from ``path`` and rebuilds the story's zones, locations, catalogue, live
        NPCs/items and spawners in place.
        """
        with self._lock:
            from tale.llm.dynamic_story import WorldInfo, Catalogue
            from tale.parse import parse_locations
            import tale.llm.llm_cache as llm_cache

            world = parse_utils.load_json(os.path.join(path, 'world.json'))
            config = parse_utils.load_story_config(parse_utils.load_json(os.path.join(path, 'story_config.json')))

            # reset state and rebuild from the saved files
            self._story._zones = dict()
            self._story._world = WorldInfo()
            self._story._catalogue = Catalogue()
            self._story.config = config

            for zone_json in world.get('zones', {}).values():
                zones, _exits = parse_locations.load_locations(zone_json)
                for zname, z in zones.items():
                    self._story.add_zone(z)
                    for loc in z.locations.values():
                        self._story.add_location(loc, zname)

            catalogue = world.get('catalogue', {})
            if catalogue.get('creatures'):
                self._story._catalogue._creatures = catalogue['creatures']
            if catalogue.get('items'):
                self._story._catalogue._items = catalogue['items']

            worldinfo = world.get('world', {})
            if worldinfo.get('items'):
                self._story._world.items = load_items(worldinfo['items'].values(), self._story.locations)
            if worldinfo.get('npcs'):
                self._story._world.npcs = parse_utils.load_npcs(
                    worldinfo['npcs'].values(), locations=self._story.locations,
                    world_items=self._story.catalogue.get_items())
            # WorldInfo.to_json() saves mob spawners under 'mob_spawners';
            # some older files (and JsonStory) use 'spawners'
            mob_spawners = worldinfo.get('mob_spawners') or worldinfo.get('spawners')
            if mob_spawners:
                self._story._world.mob_spawners = parse_utils.load_mob_spawners(
                    mob_spawners, self._story.locations,
                    self._story.catalogue.get_creatures(), self._story.catalogue.get_items())
            if worldinfo.get('item_spawners'):
                self._story._world.item_spawners = parse_utils.load_item_spawners(
                    worldinfo['item_spawners'], self._story._zones, self._story.catalogue.get_items())

            llm_cache_path = os.path.join(path, 'llm_cache.json')
            if os.path.exists(llm_cache_path):
                llm_cache.load(parse_utils.load_json(llm_cache_path))
            self._subscribe_events()   # the world was rebuilt; subscribe to its wiretaps

    # -- LLM-backed generation (optional; delegates to WorldBuilding, then
    #    applies the result to the story via the mutation API above) -----------

    def generate_world_items(self, count: int = 7) -> list:
        """Generate world items via the LLM, add them to the catalogue, and
        return them as dicts."""
        if not self._llm_util:
            raise RuntimeError("generate_world_items requires an llm_util")
        response = self._llm_util.generate_world_items(count=count)
        if not getattr(response, 'valid', False):
            return []
        items = list(response.items)
        with self._lock:
            for item in items:
                self._story.catalogue.add_item(item)
        return items

    def generate_world_creatures(self, count: int = 5) -> list:
        """Generate world creatures via the LLM, add them to the catalogue, and
        return them as dicts."""
        if not self._llm_util:
            raise RuntimeError("generate_world_creatures requires an llm_util")
        response = self._llm_util.generate_world_creatures(count=count)
        if not getattr(response, 'valid', False):
            return []
        creatures = list(response.creatures)
        with self._lock:
            for creature in creatures:
                self._story.catalogue.add_creature(creature)
        return creatures

    def generate_start_zone(self, location_desc: str) -> dict:
        """Generate a starting zone via the LLM, add it to the story, and return
        it as an info dict (or an empty dict if generation failed)."""
        if not self._llm_util:
            raise RuntimeError("generate_start_zone requires an llm_util")
        story = self._story
        world_info = {
            'world_description': story.config.world_info,
            'world_mood': story.config.world_mood,
            'world_items': list(story.catalogue.get_items()),
            'world_creatures': list(story.catalogue.get_creatures()),
        }
        zone = self._llm_util.generate_start_zone(
            location_desc=location_desc,
            story_type=story.config.type,
            story_context=story.config.context,
            world_info=world_info,
        )
        if zone is None:
            return {}
        with self._lock:
            self._story.add_zone(zone)
            for loc in zone.locations.values():
                self._story.add_location(loc, zone.name)
        return zone.get_info()

    def generate_location(self, zone: str, name: str, exit_name: str) -> dict:
        """Generate a location (via the LLM) adjacent to the existing location
        ``zone.name``, and apply the result to the story.

        Returns the serialized source location dict (with its new exits), or an
        empty dict if the location was not found or generation failed.
        """
        if not self._llm_util:
            raise RuntimeError("generate_location requires an llm_util")
        zone_obj, location = self._zone_location(zone, name)
        if location is None:
            return {}
        with self._lock:
            zone_info = zone_obj.get_info()
            neighbors = self._story.neighbors_for_location(location)
            response, _spawner = self._llm_util.build_location(
                location, exit_name, zone_info,
                neighbors=neighbors, zone=zone_obj,
            )
            if not getattr(response, 'valid', False):
                return {}
            for new_loc in response.new_locations:
                self._story.add_location(new_loc, zone)
            location.add_exits(response.exits)
            for npc in response.npcs:
                self._story.world.add_npc(npc)
            return self._location_dict(zone, location.name)

    # -- live mutations (Stage 3) -----------------------------------------------
    # These mutate the *running* story (descriptions, exits, NPC movement and
    # actions). All are guarded by the manager lock, reuse the case-insensitive
    # lookups above, and re-subscribe the event listener when new wiretap
    # topics (locations/NPCs) appear. The MCP wrappers convert any
    # (success, error) tuple into the JSON {"success", "error"} dict.

    def _find_living(self, name: str):
        """Find a live living (NPC or player) by name, case-insensitively.

        Checks the world NPC store first, then (if a driver is present) the
        connected players. Returns the Living object or None.
        """
        try:
            return self._story.world.get_npc(name)
        except KeyError:
            pass
        lower = name.lower()
        driver = self._driver
        if driver:
            for conn in driver.all_players.values():
                if conn.player.name.lower() == lower:
                    return conn.player
        return None

    def _location_exit(self, location, direction: str):
        """Find an exit on ``location`` by direction (case-insensitive),
        checking the direction and all of its aliases."""
        if direction in location.exits:
            return location.exits[direction]
        lower = direction.lower()
        for name, exit in location.exits.items():
            if name.lower() == lower or any(alias.lower() == lower for alias in exit.aliases):
                return exit
        return None

    def set_location_description(self, zone: str, name: str, description: str,
                                 short_descr: str = '') -> tuple:
        """Set the description (and optionally short description) of a live
        location. Returns ``(success, error_message)``."""
        with self._lock:
            if self._zone(zone) is None:
                return False, f"zone '{zone}' not found"
            _zone_obj, location = self._zone_location(zone, name)
            if location is None:
                return False, f"location '{name}' not found in zone '{zone}'"
            location.description = description
            if short_descr:
                location.short_description = short_descr
            return True, ""

    def add_exit(self, zone: str, name: str, direction: str, target: str,
                 short_descr: str = '') -> tuple:
        """Add a single exit from ``zone.name`` in ``direction`` to ``target``.

        If the target location does not exist yet, a new (empty) location is
        created for it (following the ``set_exits`` convention): the exit is
        named after the target (with the direction as an alias), and the target
        gets a return exit in the opposite direction. Returns
        ``(success, error_message)``.
        """
        with self._lock:
            if self._zone(zone) is None:
                return False, f"zone '{zone}' not found"
            _zone_obj, location = self._zone_location(zone, name)
            if location is None:
                return False, f"location '{name}' not found in zone '{zone}'"
            direction = parse_utils.validate_direction(direction) or direction
            if not target:
                return False, "target location name is required"
            if target.lower() in location.exits or direction in location.exits:
                return False, f"exit to '{target}' already exists in direction '{direction}'"
            target_loc = self._find_location(target)
            created = False
            if target_loc is None:
                target_loc = Location(target)
                target_loc.world_location = parse_utils.coordinates_from_direction(
                    location.world_location, direction)
                target_loc.built = False
                if not self._story.add_location(target_loc, zone):
                    return False, f"location '{target}' already exists"
                created = True
            short = short_descr or f"To the {direction} you see {target}."
            location.add_exits([Exit(directions=[target_loc.name, direction], target_location=target_loc,
                                     short_descr=short, long_descr=short)])
            opposite = parse_utils.opposite_direction(direction)
            if opposite and location.name not in target_loc.exits and opposite not in target_loc.exits:
                target_loc.add_exits([Exit(directions=[location.name, opposite], target_location=location,
                                           short_descr=f"To the {opposite} you see {location.name}.")])
            if created:
                self._subscribe_events()   # subscribe to the new location's wiretap
            return True, ""

    def remove_exit(self, zone: str, name: str, direction: str) -> tuple:
        """Remove an exit (and its target-name alias) from ``zone.name``.
        Returns ``(success, error_message)``."""
        with self._lock:
            if self._zone(zone) is None:
                return False, f"zone '{zone}' not found"
            _zone_obj, location = self._zone_location(zone, name)
            if location is None:
                return False, f"location '{name}' not found in zone '{zone}'"
            exit = self._location_exit(location, direction)
            if exit is None:
                return False, f"no exit in direction '{direction}' from '{name}'"
            for key in list(exit.names):
                if location.exits.get(key) is exit:
                    del location.exits[key]
            return True, ""

    def set_exit_state(self, zone: str, name: str, direction: str, open: bool) -> tuple:
        """Open or close an exit from ``zone.name`` in ``direction``.

        For a :class:`Door` this sets ``door.opened`` (and the linked door's
        ``opened``). For a plain :class:`Exit` (which is always open),
        ``open=False`` removes the exit and ``open=True`` re-adds it to the same
        target. Returns ``(success, error_message)``.
        """
        with self._lock:
            if self._zone(zone) is None:
                return False, f"zone '{zone}' not found"
            _zone_obj, location = self._zone_location(zone, name)
            if location is None:
                return False, f"location '{name}' not found in zone '{zone}'"
            exit = self._location_exit(location, direction)
            if exit is None:
                return False, f"no exit in direction '{direction}' from '{name}'"
            if isinstance(exit, Door):
                exit.opened = open
                if exit.linked_door:
                    exit.linked_door.opened = open
                return True, ""
            # plain Exit: it is always open, so 'close' = remove it
            if open:
                return True, ""   # nothing to do; it is already open
            target = exit.target
            for key in list(exit.names):
                if location.exits.get(key) is exit:
                    del location.exits[key]
            return True, ""

    def move_npc(self, name: str, zone: str, location_name: str) -> tuple:
        """Move a live NPC to ``zone.location_name``.

        The NPC is moved directly (transactionally) into the target location.
        Returns ``(success, error_message)``.
        """
        with self._lock:
            npc = self._find_living(name)
            if npc is None:
                return False, f"npc '{name}' not found"
            if self._zone(zone) is None:
                return False, f"zone '{zone}' not found"
            _zone_obj, target = self._zone_location(zone, location_name)
            if target is None:
                return False, f"location '{location_name}' not found in zone '{zone}'"
            npc.move(target, actor=npc)
            return True, ""

    def npc_say(self, name: str, text: str, target: str = '') -> tuple:
        """Make a live NPC say ``text`` to the room, or to a specific living
        if ``target`` is given (a living in the same location).
        Returns ``(success, error_message)``.
        """
        with self._lock:
            npc = self._find_living(name)
            if npc is None:
                return False, f"npc '{name}' not found"
            if not text:
                return False, "text is required"
            if target:
                living = self._find_living(target)
                if living is None:
                    return False, f"target '{target}' not found"
                npc.tell_others(text, target=living, evoke=False)
            else:
                npc.tell_others(text, evoke=False)
            return True, ""

    def npc_attack(self, name: str, target_name: str) -> tuple:
        """Make a live NPC attack another living (one combat round).
        Returns ``(success, error_message)``.
        """
        with self._lock:
            npc = self._find_living(name)
            if npc is None:
                return False, f"npc '{name}' not found"
            if not target_name:
                return False, "target_name is required"
            target = self._find_living(target_name)
            if target is None:
                return False, f"target '{target_name}' not found"
            npc.start_attack(target)
            return True, ""

    def npc_do(self, name: str, action: dict) -> tuple:
        """Force a live NPC to perform a specific action (say/move/take/give/
        attack/wear/hide/search) by building an :class:`ActionResponse` from
        ``action`` and running it through :meth:`LivingNpc._parse_action`.

        ``action`` may contain ``goal``, ``thoughts``, ``text``, ``action``,
        ``target`` and ``item``. Returns ``(success, error_message)``.
        """
        with self._lock:
            npc = self._find_living(name)
            if npc is None:
                return False, f"npc '{name}' not found"
            if not isinstance(npc, LivingNpc):
                return False, f"npc '{name}' is not an LLM NPC (LivingNpc)"
            response = ActionResponse(action or {})
            if not response.action:
                return False, "action dict needs an 'action' field"
            npc._parse_action(response)
            return True, ""

    def set_npc_goal(self, name: str, goal: str) -> tuple:
        """Set the free-form goal of a live NPC.
        Returns ``(success, error_message)``.
        """
        with self._lock:
            npc = self._find_living(name)
            if npc is None:
                return False, f"npc '{name}' not found"
            npc.goal = goal
            return True, ""

    # -- LLM handoff (Phase 3) -------------------------------------------------
    # The LLM path (WorldBuilding) is a *generator*: it produces a
    # LocationResponse (and an optional MobSpawner). The story-level
    # *application* of that output is routed through the manager here, so the
    # LLM path modifies the story through the same layer as MCP. The methods
    # below take real objects (Zone / Location / LocationResponse) rather than
    # plain dicts, because they apply already-constructed LLM output; they are
    # not exposed as MCP tools (the agent-facing API stays dict-based).

    def apply_location_response(self, response, zone, source_location, spawner=None) -> bool:
        """Apply a :class:`LocationResponse` (from ``WorldBuilding.build_location``)
        to the story.

        Adds the response's new locations to the zone, adds its exits to the
        ``source_location``, generates quests for stationary NPCs and note
        text for Note items, and registers the mob ``spawner`` (if any) with
        the world.

        ``zone`` is the :class:`Zone` the locations belong to. Returns True if
        new locations were added, False otherwise (mirroring
        ``Driver.build_location``).
        """
        with self._lock:
            new_locations = response.new_locations
            exits = response.exits
            npcs = response.npcs
            items = response.items
            if not new_locations:
                return False
            for location in new_locations:
                # try to add location, and if it fails, remove exit to it
                result = self._story.add_location(location, zone=zone.name)
                if not result:
                    for exit in exits:
                        if exit.name == location.name:
                            exits.remove(exit)
            for exit in exits:
                try:
                    source_location.add_exits([exit])
                except LocationIntegrityError:
                    # fail silently
                    pass
            for npc in npcs:
                if isinstance(npc, StationaryNpc) and random.random() < 0.2:
                    new_quest = self._story.generate_quest(npc)
                    new_quest.giver = npc
                    npc.quest = new_quest
            for item in items:
                if isinstance(item, Note) and self._llm_util:
                    if random.random() < 0.5:
                        new_quest = self._llm_util.generate_note_quest(zone_info=zone.get_info())
                        new_quest.giver = item
                        item.text = new_quest.reason
                    else:
                        text = self._llm_util.generate_note_lore(zone_info=zone.get_info())
                        item.text = text
            if spawner:
                self._story.world.add_mob_spawner(spawner)
            return True

    def add_zone_object(self, zone: Zone) -> bool:
        """Add a :class:`Zone` object directly to the story (LLM handoff).

        Unlike :meth:`add_zone` (which takes a dict and constructs a new
        Zone), this adds the given Zone object as-is, so the caller keeps a
        reference to the same object (and can keep mutating it). Returns True
        if it was added, False if a zone with the same name already exists.
        """
        with self._lock:
            return self._story.add_zone(zone)

    def add_location_object(self, location: Location, zone: str = '') -> bool:
        """Add a :class:`Location` object directly to the story (LLM handoff).

        Unlike :meth:`add_location` (which takes a dict and constructs a new
        Location), this adds the given Location object as-is (to the world and
        to the named zone). Returns True if it was added, False if a location
        with the same name already exists in the zone.
        """
        with self._lock:
            result = self._story.add_location(location, zone=zone)
            if result:
                self._subscribe_events()
            return result

    def add_world_npc_object(self, npc) -> bool:
        """Add a live NPC object directly to the world's store (LLM handoff).

        Unlike :meth:`add_world_npc` (which takes a dict and constructs a new
        Living), this adds the given Living object as-is. Returns True if it
        was added, False if an NPC with the same name already exists.
        """
        with self._lock:
            result = self._story.world.add_npc(npc)
            if result:
                self._subscribe_events()
            return result

    def add_world_item_object(self, item) -> bool:
        """Add a live item object directly to the world's store (LLM handoff).

        Unlike :meth:`add_world_item` (which takes a dict and constructs a new
        Item), this adds the given Item object as-is. Returns True if it was
        added, False if an item with the same name already exists.
        """
        with self._lock:
            return self._story.world.add_item(item)
