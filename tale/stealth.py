"""Stealth system: hide stance, location concealment, and passive perception.

Detection of hidden livings is always resolved by a contested dice roll
(``resolve_contest``); the LLM never decides whether something is seen, it
only narrates the grounded facts the engine injects.

Model (see design spec):
- ``hide`` enters a persistent stance (``Living.hidden``), not a one-shot action.
- ``Location.concealment`` is an integer tier (0-4) modifying stealth throws.
- ``perception`` is a hidden skill on Livings, rolled by the engine at defined
  moments only (location entry, contested hide, risky actions, search_hidden,
  movement in adjacent locations).
"""

import random
from enum import IntEnum
from typing import List, NamedTuple, Optional, Tuple, TYPE_CHECKING

from tale import lang, mud_context
from tale.skills.skills import SkillType

if TYPE_CHECKING:
    from tale.base import Living, Location


class DetectionBand(IntEnum):
    UNNOTICED = 0   # searcher believes the location empty; no event
    TRACES = 1      # partial: grounded direction/sound hint, no identity
    DETECTED = 2    # full: stance breaks, normal room visibility applies


# Contest band boundaries on a d100-style scale, kept in one place:
#   margin >= TRACES_MARGIN  -> UNNOTICED
#   0 <= margin < TRACES_MARGIN -> TRACES
#   margin < 0 -> DETECTED
TRACES_MARGIN = 20

MAX_CONCEALMENT_TIER = 4
CONCEALMENT_MODIFIER_PER_TIER = 5

SEARCH_BONUS = 25                  # searcher bonus for active search_hidden
TALK_WHILE_HIDDEN_PENALTY = 30     # hider penalty for talking while hidden
SPELL_WHILE_HIDDEN_PENALTY = 20    # hider penalty for casting (non-hide) while hidden
PICK_LOCK_FUMBLE_SEARCH_BONUS = 25  # searcher bonus on a fumbled pick_lock while hidden
REVEAL_SPELL_BONUS = 100           # cast_reveal: near-guaranteed reveal
FIRST_STRIKE_BONUS = 20            # attack bonus for a first strike from hiding
HIDDEN_ACTION_AP_SURCHARGE = 1     # extra AP cost of any action taken while hidden
ADJACENT_NOTICE_SCALE = 5          # perception skill multiplier for adjacent glimpses

_TRACE_FACTS = [
    "You catch a faint movement in the shadows.",
    "You hear a soft rustling nearby.",
    "Something shifts in the corner of your eye.",
    "You hear a quiet scraping sound close by.",
]

_GLIMPSE_FACTS = [
    "You hear footsteps from {direction}.",
    "You glimpse a figure moving to the {direction}.",
    "You catch the flicker of movement from the {direction}.",
]


class DetectionResult(NamedTuple):
    hider: 'Living'
    searcher: 'Living'
    hider_score: int
    searcher_score: int
    margin: int
    band: DetectionBand


def _d100() -> int:
    return random.randint(1, 100)


def clamp_concealment(value: int) -> int:
    return max(0, min(MAX_CONCEALMENT_TIER, int(value)))


def concealment_modifier(location: 'Location') -> int:
    return clamp_concealment(getattr(location, "concealment", 0)) * CONCEALMENT_MODIFIER_PER_TIER


def band_for_margin(margin: int) -> DetectionBand:
    if margin >= TRACES_MARGIN:
        return DetectionBand.UNNOTICED
    if margin >= 0:
        return DetectionBand.TRACES
    return DetectionBand.DETECTED


def roll_contest(hider: 'Living', searcher: 'Living', *, searcher_bonus: int = 0, hider_penalty: int = 0) -> DetectionResult:
    """Contested skill throw: stealth vs perception on a d100 scale.

    hider_score    = stealth throw + concealment(location) - hider_penalty + HIDE skill
    searcher_score = perception throw + searcher_bonus + PERCEPTION skill
    """
    hider_score = _d100() + hider.stats.skills.get(SkillType.HIDE) \
        + concealment_modifier(hider.location) - hider_penalty
    searcher_score = _d100() + searcher.stats.skills.get(SkillType.PERCEPTION) + searcher_bonus
    margin = hider_score - searcher_score
    return DetectionResult(hider, searcher, hider_score, searcher_score, margin, band_for_margin(margin))


def trace_fact() -> str:
    return random.choice(_TRACE_FACTS)


def inject_grounded_fact(living: 'Living', fact: str) -> None:
    """Inject a hard engine fact into an observer's context.

    NPC observers get it in their action context via memory; players get it
    narrated diegetically through the evoke path. Never a raw [hidden] tag.
    """
    memory = getattr(living, "memory", None)
    if memory is not None:
        memory.observe(fact)
    evoke = mud_context.driver is not None and hasattr(living, "rolling_prompt")
    try:
        living.tell(fact, evoke=evoke, short_len=False)
    except Exception:
        living.tell(fact)


def resolve_contest(hider: 'Living', searcher: 'Living', *, searcher_bonus: int = 0, hider_penalty: int = 0) -> DetectionResult:
    """The only path to detection. Applies the engine effect for the band."""
    result = roll_contest(hider, searcher, searcher_bonus=searcher_bonus, hider_penalty=hider_penalty)
    if result.band == DetectionBand.DETECTED:
        hider.hidden = False
        inject_grounded_fact(searcher, "You spot %s hiding here!" % hider.title)
        inject_grounded_fact(hider, "%s spots you hiding!" % lang.capital(searcher.title))
        if hider.location is not None:
            hider.location.tell("%s reveals %s!" % (searcher.title, hider.title), exclude_living=searcher)
    elif result.band == DetectionBand.TRACES:
        inject_grounded_fact(searcher, trace_fact())
    return result


def hide_entry_contest(hider: 'Living') -> Optional[DetectionResult]:
    """Contest entering the hide stance against the best perception in the room.

    Returns None when there are no observers (uncontested), else the best
    (highest margin) contest result among the observers.
    """
    observers = [l for l in hider.location.livings if l is not hider and l.visible and l.alive]
    if not observers:
        return None
    return max((roll_contest(hider, observer) for observer in observers), key=lambda r: r.margin)


def risky_action(hider: 'Living', *, hider_penalty: int = 0, searcher_bonus: int = 0) -> List[DetectionResult]:
    """Immediate contest with every observer when a hidden character does
    something risky (talk, fumbled pick_lock, spellcasting)."""
    results = []  # type: List[DetectionResult]
    if not hider.hidden or hider.location is None:
        return results
    for observer in list(hider.location.livings):
        if observer is hider or not observer.visible or not observer.alive:
            continue
        results.append(resolve_contest(hider, observer, searcher_bonus=searcher_bonus, hider_penalty=hider_penalty))
    return results


def _adjacent_direction(observer_location: 'Location', towards: 'Location') -> str:
    for direction, exit in observer_location.exits.items():
        if exit.target is towards:
            return direction
    return ""


def adjacent_perception(mover: 'Living', source: Optional['Location'], target: 'Location',
                        direction_names=None) -> List[Tuple['Living', str]]:
    """Passive perception for livings in locations adjacent to a movement event.

    Reveals only unhidden movers, and only as a direction/movement fact --
    never identity. A hidden mover is never revealed by this scope.
    """
    results = []  # type: List[Tuple[Living, str]]
    if mover.hidden or not mover.visible:
        return results
    seen = set()  # type: set
    for moved_in in (source, target):
        if moved_in is None:
            continue
        for exit in set(moved_in.exits.values()):
            neighbor = exit.target
            if neighbor is None or neighbor is moved_in or neighbor in (source, target) or id(neighbor) in seen:
                continue
            seen.add(id(neighbor))
            direction = _adjacent_direction(neighbor, moved_in)
            for observer in list(neighbor.livings):
                if observer is mover or not observer.visible or not observer.alive:
                    continue
                roll = _d100()
                if roll <= observer.stats.skills.get(SkillType.PERCEPTION) * ADJACENT_NOTICE_SCALE:
                    if direction:
                        fact = random.choice(_GLIMPSE_FACTS).format(direction=direction)
                    else:
                        fact = "You hear movement nearby."
                    inject_grounded_fact(observer, fact)
                    results.append((observer, fact))
    return results


def on_location_entry(entrant: 'Living', source: Optional['Location'], target: 'Location',
                      direction_names=None) -> List[DetectionResult]:
    """Perception rolls run by the engine when a living enters a location.

    The entering living's perception is rolled against each hidden occupant
    (the hidden occupant sees the entrant normally). If the entrant itself is
    hidden, the visible occupants of the destination contest against it.
    Finally, adjacent locations get a passive perception roll (early warning).
    """
    results = []  # type: List[DetectionResult]
    if target is None:
        return results
    for occupant in list(target.livings):
        if occupant is entrant or not occupant.hidden or not occupant.visible or not occupant.alive:
            continue
        results.append(resolve_contest(occupant, entrant))
    if entrant.hidden and entrant.alive:
        for occupant in list(target.livings):
            if occupant is entrant or not occupant.visible or not occupant.alive:
                continue
            results.append(resolve_contest(entrant, occupant))
    adjacent_perception(entrant, source, target, direction_names)
    return results


def perceive_sweep(observer: 'Living') -> List[str]:
    """Wizard debug: full perception sweep (both scopes) of the observer's
    location and its neighbors. Resolves contests and returns raw outcomes."""
    outcomes = []  # type: List[str]
    location = observer.location
    if location is None:
        return outcomes
    for occupant in list(location.livings):
        if occupant is observer or not occupant.hidden or not occupant.visible:
            continue
        result = resolve_contest(occupant, observer)
        outcomes.append("%s: margin=%d band=%s" % (occupant.name, result.margin, result.band.name))
    for direction, exit in location.exits.items():
        neighbor = exit.target
        if neighbor is None or neighbor is location:
            continue
        for occupant in list(neighbor.livings):
            if occupant is observer or not occupant.visible or not occupant.alive or occupant.hidden:
                continue
            roll = _d100()
            noticed = roll <= observer.stats.skills.get(SkillType.PERCEPTION) * ADJACENT_NOTICE_SCALE
            outcomes.append("%s in %s (%s): roll=%d noticed=%s" % (occupant.name, neighbor.name, direction, roll, noticed))
            if noticed:
                inject_grounded_fact(observer, random.choice(_GLIMPSE_FACTS).format(direction=direction))
    return outcomes


def charge_hidden_action(living: 'Living') -> None:
    """+1 AP surcharge for every action taken while hidden."""
    if living.hidden:
        living.stats.action_points = max(0, living.stats.action_points - HIDDEN_ACTION_AP_SURCHARGE)
