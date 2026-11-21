"""
EffectRunner: executes the declarative beat-boundary effects (on_start /
on_end / on_fail, see tale/scenario.py) against the live world.

Each effect is a dict with an "effect" discriminator. The built-in vocabulary
is deliberately small and maps onto operations the StoryManager already
exposes (spawn_npc, move_npc, set_npc_goal, spawn_item/add_world_item and the
inventory ops behind give_item/remove_item_from/remove_world_npc). Code-defined
stories can register custom effects with @scenario.register_effect; JSON
scenarios are limited to the built-ins (tale.scenario.Effect.from_json rejects
anything else), which keeps loading JSON closed and safe.

Effect errors are logged and the remaining effects still run: a story must not
wedge on one failed effect. The runner returns a per-effect result list so
callers (and tests) can see what happened.

'Tale' mud driver, mudlib and interactive fiction framework
"""
import logging
from typing import List

from tale import scenario
from tale.scenario import Effect

__all__ = ["EffectRunner", "run_effects"]

logger = logging.getLogger("tale.effects")


class EffectRunner:
    """Runs effect lists against the live world through a StoryManager.

    The manager is either given explicitly or resolved lazily from the global
    registry (tale.story_manager.current()), so a runner can be created before
    the driver has registered its manager."""

    def __init__(self, manager=None, story_context=None) -> None:
        self._manager = manager
        self.story_context = story_context

    @property
    def manager(self):
        if self._manager is not None:
            return self._manager
        from tale import story_manager
        return story_manager.current()

    def run(self, effects: list, story_context=None) -> List[dict]:
        """Run each effect in order. Returns a list of
        ``{"effect", "success", "error"}`` dicts, one per effect. A failing
        effect is logged and reported but does not stop the rest."""
        results = []  # type: List[dict]
        for effect in effects:
            if not isinstance(effect, Effect):
                try:
                    effect = Effect.from_json(effect)
                except ValueError as exc:
                    logger.error("skipping invalid beat effect %r: %s", effect, exc)
                    results.append({"effect": None, "success": False, "error": str(exc)})
                    continue
            handler = scenario.get_effect_handler(effect.effect)
            if handler is None:
                error = "unknown effect %r (known: %s)" % (effect.effect, ", ".join(scenario.known_effects()))
                logger.error("beat effect %r: %s", effect.effect, error)
                results.append({"effect": effect.effect, "success": False, "error": error})
                continue
            try:
                handler(self, effect.to_json())
                results.append({"effect": effect.effect, "success": True, "error": ""})
            except Exception as exc:
                logger.error("beat effect %r failed: %s", effect.effect, exc)
                results.append({"effect": effect.effect, "success": False, "error": str(exc)})
        return results


def run_effects(effects: list, story_context=None, manager=None) -> List[dict]:
    """Convenience wrapper: run an effect list with a fresh runner."""
    return EffectRunner(manager, story_context).run(effects, story_context)


# -- built-in effects ------------------------------------------------------------
# Each handler raises ValueError with a human-readable message on failure; the
# runner turns that into a logged, per-effect error result.


def _effect_name(args: dict) -> str:
    return args.get("npc") or args.get("name") or ""


def _find_location(manager, name: str):
    if not name:
        raise ValueError("a location name is required")
    location = manager.story.find_location(name)
    if location is None:
        # story.find_location is case-sensitive; match like StoryManager._find_location
        lower = name.lower()
        location = next((loc for loc in manager.story.locations.values() if loc.name.lower() == lower), None)
    if location is None:
        raise ValueError("location '%s' not found" % name)
    return location


def _zone_name_for(manager, location) -> str:
    zone = manager.story.find_zone(location.name)
    if zone is None:
        raise ValueError("location '%s' is not in any zone" % location.name)
    return zone.name


@scenario.register_effect("add_item")
def _effect_add_item(runner: EffectRunner, args: dict) -> None:
    """{"effect": "add_item", "item": "brass key", "to": "player"|npc|location}

    The item is a catalogue template referenced by name (loaded fresh via
    load_item, like spawn_item) or, when unknown to the catalogue, a plain
    ad-hoc item with that name."""
    manager = runner.manager
    item = args.get("item")
    to = args.get("to", "player")
    if isinstance(item, dict):
        ok, error = manager.give_item(item.get("name", ""), to, item_def=item)
    else:
        ok, error = manager.give_item(item or "", to)
    if not ok:
        raise ValueError(error)


@scenario.register_effect("remove_item")
def _effect_remove_item(runner: EffectRunner, args: dict) -> None:
    """{"effect": "remove_item", "item": "brass key", "from": "player"|npc|location}

    The holder key may be given as "from" (the alias) or "frm" (the field
    name); both validate, so accept either."""
    frm = args.get("from") or args.get("frm") or "player"
    ok, error = runner.manager.remove_item_from(args.get("item", ""), frm)
    if not ok:
        raise ValueError(error)


@scenario.register_effect("spawn_npc")
def _effect_spawn_npc(runner: EffectRunner, args: dict) -> None:
    """{"effect": "spawn_npc", "npc": "giant rat", "at": "cellar"}

    Spawns a catalogue creature (case-insensitive name lookup) into a location,
    reusing StoryManager.spawn_npc."""
    manager = runner.manager
    name = _effect_name(args)
    location = _find_location(manager, args.get("at", ""))
    creature = next((c for c in manager.story.catalogue.get_creatures()
                     if c.get("name", "").lower() == name.lower()), None)
    if creature is None:
        raise ValueError("unknown creature '%s' (not in the catalogue)" % name)
    if not manager.spawn_npc(creature["name"], _zone_name_for(manager, location), location.name):
        raise ValueError("failed to spawn '%s' at '%s'" % (name, location.name))


@scenario.register_effect("move_npc")
def _effect_move_npc(runner: EffectRunner, args: dict) -> None:
    """{"effect": "move_npc", "npc": "Mrs. Corbin", "to": "cellar"}; reuses StoryManager.move_npc."""
    manager = runner.manager
    location = _find_location(manager, args.get("to", ""))
    ok, error = manager.move_npc(_effect_name(args), _zone_name_for(manager, location), location.name)
    if not ok:
        raise ValueError(error)


@scenario.register_effect("remove_npc")
def _effect_remove_npc(runner: EffectRunner, args: dict) -> None:
    """{"effect": "remove_npc", "npc": "Mrs. Corbin"}; removes the NPC from its location and the world store."""
    ok, error = runner.manager.remove_world_npc(_effect_name(args))
    if not ok:
        raise ValueError(error)


@scenario.register_effect("set_goal")
def _effect_set_goal(runner: EffectRunner, args: dict) -> None:
    """{"effect": "set_goal", "npc": "Mrs. Corbin", "goal": "..."}; reuses StoryManager.set_npc_goal."""
    ok, error = runner.manager.set_npc_goal(_effect_name(args), args.get("goal", ""))
    if not ok:
        raise ValueError(error)


@scenario.register_effect("set_description")
def _effect_set_description(runner: EffectRunner, args: dict) -> None:
    """{"effect": "set_description", "location": "cellar", "description": "..."}
    ("at" also accepted for the location); reuses StoryManager.set_location_description."""
    manager = runner.manager
    description = args.get("description", "")
    if not description:
        raise ValueError("description must be a non-empty string")
    location = _find_location(manager, args.get("location") or args.get("at") or "")
    ok, error = manager.set_location_description(_zone_name_for(manager, location), location.name, description)
    if not ok:
        raise ValueError(error)
    location.built = True  # the LLM must not generate its own description over the authored one
