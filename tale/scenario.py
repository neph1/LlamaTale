"""
Scenario beats: the data model for beat-based story progression.

A beat is the unit of story progression: a description that enters the LLM
context, a status, and (from this phase on) a list of code-verifiable goals.
Goal satisfaction is decided by typed world events published on the
"story-events" pubsub topic at the call sites where something goal-relevant
happens (quest completed, dialogue exchanged, NPC killed); the LLM never
judges whether a beat is complete. This module holds the data model (Beat,
BeatStatus, Goal, Effect), the effect vocabulary and registry, and the typed
event vocabulary; the progression logic lives in tale/story_context.py for now
and will grow into the full Scenario engine in later phases. Beat boundary
effects (on_start/on_end/on_fail) are executed by tale/effects.py.
"""
from enum import IntEnum
from typing import Callable, Dict, List, Literal, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError

from tale import pubsub


class BeatStatus(IntEnum):
    LOCKED = 0      # not yet reached
    ACTIVE = 1      # the beat the story is currently in
    COMPLETED = 2
    FAILED = 3      # reserved; nothing sets it yet

    def __str__(self):
        return self.name.lower()


# -- typed world events --------------------------------------------------------
# The driver publishes these on the "story-events" pubsub topic at the existing
# call sites. StoryContext subscribes (see tale/story_context.py) and matches
# them against the goals of the beats. The wiretap layer stays text-only and
# is unaffected.

STORY_EVENTS_TOPIC = "story-events"


class StoryEvent:
    """Base class for typed world events. `kind` is the discriminator."""
    kind = "event"


class QuestCompleted(StoryEvent):
    """A quest reached QuestStatus.COMPLETED (published from Quest.complete)."""
    kind = "quest_complete"

    def __init__(self, quest: str, giver: str = "", target: str = "") -> None:
        self.quest = quest
        self.giver = giver
        self.target = target


class Interacted(StoryEvent):
    """A dialogue exchange with an NPC occurred (published from LivingNpc.do_say)."""
    kind = "interact"

    def __init__(self, npc: str, speaker: str = "", npc_title: str = "") -> None:
        self.npc = npc
        self.speaker = speaker
        self.npc_title = npc_title


class NpcKilled(StoryEvent):
    """A living died (published from Living.do_on_death)."""
    kind = "kill"

    def __init__(self, npc: str, npc_title: str = "") -> None:
        self.npc = npc
        self.npc_title = npc_title


def story_events_topic() -> pubsub.Topic:
    """The singleton pubsub topic carrying typed story events."""
    return pubsub.topic(STORY_EVENTS_TOPIC)


def publish_story_event(event: StoryEvent) -> None:
    """Publish a typed world event on the story-events topic. Delivery is
    synchronous, so beat transitions happen immediately at the call site
    (and deterministically in tests, without a running driver loop)."""
    story_events_topic().send(event, synchronous=True)


# -- goals ---------------------------------------------------------------------

# Goal types decidable from world events today. visit / have_item / flag land
# in a later phase (they need world-state re-checks, not just events).
GOAL_TYPES = ("quest_complete", "interact", "kill")
GOAL_MATCHES = ("all", "any")


class Goal:
    """A single code-verifiable beat goal: a type plus a target. `satisfied`
    is set only when a matching typed world event is recorded (or restored
    from a save); the LLM never judges satisfaction."""

    def __init__(self, type: str, target: str, satisfied: bool = False) -> None:
        if type not in GOAL_TYPES:
            raise ValueError("unknown goal type %r (known: %s)" % (type, ", ".join(GOAL_TYPES)))
        if not target:
            raise ValueError("goal target must be a non-empty string")
        self.type = type
        self.target = target
        self.satisfied = satisfied

    @property
    def key(self) -> str:
        return "%s:%s" % (self.type, self.target.lower())

    def matches_event(self, event: StoryEvent) -> bool:
        if self.type == "quest_complete" and event.kind == "quest_complete":
            return self.target.lower() == event.quest.lower()
        if self.type == "interact" and event.kind == "interact":
            return self.target.lower() in (event.npc.lower(), event.npc_title.lower())
        if self.type == "kill" and event.kind == "kill":
            return self.target.lower() in (event.npc.lower(), event.npc_title.lower())
        return False

    def to_json(self) -> dict:
        return {"type": self.type,
                "target": self.target,
                "satisfied": self.satisfied}

    @classmethod
    def from_json(cls, data: dict) -> "Goal":
        if not isinstance(data, dict) or "type" not in data or "target" not in data:
            raise ValueError("each goal needs a 'type' and a 'target' key: %r" % (data,))
        return cls(type=data["type"], target=data["target"], satisfied=data.get("satisfied", False))

    def __repr__(self) -> str:
        return "Goal(type=%r, target=%r, satisfied=%r)" % (self.type, self.target, self.satisfied)


# -- effects -------------------------------------------------------------------
# Beat boundary effects (on_start / on_end / on_fail) are declarative dicts with
# an "effect" discriminator. JSON scenarios are restricted to the built-in
# vocabulary below (EFFECT_MODELS validates each entry's arguments); code-defined
# stories can register additional effects with @register_effect. Execution lives
# in tale/effects.py (EffectRunner), which maps the built-ins onto the existing
# StoryManager operations.


class _EffectModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AddItemEffect(_EffectModel):
    """{"effect": "add_item", "item": "brass key", "to": "player"|npc|location}"""
    effect: Literal["add_item"] = "add_item"
    item: str = Field(min_length=1)
    to: str = Field(default="player", min_length=1)


class RemoveItemEffect(_EffectModel):
    """{"effect": "remove_item", "item": "brass key", "from": "player"|npc|location}"""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    effect: Literal["remove_item"] = "remove_item"
    item: str = Field(min_length=1)
    frm: str = Field(default="player", alias="from", min_length=1)


class SpawnNpcEffect(_EffectModel):
    """{"effect": "spawn_npc", "npc": "giant rat", "at": "cellar"} (a catalogue creature)"""
    effect: Literal["spawn_npc"] = "spawn_npc"
    name: str = Field(min_length=1, validation_alias=AliasChoices("npc", "name"))
    at: str = Field(min_length=1)


class MoveNpcEffect(_EffectModel):
    """{"effect": "move_npc", "npc": "Mrs. Corbin", "to": "cellar"}"""
    effect: Literal["move_npc"] = "move_npc"
    name: str = Field(min_length=1, validation_alias=AliasChoices("npc", "name"))
    to: str = Field(min_length=1)


class RemoveNpcEffect(_EffectModel):
    """{"effect": "remove_npc", "npc": "Mrs. Corbin"}"""
    effect: Literal["remove_npc"] = "remove_npc"
    name: str = Field(min_length=1, validation_alias=AliasChoices("npc", "name"))


class SetGoalEffect(_EffectModel):
    """{"effect": "set_goal", "npc": "Mrs. Corbin", "goal": "avoid questions about the cellar"}"""
    effect: Literal["set_goal"] = "set_goal"
    name: str = Field(min_length=1, validation_alias=AliasChoices("npc", "name"))
    goal: str = Field(min_length=1)


EFFECT_MODELS: Dict[str, type] = {
    "add_item": AddItemEffect,
    "remove_item": RemoveItemEffect,
    "spawn_npc": SpawnNpcEffect,
    "move_npc": MoveNpcEffect,
    "remove_npc": RemoveNpcEffect,
    "set_goal": SetGoalEffect,
}

_effect_handlers: Dict[str, Callable] = {}


def register_effect(name: str) -> Callable:
    """Decorator registering a custom effect handler (for code-defined stories).

    The handler is called as ``handler(ctx, args)`` where ``ctx`` is the
    tale.effects.EffectRunner (giving access to the live StoryManager) and
    ``args`` is the effect dict (including the "effect" key). JSON scenarios
    cannot use custom effects: loading rejects effect names that are neither
    built-in nor registered."""
    if not isinstance(name, str) or not name:
        raise ValueError("effect name must be a non-empty string")

    def decorator(func: Callable) -> Callable:
        _effect_handlers[name] = func
        return func
    return decorator


def get_effect_handler(name: str) -> Optional[Callable]:
    """The registered handler for an effect name, or None."""
    return _effect_handlers.get(name)


def known_effects() -> List[str]:
    """All effect names loadable from JSON: the built-in vocabulary plus any
    custom effects registered so far."""
    return sorted(set(EFFECT_MODELS) | set(_effect_handlers))


class Effect:
    """A single declarative beat-boundary effect: an ``effect`` discriminator
    plus its argument dict. ``args`` does not contain the "effect" key;
    :meth:`to_json` adds it back."""

    def __init__(self, effect: str, args: dict = None) -> None:
        if not isinstance(effect, str) or not effect:
            raise ValueError("effect name must be a non-empty string")
        self.effect = effect
        self.args = dict(args) if args else {}

    @classmethod
    def from_json(cls, data: dict) -> "Effect":
        """Validate and wrap an effect dict. Built-in effect names are validated
        against their pydantic model (EFFECT_MODELS); custom names are accepted
        only when a handler was registered with @register_effect; anything else
        is rejected, keeping the JSON vocabulary closed."""
        if not isinstance(data, dict) or not isinstance(data.get("effect"), str) or not data["effect"]:
            raise ValueError("each effect needs an 'effect' key with a non-empty string: %r" % (data,))
        name = data["effect"]
        model = EFFECT_MODELS.get(name)
        if model is not None:
            try:
                model.model_validate(data)
            except ValidationError as exc:
                raise ValueError("invalid '%s' effect %r: %s" % (name, data, exc)) from exc
        elif name not in _effect_handlers:
            raise ValueError("unknown effect %r (known: %s)" % (name, ", ".join(known_effects())))
        return cls(name, {key: value for key, value in data.items() if key != "effect"})

    def to_json(self) -> dict:
        return {"effect": self.effect, **self.args}

    def __repr__(self) -> str:
        return "Effect(%r)" % (self.to_json(),)


def _as_effect_list(effects) -> List[Effect]:
    if effects is None:
        return []
    if not isinstance(effects, list):
        raise ValueError("an effect list must be a list of effect dicts: %r" % (effects,))
    return [effect if isinstance(effect, Effect) else Effect.from_json(effect) for effect in effects]


class Beat:
    """A single story beat: an id, the description that enters the LLM
    context while the beat is active, its status, and the goals that
    complete it. `match` is "all" (default) or "any" over the goals.

    A beat with an empty goals list does not complete on its own in this
    phase (beats are advanced manually or by the previous beat completing);
    auto-completing staging beats arrive with the full DAG engine."""

    def __init__(self, id: str, description: str = "", status: BeatStatus = BeatStatus.LOCKED,
                 goals: List[Goal] = None, match: str = "all",
                 on_start: list = None, on_end: list = None, on_fail: list = None) -> None:
        if match not in GOAL_MATCHES:
            raise ValueError("beat match must be one of %s, got %r" % (GOAL_MATCHES, match))
        self.id = id
        self.description = description
        self.status = status
        self.goals = list(goals) if goals else []
        self.match = match
        self.on_start = _as_effect_list(on_start)
        self.on_end = _as_effect_list(on_end)
        self.on_fail = _as_effect_list(on_fail)
        self._effects_run = set()  # type: set  # boundaries already executed; runtime only, not serialized

    def record_event(self, event: StoryEvent) -> bool:
        """Mark every goal the event satisfies; return True if the beat's
        goals now match ("all"/"any"). Goal-less beats never match."""
        for goal in self.goals:
            if not goal.satisfied and goal.matches_event(event):
                goal.satisfied = True
        return self.goals_match()

    def goals_match(self) -> bool:
        if not self.goals:
            return False
        if self.match == "any":
            return any(goal.satisfied for goal in self.goals)
        return all(goal.satisfied for goal in self.goals)

    def to_json(self) -> dict:
        return {"id": self.id,
                "description": self.description,
                "status": str(self.status),
                "match": self.match,
                "goals": [goal.to_json() for goal in self.goals],
                "on_start": [effect.to_json() for effect in self.on_start],
                "on_end": [effect.to_json() for effect in self.on_end],
                "on_fail": [effect.to_json() for effect in self.on_fail]}

    @classmethod
    def from_json(cls, data: dict) -> "Beat":
        status = data.get("status", "locked")
        if not isinstance(status, BeatStatus):
            status = BeatStatus[str(status).upper()]
        goals = [Goal.from_json(goal) for goal in data.get("goals", [])]
        return cls(id=data["id"],
                   description=data.get("description", ""),
                   status=status,
                   goals=goals,
                   match=data.get("match", "all"),
                   on_start=data.get("on_start"),
                   on_end=data.get("on_end"),
                   on_fail=data.get("on_fail"))

    def __repr__(self) -> str:
        return "Beat(id=%r, status=%s, description=%r, goals=%r)" % (self.id, self.status, self.description, self.goals)


def validate_beats(beats: List[Beat]) -> None:
    """Validate authored beats: ids must be non-empty and unique."""
    ids = set()
    for beat in beats:
        if not beat.id:
            raise ValueError("beat id must be a non-empty string")
        if beat.id in ids:
            raise ValueError("duplicate beat id: %s" % beat.id)
        ids.add(beat.id)


def load_beats(data: list) -> List[Beat]:
    """Load authored beats from their JSON representation (a list of dicts
    with at least an 'id' and a 'description' key; optional 'status',
    'match' and 'goals'). Raises ValueError on invalid input."""
    beats = []  # type: List[Beat]
    for entry in data:
        if not isinstance(entry, dict) or "id" not in entry or "description" not in entry:
            raise ValueError("each beat needs an 'id' and a 'description' key: %r" % (entry,))
        goals = entry.get("goals", [])
        if not isinstance(goals, list):
            raise ValueError("beat 'goals' must be a list: %r" % (goals,))
        beats.append(Beat.from_json(entry))
    validate_beats(beats)
    return beats
