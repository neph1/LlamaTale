"""
Scenario beats: the data model for beat-based story progression.

A beat is the unit of story progression: a description that enters the LLM
context, plus a status. This module holds only the data model (Beat and
BeatStatus); the progression logic lives in tale/story_context.py for now
and will grow into the full Scenario engine in later phases.
"""
from enum import IntEnum
from typing import List


class BeatStatus(IntEnum):
    LOCKED = 0      # not yet reached
    ACTIVE = 1      # the beat the story is currently in
    COMPLETED = 2
    FAILED = 3      # reserved; nothing sets it yet

    def __str__(self):
        return self.name.lower()


class Beat:
    """A single story beat: an id, the description that enters the LLM
    context while the beat is active, and its status."""

    def __init__(self, id: str, description: str = "", status: BeatStatus = BeatStatus.LOCKED) -> None:
        self.id = id
        self.description = description
        self.status = status

    def to_json(self) -> dict:
        return {"id": self.id,
                "description": self.description,
                "status": str(self.status)}

    @classmethod
    def from_json(cls, data: dict) -> "Beat":
        status = data.get("status", "locked")
        if not isinstance(status, BeatStatus):
            status = BeatStatus[str(status).upper()]
        return cls(id=data["id"],
                   description=data.get("description", ""),
                   status=status)

    def __repr__(self) -> str:
        return "Beat(id=%r, status=%s, description=%r)" % (self.id, self.status, self.description)


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
    with at least an 'id' and a 'description' key). Raises ValueError on
    invalid input."""
    beats = []  # type: List[Beat]
    for entry in data:
        if not isinstance(entry, dict) or "id" not in entry or "description" not in entry:
            raise ValueError("each beat needs an 'id' and a 'description' key: %r" % (entry,))
        beats.append(Beat.from_json(entry))
    validate_beats(beats)
    return beats
