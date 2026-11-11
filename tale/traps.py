"""
Trap system: traps can be attached to any MudObject (Location, Item, Container, Door, Living, Exit)
without subclassing. A trap lives in ``obj.story_data["trap"]`` as a plain builtins-only dict,
so it persists through story_data serialization automatically.

Mechanical resolution (skill throw, effect, state change) stays in code; the LLM guidance
strings (``llm_hint``, ``effect_hint``, ``descr``) are passed along as ``extra_context`` on the
narration messages, the same way ``roleplay_prompt`` is used on MudObject.

Traps are data: they can be defined as JSON dicts (see ``trap_from_dict``) so LLM-driven world
building can create them without Python::

    {
      "name": "Snare trap",
      "type": "Trap",
      "trap": {
        "level": 2,
        "trigger": "MOVE",
        "effect": "RESTRAIN",
        "reset": false,
        "hidden": true,
        "llm_hint": "This snare is meant to humiliate, not harm.",
        "effect_hint": "On full effect the target is yanked off their feet."
      }
    }

Guardrails enforced by ``trap_from_dict``/``attach``: level is clamped to 1..10, ``effect``
must be a known effect name, ``trigger`` must be valid for the target object type
(e.g. no ENTER trap on a potion). Malformed traps are rejected here, not at trigger time.

'Tale' mud driver, mudlib and interactive fiction framework
"""

import random
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, cast

from . import lang, pubsub
from .base import Container, Door, Item, Living, Location, MudObject, ParseResult
from .errors import ActionRefused
from .skills.magic import MagicType
from .skills.skills import SkillType


__all__ = ["TrapState", "TrapTrigger", "TrapOutcome", "Trap", "TrapItem",
           "attach", "get", "remove", "resolve", "disarm", "search_reveal",
           "trigger_enter", "trigger_open", "trigger_move", "handle_touch", "tick_restrain",
           "trap_from_dict", "dodge_roll", "band_for_roll",
           "EFFECT_DAMAGE", "EFFECT_RESTRAIN", "EFFECT_HOBBLE", "EFFECT_DOOR", "EFFECT_ALARM", "EFFECT_SPELL",
           "VALID_EFFECTS"]


class TrapState(IntEnum):
    ARMED = 1
    REVEALED = 2     # noticed, but still dangerous
    SPRUNG = 3       # triggered, one-shot traps end here
    DISARMED = 4     # harmless, may be salvageable


class TrapTrigger(IntEnum):
    ENTER = 1        # living enters the location
    OPEN = 2         # container or door opened
    MOVE = 3         # item picked up / moved
    TOUCH = 4        # custom verb via handle_verb


class TrapOutcome(IntEnum):
    ESCAPE = 1       # roll > 10: clean escape, trap stays armed
    PARTIAL = 2      # roll 1..10: triggers at reduced effect, revealed
    FULL = 3         # roll -10..0: full effect
    COMPLICATION = 4 # roll < -10: full effect plus a complication the LLM narrates


EFFECT_DAMAGE = "DAMAGE"
EFFECT_RESTRAIN = "RESTRAIN"
EFFECT_HOBBLE = "HOBBLE"
EFFECT_DOOR = "DOOR"
EFFECT_ALARM = "ALARM"
EFFECT_SPELL = "SPELL"

VALID_EFFECTS = frozenset({EFFECT_DAMAGE, EFFECT_RESTRAIN, EFFECT_HOBBLE, EFFECT_DOOR, EFFECT_ALARM, EFFECT_SPELL})

TRAP_KEY = "trap"


@dataclass
class Trap:
    level: int                      # 1..10
    trigger: TrapTrigger
    effect: str                     # effect type name, see VALID_EFFECTS
    effect_params: Dict[str, Any] = field(default_factory=dict)
    state: TrapState = TrapState.ARMED
    reset: bool = False             # True = re-arms after SPRUNG (gas, spikes)
    owner: str = ""                 # setter's name; owner never triggers it
    hidden: bool = True             # needs SEARCH to notice
    # LLM guidance
    descr: str = ""                 # physical description when examined
    llm_hint: str = ""              # tone and intent for the LLM
    effect_hint: str = ""           # how to narrate each outcome band

    def to_json(self) -> dict:
        return {
            "level": self.level,
            "trigger": self.trigger.name,
            "effect": self.effect.upper(),
            "effect_params": dict(self.effect_params),
            "state": self.state.name,
            "reset": self.reset,
            "owner": self.owner,
            "hidden": self.hidden,
            "descr": self.descr,
            "llm_hint": self.llm_hint,
            "effect_hint": self.effect_hint,
        }

    @classmethod
    def from_json(cls, data: dict) -> 'Trap':
        if not isinstance(data, dict):
            raise ValueError("trap data must be a dict")
        try:
            trigger = TrapTrigger[str(data.get("trigger", "")).upper()]
        except KeyError:
            raise ValueError("unknown trap trigger: %r" % data.get("trigger"))
        try:
            state = TrapState[str(data.get("state", "ARMED")).upper()]
        except KeyError:
            raise ValueError("unknown trap state: %r" % data.get("state"))
        effect = str(data.get("effect", "")).upper()
        if effect not in VALID_EFFECTS:
            raise ValueError("unknown trap effect: %r" % data.get("effect"))
        effect_params = data.get("effect_params", {})
        if not isinstance(effect_params, dict):
            raise ValueError("trap effect_params must be a dict")
        level = int(data.get("level", 1))
        return cls(level=level, trigger=trigger, effect=effect, effect_params=dict(effect_params),
                   state=state, reset=bool(data.get("reset", False)), owner=str(data.get("owner", "")),
                   hidden=bool(data.get("hidden", True)), descr=str(data.get("descr", "")),
                   llm_hint=str(data.get("llm_hint", "")), effect_hint=str(data.get("effect_hint", "")))


class TrapItem(Item):
    """
    A trap as a hidden/visible physical item (beartrap, tripwire, poison needle) placed in a location.
    Shares the same Trap dataclass and resolution logic (stored in story_data like any other object),
    but is searchable, takeable and re-placeable by players.
    """

    @property
    def trap(self) -> Optional[Trap]:
        return get(self)

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        trap = get(self)
        if trap is not None:
            d["type"] = "Trap"
            d["trap"] = trap.to_json()
        return d


def _check_trigger_for_object(obj: MudObject, trigger: TrapTrigger) -> None:
    if trigger == TrapTrigger.ENTER:
        valid = isinstance(obj, Location)
    elif trigger == TrapTrigger.OPEN:
        valid = isinstance(obj, (Container, Door))
    elif trigger == TrapTrigger.MOVE:
        valid = isinstance(obj, Item)
    else:  # TOUCH works on any object via the verbs/handle_verb pattern
        valid = True
    if not valid:
        raise ValueError("trigger %s is not valid for %s" % (trigger.name, obj.__class__.__name__))


def trap_from_dict(data: dict, obj: Optional[MudObject] = None) -> Trap:
    """
    Validate a JSON trap dict and return a Trap. Raises ValueError on malformed input,
    so LLM-generated content is rejected at load time instead of crashing at trigger time.
    Level is clamped to 1..10. If obj is given, the trigger is checked against the object type.
    """
    trap = Trap.from_json(data)
    trap.level = max(1, min(10, trap.level))
    if trap.effect == EFFECT_SPELL:
        spell = str(trap.effect_params.get("spell", "")).upper()
        if spell not in MagicType.__members__:
            raise ValueError("unknown spell in trap effect_params: %r" % trap.effect_params.get("spell"))
        trap.effect_params["spell"] = spell
    if obj is not None:
        _check_trigger_for_object(obj, trap.trigger)
    return trap


def attach(obj: MudObject, trap: Any) -> Trap:
    """Validate and store a trap on any MudObject (in obj.story_data["trap"])."""
    if not isinstance(trap, Trap):
        trap = trap_from_dict(trap, obj)
    else:
        trap.level = max(1, min(10, trap.level))
        if trap.effect.upper() not in VALID_EFFECTS:
            raise ValueError("unknown trap effect: %r" % trap.effect)
        _check_trigger_for_object(obj, trap.trigger)
    obj.story_data[TRAP_KEY] = trap.to_json()
    return trap


def get(obj: MudObject) -> Optional[Trap]:
    """Return the trap attached to obj, or None."""
    data = obj.story_data.get(TRAP_KEY)
    if not data:
        return None
    return Trap.from_json(data)


def remove(obj: MudObject) -> None:
    obj.story_data.pop(TRAP_KEY, None)


def _set(obj: MudObject, trap: Trap) -> None:
    obj.story_data[TRAP_KEY] = trap.to_json()


def dodge_roll(target: Living, trap: Trap) -> int:
    """Skill throw following the spell idiom: randint(1, 100) + skill - difficulty."""
    difficulty = trap.level * 10
    return random.randint(1, 100) + target.stats.skills.get(SkillType.DODGE) - difficulty


def band_for_roll(roll: int) -> TrapOutcome:
    if roll > 10:
        return TrapOutcome.ESCAPE
    if roll >= 1:
        return TrapOutcome.PARTIAL
    if roll >= -10:
        return TrapOutcome.FULL
    return TrapOutcome.COMPLICATION


def _guidance(trap: Trap, outcome: TrapOutcome) -> str:
    return ("Trap effect: %s (level %d), outcome band: %s. llm_hint: %s effect_hint: %s"
            % (trap.effect, trap.level, outcome.name, trap.llm_hint, trap.effect_hint))


def _announce(target: Living, message: str, guidance: str) -> None:
    if target.location:
        target.location.tell(message, exclude_living=target, evoke=True, short_len=True, extra_context=guidance)


def resolve(obj: MudObject, target: Living, ctx=None) -> Optional[TrapOutcome]:
    """
    Run the dodge throw for obj's trap against target, apply the effect and narrate.
    Returns the outcome band, or None if the trap didn't fire (no trap, disarmed/sprung,
    or the target is the owner).
    """
    trap = get(obj)
    if trap is None or trap.state not in (TrapState.ARMED, TrapState.REVEALED):
        return None
    if trap.owner and target.name == trap.owner:
        return None  # the owner never triggers their own trap
    roll = dodge_roll(target, trap)
    outcome = band_for_roll(roll)
    guidance = _guidance(trap, outcome)
    if outcome == TrapOutcome.ESCAPE:
        # clean escape: trap stays armed, target (mostly) unaware; optional near-miss hint
        target.tell("You get a prickly feeling that you just avoided something.", evoke=False, short_len=True)
        return outcome
    _apply_effect(trap, obj, target, outcome)
    if outcome == TrapOutcome.PARTIAL:
        trap.state = TrapState.REVEALED  # triggered at reduced effect, but revealed
    else:
        trap.state = TrapState.SPRUNG
    _set(obj, trap)
    return outcome


def _apply_effect(trap: Trap, obj: MudObject, target: Living, outcome: TrapOutcome) -> None:
    """Mechanical effect dispatch. Narration strings go to the LLM via extra_context."""
    guidance = _guidance(trap, outcome)
    partial = outcome == TrapOutcome.PARTIAL
    effect = trap.effect.upper()
    params = trap.effect_params

    if effect == EFFECT_DAMAGE:
        if partial:
            damage = random.randint(1, max(1, trap.level // 2))
        else:
            damage = random.randint(1, trap.level)
        target.stats.hp -= damage
        target.tell("The trap springs on you! You take %d damage." % damage, evoke=True, extra_context=guidance)
        _announce(target, "%s triggers a trap!" % lang.capital(target.title), guidance)
    elif effect == EFFECT_RESTRAIN:
        ticks = int(params.get("ticks", 3))
        if partial:
            ticks = max(1, ticks // 2)
        elif outcome == TrapOutcome.COMPLICATION:
            ticks += 2
        target.stats.action_points = 0
        target.story_data["restrained"] = {"ticks": ticks, "trap_level": trap.level}
        target.tell("The trap restrains you! You can't move.", evoke=True, extra_context=guidance)
        _announce(target, "%s is caught in a trap!" % lang.capital(target.title), guidance)
    elif effect == EFFECT_HOBBLE:
        drain = max(1, trap.level // 2) if partial else trap.level
        target.stats.action_points = max(0, target.stats.action_points - drain)
        target.tell("The trap hobbles you, draining %d action points." % drain, evoke=True, extra_context=guidance)
        _announce(target, "%s is slowed by a trap!" % lang.capital(target.title), guidance)
    elif effect == EFFECT_DOOR:
        _effect_door(trap, target, guidance)
    elif effect == EFFECT_ALARM:
        _effect_alarm(trap, target, guidance)
    elif effect == EFFECT_SPELL:
        _effect_spell(trap, target, outcome, guidance)


def _effect_door(trap: Trap, target: Living, guidance: str) -> None:
    """Close (and optionally lock) door(s) on the target's location: one-shot area denial."""
    loc = target.location
    if loc is None:
        return
    direction = trap.effect_params.get("direction")
    lock = bool(trap.effect_params.get("lock", True))
    exits = []
    if direction and direction in loc.exits:
        exits = [cast(Door, loc.exits[direction])]
    else:
        exits = [cast(Door, e) for e in set(loc.exits.values()) if isinstance(e, Door)]
    if not exits:
        return
    for door in exits:
        door.opened = False
        if lock:
            door.locked = True
        if door.linked_door:
            door.linked_door.opened = False
            if lock:
                door.linked_door.locked = True
    message = "A mechanism slams the door shut%s!" % (" and locks it" if lock else "")
    target.tell(message, evoke=True, extra_context=guidance)
    _announce(target, message, guidance)


def _effect_alarm(trap: Trap, target: Living, guidance: str) -> None:
    """Sound an alarm: nearby locations hear it, the owner gets a pubsub message."""
    loc = target.location
    message = str(trap.effect_params.get("message", "A piercing alarm blares!"))
    if loc is not None:
        loc.tell(message, evoke=True, extra_context=guidance)
        loc.message_nearby_locations(message)
    if trap.owner:
        pubsub.topic(("trap-alarm", trap.owner)).send((loc.name if loc else "", message))


def _effect_spell(trap: Trap, target: Living, outcome: TrapOutcome, guidance: str) -> None:
    """
    Activate a spell on the trap's target. The trap paid at craft time, so the caster
    skill and magic point checks of the regular cast functions are skipped.
    """
    spell = str(trap.effect_params.get("spell", "")).upper()
    level = int(trap.effect_params.get("spell_level", trap.level))
    if outcome == TrapOutcome.PARTIAL:
        level = max(1, level // 2)
    if spell == "BOLT":
        damage = random.randint(1, level)
        target.stats.hp -= damage
        target.tell("The trap casts a bolt of energy at you for %d damage!" % damage, evoke=True, extra_context=guidance)
        _announce(target, "%s is struck by a magical trap!" % lang.capital(target.title), guidance)
    elif spell in ("HEAL", "REJUVENATE"):
        target.stats.replenish_hp(5 * level)
        target.tell("The trap casts a healing spell on you, restoring %d hit points." % (5 * level), evoke=True, extra_context=guidance)
    elif spell == "DRAIN":
        points = random.randint(1, level)
        target.stats.action_points = max(0, target.stats.action_points - points)
        target.stats.magic_points = max(0, target.stats.magic_points - points)
        target.tell("The trap drains %d of your combat and magic points!" % points, evoke=True, extra_context=guidance)
    elif spell == "HIDE":
        target.hidden = True
        target.tell("The trap hides you from view!", evoke=True, extra_context=guidance)
        _announce(target, "%s disappears in a puff of trap magic!" % lang.capital(target.title), guidance)
    elif spell == "REVEAL":
        if target.location:
            for living in target.location.livings:
                if living != target and living.hidden:
                    living.hidden = False
                    target.tell("The trap reveals %s." % living.title, evoke=True, extra_context=guidance)
    else:
        raise ActionRefused("The trap's spell %s is not supported." % spell)


def search_reveal(searcher: Living, silent: bool = False) -> List[MudObject]:
    """
    SEARCH throw against every hidden ARMED trap in scope (location first, then its items,
    then its exits). On success the trap becomes REVEALED and gets an extra_desc entry.
    Returns the list of objects whose trap was revealed.
    """
    loc = searcher.location
    if loc is None:
        return []
    if silent:
        skill_value = searcher.stats.perception * 5
    else:
        skill_value = searcher.stats.skills.get(SkillType.SEARCH)
    found = []  # type: List[MudObject]
    candidates = [loc] + sorted(loc.items, key=lambda i: i.name) + list(set(loc.exits.values()))  # type: List[MudObject]
    for obj in candidates:
        trap = get(obj)
        if trap is None or not trap.hidden or trap.state != TrapState.ARMED:
            continue
        roll = random.randint(1, 100) + skill_value - trap.level * 10
        if roll >= 1:  # same throw as the dodge roll: a high roll beats the trap's difficulty
            trap.state = TrapState.REVEALED
            _set(obj, trap)
            obj.add_extradesc({"trap"}, trap.descr or "Something dangerous is hidden here.")
            found.append(obj)
    return found


def disarm(obj: MudObject, actor: Living, ctx=None) -> str:
    """
    DISARM_TRAP throw against the trap's difficulty (level * 10).
    Success: DISARMED. Failure: 50% chance the trap springs at full effect, otherwise it
    stays REVEALED. The owner is exempt from springing their own trap on a failed disarm.
    Returns "disarmed", "sprung" or "failed".
    """
    trap = get(obj)
    if trap is None or (trap.hidden and trap.state == TrapState.ARMED):
        raise ActionRefused("You don't see any trap here.")
    if trap.state == TrapState.DISARMED:
        raise ActionRefused("That trap is already disarmed.")
    if trap.state == TrapState.SPRUNG:
        raise ActionRefused("That trap has already sprung.")
    roll = random.randint(1, 100) + actor.stats.skills.get(SkillType.DISARM_TRAP) - trap.level * 10
    if roll >= 1:
        trap.state = TrapState.DISARMED
        _set(obj, trap)
        actor.tell("You carefully disarm the trap.", evoke=True)
        if not actor.hidden and actor.location:
            actor.location.tell("%s disarms a trap." % lang.capital(actor.title), exclude_living=actor, evoke=True, short_len=True)
        return "disarmed"
    if actor.name == trap.owner:
        actor.tell("You fail to disarm your own trap, but it doesn't spring on you.", evoke=True, short_len=True)
        return "failed"
    if random.randint(1, 100) <= 50:
        trap.state = TrapState.SPRUNG
        _set(obj, trap)
        _apply_effect(trap, obj, actor, TrapOutcome.FULL)
        actor.tell("Your clumsy fingers set the trap off!", evoke=True, extra_context=_guidance(trap, TrapOutcome.FULL))
        return "sprung"
    actor.tell("You fail to disarm the trap. It is still dangerous.", evoke=True, short_len=True)
    return "failed"


def tick_restrain(living: Living) -> None:
    """One escape attempt per round for a restrained living: DODGE vs trap level * 10."""
    marker = living.story_data.get("restrained")
    if not isinstance(marker, dict):
        return
    trap_level = int(marker.get("trap_level", 1))
    roll = random.randint(1, 100) + living.stats.skills.get(SkillType.DODGE) - trap_level * 10
    marker["ticks"] = int(marker.get("ticks", 1)) - 1
    if roll >= 1 or marker["ticks"] <= 0:  # escape throw: high roll breaks free
        del living.story_data["restrained"]
        living.tell("You break free of the trap!", evoke=True)
        if living.location:
            living.location.tell("%s breaks free of a trap!" % lang.capital(living.title), exclude_living=living, evoke=True, short_len=True)
    else:
        living.stats.action_points = 0
        living.story_data["restrained"] = marker
        living.tell("You struggle against the trap, but stay caught.", evoke=False, short_len=True)


def _fire(obj: MudObject, target: Living, ctx=None) -> Optional[TrapOutcome]:
    trap = get(obj)
    if trap is None:
        return None
    if trap.state == TrapState.SPRUNG and trap.reset:
        trap.state = TrapState.ARMED  # reset traps re-arm on the next trigger opportunity
        _set(obj, trap)
    return resolve(obj, target, ctx)


def trigger_enter(location: Location, living: Living, ctx=None) -> Optional[TrapOutcome]:
    """ENTER hook: called from Location.notify_player_arrived / notify_npc_arrived."""
    trap = get(location)
    if trap is not None and trap.trigger == TrapTrigger.ENTER:
        return _fire(location, living, ctx)
    return None


def trigger_open(obj: MudObject, actor: Living, ctx=None) -> Optional[TrapOutcome]:
    """OPEN hook: called from Boxlike.open / Door.open."""
    trap = get(obj)
    if trap is not None and trap.trigger == TrapTrigger.OPEN:
        return _fire(obj, actor, ctx)
    return None


def trigger_move(item: Item, actor: Optional[Living], ctx=None) -> Optional[TrapOutcome]:
    """MOVE hook: called from Item.notify_moved."""
    if actor is None:
        return None
    trap = get(item)
    if trap is not None and trap.trigger == TrapTrigger.MOVE:
        return _fire(item, actor, ctx)
    return None


def handle_touch(obj: MudObject, parsed: ParseResult, actor: Living) -> bool:
    """TOUCH hook: custom verb via the verbs dict / handle_verb pattern (Catapult pattern)."""
    trap = get(obj)
    if trap is not None and trap.trigger == TrapTrigger.TOUCH and parsed.verb in obj.verbs:
        _fire(obj, actor)
        return True
    return False
