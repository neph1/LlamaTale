"""
StoryManager - a single modification layer over a DynamicStory.

Both the MCP server (the agent) and the LLM path (via tale.llm.WorldBuilding)
route story modifications through this class. It exposes a JSON-friendly
mutation API: plain dicts in, dicts/bools out.

This module lives in the tale/ root (not tale/llm/) because it is about story
*state*, not about LLM generation, and it is the stable hook that the MCP
server depends on.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import os
import threading
from typing import Any, Optional

from tale.base import Location, Exit
from tale.coord import Coord
from tale.story import GameMode
from tale.story_context import StoryContext
from tale.zone import Zone

import tale.parse_utils as parse_utils
from tale.load_items import load_item, load_items

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

    # -- helpers ----------------------------------------------------------------

    @property
    def story(self):
        """The wrapped DynamicStory."""
        return self._story

    def _location_dict(self, zone: str, name: str) -> dict:
        location = self._story.get_location(zone, name)
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

    def add_zone(self, zone: dict) -> bool:
        """Add a zone (given as a dict) to the story."""
        with self._lock:
            z = Zone.from_json(zone)
            return self._story.add_zone(z)

    def get_zone(self, name: str) -> dict:
        """Return the info dict for a zone."""
        return self._story.get_zone(name).get_info()

    def list_zones(self) -> list:
        """Return info dicts for all zones."""
        return [z.get_info() for z in self._story._zones.values()]

    def remove_zone(self, name: str) -> bool:
        """Remove a zone by name."""
        with self._lock:
            if name not in self._story._zones:
                return False
            del self._story._zones[name]
            return True

    def link_zones(self, a: str, b: str, direction: str) -> bool:
        """Link zone ``a`` to zone ``b`` in ``direction`` (and back the other way)."""
        with self._lock:
            za = self._story.get_zone(a)
            zb = self._story.get_zone(b)
            if za is None or zb is None:
                return False
            direction = parse_utils.validate_direction(direction) or direction
            za.neighbors[direction] = zb
            zb.neighbors[parse_utils.opposite_direction(direction)] = za
            return True

    # -- locations --------------------------------------------------------------

    def add_location(self, location: dict, zone: str = '') -> bool:
        """Add a location (given as a dict) to a zone.

        The dict needs at least a ``name`` and optionally ``descr``,
        ``short_descr``, ``world_location`` (a 3-tuple) and ``items``.
        """
        with self._lock:
            name = location.get('name')
            if not name:
                return False
            loc = Location(name, descr=location.get('descr', ''))
            loc.short_description = location.get('short_descr', loc.short_description)
            world_location = location.get('world_location')
            if world_location:
                loc.world_location = Coord(world_location[0], world_location[1], world_location[2])
            loc.built = location.get('built', True)
            for item in location.get('items', []):
                loc.insert(load_item(item), None)
            return self._story.add_location(loc, zone)

    def get_location(self, zone: str, name: str) -> dict:
        """Return the serialized dict for a location."""
        return self._location_dict(zone, name)

    def list_locations(self, zone: str) -> list:
        """Return serialized dicts for all locations in a zone."""
        return parse_utils.save_locations(self._story.get_zone(zone).locations.values())

    def remove_location(self, zone: str, name: str) -> bool:
        """Remove a location from a zone (and from the live world)."""
        with self._lock:
            zone_obj = self._story.get_zone(zone)
            if not zone_obj.remove_location(name):
                return False
            loc = self._story._world._locations.get(name)
            if loc is not None:
                self._story._world._locations.pop(name, None)
                self._story._world._grid.pop(loc.world_location.as_tuple(), None)
            return True

    def set_exits(self, zone: str, name: str, exits: list) -> bool:
        """Set exits on a location.

        Each exit is a dict with ``direction``, ``name`` (target location name)
        and optional ``short_descr``/``long_descr``. If the target location does
        not exist yet, a new (empty) location is created for it so the exit is
        always fully bound.
        """
        with self._lock:
            if zone not in self._story._zones:
                return False
            location = self._story.get_location(zone, name)
            if location is None:
                return False
            new_exits = []
            for exit in exits:
                direction = parse_utils.validate_direction(exit.get('direction', ''))
                if not direction or direction in location.exits:
                    continue
                target_name = exit.get('name')
                target = self._story.find_location(target_name)
                if target is None:
                    new_loc = Location(target_name)
                    new_loc.world_location = parse_utils.coordinates_from_direction(
                        location.world_location, direction)
                    new_loc.built = False
                    self._story.add_location(new_loc, zone)
                    target = new_loc
                short_descr = exit.get('short_descr', f"To the {direction} you see {target_name}.")
                long_descr = exit.get('long_descr', short_descr)
                new_exits.append(Exit(directions=direction, target_location=target,
                                      short_descr=short_descr, long_descr=long_descr))
            if new_exits:
                location.add_exits(new_exits)
            return True

    # -- catalogue (world items & creatures as dicts) ---------------------------

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
            location = self._story.get_location(zone, location_name)
            if location is None:
                return False
            npcs = parse_utils.load_npcs([creature], world_items=self._story.catalogue.get_items())
            npc = next(iter(npcs.values()))
            location.insert(npc, None)
            self._story.world.add_npc(npc)
            return True

    def spawn_item(self, item_name: str, zone: str, location_name: str) -> bool:
        """Spawn a live item (from the catalogue) in a location."""
        with self._lock:
            item = self._story.catalogue.get_item(item_name)
            if not item:
                return False
            location = self._story.get_location(zone, location_name)
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
        """Set the player/wizard start location to ``zone.name``."""
        with self._lock:
            location = f"{zone}.{name}"
            self._story.config.startlocation_player = location
            self._story.config.startlocation_wizard = location

    # -- persistence ------------------------------------------------------------

    def save(self, path: str) -> None:
        """Save the story to disk (see :meth:`DynamicStory.save`)."""
        self._story.save(path)

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
            if worldinfo.get('spawners'):
                self._story._world.mob_spawners = parse_utils.load_mob_spawners(
                    worldinfo['spawners'], self._story.locations,
                    self._story.catalogue.get_creatures(), self._story.catalogue.get_items())
            if worldinfo.get('item_spawners'):
                self._story._world.item_spawners = parse_utils.load_item_spawners(
                    worldinfo['item_spawners'], self._story._zones, self._story.catalogue.get_items())

            llm_cache_path = os.path.join(path, 'llm_cache.json')
            if os.path.exists(llm_cache_path):
                llm_cache.load(parse_utils.load_json(llm_cache_path))

    # -- LLM-backed generation (optional; delegates to WorldBuilding) -----------

    def generate_world_items(self, count: int = 7) -> list:
        """Generate world items via the LLM and return them as dicts."""
        if not self._llm_util:
            raise RuntimeError("generate_world_items requires an llm_util")
        response = self._llm_util.generate_world_items(count=count)
        return list(response.items) if getattr(response, 'valid', False) else []

    def generate_world_creatures(self, count: int = 5) -> list:
        """Generate world creatures via the LLM and return them as dicts."""
        if not self._llm_util:
            raise RuntimeError("generate_world_creatures requires an llm_util")
        response = self._llm_util.generate_world_creatures(count=count)
        return list(response.creatures) if getattr(response, 'valid', False) else []

    def generate_start_zone(self, location_desc: str) -> dict:
        """Generate a starting zone via the LLM and return it as an info dict."""
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
        return zone.get_info()

    def generate_location(self, location: Location, zone: str, exit_name: str) -> dict:
        """Generate a location via the LLM and apply it to the story.

        Returns the serialized source location dict (with its new exits), or an
        empty dict if generation failed.
        """
        with self._lock:
            if not self._llm_util:
                raise RuntimeError("generate_location requires an llm_util")
            zone_obj = self._story.get_zone(zone)
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
