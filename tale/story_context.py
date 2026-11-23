from typing import List, Optional

from tale import pubsub
from tale.scenario import Beat, BeatStatus, STORY_EVENTS_TOPIC, StoryEvent, validate_beats


class StoryContext(pubsub.Listener):
    """Story progression state: a base plot plus a list of beats.

    A story either has authored beats (loaded from the story config) or
    accumulates generated ones as time progresses; there is no third path.

    Beats with goals complete automatically when typed world events
    (tale.scenario.StoryEvent, published on the "story-events" topic)
    satisfy them; subscribe this context to that topic with
    subscribe_events() (StoryManager does this for the live story)."""

    def __init__(self, base_story: str = "") -> None:
        self.base_story = base_story
        self.beats = []  # type: List[Beat]
        self.authored = False  # True when the beats come from the story config, False when generated on the fly
        self.progress = 0.0
        self.length = 10.0
        self.speed = 1.0

    # -- world events ----------------------------------------------------------

    def subscribe_events(self) -> None:
        """Subscribe this context to the typed story-event bus (idempotent:
        a topic keeps a single weakref per listener)."""
        pubsub.topic(STORY_EVENTS_TOPIC).subscribe(self)

    def unsubscribe_events(self) -> None:
        pubsub.topic(STORY_EVENTS_TOPIC).unsubscribe(self)

    def pubsub_event(self, topicname, event) -> None:
        if topicname == STORY_EVENTS_TOPIC and isinstance(event, StoryEvent):
            self.on_story_event(event)

    def on_story_event(self, event: StoryEvent) -> List[str]:
        """Record a typed world event against every beat's goals, then
        complete ACTIVE beats whose goals now match and activate the next
        LOCKED beat, cascading. Returns the ids of the beats completed, in
        definition order."""
        for beat in self.beats:
            beat.record_event(event)
        return self._settle()

    def _settle(self) -> List[str]:
        """While the ACTIVE beat has goals and they are satisfied: mark it
        COMPLETED and activate the next LOCKED beat (definition order).
        Goal-less beats are not auto-completed here; they advance manually.
        Returns the ids of the beats completed, in order."""
        completed = []  # type: List[str]
        while True:
            active = self.active_beat()
            if active is None or not active.goals_match():
                break
            active.status = BeatStatus.COMPLETED
            completed.append(active.id)
            nxt = next((beat for beat in self.beats if beat.status == BeatStatus.LOCKED), None)
            if nxt is None:
                break
            nxt.status = BeatStatus.ACTIVE
        return completed

    # -- beats ---------------------------------------------------------------

    def set_beats(self, beats: List[Beat]) -> None:
        """Install authored beats. Unless statuses were authored explicitly,
        the first beat starts ACTIVE and the rest LOCKED. If the first beat's
        goals are already satisfied, it completes immediately (cascading)."""
        validate_beats(beats)
        self.beats = list(beats)
        self.authored = True
        if self.beats and all(beat.status == BeatStatus.LOCKED for beat in self.beats):
            self.beats[0].status = BeatStatus.ACTIVE
        self._settle()

    def active_beat(self) -> Optional[Beat]:
        for beat in self.beats:
            if beat.status == BeatStatus.ACTIVE:
                return beat
        return None

    def completed_beats(self) -> List[Beat]:
        return [beat for beat in self.beats if beat.status == BeatStatus.COMPLETED]

    def advance_to_next_beat(self) -> Optional[Beat]:
        """Complete the ACTIVE beat and activate the next LOCKED one.
        Returns the new ACTIVE beat, or None if there is no locked beat."""
        nxt = next((beat for beat in self.beats if beat.status == BeatStatus.LOCKED), None)
        if nxt is None:
            return None
        active = self.active_beat()
        if active is not None:
            active.status = BeatStatus.COMPLETED
        nxt.status = BeatStatus.ACTIVE
        self._settle()
        return self.active_beat()

    def set_beat(self, beat_id: str, description: str = "") -> Beat:
        """Activate the beat with the given id; the previously ACTIVE beat
        becomes COMPLETED. If no beat with that id exists, a new beat is
        added and selected. If the activated beat's goals are already
        satisfied it completes immediately and the next beat activates.
        Returns the resulting ACTIVE beat."""
        if not beat_id:
            raise ValueError("beat id must be a non-empty string")
        beat = next((b for b in self.beats if b.id == beat_id), None)
        if beat is not None:
            active = self.active_beat()
            if active is not None and active is not beat:
                active.status = BeatStatus.COMPLETED
            beat.status = BeatStatus.ACTIVE
            self._settle()
            return self.active_beat() or beat
        return self.add_beat(description, id=beat_id)

    def add_beat(self, description: str, id: str = None) -> Beat:
        """Generated stories: complete the ACTIVE beat and append a new ACTIVE
        beat with a generated id "beat-{n}" (or the given id). Returns the new beat."""
        active = self.active_beat()
        if active is not None:
            if active.description:
                active.status = BeatStatus.COMPLETED
            else:
                self.beats.remove(active)
        beat = Beat(id=id or "beat-%d" % len(self.beats), description=description, status=BeatStatus.ACTIVE)
        self.beats.append(beat)
        return beat

    # -- rendering -----------------------------------------------------------

    def to_context(self) -> str:
        active = self.active_beat()
        return f"<story> Base plot: {self.base_story}; Active beat: {active.description if active else ''}</story>"

    def to_context_with_past(self) -> str:
        active = self.active_beat()
        past = ' '.join(beat.description for beat in self.completed_beats()) or 'This is the beginning of the story'
        return f"<story> Base plot: {self.base_story}; Past: {past}; Active beat: {active.description if active else ''}; Progress: {self.progress}/{self.length};</story>"

    # -- serialization ---------------------------------------------------------

    def from_json(self, data: dict) -> 'StoryContext':
        self.base_story = data.get("base_story", "")
        self.progress = data.get("progress", 0.0)
        self.length = data.get("length", 10.0)
        self.speed = data.get("speed", 1.0)
        if "beats" in data:
            self.beats = [Beat.from_json(beat) for beat in data["beats"]]
        else:
            # legacy save migration: current_section/past_sections become beats
            past_sections = data.get("past_sections", [])
            current_section = data.get("current_section", "")
            self.beats = [Beat(id="beat-%d" % i, description=section, status=BeatStatus.COMPLETED)
                          for i, section in enumerate(past_sections)]
            self.beats.append(Beat(id="beat-%d" % len(past_sections), description=current_section, status=BeatStatus.ACTIVE))
        self._settle()
        return self

    def to_json(self) -> dict:
        return {"base_story": self.base_story,
                "beats": [beat.to_json() for beat in self.beats],
                "progress": self.progress,
                "length": self.length,
                "speed": self.speed}
