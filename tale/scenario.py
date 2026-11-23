"""
Scenario beats: the data model for beat-based story progression.

A beat is the unit of story progression: a description that enters the LLM
context, a status, and (from this phase on) a list of code-verifiable goals.
Goal satisfaction is decided by typed world events published on the
"story-events" pubsub topic at the call sites where something goal-relevant
happens (quest completed, dialogue exchanged, NPC killed); the LLM never
judges whether a beat is complete. This module holds the data model (Beat,
BeatStatus, Goal) and the typed event vocabulary; the progression logic lives
in tale/story_context.py for now and will grow into the full Scenario engine
in later phases.
"""
from enum import IntEnum
from typing import List

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


class Beat:
    """A single story beat: an id, the description that enters the LLM
    context while the beat is active, its status, and the goals that
    complete it. `match` is "all" (default) or "any" over the goals.

    A beat with an empty goals list does not complete on its own in this
    phase (beats are advanced manually or by the previous beat completing);
    auto-completing staging beats arrive with the full DAG engine."""

    def __init__(self, id: str, description: str = "", status: BeatStatus = BeatStatus.LOCKED,
                 goals: List[Goal] = None, match: str = "all") -> None:
        if match not in GOAL_MATCHES:
            raise ValueError("beat match must be one of %s, got %r" % (GOAL_MATCHES, match))
        self.id = id
        self.description = description
        self.status = status
        self.goals = list(goals) if goals else []
        self.match = match

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
                "goals": [goal.to_json() for goal in self.goals]}

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
                   match=data.get("match", "all"))

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
